from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, get_current_user, get_db
from app.core.config import settings
from app.core.rate_limit import check_rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserProfile
from app.schemas.auth import LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user_id),
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, full_name=user.profile.full_name if user.profile else "")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=data.email, password_hash=hash_password(data.password))
    user.profile = UserProfile(full_name=data.full_name, skills=[], preferred_roles=[])
    db.add(user)
    try:
        db.commit()  # user + profile are saved in one transaction
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    _set_cookie(response, user.id)
    return _user_out(user)


@router.post("/login", response_model=UserOut)
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    client = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:{client}:{data.email}")
    user = db.scalar(select(User).where(User.email == data.email))
    # Same message for unknown email and wrong password, so emails can't be probed.
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    _set_cookie(response, user.id)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
