from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base, TimestampMixin

class QuestionAttempt(Base, TimestampMixin):
    __tablename__ = "question_attempts"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_attempt_user_client"), Index("ix_attempts_user_created", "user_id", "created_at"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    question_id: Mapped[str | None] = mapped_column(String(120))
    level: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(String(500))
