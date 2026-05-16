"""Add deterministic_explanation column to control_results.

Revision ID: 0007_deterministic_explanation
Revises: 0006_cr_llm_fields
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_deterministic_explanation"
down_revision = "0006_cr_llm_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "control_results",
        sa.Column("deterministic_explanation", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("control_results", "deterministic_explanation")
