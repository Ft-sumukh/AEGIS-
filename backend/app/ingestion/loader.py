"""High-performance idempotent batch database loader using SQLAlchemy."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import EntityIngestionSummary
from app.models.company import Company
from app.models.customer import Customer
from app.models.enums import (
    CompanyStatus,
    DeploymentStatus,
    OrderStatus,
    SeverityLevel,
    TicketPriority,
    TicketStatus,
)
from app.models.events import Deployment, SystemEvent
from app.models.metrics import OperationalMetric
from app.models.order import Order, OrderItem
from app.models.support import CustomerComplaint, SupportTicket


def _parse_dt(val: Any) -> datetime | None:
    """Safely parses string or datetime into UTC-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(val))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def _to_uuid(val: Any) -> uuid.UUID:
    """Converts value to UUID instance."""
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(str(val))


class BatchDataLoader:
    """Batch-loads validated entity dictionaries into PostgreSQL/SQLite with idempotency."""

    def __init__(self, session: Session, batch_size: int = 1000) -> None:
        self.session = session
        self.batch_size = batch_size

    def load_company(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> Company | None:
        """Upserts company entity."""
        if not records:
            return None
        rec = records[0]
        co_id = _to_uuid(rec.get("id"))
        existing = self.session.get(Company, co_id)
        if existing:
            summary.duplicates += 1
            return existing

        st_val = str(rec.get("status", "ACTIVE")).upper()
        co_status = (
            CompanyStatus[st_val] if st_val in CompanyStatus.__members__ else CompanyStatus.ACTIVE
        )
        slug_val = rec.get("slug") or rec["name"].lower().replace(" ", "-")

        co = Company(
            id=co_id,
            name=rec["name"],
            slug=slug_val,
            industry=rec.get("industry", "Technology"),
            status=co_status,
            created_at=_parse_dt(rec.get("created_at")) or datetime.now(UTC),
        )
        self.session.add(co)
        self.session.commit()
        summary.inserted += 1
        return co

    def load_customers(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> None:
        """Batch loads customers with external_reference idempotency."""
        if not records:
            return

        company_id = _to_uuid(records[0]["company_id"])
        # Query existing external references to avoid duplicate key conflicts
        existing_refs = set(
            self.session.scalars(
                select(Customer.external_reference).where(Customer.company_id == company_id)
            ).all()
        )

        to_insert = []
        for rec in records:
            ext_ref = rec["external_reference"]
            if ext_ref in existing_refs:
                summary.duplicates += 1
                continue

            created = _parse_dt(rec.get("created_at")) or datetime.now(UTC)
            updated = _parse_dt(rec.get("updated_at")) or created

            cust = Customer(
                id=_to_uuid(rec.get("id", uuid.uuid4())),
                company_id=company_id,
                external_reference=ext_ref,
                name=rec["name"],
                email=rec.get("email"),
                phone=rec.get("phone"),
                region=rec.get("region"),
                created_at=created,
                updated_at=updated,
            )
            to_insert.append(cust)
            existing_refs.add(ext_ref)

        self._flush_chunks(to_insert, summary)

    def load_orders(self, records: list[dict[str, Any]], summary: EntityIngestionSummary) -> None:
        """Batch loads orders with external_reference idempotency."""
        if not records:
            return

        company_id = _to_uuid(records[0]["company_id"])
        existing_refs = set(
            self.session.scalars(
                select(Order.external_reference).where(Order.company_id == company_id)
            ).all()
        )

        to_insert = []
        for rec in records:
            ext_ref = rec["external_reference"]
            if ext_ref in existing_refs:
                summary.duplicates += 1
                continue

            st_val = str(rec.get("status", "COMPLETED")).upper()
            status_enum = (
                OrderStatus[st_val] if st_val in OrderStatus.__members__ else OrderStatus.PENDING
            )
            ordered = _parse_dt(rec.get("ordered_at")) or datetime.now(UTC)

            ord_obj = Order(
                id=_to_uuid(rec.get("id", uuid.uuid4())),
                company_id=company_id,
                customer_id=_to_uuid(rec["customer_id"]),
                external_reference=ext_ref,
                status=status_enum,
                currency=rec.get("currency", "USD"),
                total_amount=Decimal(str(rec.get("total_amount", 0.0))),
                ordered_at=ordered,
                created_at=ordered,
                updated_at=ordered,
            )
            to_insert.append(ord_obj)
            existing_refs.add(ext_ref)

        self._flush_chunks(to_insert, summary)

    def load_order_items(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> None:
        """Batch loads order items with ID idempotency."""
        if not records:
            return

        to_insert = []
        for rec in records:
            item_id = _to_uuid(rec.get("id", uuid.uuid4()))
            item_obj = OrderItem(
                id=item_id,
                order_id=_to_uuid(rec["order_id"]),
                product_reference=rec.get("product_reference", "SKU-00000"),
                quantity=int(rec.get("quantity", 1)),
                unit_price=Decimal(str(rec.get("unit_price", 0.0))),
                total_price=Decimal(str(rec.get("total_price", 0.0))),
            )
            to_insert.append(item_obj)

        self._flush_chunks_with_id_check(OrderItem, to_insert, summary)

    def load_metrics(self, records: list[dict[str, Any]], summary: EntityIngestionSummary) -> None:
        """Batch loads time-series operational metrics."""
        if not records:
            return

        to_insert = []
        for rec in records:
            m_id = _to_uuid(rec.get("id", uuid.uuid4()))
            ts = _parse_dt(rec.get("timestamp")) or datetime.now(UTC)
            m_obj = OperationalMetric(
                id=m_id,
                company_id=_to_uuid(rec["company_id"]),
                metric_name=rec["metric_name"],
                timestamp=ts,
                value=float(rec.get("value", 0.0)),
                unit=rec.get("unit", "count"),
                source=rec.get("source", "telemetry"),
                dimension_data=rec.get("dimension_data", {}),
                created_at=ts,
            )
            to_insert.append(m_obj)

        self._flush_chunks_with_id_check(OperationalMetric, to_insert, summary)

    def load_events(self, records: list[dict[str, Any]], summary: EntityIngestionSummary) -> None:
        """Batch loads system events."""
        if not records:
            return

        to_insert = []
        for rec in records:
            ev_id = _to_uuid(rec.get("id", uuid.uuid4()))
            sev_val = str(rec.get("severity", "INFO")).upper()
            sev_enum = (
                SeverityLevel[sev_val]
                if sev_val in SeverityLevel.__members__
                else SeverityLevel.INFO
            )
            ts = _parse_dt(rec.get("timestamp")) or datetime.now(UTC)

            ev_obj = SystemEvent(
                id=ev_id,
                company_id=_to_uuid(rec["company_id"]),
                event_type=rec["event_type"],
                severity=sev_enum,
                service=rec["service"],
                environment=rec.get("environment", "production"),
                message=rec.get("message", ""),
                timestamp=ts,
                event_metadata=rec.get("event_metadata", {}),
                created_at=ts,
            )
            to_insert.append(ev_obj)

        self._flush_chunks_with_id_check(SystemEvent, to_insert, summary)

    def load_deployments(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> None:
        """Batch loads deployments."""
        if not records:
            return

        to_insert = []
        for rec in records:
            dep_id = _to_uuid(rec.get("id", uuid.uuid4()))
            st_val = str(rec.get("status", "SUCCESS")).upper()
            st_enum = (
                DeploymentStatus[st_val]
                if st_val in DeploymentStatus.__members__
                else DeploymentStatus.STARTED
            )
            dep_at = _parse_dt(rec.get("deployed_at")) or datetime.now(UTC)

            dep_obj = Deployment(
                id=dep_id,
                company_id=_to_uuid(rec["company_id"]),
                service=rec["service"],
                version=rec["version"],
                environment=rec.get("environment", "production"),
                status=st_enum,
                deployed_at=dep_at,
                deployed_by=rec.get("deployed_by", "system"),
                deployment_metadata=rec.get("deployment_metadata", {}),
                created_at=dep_at,
            )
            to_insert.append(dep_obj)

        self._flush_chunks_with_id_check(Deployment, to_insert, summary)

    def load_support_tickets(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> None:
        """Batch loads support tickets."""
        if not records:
            return

        to_insert = []
        for rec in records:
            t_id = _to_uuid(rec.get("id", uuid.uuid4()))
            prio_val = str(rec.get("priority", "MEDIUM")).upper()
            prio_enum = (
                TicketPriority[prio_val]
                if prio_val in TicketPriority.__members__
                else TicketPriority.MEDIUM
            )

            st_val = str(rec.get("status", "OPEN")).upper()
            st_enum = (
                TicketStatus[st_val] if st_val in TicketStatus.__members__ else TicketStatus.OPEN
            )

            c_at = _parse_dt(rec.get("created_at")) or datetime.now(UTC)
            r_at = _parse_dt(rec.get("resolved_at"))

            cust_id = _to_uuid(rec["customer_id"]) if rec.get("customer_id") else None

            ticket_obj = SupportTicket(
                id=t_id,
                company_id=_to_uuid(rec["company_id"]),
                customer_id=cust_id,
                category=rec.get("category", "General"),
                priority=prio_enum,
                status=st_enum,
                summary=rec.get("summary", ""),
                created_at=c_at,
                resolved_at=r_at,
                ticket_metadata=rec.get("ticket_metadata", {}),
            )
            to_insert.append(ticket_obj)

        self._flush_chunks_with_id_check(SupportTicket, to_insert, summary)

    def load_complaints(
        self, records: list[dict[str, Any]], summary: EntityIngestionSummary
    ) -> None:
        """Batch loads customer complaints."""
        if not records:
            return

        to_insert = []
        for rec in records:
            c_id = _to_uuid(rec.get("id", uuid.uuid4()))
            sev_val = str(rec.get("severity", "MEDIUM")).upper()
            sev_enum = (
                SeverityLevel[sev_val]
                if sev_val in SeverityLevel.__members__
                else SeverityLevel.MEDIUM
            )

            c_at = _parse_dt(rec.get("created_at")) or datetime.now(UTC)
            r_at = _parse_dt(rec.get("resolved_at"))
            cust_id = _to_uuid(rec["customer_id"]) if rec.get("customer_id") else None

            comp_obj = CustomerComplaint(
                id=c_id,
                company_id=_to_uuid(rec["company_id"]),
                customer_id=cust_id,
                category=rec.get("category", "General"),
                severity=sev_enum,
                summary=rec.get("summary", ""),
                created_at=c_at,
                resolved_at=r_at,
                complaint_metadata=rec.get("complaint_metadata", {}),
            )
            to_insert.append(comp_obj)

        self._flush_chunks_with_id_check(CustomerComplaint, to_insert, summary)

    def _flush_chunks(self, entities: list[Any], summary: EntityIngestionSummary) -> None:
        """Flushes entity objects into database in transactional chunks."""
        for i in range(0, len(entities), self.batch_size):
            chunk = entities[i : i + self.batch_size]
            self.session.add_all(chunk)
            self.session.commit()
            summary.inserted += len(chunk)

    def _flush_chunks_with_id_check(
        self, model_cls: Any, entities: list[Any], summary: EntityIngestionSummary
    ) -> None:
        """Batches inserts while filtering out existing primary key IDs for idempotency."""
        for i in range(0, len(entities), self.batch_size):
            chunk = entities[i : i + self.batch_size]
            chunk_ids = [e.id for e in chunk]
            existing_ids = set(
                self.session.scalars(select(model_cls.id).where(model_cls.id.in_(chunk_ids))).all()
            )

            insertable = [e for e in chunk if e.id not in existing_ids]
            summary.duplicates += len(chunk) - len(insertable)

            if insertable:
                self.session.add_all(insertable)
                self.session.commit()
                summary.inserted += len(insertable)
