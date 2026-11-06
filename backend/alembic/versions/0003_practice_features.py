"""resumes, generated questions, practice records, stats and kv

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TS = lambda: [  # noqa: E731
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
]
USER = lambda: sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # noqa: E731


def upgrade() -> None:
    op.create_table(
        "resumes", sa.Column("id", sa.Integer(), primary_key=True), USER(),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False), sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_percent", sa.Integer(), nullable=False, server_default="0"), *TS())
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_table(
        "generated_questions", sa.Column("id", sa.String(36), primary_key=True), USER(),
        sa.Column("module", sa.String(40), nullable=False), sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False), sa.Column("answered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(32), nullable=False))
    op.create_index("ix_genq_user_module", "generated_questions", ["user_id", "module"])
    op.create_table(
        "practice_records", sa.Column("id", sa.Integer(), primary_key=True), USER(),
        sa.Column("module", sa.String(40), nullable=False), sa.Column("kind", sa.String(40), nullable=False, server_default=""),
        sa.Column("topic", sa.String(120), nullable=False, server_default=""), sa.Column("title", sa.String(200), nullable=False),
        sa.Column("question", sa.Text(), nullable=False), sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"), sa.Column("max_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("feedback", sa.JSON(), nullable=False), sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"), sa.Column("question_id", sa.String(36)), *TS())
    op.create_index("ix_records_user_created", "practice_records", ["user_id", "created_at"])
    op.create_table(
        "user_stats", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"), sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"), sa.Column("last_active", sa.Date()), *TS())
    op.create_table(
        "user_kv", sa.Column("id", sa.Integer(), primary_key=True), USER(),
        sa.Column("key", sa.String(80), nullable=False), sa.Column("value", sa.JSON(), nullable=False), *TS(),
        sa.UniqueConstraint("user_id", "key", name="uq_kv_user_key"))


def downgrade() -> None:
    for name in ("user_kv", "user_stats", "practice_records", "generated_questions", "resumes"):
        op.drop_table(name)
