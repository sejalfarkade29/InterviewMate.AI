"""Question generation and answer evaluation (Gemini first, offline fallback second)."""
import logging
import random
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.practice import GeneratedQuestion
from app.services import banks, gemini
from app.services.gemini import clamp_int, str_list

log = logging.getLogger("interviewmate.questions")

PRIVATE_KEYS = {"answer_index", "explanation", "ideal_points", "keywords", "tests", "reference_solution"}
LEVEL_NAMES = {1: "beginner", 2: "easy-medium", 3: "medium", 4: "hard", 5: "very hard"}

SYSTEM_QUESTIONS = (
    "You are an expert interviewer who writes realistic, original interview questions for Indian and global campus and "
    "entry-level hiring. Questions must be self-contained, unambiguous, and correct. Never copy text from a specific website. "
    "Return ONLY valid JSON."
)


def public_view(q_id: str, payload: dict) -> dict:
    out = {k: v for k, v in payload.items() if k not in PRIVATE_KEYS}
    out["id"] = q_id
    return out


def recent_questions(db: Session, user_id: int, module: str, limit: int = 25) -> list[str]:
    rows = db.scalars(select(GeneratedQuestion).where(GeneratedQuestion.user_id == user_id, GeneratedQuestion.module == module)
                      .order_by(GeneratedQuestion.created_at.desc()).limit(limit)).all()
    return [str(r.payload.get("question", ""))[:140] for r in rows]


def _store(db: Session, user_id: int, module: str, kind: str, payload: dict) -> str:
    q_id = str(uuid.uuid4())
    db.add(GeneratedQuestion(id=q_id, user_id=user_id, module=module, kind=kind, payload=payload,
                             created_at=datetime.now(timezone.utc).isoformat()))
    db.commit()
    return q_id


def _seen(question: str, avoid: list[str]) -> bool:
    key = re.sub(r"\W+", " ", question.lower())[:100]
    return any(re.sub(r"\W+", " ", a.lower())[:100] == key for a in avoid)


# ------------------------------------------------------------------ generation
def _type_for(module: str, kind: str) -> str:
    return "mcq" if module == "aptitude" or kind in ("aptitude", "logic puzzle") else "text"


def _prompt(module: str, kind: str, topic: str, level: int, avoid: list[str], context: str, qtype: str) -> str:
    avoid_txt = "\n".join(f"- {a}" for a in avoid[:20]) or "- (none)"
    base = (f"Create ONE brand-new {LEVEL_NAMES[level]} interview practice question.\nCategory: {kind or module}\nTopic: {topic}\n"
            f"Random variation seed (use it to pick an unusual angle): {random.randint(1000, 999999)}\n"
            f"Do NOT repeat or paraphrase any of these earlier questions:\n{avoid_txt}\n")
    if context:
        base += f"\nCandidate context (use it to personalise):\n{context[:2500]}\n"
    if qtype == "mcq":
        return base + ('\nReturn JSON: {"topic": str, "difficulty": 1-5, "question": str, "options": [exactly 4 short strings], '
                       '"answer_index": 0-3, "explanation": "step by step working", "hints": [one short hint]}.\n'
                       "Exactly one option must be correct. Verify the arithmetic before answering.")
    if kind == "dsa" or module == "dsa":
        return base + ('\nWrite a data-structures-and-algorithms problem as the interviewer would say it, with a short example and constraints inside "question". '
                       'Return JSON: {"topic": str, "difficulty": 1-5, "question": str, "hints": [2-3 progressive hints], '
                       '"keywords": [key ideas], "ideal_points": [expected approach, time and space complexity], "reference_solution": "concise optimal approach"}.')
    if kind == "hr" or module == "hr":
        return base + ('\nPick a question that is frequently asked in real HR / behavioural rounds (self-introduction, strengths, conflict, failure, leadership, '
                       'why this company, relocation, pressure, ethics...). Prefer the most commonly asked real questions over unusual ones. '
                       'Return JSON: {"topic": "theme such as Conflict", "difficulty": 1-5, "question": str, "hints": [2 short tips], '
                       '"keywords": [words a strong STAR answer would contain], "ideal_points": [4 things a strong answer includes]}.')
    return base + ('\nReturn JSON: {"topic": str, "difficulty": 1-5, "question": str, "hints": [1-2 short hints], '
                   '"keywords": [terms a good answer contains], "ideal_points": [3-5 points of a strong answer]}.\n'
                   "The question must need a written explanation (a few sentences), not a one-word answer.")


