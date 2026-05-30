"""Add LLM scan columns to control_results.

Revision ID: 0008_llm_scan_columns
Revises: 0007_deterministic_explanation
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_llm_scan_columns"
down_revision = "0007_deterministic_explanation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("control_results", sa.Column("llm_outcome", sa.String(20), nullable=True))
    op.add_column("control_results", sa.Column("llm_confidence", sa.Float(), nullable=True))
    op.add_column("control_results", sa.Column("llm_evidence", JSONB(), nullable=True))
    op.add_column("control_results", sa.Column("llm_reasoning", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("control_results", "llm_reasoning")
    op.drop_column("control_results", "llm_evidence")
    op.drop_column("control_results", "llm_confidence")
    op.drop_column("control_results", "llm_outcome")
