from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.practice import GeneratedQuestion, PracticeRecord, Resume
from app.models.user import User
from app.services import banks, questions
from app.services.records import save_record

router = APIRouter(prefix="/practice", tags=["practice"])

MODULES = {"aptitude", "technical", "dsa", "hr", "project", "daily", "simulation"}
TITLES = {"aptitude": "Aptitude", "technical": "Technical interview", "dsa": "DSA practice", "hr": "HR interview",
          "project": "Project interview", "daily": "Daily challenge", "simulation": "Full simulation"}


class QuestionIn(BaseModel):
    module: str
    kind: str = ""
    topic: str = ""
    level: int | None = Field(default=None, ge=1, le=5)
    context: str = Field(default="", max_length=4000)
    resume_id: int | None = None


class AnswerIn(BaseModel):
    question_id: str = Field(min_length=36, max_length=36)
    answer: str = Field(default="", max_length=8000)
    choice: int | None = Field(default=None, ge=0, le=5)
    time_spent_sec: int | None = Field(default=None, ge=0, le=86400)
    meta: dict = Field(default_factory=dict)


@router.get("/topics")
def topics():
    return {"aptitude": banks.APTITUDE_TOPICS, "technical": banks.TECH_TOPICS, "dsa": banks.DSA_TOPICS, "daily": banks.DAILY_KINDS}


def adaptive_level(db: Session, user_id: int, module: str) -> int:
    rows = db.scalars(select(PracticeRecord).where(PracticeRecord.user_id == user_id, PracticeRecord.module == module)
                      .order_by(PracticeRecord.created_at.desc()).limit(4)).all()
    if not rows:
        return 2
    avg = sum(r.score for r in rows) / len(rows)
    last_level = int((rows[0].meta or {}).get("difficulty", 2))
    return max(1, min(5, last_level + (1 if avg >= 75 else -1 if avg < 45 else 0)))


def project_context(db: Session, user: User, resume_id: int | None, extra: str) -> str:
    parts = [extra] if extra else []
    resume = db.get(Resume, resume_id) if resume_id else db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()))
    if resume and resume.user_id == user.id:
        projects = (resume.analysis or {}).get("projects") or []
        parts.append("Resume projects: " + "; ".join(f"{p.get('name')}: {p.get('description')} [{', '.join(p.get('technologies', []))}]" for p in projects if isinstance(p, dict)) if projects else resume.text[:2000])
    return "\n".join(parts)


@router.post("/question")
def new_question(data: QuestionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.module not in MODULES:
        raise HTTPException(status_code=422, detail="Unknown module")
    level = data.level or adaptive_level(db, user.id, data.module)
    kind = data.kind or data.module
    context = data.context
    if data.module == "project" or kind.startswith("project"):
        context = project_context(db, user, data.resume_id, data.context)
        if not context:
            raise HTTPException(status_code=422, detail="Analyze a resume first, or describe your project, so questions can be based on it.")
    return questions.generate_question(db, user.id, data.module, kind=kind, topic=data.topic, level=level, context=context)


@router.post("/answer")
def answer(data: AnswerIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(GeneratedQuestion, data.question_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Question not found")
    if row.answered:
        raise HTTPException(status_code=409, detail="This question has already been answered. Use Next to get a new one.")
    payload = row.payload
    if payload.get("type") == "mcq":
        if data.choice is None:
            raise HTTPException(status_code=422, detail="Choose an option first")
        result = questions.evaluate_mcq(payload, data.choice)
        opts = payload.get("options", [])
        answer_text = opts[data.choice] if data.choice < len(opts) else str(data.choice)
    else:
        if len(data.answer.strip()) < 3:
            raise HTTPException(status_code=422, detail="Write your answer first")
        result = questions.evaluate_text(payload, data.answer)
        answer_text = data.answer
    row.answered = 1
    db.add(row)
    module = row.module
    title = f"{TITLES.get(module, module)}: {payload.get('topic') or payload.get('kind')}"
    meta = {**data.meta, "difficulty": payload.get("difficulty"), "time_spent_sec": data.time_spent_sec, "source": payload.get("source"),
            "round": row.kind if module in ("simulation", "daily") else None, "evaluation": result.get("source")}
    rec, reward = save_record(db, user.id, module=module, kind=payload.get("kind", ""), topic=payload.get("topic", ""), title=title,
                              question=payload["question"], answer=answer_text, score=result["score"], feedback=result,
                              meta=meta, question_id=row.id, extra_xp=8 if module == "daily" else 0)
    return {"record_id": rec.id, "result": result, "reward": reward}
