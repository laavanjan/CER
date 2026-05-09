"""Migration — add extended profile fields to projects table.

Adds: vulnerable_users, rights_affecting, regulated_sector,
      cross_border_transfer, jurisdiction, user_facing

Revision ID: 0003_add_extended_profile_fields
Revises: 0002_add_controls_table
Create Date: 2024-01-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_add_extended_profile_fields"
down_revision: str | None = "0002_add_controls_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("vulnerable_users", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("projects", sa.Column("rights_affecting", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("projects", sa.Column("regulated_sector", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("projects", sa.Column("cross_border_transfer", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("projects", sa.Column("jurisdiction", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("user_facing", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("projects", "user_facing")
    op.drop_column("projects", "jurisdiction")
    op.drop_column("projects", "cross_border_transfer")
    op.drop_column("projects", "regulated_sector")
    op.drop_column("projects", "rights_affecting")
    op.drop_column("projects", "vulnerable_users")
