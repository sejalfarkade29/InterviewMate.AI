from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class GeneratedQuestion(Base):
    """A question served to a user. The answer key stays here, never in the browser."""
    __tablename__ = "generated_questions"
    __table_args__ = (Index("ix_genq_user_module", "user_id", "module"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    answered: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


class PracticeRecord(Base, TimestampMixin):
    """One finished activity: an answered question, a code submission, a resume analysis, a voice session..."""
    __tablename__ = "practice_records"
    __table_args__ = (Index("ix_records_user_created", "user_id", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    topic: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    question: Mapped[str] = mapped_column(Text, default="", nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    feedback: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_id: Mapped[str | None] = mapped_column(String(36))


class UserStats(Base, TimestampMixin):
    __tablename__ = "user_stats"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active: Mapped[date | None] = mapped_column(Date)


class UserKV(Base, TimestampMixin):
    """Small per-user JSON documents (roadmap, preferences)."""
    __tablename__ = "user_kv"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_kv_user_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
