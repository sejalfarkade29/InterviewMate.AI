from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.practice import PracticeRecord
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def build(db: Session, user_id: int) -> dict:
    recs = db.scalars(select(PracticeRecord).where(PracticeRecord.user_id == user_id).order_by(PracticeRecord.created_at)).all()
    by_module: dict[str, list[int]] = defaultdict(list)
    by_topic: dict[tuple[str, str], list[int]] = defaultdict(list)
    by_day: dict[str, list[int]] = defaultdict(list)
    for r in recs:
        by_module[r.module].append(r.score)
        if r.topic and r.module not in ("resume", "job-match"):
            by_topic[(r.module, r.topic)].append(r.score)
        if r.created_at:
            by_day[r.created_at.date().isoformat()].append(r.score)
    topics = [{"module": m, "topic": t, "count": len(v), "avg": round(sum(v) / len(v))} for (m, t), v in by_topic.items()]
    topics.sort(key=lambda x: x["avg"])
    return {
        "total": len(recs), "average": round(sum(r.score for r in recs) / len(recs)) if recs else 0,
        "by_module": sorted([{"module": m, "count": len(v), "avg": round(sum(v) / len(v)), "best": max(v)} for m, v in by_module.items()], key=lambda x: -x["count"]),
        "trend": [{"date": d, "avg": round(sum(v) / len(v)), "count": len(v)} for d, v in sorted(by_day.items())][-30:],
        "weakest": topics[:5], "strongest": list(reversed(topics[-5:])) if len(topics) > 5 else list(reversed(topics))[:3],
    }


@router.get("")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build(db, user.id)
