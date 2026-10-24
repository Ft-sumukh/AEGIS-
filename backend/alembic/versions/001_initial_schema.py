"""Initial Aegis enterprise schema covering all 18 core domain entities.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-10 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. companies
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"])

    # 2. customers
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("external_reference", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("region", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "external_reference", name="uq_customers_company_ext_ref"
        ),
    )
    op.create_index("ix_customers_company_id", "customers", ["company_id"])
    op.create_index("ix_customers_region", "customers", ["region"])

    # 3. orders
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("external_reference", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_company_id", "orders", ["company_id"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_external_reference", "orders", ["external_reference"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_ordered_at", "orders", ["ordered_at"])
    op.create_index("ix_orders_company_ordered_at", "orders", ["company_id", "ordered_at"])
    op.create_index("ix_orders_company_status", "orders", ["company_id", "status"])

    # 4. order_items
    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_reference", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="chk_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="chk_order_items_unit_price_non_negative"),
        sa.CheckConstraint("total_price >= 0", name="chk_order_items_total_price_non_negative"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    # 5. operational_metrics
    op.create_table(
        "operational_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column(
            "dimension_data", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operational_metrics_company_id", "operational_metrics", ["company_id"])
    op.create_index("ix_operational_metrics_metric_name", "operational_metrics", ["metric_name"])
    op.create_index("ix_operational_metrics_timestamp", "operational_metrics", ["timestamp"])
    op.create_index(
        "ix_metrics_company_timestamp", "operational_metrics", ["company_id", "timestamp"]
    )
    op.create_index(
        "ix_metrics_company_name_timestamp",
        "operational_metrics",
        ["company_id", "metric_name", "timestamp"],
    )

    # 6. system_events
    op.create_table(
        "system_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "event_metadata", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_events_company_id", "system_events", ["company_id"])
    op.create_index("ix_system_events_event_type", "system_events", ["event_type"])
    op.create_index("ix_system_events_service", "system_events", ["service"])
    op.create_index("ix_system_events_timestamp", "system_events", ["timestamp"])
    op.create_index(
        "ix_system_events_company_timestamp", "system_events", ["company_id", "timestamp"]
    )
    op.create_index(
        "ix_system_events_company_service_timestamp",
        "system_events",
        ["company_id", "service", "timestamp"],
    )

    # 7. deployments
    op.create_table(
        "deployments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deployed_by", sa.String(length=100), nullable=False),
        sa.Column(
            "deployment_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deployments_company_id", "deployments", ["company_id"])
    op.create_index("ix_deployments_service", "deployments", ["service"])
    op.create_index("ix_deployments_deployed_at", "deployments", ["deployed_at"])
    op.create_index(
        "ix_deployments_company_service_deployed_at",
        "deployments",
        ["company_id", "service", "deployed_at"],
    )

    # 8. support_tickets
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ticket_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_company_id", "support_tickets", ["company_id"])
    op.create_index("ix_support_tickets_customer_id", "support_tickets", ["customer_id"])
    op.create_index("ix_support_tickets_created_at", "support_tickets", ["created_at"])
    op.create_index(
        "ix_support_tickets_company_status_created",
        "support_tickets",
        ["company_id", "status", "created_at"],
    )

    # 9. customer_complaints
    op.create_table(
        "customer_complaints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "complaint_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_complaints_company_id", "customer_complaints", ["company_id"])
    op.create_index("ix_customer_complaints_customer_id", "customer_complaints", ["customer_id"])
    op.create_index("ix_customer_complaints_created_at", "customer_complaints", ["created_at"])
    op.create_index(
        "ix_customer_complaints_company_created",
        "customer_complaints",
        ["company_id", "created_at"],
    )

    # 10. anomalies
    op.create_table(
        "anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("metric_id", sa.Uuid(), nullable=True),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("expected_value", sa.Float(), nullable=False),
        sa.Column("deviation", sa.Float(), nullable=False),
        sa.Column("detector_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "anomaly_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["metric_id"], ["operational_metrics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomalies_company_id", "anomalies", ["company_id"])
    op.create_index("ix_anomalies_metric_id", "anomalies", ["metric_id"])
    op.create_index("ix_anomalies_metric_name", "anomalies", ["metric_name"])
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])
    op.create_index("ix_anomalies_severity", "anomalies", ["severity"])
    op.create_index("ix_anomalies_status", "anomalies", ["status"])
    op.create_index("ix_anomalies_company_detected_at", "anomalies", ["company_id", "detected_at"])
    op.create_index("ix_anomalies_company_status", "anomalies", ["company_id", "status"])
    op.create_index("ix_anomalies_company_severity", "anomalies", ["company_id", "severity"])

    # 11. incidents
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("investigation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mitigated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("estimated_revenue_impact", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("estimated_orders_affected", sa.Integer(), nullable=True),
        sa.Column("estimated_users_affected", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_company_id", "incidents", ["company_id"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_detected_at", "incidents", ["detected_at"])
    op.create_index("ix_incidents_company_status", "incidents", ["company_id", "status"])
    op.create_index(
        "ix_incidents_company_severity_status", "incidents", ["company_id", "severity", "status"]
    )
    op.create_index("ix_incidents_company_detected_at", "incidents", ["company_id", "detected_at"])

    # 12. incident_anomalies
    op.create_table(
        "incident_anomalies",
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("anomaly_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["anomaly_id"], ["anomalies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("incident_id", "anomaly_id"),
    )
    op.create_index("ix_incident_anomalies_incident_id", "incident_anomalies", ["incident_id"])
    op.create_index("ix_incident_anomalies_anomaly_id", "incident_anomalies", ["anomaly_id"])

    # 13. incident_evidence
    op.create_table(
        "incident_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column(
            "evidence_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_evidence_incident_id", "incident_evidence", ["incident_id"])
    op.create_index("ix_incident_evidence_observed_at", "incident_evidence", ["observed_at"])
    op.create_index(
        "ix_incident_evidence_incident_observed",
        "incident_evidence",
        ["incident_id", "observed_at"],
    )

    # 14. investigations
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("uncertainty", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investigations_incident_id", "investigations", ["incident_id"])

    # 15. investigation_hypotheses
    op.create_table(
        "investigation_hypotheses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("supporting_evidence_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_investigation_hypotheses_investigation_id",
        "investigation_hypotheses",
        ["investigation_id"],
    )

    # 16. recommendations
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_investigation_id", "recommendations", ["investigation_id"])
    op.create_index("ix_recommendations_incident_id", "recommendations", ["incident_id"])
    op.create_index(
        "ix_recommendations_incident_status", "recommendations", ["incident_id", "status"]
    )

    # 17. actions
    op.create_table(
        "actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("approval_status", sa.String(length=32), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("execution_result", sa.Text(), nullable=True),
        sa.Column(
            "action_metadata",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actions_recommendation_id", "actions", ["recommendation_id"])
    op.create_index("ix_actions_incident_id", "actions", ["incident_id"])
    op.create_index("ix_actions_approval_status", "actions", ["approval_status"])
    op.create_index("ix_actions_incident_execution", "actions", ["incident_id", "execution_status"])

    # 18. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column(
            "audit_metadata", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_company_id", "audit_logs", ["company_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_company_timestamp", "audit_logs", ["company_id", "timestamp"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("actions")
    op.drop_table("recommendations")
    op.drop_table("investigation_hypotheses")
    op.drop_table("investigations")
    op.drop_table("incident_evidence")
    op.drop_table("incident_anomalies")
    op.drop_table("incidents")
    op.drop_table("anomalies")
    op.drop_table("customer_complaints")
    op.drop_table("support_tickets")
    op.drop_table("deployments")
    op.drop_table("system_events")
    op.drop_table("operational_metrics")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("customers")
    op.drop_table("companies")
