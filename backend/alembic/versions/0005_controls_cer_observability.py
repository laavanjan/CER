"""Add cer_observability, supplement_prompt, artefact_type_expected to controls.

Revision ID: 0005_controls_cer_obs
Revises: 0004_rel_ai_audit_tables
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_controls_cer_obs"
down_revision = "0004_rel_ai_audit_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "controls",
        sa.Column("cer_observability", sa.String(10), nullable=False, server_default="T1"),
    )
    op.add_column(
        "controls",
        sa.Column("supplement_prompt", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "controls",
        sa.Column("artefact_type_expected", sa.String(100), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("controls", "artefact_type_expected")
    op.drop_column("controls", "supplement_prompt")
    op.drop_column("controls", "cer_observability")
