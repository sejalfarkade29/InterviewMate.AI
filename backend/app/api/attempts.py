from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.attempt import QuestionAttempt
from app.models.user import User
from app.schemas.attempt import AttemptCreate, AttemptOut
router = APIRouter(prefix="/attempts", tags=["attempts"])
def out(item: QuestionAttempt) -> AttemptOut:
    return AttemptOut(id=item.client_id, module=item.module, title=item.title, score=item.score, maxScore=item.max_score, createdAt=item.created_at, summary=item.summary, details=item.details or [], questionId=item.question_id, level=item.level, sourceUrl=item.source_url)
@router.get("", response_model=list[AttemptOut])
def list_attempts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(QuestionAttempt).where(QuestionAttempt.user_id == user.id).order_by(QuestionAttempt.created_at.desc()).limit(200)).all()
    return [out(row) for row in rows]
@router.post("", response_model=AttemptOut, status_code=status.HTTP_201_CREATED)
def upsert_attempt(data: AttemptCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(QuestionAttempt).where(QuestionAttempt.user_id == user.id, QuestionAttempt.client_id == data.id))
    if item is None: item = QuestionAttempt(user_id=user.id, client_id=data.id)
    item.module, item.title, item.score, item.max_score, item.summary, item.details = data.module, data.title, data.score, data.maxScore, data.summary, data.details
    item.question_id, item.level, item.source_url = data.questionId, data.level, str(data.sourceUrl) if data.sourceUrl else None
    db.add(item); db.commit(); db.refresh(item); return out(item)
@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_attempts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(QuestionAttempt).where(QuestionAttempt.user_id == user.id)); db.commit(); return Response(status_code=204)
