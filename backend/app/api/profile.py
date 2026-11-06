from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.profile import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])

# Fields counted toward the completeness percentage.
_TRACKED = [
    "education", "college", "degree", "branch", "graduation_year",
    "skills", "experience_level", "career_interests", "preferred_roles",
]


def _to_out(user: User) -> ProfileOut:
    p = user.profile
    filled = sum(1 for f in _TRACKED if getattr(p, f))
    return ProfileOut(
        email=user.email,
        full_name=p.full_name,
        education=p.education,
        college=p.college,
        degree=p.degree,
        branch=p.branch,
        graduation_year=p.graduation_year,
        skills=p.skills or [],
        experience_level=p.experience_level,
        career_interests=p.career_interests,
        preferred_roles=p.preferred_roles or [],
        completeness=round(100 * filled / len(_TRACKED)),
    )


@router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return _to_out(user)


@router.put("", response_model=ProfileOut)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # The profile is always the signed-in user's own row, never looked up by a client-supplied id.
    for field, value in data.model_dump().items():
        setattr(user.profile, field, value)
    db.add(user.profile)
    db.commit()
    return _to_out(user)
