import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.practice import adaptive_level, project_context
from app.models.practice import GeneratedQuestion, PracticeRecord
from app.models.user import User
from app.services import banks, questions, rewards

router = APIRouter(prefix="/daily", tags=["daily"])


class DailyIn(BaseModel):
    kind: str = ""


@router.post("/question")
def daily_question(data: DailyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A new question every time, and a different TYPE of question from the last few the user received."""
    recent = db.scalars(select(GeneratedQuestion.kind).where(GeneratedQuestion.user_id == user.id, GeneratedQuestion.module == "daily")
                        .order_by(GeneratedQuestion.created_at.desc()).limit(4)).all()
    options = [k for k in banks.DAILY_KINDS if k not in recent] or banks.DAILY_KINDS
    kind = data.kind if data.kind in banks.DAILY_KINDS else random.choice(options)
    context = project_context(db, user, None, "") if kind.startswith("project") else ""
    return questions.generate_question(db, user.id, "daily", kind=kind, level=adaptive_level(db, user.id, "daily"), context=context)


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    done = db.scalar(select(func.count()).select_from(PracticeRecord).where(
        PracticeRecord.user_id == user.id, PracticeRecord.module == "daily", PracticeRecord.created_at >= start)) or 0
    info = rewards.overview(db, user.id)
    return {"completed_today": done, "streak": info["streak"], "best_streak": info["best_streak"], "kinds": banks.DAILY_KINDS}
