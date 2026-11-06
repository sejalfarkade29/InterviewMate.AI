from sqlalchemy.orm import Session

from app.models.practice import PracticeRecord
from app.services import rewards


def save_record(db: Session, user_id: int, *, module: str, title: str, question: str = "", answer: str = "",
                score: int = 0, kind: str = "", topic: str = "", feedback: dict | None = None,
                meta: dict | None = None, question_id: str | None = None, extra_xp: int = 0, xp: int | None = None) -> tuple[PracticeRecord, dict]:
    """Store one finished activity and award XP. Returns (record, reward summary)."""
    gained = xp if xp is not None else rewards.xp_for(module, score, extra_xp)
    before = rewards.before_state(db, user_id)
    rec = PracticeRecord(user_id=user_id, module=module, kind=kind, topic=topic[:120], title=title[:200], question=question,
                         answer=answer, score=max(0, min(100, int(score))), feedback=feedback or {}, meta=meta or {},
                         xp=gained, question_id=question_id)
    db.add(rec)
    db.flush()
    reward = rewards.award(db, user_id, gained, before)
    db.commit()
    db.refresh(rec)
    return rec, reward
