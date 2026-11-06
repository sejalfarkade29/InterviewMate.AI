"""question attempts and durable history
Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("question_attempts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("client_id", sa.String(100), nullable=False), sa.Column("module", sa.String(80), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("score", sa.Integer(), nullable=False), sa.Column("max_score", sa.Integer(), nullable=False, server_default="100"), sa.Column("summary", sa.Text(), nullable=False), sa.Column("details", sa.JSON(), nullable=False), sa.Column("question_id", sa.String(120)), sa.Column("level", sa.Integer()), sa.Column("source_url", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("user_id", "client_id", name="uq_attempt_user_client"))
    op.create_index("ix_attempts_user_created", "question_attempts", ["user_id", "created_at"])
def downgrade() -> None:
    op.drop_index("ix_attempts_user_created", table_name="question_attempts")
    op.drop_table("question_attempts")
