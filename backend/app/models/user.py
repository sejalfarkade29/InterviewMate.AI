from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("graduation_year IS NULL OR (graduation_year >= 1980 AND graduation_year <= 2100)",
                        name="ck_profile_graduation_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    education: Mapped[str | None] = mapped_column(String(120))
    college: Mapped[str | None] = mapped_column(String(160))
    degree: Mapped[str | None] = mapped_column(String(120))
    branch: Mapped[str | None] = mapped_column(String(120))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    experience_level: Mapped[str | None] = mapped_column(String(40))
    career_interests: Mapped[str | None] = mapped_column(Text)
    preferred_roles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped["User"] = relationship(back_populates="profile")
