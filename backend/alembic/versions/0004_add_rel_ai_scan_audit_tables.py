"""Migration — add uses_rel_ai to projects, audit columns to scans,
and create metadata_supplements + handoff_exports tables.

Revision ID: 0004_add_rel_ai_scan_audit_tables
Revises: 0003_add_extended_profile_fields
Create Date: 2025-05-09 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_rel_ai_audit_tables"
down_revision: str | None = "0003_add_extended_profile_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- projects: add uses_rel_ai -----------------------------------------------
    op.add_column(
        "projects",
        sa.Column("uses_rel_ai", sa.Boolean(), nullable=False, server_default="false"),
    )

    # -- scans: add audit reproducibility columns (§14.1) ------------------------
    op.add_column("scans", sa.Column("workspace_hash", sa.String(64), nullable=True))
    op.add_column("scans", sa.Column("commit_sha", sa.String(40), nullable=True))
    op.add_column(
        "scans",
        sa.Column("plugin_versions_used", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "scans",
        sa.Column("escalation_hints", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "scans",
        sa.Column("cer_observability_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # -- metadata_supplements: T3 design-only supplement entries (§6) ------------
    op.create_table(
        "metadata_supplements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("supplement_prompt", sa.Text(), nullable=False),
        sa.Column("artefact_type_expected", sa.String(10), nullable=False),
        sa.Column("declared_path", sa.Text(), nullable=True),
        sa.Column("existence_check_result", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status_after_supplement", sa.String(20), nullable=False, server_default="not_evaluable"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -- handoff_exports: Reviewer + Certifier handoff packages (§11, §14.2) ----
    op.create_table(
        "handoff_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target", sa.String(20), nullable=False),
        sa.Column("registry_version", sa.String(20), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("handoff_exports")
    op.drop_table("metadata_supplements")
    op.drop_column("scans", "cer_observability_summary")
    op.drop_column("scans", "escalation_hints")
    op.drop_column("scans", "plugin_versions_used")
    op.drop_column("scans", "commit_sha")
    op.drop_column("scans", "workspace_hash")
    op.drop_column("projects", "uses_rel_ai")
