"""add model metadata to tasks

Revision ID: 20260407_add_task_model_metadata
Revises: 
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa

revision = "20260407_add_task_model_metadata"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("model_name", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("model_version", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("label_set", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "label_set")
    op.drop_column("tasks", "model_version")
    op.drop_column("tasks", "model_name")
