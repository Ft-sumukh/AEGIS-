"""Aegis Phase 2 Telemetry Ingestion & Distributed Tracing schema evolution.

Revision ID: 004_telemetry_and_traces
Revises: 003_action_approval_engine
Create Date: 2026-09-17 11:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_telemetry_and_traces"
down_revision: str | None = "003_action_approval_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    # 1. Create telemetry_source_states table
    op.create_table(
        "telemetry_source_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="SYNTHETIC"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="HEALTHY"),
        sa.Column("endpoint_url", sa.String(length=500), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source"),
    )
    op.create_index("ix_telemetry_source_states_source", "telemetry_source_states", ["source"])
    op.create_index("ix_telemetry_source_states_status", "telemetry_source_states", ["status"])

    # 2. Create trace_spans table
    op.create_table(
        "trace_spans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("span_id", sa.String(length=64), nullable=False),
        sa.Column("parent_span_id", sa.String(length=64), nullable=True),
        sa.Column("timestamp_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timestamp_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("service_version", sa.String(length=50), nullable=True),
        sa.Column("environment", sa.String(length=50), nullable=False, server_default="production"),
        sa.Column("operation_name", sa.String(length=150), nullable=False),
        sa.Column("span_kind", sa.String(length=30), nullable=False, server_default="SERVER"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="OK"),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("http_method", sa.String(length=20), nullable=True),
        sa.Column("http_route", sa.String(length=200), nullable=True),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("rpc_system", sa.String(length=50), nullable=True),
        sa.Column("rpc_service", sa.String(length=100), nullable=True),
        sa.Column("rpc_method", sa.String(length=100), nullable=True),
        sa.Column("database_system", sa.String(length=50), nullable=True),
        sa.Column("database_operation", sa.String(length=50), nullable=True),
        sa.Column("peer_service", sa.String(length=100), nullable=True),
        sa.Column("host", sa.String(length=150), nullable=True),
        sa.Column("trace_flags", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="opentelemetry"),
        sa.Column("schema_version", sa.String(length=16), nullable=False, server_default="1.0"),
        sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sanitized_attributes", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trace_spans_trace_id", "trace_spans", ["trace_id"])
    op.create_index("ix_trace_spans_span_id", "trace_spans", ["span_id"])
    op.create_index("ix_trace_spans_parent_span_id", "trace_spans", ["parent_span_id"])
    op.create_index("ix_trace_spans_timestamp_start", "trace_spans", ["timestamp_start"])
    op.create_index("ix_trace_spans_duration_ms", "trace_spans", ["duration_ms"])
    op.create_index("ix_trace_spans_service_name", "trace_spans", ["service_name"])
    op.create_index("ix_trace_spans_environment", "trace_spans", ["environment"])
    op.create_index("ix_trace_spans_operation_name", "trace_spans", ["operation_name"])
    op.create_index("ix_trace_spans_status", "trace_spans", ["status"])
    op.create_index("ix_trace_spans_company_trace", "trace_spans", ["company_id", "trace_id"])
    op.create_index("ix_trace_spans_company_service", "trace_spans", ["company_id", "service_name", "timestamp_start"])
    op.create_index("ix_trace_spans_company_status", "trace_spans", ["company_id", "status", "timestamp_start"])
    op.create_index("ix_trace_spans_duration", "trace_spans", ["company_id", "duration_ms"])
    op.create_index("ix_trace_spans_trace_span", "trace_spans", ["trace_id", "span_id"])
    op.create_index("ix_trace_spans_parent", "trace_spans", ["trace_id", "parent_span_id"])

    # 3. Add telemetry & trace context columns to operational_metrics
    op.add_column("operational_metrics", sa.Column("trace_id", sa.String(length=64), nullable=True))
    op.add_column("operational_metrics", sa.Column("span_id", sa.String(length=64), nullable=True))
    op.add_column("operational_metrics", sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("operational_metrics", sa.Column("schema_version", sa.String(length=16), nullable=False, server_default="1.0"))
    op.create_index("ix_operational_metrics_trace_id", "operational_metrics", ["trace_id"])

    # 4. Add telemetry & trace context columns to system_events
    op.add_column("system_events", sa.Column("source", sa.String(length=100), nullable=False, server_default="system"))
    op.add_column("system_events", sa.Column("trace_id", sa.String(length=64), nullable=True))
    op.add_column("system_events", sa.Column("span_id", sa.String(length=64), nullable=True))
    op.add_column("system_events", sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("system_events", sa.Column("schema_version", sa.String(length=16), nullable=False, server_default="1.0"))
    op.create_index("ix_system_events_trace_id", "system_events", ["trace_id"])

    # 5. Add telemetry lineage columns to incident_evidence
    op.add_column("incident_evidence", sa.Column("source", sa.String(length=50), nullable=False, server_default="synthetic"))
    op.add_column("incident_evidence", sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incident_evidence", sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # 5. Drop from incident_evidence
    op.drop_column("incident_evidence", "ingestion_timestamp")
    op.drop_column("incident_evidence", "source_timestamp")
    op.drop_column("incident_evidence", "source")

    # 4. Drop from system_events
    op.drop_index("ix_system_events_trace_id", table_name="system_events")
    op.drop_column("system_events", "schema_version")
    op.drop_column("system_events", "ingestion_timestamp")
    op.drop_column("system_events", "span_id")
    op.drop_column("system_events", "trace_id")
    op.drop_column("system_events", "source")

    # 3. Drop from operational_metrics
    op.drop_index("ix_operational_metrics_trace_id", table_name="operational_metrics")
    op.drop_column("operational_metrics", "schema_version")
    op.drop_column("operational_metrics", "ingestion_timestamp")
    op.drop_column("operational_metrics", "span_id")
    op.drop_column("operational_metrics", "trace_id")

    # 2. Drop trace_spans
    op.drop_table("trace_spans")

    # 1. Drop telemetry_source_states
    op.drop_table("telemetry_source_states")
