"""Aegis Group 5 incident management schema evolution.

Revision ID: 002_incident_management
Revises: 001_initial_schema
Create Date: 2026-09-10 22:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_incident_management"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add new columns to incidents
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.add_column("incidents", sa.Column("severity_reason", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("tags", json_type, nullable=False, server_default="[]"),
    )
    op.add_column(
        "incidents",
        sa.Column("affected_systems", json_type, nullable=False, server_default="[]"),
    )
    op.add_column(
        "incidents",
        sa.Column("affected_metrics", json_type, nullable=False, server_default="[]"),
    )
    op.add_column("incidents", sa.Column("owner_id", sa.String(length=100), nullable=True))
    op.add_column("incidents", sa.Column("team_name", sa.String(length=100), nullable=True))
    op.add_column(
        "incidents", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("incidents", sa.Column("acknowledged_by", sa.String(length=100), nullable=True))
    op.add_column("incidents", sa.Column("resolved_by", sa.String(length=100), nullable=True))
    op.add_column("incidents", sa.Column("resolution_summary", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("closed_by", sa.String(length=100), nullable=True))
    op.add_column("incidents", sa.Column("recovery_status", sa.String(length=50), nullable=True))
    op.add_column("incidents", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.add_column("incidents", sa.Column("estimated_support_impact", sa.Integer(), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("incident_metadata", json_type, nullable=False, server_default="{}"),
    )

    op.create_index("ix_incidents_company_fingerprint", "incidents", ["company_id", "fingerprint"])
    op.create_index("ix_incidents_category", "incidents", ["category"])
    op.create_index("ix_incidents_owner_id", "incidents", ["owner_id"])

    # 2. Create incident_notes table
    op.create_table(
        "incident_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_incident_notes_incident_created",
        "incident_notes",
        ["incident_id", "created_at"],
    )

    # 3. Add deduplication index on incident_evidence
    op.create_index(
        "ix_incident_evidence_unique_source",
        "incident_evidence",
        ["incident_id", "source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_evidence_unique_source", table_name="incident_evidence")
    op.drop_table("incident_notes")
    op.drop_index("ix_incidents_owner_id", table_name="incidents")
    op.drop_index("ix_incidents_category", table_name="incidents")
    op.drop_index("ix_incidents_company_fingerprint", table_name="incidents")

    op.drop_column("incidents", "incident_metadata")
    op.drop_column("incidents", "estimated_support_impact")
    op.drop_column("incidents", "fingerprint")
    op.drop_column("incidents", "recovery_status")
    op.drop_column("incidents", "closed_by")
    op.drop_column("incidents", "resolution_summary")
    op.drop_column("incidents", "resolved_by")
    op.drop_column("incidents", "acknowledged_by")
    op.drop_column("incidents", "acknowledged_at")
    op.drop_column("incidents", "team_name")
    op.drop_column("incidents", "owner_id")
    op.drop_column("incidents", "affected_metrics")
    op.drop_column("incidents", "affected_systems")
    op.drop_column("incidents", "tags")
    op.drop_column("incidents", "category")
    op.drop_column("incidents", "severity_reason")
