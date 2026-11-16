"""Multi-phase data validation and schema integrity checking engine."""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.ingestion.models import EntityIngestionSummary, ValidationErrorItem
from app.models.enums import (
    DeploymentStatus,
    OrderStatus,
    SeverityLevel,
    TicketPriority,
    TicketStatus,
)


class DataValidator:
    """Validates types, ranges, enums, duplicates, and foreign keys for incoming data."""

    def __init__(self) -> None:
        self.valid_customer_ids: set[str] = set()
        self.valid_order_ids: set[str] = set()

    def validate_company(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates company records."""
        valid = []
        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))
            if not rec.get("name"):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "company", rec_id, "name", "Company name is required", rec.get("name")
                    )
                )
                continue
            valid.append(rec)
        return valid

    def validate_customers(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates customer entities and records customer IDs for order cross-referencing."""
        valid = []
        seen_refs = set()
        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))
            ext_ref = rec.get("external_reference")

            # Check required
            if not ext_ref:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "customer", rec_id, "external_reference", "external_reference is required"
                    )
                )
                continue

            if not rec.get("name"):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem("customer", rec_id, "name", "name is required")
                )
                continue

            # Check duplicate within incoming payload
            if ext_ref in seen_refs:
                summary.duplicates += 1
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "customer",
                        rec_id,
                        "external_reference",
                        f"Duplicate external_reference: {ext_ref}",
                    )
                )
                continue
            seen_refs.add(ext_ref)

            # Store ID for foreign key validation
            self.valid_customer_ids.add(rec_id)
            valid.append(rec)
        return valid

    def validate_orders(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates order transactions, status enums, amounts, and customer foreign keys."""
        valid = []
        seen_refs = set()
        valid_statuses = {s.value for s in OrderStatus}

        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))
            ext_ref = rec.get("external_reference")

            if not ext_ref:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order", rec_id, "external_reference", "external_reference is required"
                    )
                )
                continue

            if ext_ref in seen_refs:
                summary.duplicates += 1
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order",
                        rec_id,
                        "external_reference",
                        f"Duplicate external_reference: {ext_ref}",
                    )
                )
                continue
            seen_refs.add(ext_ref)

            # Status validation
            status_val = str(rec.get("status", "")).upper()
            if status_val not in valid_statuses:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order", rec_id, "status", f"Invalid order status: {rec.get('status')}"
                    )
                )
                continue

            # Amount validation
            try:
                amt = Decimal(str(rec.get("total_amount", -1)))
                if amt < Decimal("0.00"):
                    summary.rejected += 1
                    summary.validation_errors.append(
                        ValidationErrorItem(
                            "order",
                            rec_id,
                            "total_amount",
                            f"Order total must be non-negative: {amt}",
                        )
                    )
                    continue
            except (InvalidOperation, TypeError, ValueError):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order",
                        rec_id,
                        "total_amount",
                        f"Invalid amount: {rec.get('total_amount')}",
                    )
                )
                continue

            # Customer Foreign Key validation (if customers were validated)
            cust_id = str(rec.get("customer_id", ""))
            if self.valid_customer_ids and cust_id not in self.valid_customer_ids:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order",
                        rec_id,
                        "customer_id",
                        f"Referenced customer {cust_id} does not exist",
                    )
                )
                continue

            self.valid_order_ids.add(rec_id)
            valid.append(rec)
        return valid

    def validate_order_items(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates order items and order foreign keys."""
        valid = []
        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))
            order_id = str(rec.get("order_id", ""))

            if self.valid_order_ids and order_id not in self.valid_order_ids:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order_item",
                        rec_id,
                        "order_id",
                        f"Referenced order {order_id} does not exist",
                    )
                )
                continue

            try:
                qty = int(rec.get("quantity", 0))
                if qty <= 0:
                    summary.rejected += 1
                    summary.validation_errors.append(
                        ValidationErrorItem(
                            "order_item", rec_id, "quantity", f"Quantity must be positive: {qty}"
                        )
                    )
                    continue
            except (ValueError, TypeError):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "order_item", rec_id, "quantity", f"Invalid quantity: {rec.get('quantity')}"
                    )
                )
                continue

            valid.append(rec)
        return valid

    def validate_metrics(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates time-series metrics, timestamps, and numerical bounds."""
        valid = []
        seen_keys = set()
        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))
            m_name = rec.get("metric_name")
            ts = rec.get("timestamp")

            if not m_name or not ts:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "metric", rec_id, "metric_name", "metric_name and timestamp are required"
                    )
                )
                continue

            # Duplicate metric check at same timestamp
            metric_key = (m_name, ts)
            if metric_key in seen_keys:
                summary.duplicates += 1
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "metric", rec_id, "timestamp", f"Duplicate metric entry: {metric_key}"
                    )
                )
                continue
            seen_keys.add(metric_key)

            # Value check
            try:
                val = float(rec.get("value", 0))
                if "rate" in m_name and (val < 0.0 or val > 1.0001):
                    summary.rejected += 1
                    summary.validation_errors.append(
                        ValidationErrorItem(
                            "metric",
                            rec_id,
                            "value",
                            f"Rate metric {m_name} must be between 0.0 and 1.0: {val}",
                        )
                    )
                    continue
                if "latency" in m_name and val < 0.0:
                    summary.rejected += 1
                    summary.validation_errors.append(
                        ValidationErrorItem(
                            "metric", rec_id, "value", f"Latency cannot be negative: {val}"
                        )
                    )
                    continue
            except (ValueError, TypeError):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "metric", rec_id, "value", f"Invalid numeric value: {rec.get('value')}"
                    )
                )
                continue

            valid.append(rec)
        return valid

    def validate_events(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates system events and severity enums."""
        valid = []
        valid_sevs = {s.value for s in SeverityLevel}
        seen_ids = set()

        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))

            if rec_id in seen_ids:
                summary.duplicates += 1
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "system_event", rec_id, "id", f"Duplicate system event ID: {rec_id}"
                    )
                )
                continue
            seen_ids.add(rec_id)

            if not rec.get("event_type") or not rec.get("service"):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "system_event", rec_id, "event_type", "event_type and service are required"
                    )
                )
                continue

            sev = str(rec.get("severity", "")).upper()
            if sev not in valid_sevs:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "system_event",
                        rec_id,
                        "severity",
                        f"Invalid severity: {rec.get('severity')}",
                    )
                )
                continue

            valid.append(rec)
        return valid

    def validate_deployments(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates service deployment records and deployment status enums."""
        valid = []
        valid_statuses = {s.value for s in DeploymentStatus}
        seen_keys = set()

        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))
            service = rec.get("service")
            version = rec.get("version")
            dep_at = rec.get("deployed_at")

            if not service or not version or not dep_at:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "deployment",
                        rec_id,
                        "service",
                        "service, version, and deployed_at are required",
                    )
                )
                continue

            dep_key = (service, version, dep_at)
            if dep_key in seen_keys:
                summary.duplicates += 1
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "deployment", rec_id, "version", f"Duplicate deployment: {dep_key}"
                    )
                )
                continue
            seen_keys.add(dep_key)

            st = str(rec.get("status", "")).upper()
            if st not in valid_statuses:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "deployment",
                        rec_id,
                        "status",
                        f"Invalid deployment status: {rec.get('status')}",
                    )
                )
                continue

            valid.append(rec)
        return valid

    def validate_support_tickets(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates customer support tickets and priority/status enums."""
        valid = []
        valid_prios = {p.value for p in TicketPriority}
        valid_statuses = {s.value for s in TicketStatus}

        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))

            if not rec.get("category") or not rec.get("summary"):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "support_ticket", rec_id, "summary", "category and summary are required"
                    )
                )
                continue

            prio = str(rec.get("priority", "")).upper()
            if prio not in valid_prios:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "support_ticket",
                        rec_id,
                        "priority",
                        f"Invalid ticket priority: {rec.get('priority')}",
                    )
                )
                continue

            st = str(rec.get("status", "")).upper()
            if st not in valid_statuses:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "support_ticket",
                        rec_id,
                        "status",
                        f"Invalid ticket status: {rec.get('status')}",
                    )
                )
                continue

            valid.append(rec)
        return valid

    def validate_complaints(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> list[dict[str, Any]]:
        """Validates customer complaint feedback records."""
        valid = []
        valid_sevs = {s.value for s in SeverityLevel}

        for i, rec in enumerate(records):
            summary.received += 1
            rec_id = str(rec.get("id", f"idx-{i}"))

            if not rec.get("category") or not rec.get("summary"):
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "customer_complaint", rec_id, "summary", "category and summary are required"
                    )
                )
                continue

            sev = str(rec.get("severity", "")).upper()
            if sev not in valid_sevs:
                summary.rejected += 1
                summary.validation_errors.append(
                    ValidationErrorItem(
                        "customer_complaint",
                        rec_id,
                        "severity",
                        f"Invalid complaint severity: {rec.get('severity')}",
                    )
                )
                continue

            valid.append(rec)
        return valid
