"""Unified Telemetry Ingestion Service coordinating validation, sanitization,
normalization, deduplication, persistence, and source health tracking.
"""

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.company import Company
from app.models.enums import SeverityLevel
from app.models.events import SystemEvent
from app.models.metrics import OperationalMetric
from app.models.telemetry import TelemetrySourceState
from app.models.trace import TraceSpan
from app.security.sanitizer import DataSanitizer
from app.telemetry.adapters.opentelemetry import OpenTelemetryAdapter
from app.telemetry.deduplication import TelemetryDeduplicator
from app.telemetry.normalizer import EnvironmentNormalizer, MetricNameNormalizer, ServiceIdentityNormalizer
from app.telemetry.rate_limiter import ingestion_rate_limiter
from app.telemetry.schemas import (
    BatchTelemetryPayload,
    DataQualityMetrics,
    IngestionResult,
    SourceHealthStatus,
    SourceStatus,
    TelemetryEventType,
    TelemetryExploreItem,
    TelemetryExploreQuery,
    TelemetryRecord,
    TelemetrySourceType,
)
from app.telemetry.trace_deduplication import trace_deduplicator
from app.telemetry.trace_normalizer import TraceNormalizer
from app.telemetry.trace_schemas import BatchTracePayload, TraceIngestionResult

logger = get_logger("aegis.telemetry.service")


