"""Voice interviews.

Primary path: the browser streams microphone audio over a WebSocket to THIS server, which relays it to the
Gemini Live API and streams the interviewer's spoken reply back. The Gemini API key stays on the server.
Fallback path: /voice/turn (text in, text out) used with the browser's own speech recognition + speech synthesis.
"""
import asyncio
import base64
import json
import logging
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.database import session as dbsession
from app.models.practice import Resume
from app.models.user import User
from app.services import banks, interview_ai
from app.services.records import save_record

log = logging.getLogger("interviewmate.voice")
router = APIRouter(prefix="/voice", tags=["voice"])

_SESSIONS: dict[str, dict] = {}     # session id -> config (single-process, expires with the token)
MAX_SESSION_SECONDS = 20 * 60


class SessionIn(BaseModel):
    mode: str = Field(default="voice", pattern="^(voice|hr)$")
    role: str = Field(default="Software Engineer (fresher)", max_length=120)
    style: str = Field(default="neutral", pattern="^(friendly|neutral|strict)$")
    minutes: int = Field(default=10, ge=3, le=20)
    resume_id: int | None = None


class TurnIn(SessionIn):
    history: list[dict] = Field(default_factory=list, max_length=60)
    user_text: str = Field(default="", max_length=3000)


class FeedbackIn(BaseModel):
    mode: str = Field(default="voice", pattern="^(voice|hr)$")
    role: str = Field(default="", max_length=120)
    transcript: list[dict] = Field(max_length=120)
    duration_sec: int = Field(default=0, ge=0, le=7200)


def resume_brief(db: Session, user: User, resume_id: int | None) -> str:
    r = db.get(Resume, resume_id) if resume_id else db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc(), Resume.id.desc()))
    if not r or r.user_id != user.id:
        return ""
    a = r.analysis or {}
    projects = "; ".join(f"{p.get('name')} ({', '.join(p.get('technologies', [])[:4])})" for p in (a.get("projects") or []) if isinstance(p, dict))[:600]
    skills = ", ".join((a.get("skills") or {}).get("technical", [])[:15])
    return f"{a.get('summary', '')} Skills: {skills}. Projects: {projects}"