def _validate(p: dict, qtype: str) -> dict:
    if not isinstance(p, dict) or not str(p.get("question", "")).strip():
        raise gemini.GeminiError("Question missing")
    out = {"topic": str(p.get("topic", "")).strip()[:100], "difficulty": clamp_int(p.get("difficulty"), 1, 5, 2),
           "question": str(p["question"]).strip(), "hints": str_list(p.get("hints"), 4),
           "keywords": str_list(p.get("keywords"), 12), "ideal_points": str_list(p.get("ideal_points"), 8),
           "reference_solution": str(p.get("reference_solution", ""))[:2000], "explanation": str(p.get("explanation", ""))[:2500]}
    if qtype == "mcq":
        opts = str_list(p.get("options"), 6)
        idx = clamp_int(p.get("answer_index"), 0, 3, -1)
        if len(opts) != 4 or idx < 0:
            raise gemini.GeminiError("Bad MCQ")
        out.update(options=opts, answer_index=idx)
    return out


def _fallback(module: str, kind: str, topic: str, level: int, avoid: list[str]) -> dict:
    which = kind or module
    if which in ("aptitude", "logic puzzle"):
        pool = banks.APTITUDE_FALLBACK
    elif which in ("dsa", "coding"):
        pool = banks.DSA_FALLBACK
    elif which in ("hr", "project / behavioural", "behavioural"):
        pool = [dict(topic=t, difficulty=1, question=q, hints=banks.HR_STAR_POINTS[:2], keywords=["situation", "action", "result", "learn"],
                     ideal_points=banks.HR_STAR_POINTS) for q, t in banks.HR_MOST_ASKED]
    else:
        pool = banks.TECH_FALLBACK
    fresh = [p for p in pool if not _seen(p["question"], avoid)]
    pick = dict(random.choice(fresh or pool))
    return pick


def generate_question(db: Session, user_id: int, module: str, *, kind: str = "", topic: str = "", level: int = 2,
                      context: str = "", prefer_bank: bool = False) -> dict:
    kind = kind or module
    level = max(1, min(5, level))
    avoid = recent_questions(db, user_id, module)
    qtype = _type_for(module, kind)
    topic_pool = {"aptitude": banks.APTITUDE_TOPICS, "technical": banks.TECH_TOPICS, "dsa": banks.DSA_TOPICS}.get(kind, [])
    topic = topic or (random.choice(topic_pool) if topic_pool else "")
    source = "gemini"
    payload: dict | None = None

    # HR: the real, most frequently asked questions come first.
    if kind == "hr" and (prefer_bank or random.random() < 0.7 or not gemini.is_configured()):
        fresh = [(q, t) for q, t in banks.HR_MOST_ASKED if not _seen(q, avoid)]
        if fresh:
            q, t = random.choice(fresh)
            payload = dict(topic=t, difficulty=level, question=q, hints=banks.HR_STAR_POINTS[:2], keywords=["situation", "action", "result", "learn"],
                           ideal_points=banks.HR_STAR_POINTS, reference_solution="", explanation="")
            source = "most-asked"

    if payload is None and gemini.is_configured():
        try:
            payload = _validate(gemini.generate_json(_prompt(module, kind, topic, level, avoid, context, qtype), system=SYSTEM_QUESTIONS, temperature=1.0), qtype)
            if _seen(payload["question"], avoid):
                raise gemini.GeminiError("Repeated question")
        except (gemini.GeminiError, KeyError, TypeError) as exc:
            log.warning("Gemini question failed (%s); using fallback", exc)
            payload = None
    if payload is None:
        fb = _fallback(module, kind, topic, level, avoid)
        payload = {"hints": [], "keywords": [], "ideal_points": [], "reference_solution": "", "explanation": "", **fb}
        payload["difficulty"] = payload.get("difficulty", level)
        source = "offline"

    payload.update(type=qtype, module=module, kind=kind, source=source, topic=payload.get("topic") or topic)
    payload["time_limit_sec"] = 90 if qtype == "mcq" else (600 if kind == "dsa" else 300)
    q_id = _store(db, user_id, module, kind, payload)
    return public_view(q_id, payload)


