"""Synthetic Distributed Trace Generator for Realistic Microservices Scenarios."""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from app.models.trace import TraceSpan


class SyntheticTraceGenerator:
    """Generates realistic distributed traces across e-commerce microservices."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def generate_trace_id(self) -> str:
        """Generates 32-hex character W3C trace ID."""
        return uuid.UUID(int=self.rng.getrandbits(128)).hex

    def generate_span_id(self) -> str:
        """Generates 16-hex character W3C span ID."""
        return f"{self.rng.getrandbits(64):016x}"

    def generate_normal_checkout_trace(
        self,
        company_id: uuid.UUID,
        start_time: datetime,
        service_version: str = "v4.8.1",
        environment: str = "production",
    ) -> list[TraceSpan]:
        """Generates healthy checkout trace across 6 microservices:

        api-gateway -> checkout-service -> order-service -> inventory-service -> payment-service -> postgres-cluster
        """
        trace_id = self.generate_trace_id()
        spans: list[TraceSpan] = []

        # 1. Gateway Span (Root)
        gateway_span_id = self.generate_span_id()
        gw_lat = self.rng.uniform(70.0, 130.0)

        # 2. Checkout Service Span
        checkout_span_id = self.generate_span_id()
        co_lat = gw_lat - self.rng.uniform(10.0, 20.0)

        # 3. Order Service Span
        order_span_id = self.generate_span_id()
        ord_lat = co_lat - self.rng.uniform(15.0, 25.0)

        # 4. Inventory Service Span
        inv_span_id = self.generate_span_id()
        inv_lat = self.rng.uniform(10.0, 25.0)

        # 5. Payment Gateway Span
        pay_span_id = self.generate_span_id()
        pay_lat = self.rng.uniform(20.0, 45.0)

        # 6. Database Span
        db_span_id = self.generate_span_id()
        db_lat = self.rng.uniform(5.0, 15.0)

        now = datetime.now(UTC)

        # Gateway (Root)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=gateway_span_id,
                parent_span_id=None,
                timestamp_start=start_time,
                timestamp_end=start_time + timedelta(milliseconds=gw_lat),
                duration_ms=round(gw_lat, 2),
                service_name="api-gateway",
                service_version=service_version,
                environment=environment,
                operation_name="POST /api/v1/checkout",
                span_kind="SERVER",
                status="OK",
                http_method="POST",
                http_route="/api/v1/checkout",
                http_status_code=200,
                peer_service="client-browser",
                source="opentelemetry",
                sanitized_attributes={"http.status_code": 200, "http.method": "POST"},
                created_at=now,
            )
        )

        # Checkout
        co_start = start_time + timedelta(milliseconds=5.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=checkout_span_id,
                parent_span_id=gateway_span_id,
                timestamp_start=co_start,
                timestamp_end=co_start + timedelta(milliseconds=co_lat),
                duration_ms=round(co_lat, 2),
                service_name="checkout-service",
                service_version=service_version,
                environment=environment,
                operation_name="process_checkout_flow",
                span_kind="INTERNAL",
                status="OK",
                http_method="POST",
                http_route="/checkout",
                http_status_code=200,
                source="opentelemetry",
                sanitized_attributes={"checkout.type": "standard"},
                created_at=now,
            )
        )

        # Order
        ord_start = co_start + timedelta(milliseconds=8.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=order_span_id,
                parent_span_id=checkout_span_id,
                timestamp_start=ord_start,
                timestamp_end=ord_start + timedelta(milliseconds=ord_lat),
                duration_ms=round(ord_lat, 2),
                service_name="order-service",
                service_version=service_version,
                environment=environment,
                operation_name="create_order",
                span_kind="INTERNAL",
                status="OK",
                rpc_system="grpc",
                rpc_service="OrderService",
                rpc_method="CreateOrder",
                source="opentelemetry",
                sanitized_attributes={"order.currency": "USD"},
                created_at=now,
            )
        )

        # Inventory (child of order)
        inv_start = ord_start + timedelta(milliseconds=5.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=inv_span_id,
                parent_span_id=order_span_id,
                timestamp_start=inv_start,
                timestamp_end=inv_start + timedelta(milliseconds=inv_lat),
                duration_ms=round(inv_lat, 2),
                service_name="inventory-service",
                service_version=service_version,
                environment=environment,
                operation_name="reserve_stock",
                span_kind="CLIENT",
                peer_service="inventory-service",
                status="OK",
                source="opentelemetry",
                sanitized_attributes={"items.count": 2},
                created_at=now,
            )
        )

        # Payment (child of checkout)
        pay_start = ord_start + timedelta(milliseconds=ord_lat - pay_lat - 5.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=pay_span_id,
                parent_span_id=checkout_span_id,
                timestamp_start=pay_start,
                timestamp_end=pay_start + timedelta(milliseconds=pay_lat),
                duration_ms=round(pay_lat, 2),
                service_name="payment-service",
                service_version=service_version,
                environment=environment,
                operation_name="charge_authorization",
                span_kind="CLIENT",
                peer_service="payment-gateway",
                status="OK",
                http_method="POST",
                http_status_code=200,
                source="opentelemetry",
                sanitized_attributes={"payment.provider": "stripe_simulated"},
                created_at=now,
            )
        )

        # Database (child of order)
        db_start = ord_start + timedelta(milliseconds=10.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=db_span_id,
                parent_span_id=order_span_id,
                timestamp_start=db_start,
                timestamp_end=db_start + timedelta(milliseconds=db_lat),
                duration_ms=round(db_lat, 2),
                service_name="postgres-cluster",
                service_version="15.4",
                environment=environment,
                operation_name="INSERT INTO orders",
                span_kind="CLIENT",
                status="OK",
                database_system="postgresql",
                database_operation="INSERT",
                source="opentelemetry",
                sanitized_attributes={"db.name": "commerce_db"},
                created_at=now,
            )
        )

        return spans

    def generate_degraded_incident_trace(
        self,
        company_id: uuid.UUID,
        start_time: datetime,
        service_version: str = "v4.8.2",
        environment: str = "production",
        is_hard_failure: bool = False,
    ) -> list[TraceSpan]:
        """Generates degraded or failing checkout trace reflecting deployment v4.8.2 regression.

        payment-service latency surges to 1800-2500ms; if is_hard_failure, payment-service throws 500,
        checkout-service returns 502, api-gateway returns 500.
        """
        trace_id = self.generate_trace_id()
        spans: list[TraceSpan] = []

        gateway_span_id = self.generate_span_id()
        checkout_span_id = self.generate_span_id()
        order_span_id = self.generate_span_id()
        pay_span_id = self.generate_span_id()

        pay_lat = self.rng.uniform(1800.0, 2600.0) if not is_hard_failure else self.rng.uniform(800.0, 1500.0)
        co_lat = pay_lat + self.rng.uniform(50.0, 120.0)
        gw_lat = co_lat + self.rng.uniform(20.0, 40.0)
        ord_lat = 45.0

        now = datetime.now(UTC)
        gw_status = "ERROR" if is_hard_failure else "OK"
        gw_code = 500 if is_hard_failure else 200
        co_status = "ERROR" if is_hard_failure else "OK"
        co_code = 502 if is_hard_failure else 200
        pay_status = "ERROR" if is_hard_failure else "OK"
        pay_code = 500 if is_hard_failure else 200
        pay_msg = "Upstream connection reset during handshake" if is_hard_failure else None

        # 1. Gateway
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=gateway_span_id,
                parent_span_id=None,
                timestamp_start=start_time,
                timestamp_end=start_time + timedelta(milliseconds=gw_lat),
                duration_ms=round(gw_lat, 2),
                service_name="api-gateway",
                service_version="v4.8.1",
                environment=environment,
                operation_name="POST /api/v1/checkout",
                span_kind="SERVER",
                status=gw_status,
                status_message="Internal server error on downstream checkout invocation" if is_hard_failure else None,
                http_method="POST",
                http_route="/api/v1/checkout",
                http_status_code=gw_code,
                peer_service="client-browser",
                source="opentelemetry",
                sanitized_attributes={"http.status_code": gw_code, "http.method": "POST"},
                created_at=now,
            )
        )

        # 2. Checkout
        co_start = start_time + timedelta(milliseconds=5.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=checkout_span_id,
                parent_span_id=gateway_span_id,
                timestamp_start=co_start,
                timestamp_end=co_start + timedelta(milliseconds=co_lat),
                duration_ms=round(co_lat, 2),
                service_name="checkout-service",
                service_version="v4.8.1",
                environment=environment,
                operation_name="process_checkout_flow",
                span_kind="INTERNAL",
                status=co_status,
                status_message="Bad gateway response from payment provider" if is_hard_failure else None,
                http_method="POST",
                http_route="/checkout",
                http_status_code=co_code,
                source="opentelemetry",
                sanitized_attributes={"checkout.error": "payment_failure" if is_hard_failure else "none"},
                created_at=now,
            )
        )

        # 3. Order
        ord_start = co_start + timedelta(milliseconds=8.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=order_span_id,
                parent_span_id=checkout_span_id,
                timestamp_start=ord_start,
                timestamp_end=ord_start + timedelta(milliseconds=ord_lat),
                duration_ms=round(ord_lat, 2),
                service_name="order-service",
                service_version="v4.8.1",
                environment=environment,
                operation_name="create_order",
                span_kind="INTERNAL",
                status="OK",
                rpc_system="grpc",
                rpc_service="OrderService",
                rpc_method="CreateOrder",
                source="opentelemetry",
                sanitized_attributes={"order.currency": "USD"},
                created_at=now,
            )
        )

        # 4. Payment Gateway (Culprit with v4.8.2)
        pay_start = ord_start + timedelta(milliseconds=ord_lat + 2.0)
        spans.append(
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=pay_span_id,
                parent_span_id=checkout_span_id,
                timestamp_start=pay_start,
                timestamp_end=pay_start + timedelta(milliseconds=pay_lat),
                duration_ms=round(pay_lat, 2),
                service_name="payment-service",
                service_version=service_version,  # v4.8.2
                environment=environment,
                operation_name="charge_authorization",
                span_kind="CLIENT",
                peer_service="payment-gateway",
                status=pay_status,
                status_message=pay_msg,
                http_method="POST",
                http_status_code=pay_code,
                source="opentelemetry",
                sanitized_attributes={"payment.error_code": "GATEWAY_TIMEOUT" if is_hard_failure else "SLOW_AUTH"},
                created_at=now,
            )
        )

        return spans

    def generate_false_positive_trace(
        self,
        company_id: uuid.UUID,
        start_time: datetime,
        environment: str = "production",
    ) -> list[TraceSpan]:
        """Generates a harmless trace anomaly for internal reporting-worker.

        It runs slow (3500ms) but has zero impact on user checkout or business revenue.
        """
        trace_id = self.generate_trace_id()
        root_span_id = self.generate_span_id()
        db_span_id = self.generate_span_id()
        dur = self.rng.uniform(3200.0, 4200.0)
        now = datetime.now(UTC)

        spans = [
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=root_span_id,
                parent_span_id=None,
                timestamp_start=start_time,
                timestamp_end=start_time + timedelta(milliseconds=dur),
                duration_ms=round(dur, 2),
                service_name="reporting-worker",
                service_version="v1.2.0",
                environment=environment,
                operation_name="batch_aggregate_weekly_report",
                span_kind="INTERNAL",
                status="OK",
                source="opentelemetry",
                sanitized_attributes={"job.type": "internal_analytics", "is_background": True},
                created_at=now,
            ),
            TraceSpan(
                id=uuid.uuid4(),
                company_id=company_id,
                trace_id=trace_id,
                span_id=db_span_id,
                parent_span_id=root_span_id,
                timestamp_start=start_time + timedelta(milliseconds=10.0),
                timestamp_end=start_time + timedelta(milliseconds=dur - 10.0),
                duration_ms=round(dur - 20.0, 2),
                service_name="postgres-reporting-replica",
                service_version="15.4",
                environment=environment,
                operation_name="SELECT historical_aggregates",
                span_kind="CLIENT",
                status="OK",
                database_system="postgresql",
                database_operation="SELECT",
                source="opentelemetry",
                sanitized_attributes={"db.name": "analytics_replica"},
                created_at=now,
            ),
        ]
        return spans

    def simulate_incident_trace_scenario(
        self,
        company_id: uuid.UUID,
        base_time: Optional[datetime] = None,
    ) -> list[TraceSpan]:
        """Generates complete chronological trace scenario:
        - 14:00-14:10: Healthy normal checkout traffic
        - 14:05: Harmless reporting-worker slow trace (false positive test)
        - 14:11: Latency begins climbing in payment-service
        - 14:12: Severe latency degradation (1800ms-2500ms)
        - 14:14: Cascading HTTP 500/502 errors originating in payment-service
        - 14:15-14:25: Incident ongoing with high error concentration
        """
        if not base_time:
            now = datetime.now(UTC)
            base_time = now.replace(hour=14, minute=0, second=0, microsecond=0)

        all_spans: list[TraceSpan] = []

        # 1. 14:00 - 14:10: Healthy baseline traffic (15 traces)
        for i in range(15):
            t = base_time + timedelta(minutes=self.rng.uniform(0.5, 9.5))
            all_spans.extend(self.generate_normal_checkout_trace(company_id, t))

        # 2. 14:05: False-positive reporting-worker slow trace
        fp_time = base_time + timedelta(minutes=5.0)
        all_spans.extend(self.generate_false_positive_trace(company_id, fp_time))

        # 3. 14:11: Latency starts increasing
        t_1411 = base_time + timedelta(minutes=11.0)
        for i in range(5):
            t = t_1411 + timedelta(seconds=i * 12.0)
            all_spans.extend(self.generate_degraded_incident_trace(company_id, t, is_hard_failure=False))

        # 4. 14:12 - 14:13: Slow traces surge (payment latency 1800-2500ms)
        t_1412 = base_time + timedelta(minutes=12.0)
        for i in range(8):
            t = t_1412 + timedelta(seconds=i * 10.0)
            all_spans.extend(self.generate_degraded_incident_trace(company_id, t, is_hard_failure=False))

        # 5. 14:14: Hard failures spike (payment-service throws 500, checkout 502, gateway 500)
        t_1414 = base_time + timedelta(minutes=14.0)
        for i in range(10):
            t = t_1414 + timedelta(seconds=i * 5.0)
            all_spans.extend(self.generate_degraded_incident_trace(company_id, t, is_hard_failure=True))

        # 6. 14:15 - 14:25: Mixed degraded and failed traces
        t_1415 = base_time + timedelta(minutes=15.0)
        for i in range(10):
            t = t_1415 + timedelta(minutes=self.rng.uniform(0.5, 9.5))
            hard_fail = self.rng.random() < 0.60
            all_spans.extend(self.generate_degraded_incident_trace(company_id, t, is_hard_failure=hard_fail))

        return all_spans