@router.post("/session")
def create_session(data: SessionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sid = uuid.uuid4().hex
    seeds = [q for q, _ in random.sample(banks.HR_MOST_ASKED, 10)]
    _SESSIONS[sid] = {"user_id": user.id, "mode": data.mode, "role": data.role, "style": data.style, "minutes": data.minutes,
                      "resume": resume_brief(db, user, data.resume_id), "seeds": seeds, "created": time.time()}
    for k in [k for k, v in _SESSIONS.items() if time.time() - v["created"] > 3600]:
        _SESSIONS.pop(k, None)
    token = jwt.encode({"sub": str(user.id), "sid": sid, "scope": "voice", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}, settings.SECRET_KEY, algorithm="HS256")
    return {"token": token, "path": "/api/voice/ws", "live_available": bool(settings.GEMINI_API_KEY)}


@router.post("/turn")
def browser_turn(data: TurnIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = [{"role": "user" if h.get("role") == "user" else "ai", "text": str(h.get("text", ""))[:2000]} for h in data.history]
    reply = interview_ai.interviewer_turn(history, data.user_text, mode=data.mode, role=data.role, style=data.style, minutes=data.minutes,
                                          resume_summary=resume_brief(db, user, data.resume_id))
    return {"reply": reply}


def _save_feedback(db: Session, user_id: int, mode: str, role: str, transcript: list[dict], duration: int, fb: dict) -> dict:
    module = "hr-voice" if mode == "hr" else "voice"
    first_q = next((t["text"] for t in transcript if t.get("role") == "ai"), "Voice interview")
    rec, reward = save_record(db, user_id, module=module, kind=mode, topic=role[:100], title=("HR voice interview" if mode == "hr" else "Voice interview") + f": {role[:60]}",
                              question=first_q[:500], answer="\n".join(f"{'You' if t['role'] == 'user' else 'Interviewer'}: {t['text']}" for t in transcript)[:12000],
                              score=fb.get("overall_score", 0), feedback=fb, meta={"transcript": transcript[:200], "duration_sec": duration, "role": role})
    return {"record_id": rec.id, "reward": reward}


@router.post("/feedback")
def feedback(data: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tr = [{"role": "user" if t.get("role") == "user" else "ai", "text": str(t.get("text", ""))[:3000]} for t in data.transcript]
    fb = interview_ai.voice_feedback(tr, mode=data.mode, role=data.role, duration_sec=data.duration_sec)
    saved = _save_feedback(db, user.id, data.mode, data.role, tr, data.duration_sec, fb) if any(t["role"] == "user" for t in tr) else {}
    return {"feedback": fb, **saved}


# ----------------------------------------------------------------------------- live websocket
def _live_url() -> str:
    sep = "&" if "?" in settings.GEMINI_LIVE_URL else "?"
    return f"{settings.GEMINI_LIVE_URL}{sep}key={settings.GEMINI_API_KEY}"


def _setup_message(model: str, system: str) -> dict:
    return {"setup": {
        "model": f"models/{model}",
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": settings.GEMINI_VOICE}}}},
        "systemInstruction": {"parts": [{"text": system}]},
        "inputAudioTranscription": {}, "outputAudioTranscription": {},
        "contextWindowCompression": {"slidingWindow": {}},
    }}


async def _connect_upstream(system: str):
    import websockets
    last = "unknown error"
    for model in settings.gemini_live_models:
        try:
            up = await websockets.connect(_live_url(), max_size=None, open_timeout=15)
            await up.send(json.dumps(_setup_message(model, system)))
            while True:
                raw = await asyncio.wait_for(up.recv(), 20)
                msg = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                if "setupComplete" in msg:
                    return up, model
        except Exception as exc:  # noqa: BLE001
            last = f"{exc.__class__.__name__}: {str(exc)[:200]}"
            log.warning("Live model %s failed: %s", model, last)
    raise ConnectionError(last)


@router.websocket("/ws")
async def live_socket(ws: WebSocket, token: str = ""):
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert claims.get("scope") == "voice"
        cfg = _SESSIONS.get(claims["sid"])
        assert cfg and cfg["user_id"] == int(claims["sub"])
    except Exception:  # noqa: BLE001
        await ws.close(code=4401)
        return
    await ws.accept()
    if not settings.GEMINI_API_KEY:
        await ws.send_json({"type": "error", "code": "no_key", "message": "GEMINI_API_KEY is not set on the server, so live voice is unavailable."})
        await ws.close()
        return
    system = interview_ai.interviewer_system(cfg["mode"], cfg["role"], cfg["style"], cfg["minutes"], cfg["resume"], cfg["seeds"])
    try:
        upstream, model = await _connect_upstream(system)
    except ConnectionError as exc:
        await ws.send_json({"type": "error", "code": "live_unavailable", "message": f"Could not start the live voice session ({exc}). You can use browser voice mode instead."})
        await ws.close()
        return

    await ws.send_json({"type": "ready", "model": model})
    await upstream.send(json.dumps({"realtimeInput": {"text": "Please begin the interview now."}}))
    transcript: list[dict] = []
    started = time.time()
    state = {"ended": False}

    def add_text(role: str, text: str) -> None:
        if transcript and transcript[-1]["role"] == role and not transcript[-1].get("closed"):
            transcript[-1]["text"] += text
        else:
            transcript.append({"role": role, "text": text})

    def close_turns() -> None:
        for t in transcript:
            t["closed"] = True

    async def from_browser():
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                return
            if msg.get("bytes"):
                await upstream.send(json.dumps({"realtimeInput": {"audio": {"data": base64.b64encode(msg["bytes"]).decode(), "mimeType": "audio/pcm;rate=16000"}}}))
            elif msg.get("text"):
                try:
                    ctrl = json.loads(msg["text"])
                except ValueError:
                    continue
                if ctrl.get("type") == "next":
                    await upstream.send(json.dumps({"realtimeInput": {"text": "Let's move on. Briefly acknowledge, then ask me a NEW question on a different topic."}}))
                elif ctrl.get("type") == "text" and str(ctrl.get("text", "")).strip():
                    await upstream.send(json.dumps({"realtimeInput": {"text": str(ctrl["text"])[:1000]}}))
                elif ctrl.get("type") == "end":
                    state["ended"] = True
                    return

    async def from_gemini():
        async for raw in upstream:
            try:
                msg = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
            except ValueError:
                continue
            sc = msg.get("serverContent")
            if sc:
                for part in (sc.get("modelTurn") or {}).get("parts", []):
                    data = (part.get("inlineData") or {}).get("data")
                    if data:
                        await ws.send_bytes(base64.b64decode(data))
                if (t := (sc.get("inputTranscription") or {}).get("text")):
                    add_text("user", t)
                    await ws.send_json({"type": "transcript", "role": "user", "text": t})
                if (t := (sc.get("outputTranscription") or {}).get("text")):
                    add_text("ai", t)
                    await ws.send_json({"type": "transcript", "role": "ai", "text": t})
                if sc.get("interrupted"):
                    await ws.send_json({"type": "interrupted"})
                if sc.get("turnComplete"):
                    close_turns()
                    await ws.send_json({"type": "turn_complete"})
            if "goAway" in msg:
                await ws.send_json({"type": "notice", "message": "The live session is about to time out."})

    async def watchdog():
        await asyncio.sleep(MAX_SESSION_SECONDS)
        await ws.send_json({"type": "notice", "message": "Maximum session length reached."})
        state["ended"] = True

    tasks = [asyncio.create_task(from_browser()), asyncio.create_task(from_gemini()), asyncio.create_task(watchdog())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except Exception:  # noqa: BLE001
        pass
    for t in tasks:
        t.cancel()
    try:
        await upstream.close()
    except Exception:  # noqa: BLE001
        pass

    clean = [{"role": t["role"], "text": " ".join(t["text"].split())} for t in transcript if t["text"].strip()]
    if state["ended"] or time.time() - started > MAX_SESSION_SECONDS:
        duration = int(time.time() - started)

        def finish() -> dict:
            fb = interview_ai.voice_feedback(clean, mode=cfg["mode"], role=cfg["role"], duration_sec=duration)
            saved = {}
            if any(t["role"] == "user" for t in clean):
                db = dbsession.SessionLocal()
                try:
                    saved = _save_feedback(db, cfg["user_id"], cfg["mode"], cfg["role"], clean, duration, fb)
                finally:
                    db.close()
            return {"type": "feedback", "feedback": fb, "transcript": clean, **saved}
        try:
            await ws.send_json(await run_in_threadpool(finish))
        except Exception:  # noqa: BLE001
            pass
    _SESSIONS.pop(claims["sid"], None)
    try:
        await ws.close()
    except Exception:  # noqa: BLE001
        pass
