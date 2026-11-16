"""Aegis Group 9 action & human approval engine schema evolution.

Revision ID: 003_action_approval_engine
Revises: 002_incident_management
Create Date: 2026-09-11 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_action_approval_engine"
down_revision: str | None = "002_incident_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    # 1. Add new columns to actions table
    op.add_column(
        "actions",
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Operational Action"),
    )
    op.add_column(
        "actions",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PROPOSED"),
    )
    op.add_column(
        "actions",
        sa.Column("target_service", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("parameters", json_type, nullable=False, server_default="{}"),
    )
    op.add_column(
        "actions",
        sa.Column("preconditions", json_type, nullable=False, server_default="[]"),
    )
    op.add_column(
        "actions",
        sa.Column("expected_outcome", sa.Text(), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("verification_strategy", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("verification_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("verification_result", json_type, nullable=False, server_default="{}"),
    )
    op.add_column(
        "actions",
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("verification_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "actions",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "actions",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_actions_status", "actions", ["status"])
    op.create_index("ix_actions_target_service", "actions", ["target_service"])
    op.create_index("ix_actions_fingerprint", "actions", ["fingerprint"])
    op.create_index("ix_actions_idempotency_key", "actions", ["idempotency_key"])

    # 2. Create action_approvals table
    op.create_table(
        "action_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("decision_by", sa.String(length=100), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("fingerprint_verified", sa.String(length=64), nullable=False),
        sa.Column("approval_metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_approvals_action_id", "action_approvals", ["action_id"])
    op.create_index("ix_action_approvals_action_decision", "action_approvals", ["action_id", "decision"])


def downgrade() -> None:
    op.drop_table("action_approvals")

    op.drop_index("ix_actions_idempotency_key", table_name="actions")
    op.drop_index("ix_actions_fingerprint", table_name="actions")
    op.drop_index("ix_actions_target_service", table_name="actions")
    op.drop_index("ix_actions_status", table_name="actions")

    op.drop_column("actions", "updated_at")
    op.drop_column("actions", "created_at")
    op.drop_column("actions", "verified_at")
    op.drop_column("actions", "verification_started_at")
    op.drop_column("actions", "started_at")
    op.drop_column("actions", "expires_at")
    op.drop_column("actions", "idempotency_key")
    op.drop_column("actions", "fingerprint")
    op.drop_column("actions", "failure_reason")
    op.drop_column("actions", "verification_result")
    op.drop_column("actions", "verification_status")
    op.drop_column("actions", "verification_strategy")
    op.drop_column("actions", "expected_outcome")
    op.drop_column("actions", "preconditions")
    op.drop_column("actions", "parameters")
    op.drop_column("actions", "target_service")
    op.drop_column("actions", "status")
    op.drop_column("actions", "title")
