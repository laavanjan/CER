"""Migration — create controls table.

Revision ID: 0002_add_controls_table
Revises: 0001_initial
Create Date: 2024-01-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_add_controls_table"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("pillar", sa.String(255), nullable=False, server_default=""),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("auto", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "plugins",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("pass_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column("partial_criteria", sa.Text(), nullable=False, server_default=""),
        sa.Column("missing_criteria", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("control_id", name="uq_controls_control_id"),
    )
    op.create_index("ix_controls_control_id", "controls", ["control_id"])


def downgrade() -> None:
    op.drop_index("ix_controls_control_id", table_name="controls")
    op.drop_table("controls")
