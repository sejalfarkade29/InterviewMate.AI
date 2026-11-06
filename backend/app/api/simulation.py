import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.practice import PracticeRecord
from app.models.user import User
from app.services import gemini
from app.services.gemini import clamp_int, str_list
from app.services.records import save_record

log = logging.getLogger("interviewmate.simulation")
router = APIRouter(prefix="/simulation", tags=["simulation"])


class ReportIn(BaseModel):
    role: str = Field(default="Software Engineer", max_length=120)
    record_ids: list[int] = Field(min_length=1, max_length=60)


@router.post("/report")
def report(data: ReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recs = db.scalars(select(PracticeRecord).where(PracticeRecord.user_id == user.id, PracticeRecord.id.in_(data.record_ids))).all()
    if not recs:
        raise HTTPException(status_code=404, detail="No answered questions found for this simulation")
    rounds: dict[str, list[int]] = {}
    for r in recs:
        rounds.setdefault((r.meta or {}).get("round") or r.kind or r.module, []).append(r.score)
    per_round = [{"round": k, "questions": len(v), "avg": round(sum(v) / len(v))} for k, v in rounds.items()]
    overall = round(sum(r.score for r in recs) / len(recs))
    out = {"readiness_score": overall, "verdict": "Interview ready" if overall >= 75 else "Almost there" if overall >= 55 else "Needs more practice",
           "summary": f"You answered {len(recs)} questions across {len(per_round)} rounds with an average of {overall}%.", "per_round": per_round,
           "strengths": [f"{p['round']} ({p['avg']}%)" for p in sorted(per_round, key=lambda p: -p["avg"])[:2]],
           "weaknesses": [f"{p['round']} ({p['avg']}%)" for p in sorted(per_round, key=lambda p: p["avg"])[:2] if p["avg"] < 70],
           "next_steps": ["Review the feedback for your lowest round", "Retake the simulation after a week of focused practice"], "source": "offline"}
    if gemini.is_configured():
        digest = "\n".join(f"- [{(r.meta or {}).get('round') or r.kind}] score {r.score}: {r.question[:160]} | answer: {r.answer[:200]} | feedback: {(r.feedback or {}).get('summary', '')[:200]}" for r in recs)[:9000]
        try:
            r = gemini.generate_json(f"""A candidate for "{data.role}" finished a full mock interview simulation. Results:\n{digest}\n
Write a readiness report. Return JSON: {{"readiness_score": 0-100 (consistent with the scores above), "verdict": "Interview ready|Almost there|Needs more practice",
"summary": "3 sentences addressed to the candidate", "strengths": [], "weaknesses": [], "next_steps": [4 concrete actions for the next 2 weeks]}}""", temperature=0.3)
            out.update(readiness_score=clamp_int(r.get("readiness_score"), default=overall), verdict=str(r.get("verdict", out["verdict"]))[:40], summary=str(r.get("summary", out["summary"]))[:800],
                       strengths=str_list(r.get("strengths")) or out["strengths"], weaknesses=str_list(r.get("weaknesses")) or out["weaknesses"],
                       next_steps=str_list(r.get("next_steps")) or out["next_steps"], source="gemini")
        except (gemini.GeminiError, AttributeError, TypeError) as exc:
            log.warning("Simulation report failed: %s", exc)
    rec, reward = save_record(db, user.id, module="simulation", kind="report", topic=data.role[:100], title=f"Simulation report: {data.role[:80]}",
                              question=f"Full simulation for {data.role}", answer=", ".join(f"{p['round']}: {p['avg']}%" for p in per_round), score=out["readiness_score"],
                              feedback={**out, "improvements": out["weaknesses"]}, meta={"record_ids": data.record_ids, "per_round": per_round}, extra_xp=40)
    return {"report": out, "record_id": rec.id, "reward": reward}
