"""Add full LLM output fields to control_results.

Revision ID: 0006_cr_llm_fields
Revises: 0005_controls_cer_obs
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_cr_llm_fields"
down_revision = "0005_controls_cer_obs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("control_results", sa.Column("student_summary",   sa.Text(),        nullable=True))
    op.add_column("control_results", sa.Column("what_is_present",   sa.Text(),        nullable=True))
    op.add_column("control_results", sa.Column("what_is_missing",   sa.Text(),        nullable=True))
    op.add_column("control_results", sa.Column("doc_classification", sa.String(30),   nullable=True))


def downgrade() -> None:
    op.drop_column("control_results", "doc_classification")
    op.drop_column("control_results", "what_is_missing")
    op.drop_column("control_results", "what_is_present")
    op.drop_column("control_results", "student_summary")
