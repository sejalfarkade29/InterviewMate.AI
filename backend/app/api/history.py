from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.practice import PracticeRecord
from app.models.user import User

router = APIRouter(prefix="/history", tags=["history"])


def _row(r: PracticeRecord, full: bool = False) -> dict:
    out = {"id": r.id, "module": r.module, "kind": r.kind, "topic": r.topic, "title": r.title, "score": r.score, "max_score": r.max_score,
           "xp": r.xp, "created_at": r.created_at.isoformat() if r.created_at else None,
           "question": r.question if full else r.question[:200], "summary": (r.feedback or {}).get("summary", "")}
    if full:
        out.update(answer=r.answer, feedback=r.feedback, meta={k: v for k, v in (r.meta or {}).items() if k != "transcript_raw"})
    return out


@router.get("")
def list_history(module: str | None = None, q: str | None = None, limit: int = 50, offset: int = 0,
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(PracticeRecord).where(PracticeRecord.user_id == user.id)
    if module:
        stmt = stmt.where(PracticeRecord.module == module)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(PracticeRecord.question.ilike(like), PracticeRecord.title.ilike(like), PracticeRecord.topic.ilike(like), PracticeRecord.answer.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(PracticeRecord.created_at.desc(), PracticeRecord.id.desc()).limit(min(limit, 100)).offset(max(offset, 0))).all()
    return {"total": total, "items": [_row(r) for r in rows]}


@router.get("/{record_id}")
def get_record(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(PracticeRecord, record_id)
    if not r or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    return _row(r, full=True)


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(PracticeRecord, record_id)
    if not r or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(r)
    db.commit()
    return Response(status_code=204)


@router.delete("", status_code=204)
def clear_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(PracticeRecord).where(PracticeRecord.user_id == user.id))
    db.commit()
    return Response(status_code=204)