class TelemetryIngestionService:
    """Enterprise ingestion service for metrics, logs, events, and distributed traces."""

    def __init__(self) -> None:
        self.metric_deduplicator = TelemetryDeduplicator(max_entries=50000, ttl_seconds=600.0)
        self.otel_adapter = OpenTelemetryAdapter()

    def _resolve_company_id(self, db: Session, target_company_id: Optional[uuid.UUID] = None) -> uuid.UUID:
        """Resolves target company or fallback default company."""
        if target_company_id:
            comp = db.get(Company, target_company_id)
            if comp:
                return comp.id

        first_comp = db.scalar(select(Company).limit(1))
        if first_comp:
            return first_comp.id

        # Auto-create default tenant if database is completely empty
        new_comp = Company(
            id=uuid.uuid4(),
            name="Acme Cloud Commerce",
            slug="acme-cloud-commerce",
            industry="E-Commerce",
        )
        db.add(new_comp)
        db.flush()
        return new_comp.id

    def _update_source_health(
        self,
        db: Session,
        source_name: str,
        source_type: TelemetrySourceType,
        received_count: int,
        rejected_count: int,
        error_msg: Optional[str] = None,
    ) -> None:
        """Updates or registers persistent source health state."""
        state = db.scalar(select(TelemetrySourceState).where(TelemetrySourceState.source == source_name))
        now = datetime.now(UTC)

        if not state:
            state = TelemetrySourceState(
                source=source_name,
                source_type=source_type,
                status=SourceStatus.HEALTHY if not error_msg else SourceStatus.DEGRADED,
                records_received=received_count,
                records_rejected=rejected_count,
                last_success_at=now if not error_msg else None,
                last_failure_at=now if error_msg else None,
                last_error=error_msg,
            )
            db.add(state)
        else:
            state.records_received += received_count
            state.records_rejected += rejected_count
            if error_msg:
                state.last_failure_at = now
                state.last_error = error_msg
                state.status = SourceStatus.DEGRADED
            else:
                state.last_success_at = now
                state.status = SourceStatus.HEALTHY
                state.last_error = None

        db.commit()

    def ingest_batch(
        self,
        db: Session,
        payload: BatchTelemetryPayload,
        client_key: str = "default_client",
        company_id: Optional[uuid.UUID] = None,
    ) -> IngestionResult:
        """Validates, sanitizes, normalizes, deduplicates, and stores telemetry records."""
        # 1. Backpressure and Rate Limiting
        ingestion_rate_limiter.check_rate_limit(client_key)
        ingestion_rate_limiter.validate_batch_size(len(payload.events))

        batch_id = str(uuid.uuid4())
        accepted = 0
        rejected = 0
        duplicates = 0
        errors: list[str] = []

        target_company_id = self._resolve_company_id(db, company_id)

        metrics_to_insert: list[OperationalMetric] = []
        events_to_insert: list[SystemEvent] = []

        for idx, raw_item in enumerate(payload.events):
            try:
                # 2. Extract and Validate Record
                raw_service = raw_item.get("service") or raw_item.get("service_name") or "unknown-service"
                service = ServiceIdentityNormalizer.normalize(raw_service)
                env = EnvironmentNormalizer.normalize(raw_item.get("environment"))

                # 3. Privacy Sanitization via Group 7 Controls
                raw_dims = raw_item.get("dimensions") or raw_item.get("attributes") or {}
                sanitized_dims = DataSanitizer.sanitize_dict(raw_dims)
                sanitized_msg = DataSanitizer.sanitize_text(raw_item.get("message")) if raw_item.get("message") else None

                # Timestamp
                raw_ts = raw_item.get("timestamp") or raw_item.get("time")
                if isinstance(raw_ts, (int, float)):
                    ts = datetime.fromtimestamp(raw_ts if raw_ts < 1e11 else raw_ts / 1000.0, tz=UTC)
                elif isinstance(raw_ts, str):
                    cleaned = raw_ts.replace("Z", "+00:00")
                    ts = datetime.fromisoformat(cleaned)
                    if not ts.tzinfo:
                        ts = ts.replace(tzinfo=UTC)
                else:
                    ts = datetime.now(UTC)

                # 4. Deduplication Fingerprinting
                metric_name = raw_item.get("metric_name")
                normalized_metric = MetricNameNormalizer.normalize(metric_name) if metric_name else None
                event_id = str(raw_item.get("id") or "")
                fingerprint = self.metric_deduplicator.compute_fingerprint(
                    source=payload.source,
                    timestamp_iso=ts.isoformat(),
                    service=service,
                    metric_name=normalized_metric,
                    event_id=event_id,
                    dimensions=sanitized_dims,
                )

                if self.metric_deduplicator.is_duplicate(fingerprint):
                    duplicates += 1
                    continue

                event_type_str = str(raw_item.get("event_type", "METRIC")).upper()
                trace_id = raw_item.get("trace_id")
                span_id = raw_item.get("span_id")
                val = raw_item.get("value")

                # 5. Route to Metric or System Event
                if event_type_str == "METRIC" or val is not None or normalized_metric:
                    m_val = float(val) if val is not None else 0.0
                    metric_obj = OperationalMetric(
                        id=uuid.uuid4(),
                        company_id=target_company_id,
                        metric_name=normalized_metric or "api_latency",
                        timestamp=ts,
                        value=m_val,
                        unit=raw_item.get("unit", "ms"),
                        source=payload.source,
                        dimension_data={"service": service, "environment": env, **sanitized_dims},
                        trace_id=trace_id,
                        span_id=span_id,
                        ingestion_timestamp=datetime.now(UTC),
                        schema_version="1.0",
                        created_at=datetime.now(UTC),
                    )
                    metrics_to_insert.append(metric_obj)
                    accepted += 1
                else:
                    sev_str = str(raw_item.get("severity", "INFO")).upper()
                    sev_enum = SeverityLevel[sev_str] if sev_str in SeverityLevel.__members__ else SeverityLevel.INFO

                    event_obj = SystemEvent(
                        id=uuid.uuid4(),
                        company_id=target_company_id,
                        event_type=event_type_str,
                        severity=sev_enum,
                        service=service,
                        environment=env,
                        message=sanitized_msg or f"{event_type_str} received from {payload.source}",
                        timestamp=ts,
                        event_metadata=sanitized_dims,
                        source=payload.source,
                        trace_id=trace_id,
                        span_id=span_id,
                        ingestion_timestamp=datetime.now(UTC),
                        schema_version="1.0",
                        created_at=datetime.now(UTC),
                    )
                    events_to_insert.append(event_obj)
                    accepted += 1

            except Exception as e:
                rejected += 1
                errors.append(f"Item #{idx} error: {str(e)}")

        # Batch insert
        if metrics_to_insert:
            db.add_all(metrics_to_insert)
        if events_to_insert:
            db.add_all(events_to_insert)

        db.commit()

        # Update source health
        self._update_source_health(
            db=db,
            source_name=payload.source,
            source_type=payload.source_type,
            received_count=accepted + duplicates,
            rejected_count=rejected,
            error_msg=errors[0] if errors else None,
        )

        return IngestionResult(
            accepted=accepted,
            rejected=rejected,
            duplicates=duplicates,
            source=payload.source,
            batch_id=batch_id,
            errors=errors[:10],
        )

    def ingest_traces(
        self,
        db: Session,
        payload: BatchTracePayload,
        client_key: str = "default_client",
        company_id: Optional[uuid.UUID] = None,
    ) -> TraceIngestionResult:
        """Normalizes, sanitizes, deduplicates, and stores distributed trace spans."""
        ingestion_rate_limiter.check_rate_limit(client_key)
        ingestion_rate_limiter.validate_batch_size(len(payload.spans))

        batch_id = str(uuid.uuid4())
        accepted = 0
        rejected = 0
        duplicates = 0
        malformed = 0
        errors: list[str] = []

        target_company_id = self._resolve_company_id(db, company_id)
        spans_to_insert: list[TraceSpan] = []

        for idx, raw_span in enumerate(payload.spans):
            try:
                norm_span, norm_err = TraceNormalizer.normalize_span(
                    raw_span=raw_span,
                    default_source=payload.source,
                )

                if norm_err or not norm_span:
                    malformed += 1
                    errors.append(f"Span #{idx} malformed: {norm_err}")
                    continue

                # Deduplication check
                fp = trace_deduplicator.compute_fingerprint(
                    source=payload.source,
                    trace_id=norm_span.trace_id,
                    span_id=norm_span.span_id,
                    timestamp_start_iso=norm_span.timestamp_start.isoformat(),
                )

                if trace_deduplicator.is_duplicate(fp):
                    duplicates += 1
                    continue

                span_entity = TraceSpan(
                    id=norm_span.id,
                    company_id=target_company_id,
                    trace_id=norm_span.trace_id,
                    span_id=norm_span.span_id,
                    parent_span_id=norm_span.parent_span_id,
                    timestamp_start=norm_span.timestamp_start,
                    timestamp_end=norm_span.timestamp_end,
                    duration_ms=norm_span.duration_ms,
                    service_name=norm_span.service_name,
                    service_version=norm_span.service_version,
                    environment=norm_span.environment,
                    operation_name=norm_span.operation_name,
                    span_kind=norm_span.span_kind,
                    status=norm_span.status,
                    status_message=norm_span.status_message,
                    http_method=norm_span.http_method,
                    http_route=norm_span.http_route,
                    http_status_code=norm_span.http_status_code,
                    rpc_system=norm_span.rpc_system,
                    rpc_service=norm_span.rpc_service,
                    rpc_method=norm_span.rpc_method,
                    database_system=norm_span.database_system,
                    database_operation=norm_span.database_operation,
                    peer_service=norm_span.peer_service,
                    host=norm_span.host,
                    trace_flags=norm_span.trace_flags,
                    source=norm_span.source,
                    schema_version=norm_span.schema_version,
                    ingestion_timestamp=norm_span.ingestion_timestamp,
                    sanitized_attributes=norm_span.sanitized_attributes,
                    created_at=datetime.now(UTC),
                )
                spans_to_insert.append(span_entity)
                accepted += 1

            except Exception as e:
                rejected += 1
                errors.append(f"Span #{idx} error: {str(e)}")

        if spans_to_insert:
            db.add_all(spans_to_insert)
            db.commit()

        self._update_source_health(
            db=db,
            source_name=payload.source,
            source_type=payload.source_type,
            received_count=accepted + duplicates,
            rejected_count=rejected + malformed,
            error_msg=errors[0] if errors else None,
        )

        return TraceIngestionResult(
            accepted=accepted,
            rejected=rejected,
            duplicates=duplicates,
            malformed=malformed,
            source=payload.source,
            batch_id=batch_id,
            errors=errors[:10],
        )

    def ingest_otel(
        self,
        db: Session,
        raw_payload: dict[str, Any],
        client_key: str = "default_client",
        company_id: Optional[uuid.UUID] = None,
    ) -> IngestionResult:
        """Parses and ingests OTLP JSON payload containing metrics, logs, and spans."""
        valid, validation_errors = self.otel_adapter.validate(raw_payload)
        if not valid:
            return IngestionResult(
                accepted=0,
                rejected=len(raw_payload),
                duplicates=0,
                source="opentelemetry",
                batch_id=str(uuid.uuid4()),
                errors=validation_errors,
            )

        # 1. Parse standard records (metrics & logs)
        records = self.otel_adapter.normalize(raw_payload)
        event_dicts = [
            {
                "service": r.service,
                "environment": r.environment,
                "timestamp": r.timestamp.isoformat(),
                "event_type": r.event_type.value,
                "metric_name": r.metric_name,
                "value": r.value,
                "unit": r.unit,
                "severity": r.severity,
                "message": r.message,
                "trace_id": r.trace_id,
                "span_id": r.span_id,
                "parent_span_id": r.parent_span_id,
                "dimensions": r.dimensions,
            }
            for r in records
        ]

        batch_payload = BatchTelemetryPayload(
            source="opentelemetry",
            source_type=TelemetrySourceType.OTEL,
            events=event_dicts,
        )
        ingest_res = self.ingest_batch(db, batch_payload, client_key, company_id)

        # 2. Extract and ingest spans if resourceSpans is present
        if "resourceSpans" in raw_payload:
            spans_list: list[dict[str, Any]] = []
            for rs in raw_payload.get("resourceSpans", []):
                res_attrs = {}
                for itm in rs.get("resource", {}).get("attributes", []):
                    k = itm.get("key")
                    v = itm.get("value", {})
                    res_attrs[k] = v.get("stringValue") or v.get("intValue") or v
                svc = res_attrs.get("service.name", "otel-service")
                env = res_attrs.get("deployment.environment", "production")

                for ss in rs.get("scopeSpans", []):
                    for sp in ss.get("spans", []):
                        sp_dict = dict(sp)
                        sp_dict["service"] = svc
                        sp_dict["environment"] = env
                        spans_list.append(sp_dict)

            if spans_list:
                trace_payload = BatchTracePayload(
                    source="opentelemetry",
                    source_type=TelemetrySourceType.OTEL,
                    spans=spans_list,
                )
                trace_res = self.ingest_traces(db, trace_payload, client_key, company_id)
                ingest_res.accepted += trace_res.accepted
                ingest_res.rejected += trace_res.rejected
                ingest_res.duplicates += trace_res.duplicates

        return ingest_res

    def get_source_health(self, db: Session) -> list[SourceHealthStatus]:
        """Returns health and status of all registered sources."""
        states = db.scalars(select(TelemetrySourceState).order_by(TelemetrySourceState.source.asc())).all()
        result: list[SourceHealthStatus] = []
        for s in states:
            result.append(
                SourceHealthStatus(
                    source=s.source,
                    source_type=s.source_type,
                    status=s.status,
                    last_success=s.last_success_at,
                    last_failure=s.last_failure_at,
                    records_received=s.records_received,
                    records_rejected=s.records_rejected,
                    error_message=s.last_error,
                )
            )
        return result

    def get_quality_metrics(self, db: Session) -> DataQualityMetrics:
        """Returns aggregate data quality indicators across all sources."""
        sources = db.scalars(select(TelemetrySourceState)).all()
        total_rcv = sum(s.records_received for s in sources)
        total_rej = sum(s.records_rejected for s in sources)
        active_cnt = sum(1 for s in sources if s.status == SourceStatus.HEALTHY)

        return DataQualityMetrics(
            records_received=total_rcv,
            records_accepted=max(0, total_rcv - total_rej),
            records_rejected=total_rej,
            duplicates_filtered=self.metric_deduplicator.duplicate_count + trace_deduplicator.duplicate_count,
            active_sources_count=active_cnt,
        )

    def explore_telemetry(self, db: Session, query: TelemetryExploreQuery) -> list[TelemetryExploreItem]:
        """Queries operational metrics and events matching filters."""
        items: list[TelemetryExploreItem] = []

        # Query metrics
        m_q = select(OperationalMetric)
        if query.metric_name:
            m_q = m_q.where(OperationalMetric.metric_name == query.metric_name)
        if query.source:
            m_q = m_q.where(OperationalMetric.source == query.source)
        if query.start_time:
            m_q = m_q.where(OperationalMetric.timestamp >= query.start_time)
        if query.end_time:
            m_q = m_q.where(OperationalMetric.timestamp <= query.end_time)

        metrics = db.scalars(m_q.order_by(OperationalMetric.timestamp.desc()).limit(query.limit)).all()
        for m in metrics:
            svc = m.dimension_data.get("service", "unknown-service")
            env = m.dimension_data.get("environment", "production")
            if query.service and svc != query.service:
                continue
            if query.environment and env != query.environment:
                continue

            items.append(
                TelemetryExploreItem(
                    id=str(m.id),
                    timestamp=m.timestamp,
                    ingestion_timestamp=m.ingestion_timestamp or m.timestamp,
                    source=m.source,
                    service=svc,
                    environment=env,
                    metric_name=m.metric_name,
                    value=m.value,
                    unit=m.unit,
                    severity="INFO",
                    trace_id=m.trace_id,
                )
            )

        # Query events
        e_q = select(SystemEvent)
        if query.source:
            e_q = e_q.where(SystemEvent.source == query.source)
        if query.service:
            e_q = e_q.where(SystemEvent.service == query.service)
        if query.environment:
            e_q = e_q.where(SystemEvent.environment == query.environment)
        if query.start_time:
            e_q = e_q.where(SystemEvent.timestamp >= query.start_time)
        if query.end_time:
            e_q = e_q.where(SystemEvent.timestamp <= query.end_time)

        events = db.scalars(e_q.order_by(SystemEvent.timestamp.desc()).limit(query.limit)).all()
        for ev in events:
            items.append(
                TelemetryExploreItem(
                    id=str(ev.id),
                    timestamp=ev.timestamp,
                    ingestion_timestamp=ev.ingestion_timestamp or ev.timestamp,
                    source=ev.source,
                    service=ev.service,
                    environment=ev.environment,
                    severity=ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity),
                    message=ev.message,
                    trace_id=ev.trace_id,
                )
            )

        # Sort combined items by timestamp descending
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items[: query.limit]