# ------------------------------------------------------------------ evaluation
SYSTEM_EVAL = (
    "You are a strict but fair interview evaluator. Score honestly: a vague or off-topic answer must score low, a complete and "
    "correct answer high. Speak directly to the candidate ('you'). Return ONLY valid JSON."
)


def _keyword_eval(payload: dict, answer: str) -> dict:
    text = answer.lower()
    kws = payload.get("keywords") or []
    hits = [k for k in kws if k.lower() in text]
    words = len(answer.split())
    length_pts = min(40, words * 0.8)
    kw_pts = 60 * (len(hits) / len(kws)) if kws else min(30, words * 0.4)
    score = clamp_int(length_pts + kw_pts)
    if words < 8:
        score = min(score, 25)
    return {
        "score": score, "verdict": "Offline estimate",
        "summary": "AI evaluation is unavailable, so this score is a rough keyword and length estimate.",
        "strengths": [f"Mentioned: {', '.join(hits)}"] if hits else [],
        "improvements": [f"Cover: {', '.join(k for k in kws if k not in hits)}"] if kws and len(hits) < len(kws) else ["Add more detail and a concrete example"],
        "ideal_answer": " ".join(payload.get("ideal_points") or []) or payload.get("reference_solution", ""),
        "rubric": {}, "extras": {}, "source": "offline",
    }


def evaluate_text(payload: dict, answer: str, *, level_hint: str = "") -> dict:
    kind = payload.get("kind")
    if not gemini.is_configured():
        return _keyword_eval(payload, answer)
    extra = ""
    if kind == "hr":
        extra = ('Judge with the STAR method. Add "extras": {"star": {"situation": 0-100, "task": 0-100, "action": 0-100, "result": 0-100}, "filler_or_vague_phrases": [..]}.')
    elif kind == "dsa":
        extra = ('Judge correctness of the approach, edge cases and complexity. Add "extras": {"correct_approach": true/false, "time_complexity": "...", "space_complexity": "...", "your_stated_complexity_correct": true/false, "edge_cases_missed": [..]}.')
    prompt = (
        f"Question ({payload.get('topic','')}, difficulty {payload.get('difficulty')}): {payload['question']}\n"
        f"Expected key points: {payload.get('ideal_points')}\nKeywords: {payload.get('keywords')}\n"
        f"Reference approach: {payload.get('reference_solution','')}\n\nCandidate answer:\n\"\"\"\n{answer[:6000]}\n\"\"\"\n\n"
        'Return JSON: {"score": 0-100, "verdict": "Excellent|Good|Fair|Needs work", "summary": "2 sentences", '
        '"strengths": [..], "improvements": [specific, actionable], "ideal_answer": "a model answer in under 150 words", '
        '"rubric": {"correctness": 0-100, "depth": 0-100, "clarity": 0-100}, "extras": {}}. ' + extra
    )
    try:
        r = gemini.generate_json(prompt, system=SYSTEM_EVAL, temperature=0.3)
        return {"score": clamp_int(r.get("score")), "verdict": str(r.get("verdict", ""))[:30], "summary": str(r.get("summary", ""))[:600],
                "strengths": str_list(r.get("strengths")), "improvements": str_list(r.get("improvements")),
                "ideal_answer": str(r.get("ideal_answer", ""))[:2500],
                "rubric": {str(k): clamp_int(v) for k, v in (r.get("rubric") or {}).items()} if isinstance(r.get("rubric"), dict) else {},
                "extras": r.get("extras") if isinstance(r.get("extras"), dict) else {}, "source": "gemini"}
    except (gemini.GeminiError, AttributeError, TypeError) as exc:
        log.warning("Gemini evaluation failed (%s); using keyword fallback", exc)
        return _keyword_eval(payload, answer)


def evaluate_mcq(payload: dict, choice: int) -> dict:
    correct = int(payload.get("answer_index", -1))
    ok = choice == correct
    opts = payload.get("options", [])
    return {
        "score": 100 if ok else 0, "verdict": "Correct" if ok else "Incorrect", "correct": ok, "correct_index": correct,
        "summary": "Well done." if ok else f"The correct answer is {opts[correct] if 0 <= correct < len(opts) else '?'}.",
        "strengths": ["Correct answer"] if ok else [], "improvements": [] if ok else ["Review the working below and try a similar question"],
        "ideal_answer": payload.get("explanation", ""), "rubric": {}, "extras": {}, "source": "key",
    }
