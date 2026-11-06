from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services import rewards

router = APIRouter(prefix="/rewards", tags=["rewards"])


@router.get("")
def my_rewards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = rewards.overview(db, user.id)
    db.commit()
    return data
