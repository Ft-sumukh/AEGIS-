"""Core enterprise simulation engine producing correlated operational telemetry."""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any

from app.generator.config import GeneratorConfig
from app.generator.incident import IncidentEngine
from app.generator.noise import StochasticNoiseEngine
from app.generator.seasonality import SeasonalityProfile


@dataclass
class GeneratedDataset:
    """In-memory container for the full synthetic enterprise dataset."""

    company: dict[str, Any]
    customers: list[dict[str, Any]]
    deployments: list[dict[str, Any]]
    system_events: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    orders: list[dict[str, Any]]
    order_items: list[dict[str, Any]]
    support_tickets: list[dict[str, Any]]
    complaints: list[dict[str, Any]]
    scenario_metadata: dict[str, Any]
    generation_stats: dict[str, Any] = field(default_factory=dict)


class EnterpriseDataSynthesizer:
    """Synthesizes realistic operational data with strict causal coupling."""

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        self.config = config or GeneratorConfig()
        self.noise = StochasticNoiseEngine(seed=self.config.seed)
        self.seasonality = SeasonalityProfile()
        self.incident_engine = IncidentEngine(self.config)

        # Base deterministic IDs
        self.company_id = uuid.uuid5(
            uuid.NAMESPACE_DNS, f"{self.config.company_name.lower()}.aegis.internal"
        )

    def synthesize(self) -> GeneratedDataset:
        """Executes full synthesis pipeline generating all correlated operational domains."""
        # 1. Company entity
        company = {
            "id": str(self.company_id),
            "name": self.config.company_name,
            "slug": self.config.company_name.lower().replace(" ", "-"),
            "industry": self.config.company_industry,
            "status": "ACTIVE",
            "metadata": {
                "tier": "enterprise",
                "cloud_provider": "aws",
                "primary_region": "us-east-1",
                "classification": self.config.data_classification,
            },
            "created_at": self.config.start_date.isoformat(),
        }

        # 2. Customers
        customers = self._generate_customers()

        # 3. Deployments
        deployments = self._generate_deployments()

        # 4. Hourly telemetry loop (Metrics, Orders, System Events, Tickets, Complaints)
        (
            metrics,
            orders,
            order_items,
            events,
            tickets,
            complaints,
        ) = self._generate_operational_timeline(customers)

        scenario_meta = self.incident_engine.get_scenario_metadata().__dict__

        stats = {
            "simulation_days": self.config.days,
            "simulation_hours": self.config.total_hours,
            "random_seed": self.config.seed,
            "total_customers": len(customers),
            "total_deployments": len(deployments),
            "total_metrics": len(metrics),
            "total_orders": len(orders),
            "total_order_items": len(order_items),
            "total_system_events": len(events),
            "total_support_tickets": len(tickets),
            "total_complaints": len(complaints),
        }

        return GeneratedDataset(
            company=company,
            customers=customers,
            deployments=deployments,
            system_events=events,
            metrics=metrics,
            orders=orders,
            order_items=order_items,
            support_tickets=tickets,
            complaints=complaints,
            scenario_metadata=scenario_meta,
            generation_stats=stats,
        )

    def _generate_customers(self) -> list[dict[str, Any]]:
        """Generates synthetic customer population with synthetic identities."""
        first_names = [
            "Alex",
            "Jordan",
            "Taylor",
            "Morgan",
            "Casey",
            "Riley",
            "Avery",
            "Sam",
            "Pat",
            "Quinn",
            "Chris",
            "Jamie",
            "Skyler",
            "Cameron",
            "Dakota",
        ]
        last_names = [
            "Chen",
            "Smith",
            "Patel",
            "Garcia",
            "Johnson",
            "Davis",
            "Miller",
            "Wilson",
            "Taylor",
            "Anderson",
            "Thomas",
            "Jackson",
            "White",
            "Harris",
            "Martin",
        ]
        regions = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]
        channels = ["ORGANIC", "PAID_SEARCH", "DIRECT", "SOCIAL", "PARTNER"]
        segments = ["NEW", "REGULAR", "PREMIUM"]

        customers = []
        for i in range(1, self.config.customer_count + 1):
            cust_uuid = uuid.uuid5(self.company_id, f"customer-{i:06d}")
            ext_ref = f"CUST-{i:06d}"
            fname = self.noise.choice(first_names)
            lname = self.noise.choice(last_names)
            name = f"{fname} {lname}"
            email = f"user.{i:06d}@example.com"
            phone = f"+1-555-{1000 + (i % 9000):04d}"
            region = self.noise.choice(regions)

            # Customer registration distributed in first 15 days or before simulation
            offset_days = self.noise.uniform(0.0, 15.0)
            created_at = self.config.start_date + timedelta(days=offset_days)

            customers.append(
                {
                    "id": str(cust_uuid),
                    "company_id": str(self.company_id),
                    "external_reference": ext_ref,
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "region": region,
                    "segment": self.noise.choice(segments),
                    "acquisition_channel": self.noise.choice(channels),
                    "created_at": created_at.isoformat(),
                    "updated_at": created_at.isoformat(),
                }
            )
        return customers

    def _generate_deployments(self) -> list[dict[str, Any]]:
        """Generates realistic deployment history over 90 days."""
        deployments = []

        # Scheduled routine deployments
        schedule = [
            (5, 10, 15, "auth-service", "v2.1.0", "SUCCESS", "ci-cd-runner"),
            (14, 14, 30, "catalog-service", "v3.4.0", "SUCCESS", "ci-cd-runner"),
            (28, 9, 45, "notification-service", "v1.9.2", "SUCCESS", "ci-cd-runner"),
            (35, 11, 20, "checkout-service", "v4.8.0", "SUCCESS", "ci-cd-runner"),
            (48, 15, 10, "payment-gateway", "v2.3.1", "SUCCESS", "ci-cd-runner"),
            (54, 10, 0, "checkout-service", "v4.8.1", "SUCCESS", "ci-cd-runner"),
            # The Injected Incident Deployment on Day 60
            (
                self.config.incidents.primary_day_offset,
                self.config.incidents.primary_start_hour,
                self.config.incidents.primary_start_minute,
                "checkout-service",
                "v4.8.2",
                "FAILED",
                "release-pipeline",
            ),
            # The Emergency Rollback Deployment on Day 60
            (
                self.config.incidents.primary_day_offset,
                self.config.incidents.primary_rollback_hour,
                0,
                "checkout-service",
                "v4.8.1",
                "SUCCESS",
                "sre-oncall-lead",
            ),
            (72, 13, 15, "catalog-service", "v3.4.1", "SUCCESS", "ci-cd-runner"),
            (84, 10, 30, "checkout-service", "v4.8.3", "SUCCESS", "ci-cd-runner"),
        ]

        for day, hr, minute, service, version, status, deployed_by in schedule:
            dep_time = self.config.start_date + timedelta(days=day, hours=hr, minutes=minute)
            dep_id = uuid.uuid5(self.company_id, f"deployment-{service}-{version}-{day}")

            meta = {
                "commit_hash": f"git-{abs(hash(f'{service}-{version}')) % 0xFFFFFF:06x}",
                "environment": "production",
                "pipeline_build": f"build-{day * 100 + hr}",
                "change_log": f"Scheduled production release of {service} {version}",
            }
            if version == "v4.8.2":
                meta["connection_pool_max"] = 5
                meta["connection_timeout_ms"] = 30000
                meta["release_notes"] = (
                    "Performance optimization: reduced connection pool to conservative limit"
                )
            elif version == "v4.8.1" and day == self.config.incidents.primary_day_offset:
                meta["rollback_reason"] = (
                    "EMERGENCY ROLLBACK: Connection starvation and 504 timeouts detected in checkout-service v4.8.2"
                )

            deployments.append(
                {
                    "id": str(dep_id),
                    "company_id": str(self.company_id),
                    "service": service,
                    "version": version,
                    "environment": "production",
                    "status": status,
                    "deployed_at": dep_time.isoformat(),
                    "deployed_by": deployed_by,
                    "deployment_metadata": meta,
                    "created_at": dep_time.isoformat(),
                }
            )

        return deployments

    def _generate_operational_timeline(
        self, customers: list[dict[str, Any]]
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        """Iterates hour-by-hour across 90 days generating causally synchronized datasets."""
        metrics: list[dict[str, Any]] = []
        orders: list[dict[str, Any]] = []
        order_items: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        tickets: list[dict[str, Any]] = []
        complaints: list[dict[str, Any]] = []

        total_hours = self.config.total_hours
        start_date = self.config.start_date
        window = self.incident_engine.window

        order_sequence = 0
        ticket_sequence = 0
        complaint_sequence = 0
        event_sequence = 0

        # Pre-seed incident system events on Day 60
        events.extend(self._create_incident_events(window))

        for hour_idx in range(total_hours):
            current_time = start_date + timedelta(hours=hour_idx)
            hour_mult = self.seasonality.get_combined_multiplier(current_time)

            # Secondary anomalies check
            is_marketing_spike = self.incident_engine.is_secondary_marketing_spike(current_time)
            is_network_blip = self.incident_engine.is_secondary_network_blip(current_time)
            is_weekend_promo = self.incident_engine.is_secondary_weekend_promo(current_time)

            # Incident degradation factor [0.0, 1.0]
            degradation = self.incident_engine.window.get_degradation_factor(current_time)

            # -------------------------------------------------------------
            # 1. CAUSAL ENGINE: TRAFFIC & ACTIVE USERS
            # -------------------------------------------------------------
            base_traffic = self.config.base_hourly_traffic * hour_mult
            if is_marketing_spike:
                base_traffic *= 1.55  # 55% traffic surge on marketing campaign
            elif is_weekend_promo:
                base_traffic *= 1.30  # 30% weekend flash sale surge

            traffic = int(
                round(
                    self.noise.additive_gaussian(
                        base_traffic, std_dev=base_traffic * 0.035, min_val=500
                    )
                )
            )

            # Active Users = ~35% of overall traffic browsing sessions
            active_users = int(
                round(traffic * self.noise.gaussian_multiplier(0.35, 0.02, 0.28, 0.42))
            )

            # -------------------------------------------------------------
            # 2. CAUSAL ENGINE: API LATENCY & ERROR RATE
            # -------------------------------------------------------------
            # Baseline latency: ~120ms +/- 8ms
            base_latency = 120.0 * self.noise.gaussian_multiplier(1.0, 0.05, 0.88, 1.15)
            if is_network_blip:
                base_latency = 285.0  # Transient benign network spike
            if degradation > 0:
                # Surges up to ~920ms at peak
                base_latency += degradation * (self.config.incidents.api_latency_ms_peak - 120.0)
            api_latency = round(max(30.0, base_latency), 2)

            # Baseline error rate: ~0.002 (0.2%) +/- 0.0005
            base_error = 0.002 * self.noise.gaussian_multiplier(1.0, 0.15, 0.6, 1.5)
            if degradation > 0:
                # Surges to ~16.5% at peak
                base_error += degradation * (self.config.incidents.api_error_rate_peak - 0.002)
            api_error_rate = round(max(0.0001, min(0.999, base_error)), 4)

            # -------------------------------------------------------------
            # 3. CAUSAL ENGINE: CHECKOUT FAILURE RATE
            # -------------------------------------------------------------
            # Baseline checkout failure rate: ~0.012 (1.2%)
            base_checkout_fail = 0.012 * self.noise.gaussian_multiplier(1.0, 0.12, 0.7, 1.4)
            if degradation > 0:
                # Surges to ~32% at peak
                base_checkout_fail += degradation * (
                    self.config.incidents.checkout_failure_rate_peak - 0.012
                )
            checkout_failure_rate = round(max(0.001, min(0.999, base_checkout_fail)), 4)

            # -------------------------------------------------------------
            # 4. CAUSAL ENGINE: CONVERSION RATE & ORDERS
            # -------------------------------------------------------------
            # Potential buyer conversion rate (~3.2% normal)
            attempted_conv_rate = self.config.base_conversion_rate * self.noise.gaussian_multiplier(
                1.0, 0.04, 0.9, 1.1
            )
            if is_weekend_promo:
                attempted_conv_rate *= 1.22  # High buying intent during promo
            if degradation > 0:
                attempted_conv_rate *= (
                    1.0 - 0.45 * degradation
                )  # User cart abandonment due to timeouts & errors

            total_order_attempts = max(1, int(round(active_users * attempted_conv_rate)))
            failed_orders_count = int(round(total_order_attempts * checkout_failure_rate))
            completed_orders_count = max(0, total_order_attempts - failed_orders_count)

            # Realized conversion rate = completed_orders / active_users
            actual_conversion_rate = round(completed_orders_count / max(1, active_users), 5)

            # -------------------------------------------------------------
            # 5. CAUSAL ENGINE: REVENUE
            # -------------------------------------------------------------
            # Mean basket value ~ $85.50
            avg_order_value = self.config.base_average_order_value * self.noise.gaussian_multiplier(
                1.0, 0.03, 0.92, 1.08
            )
            revenue_amount = round(completed_orders_count * avg_order_value, 2)

            # -------------------------------------------------------------
            # 6. CAUSAL ENGINE: SUPPORT TICKETS & CUSTOMER COMPLAINTS
            # -------------------------------------------------------------
            # Baseline tickets: ~0.015 per order attempt (e.g. 2-5 tickets per normal hour)
            baseline_ticket_lambda = max(0.5, total_order_attempts * 0.015)
            # Extra tickets generated directly by failed orders
            incident_ticket_boost = failed_orders_count * 0.35 if degradation > 0 else 0
            tickets_this_hour = self.noise.poisson_count(
                baseline_ticket_lambda + incident_ticket_boost
            )

            # Complaints: ~0.005 per order attempt + 0.20 per failed order during incident
            baseline_complaint_lambda = max(0.2, total_order_attempts * 0.005)
            incident_complaint_boost = failed_orders_count * 0.22 if degradation > 0 else 0
            complaints_this_hour = self.noise.poisson_count(
                baseline_complaint_lambda + incident_complaint_boost
            )

            # Resolution time: ~45 mins baseline, up to 185 mins under queue congestion
            avg_resolution_time = round(
                45.0 + degradation * 135.0 + self.noise.additive_gaussian(0, 5.0, -10.0), 1
            )

            # -------------------------------------------------------------
            # RECORD 12 HOURLY OPERATIONAL METRICS
            # -------------------------------------------------------------
            metric_defs = [
                ("traffic", float(traffic), "requests/hr", "cdn_edge", {"channel": "global"}),
                (
                    "active_users",
                    float(active_users),
                    "users/hr",
                    "analytics_session",
                    {"scope": "platform"},
                ),
                (
                    "orders",
                    float(total_order_attempts),
                    "count/hr",
                    "order_service",
                    {"type": "total_attempts"},
                ),
                (
                    "failed_orders",
                    float(failed_orders_count),
                    "count/hr",
                    "order_service",
                    {"type": "checkout_failed"},
                ),
                (
                    "checkout_failure_rate",
                    float(checkout_failure_rate),
                    "ratio",
                    "checkout_service",
                    {"service": "checkout-service"},
                ),
                (
                    "api_error_rate",
                    float(api_error_rate),
                    "ratio",
                    "api_gateway",
                    {"tier": "ingress"},
                ),
                (
                    "api_latency",
                    float(api_latency),
                    "milliseconds",
                    "api_gateway",
                    {"percentile": "p95"},
                ),
                ("revenue", float(revenue_amount), "USD", "billing_service", {"currency": "USD"}),
                (
                    "conversion_rate",
                    float(actual_conversion_rate),
                    "ratio",
                    "analytics_conversion",
                    {"metric": "net_conversion"},
                ),
                (
                    "support_ticket_count",
                    float(tickets_this_hour),
                    "count/hr",
                    "zendesk_sync",
                    {"queue": "customer_support"},
                ),
                (
                    "customer_complaint_count",
                    float(complaints_this_hour),
                    "count/hr",
                    "crm_feedback",
                    {"channel": "direct"},
                ),
                (
                    "average_resolution_time",
                    float(avg_resolution_time),
                    "minutes",
                    "support_ops",
                    {"unit": "minutes"},
                ),
            ]

            for m_name, m_val, m_unit, m_src, m_dims in metric_defs:
                # Check for intentional controlled missing value (0.3% probability)
                if self.noise.random() < self.config.incidents.missing_metric_probability:
                    continue

                m_uuid = uuid.uuid5(self.company_id, f"metric-{m_name}-{hour_idx}")
                metrics.append(
                    {
                        "id": str(m_uuid),
                        "company_id": str(self.company_id),
                        "metric_name": m_name,
                        "timestamp": current_time.isoformat(),
                        "value": m_val,
                        "unit": m_unit,
                        "source": m_src,
                        "dimension_data": m_dims,
                        "created_at": current_time.isoformat(),
                    }
                )

            # -------------------------------------------------------------
            # SAMPLE DETAILED ORDERS FOR THE HOUR
            # (Sample up to 10-15 representative individual orders per hour for DB realism)
            # -------------------------------------------------------------
            sample_order_count = min(12, total_order_attempts)
            sample_failed_count = min(
                sample_order_count, max(0, int(round(sample_order_count * checkout_failure_rate)))
            )
            sample_success_count = sample_order_count - sample_failed_count

            # Generate successful sample orders
            for _ in range(sample_success_count):
                order_sequence += 1
                cust = self.noise.choice(customers)
                ord_time = current_time + timedelta(minutes=self.noise.uniform(0.0, 59.0))
                amount = Decimal(
                    str(self.noise.lognormal_order_value(self.config.base_average_order_value))
                )
                ord_uuid = uuid.uuid5(self.company_id, f"order-{order_sequence:08d}")

                orders.append(
                    {
                        "id": str(ord_uuid),
                        "company_id": str(self.company_id),
                        "customer_id": cust["id"],
                        "external_reference": f"ORD-{order_sequence:08d}",
                        "status": "COMPLETED",
                        "currency": "USD",
                        "total_amount": float(amount),
                        "ordered_at": ord_time.isoformat(),
                        "created_at": ord_time.isoformat(),
                    }
                )

                # Line item
                item_uuid = uuid.uuid5(self.company_id, f"item-{order_sequence:08d}-1")
                order_items.append(
                    {
                        "id": str(item_uuid),
                        "order_id": str(ord_uuid),
                        "product_reference": f"SKU-{1000 + (order_sequence % 500):05d}",
                        "quantity": 1,
                        "unit_price": float(amount),
                        "total_price": float(amount),
                    }
                )

            # Generate failed sample orders
            for _ in range(sample_failed_count):
                order_sequence += 1
                cust = self.noise.choice(customers)
                ord_time = current_time + timedelta(minutes=self.noise.uniform(0.0, 59.0))
                amount = Decimal(
                    str(self.noise.lognormal_order_value(self.config.base_average_order_value))
                )
                ord_uuid = uuid.uuid5(self.company_id, f"order-{order_sequence:08d}")

                orders.append(
                    {
                        "id": str(ord_uuid),
                        "company_id": str(self.company_id),
                        "customer_id": cust["id"],
                        "external_reference": f"ORD-{order_sequence:08d}",
                        "status": "FAILED",
                        "currency": "USD",
                        "total_amount": float(amount),
                        "ordered_at": ord_time.isoformat(),
                        "created_at": ord_time.isoformat(),
                    }
                )

            # -------------------------------------------------------------
            # SAMPLE DETAILED TICKETS & COMPLAINTS
            # -------------------------------------------------------------
            if tickets_this_hour > 0:
                sample_t_count = min(3, tickets_this_hour)
                for _ in range(sample_t_count):
                    ticket_sequence += 1
                    cust = self.noise.choice(customers)
                    t_time = current_time + timedelta(minutes=self.noise.uniform(0.0, 59.0))
                    t_uuid = uuid.uuid5(self.company_id, f"ticket-{ticket_sequence:06d}")

                    priority = (
                        "CRITICAL"
                        if degradation > 0.5
                        else ("HIGH" if degradation > 0 else "MEDIUM")
                    )
                    category = (
                        "Checkout & Payment"
                        if degradation > 0
                        else self.noise.choice(
                            ["Order Status", "Return Request", "Account", "Billing"]
                        )
                    )
                    summary = (
                        "Checkout timed out; payment card declined with gateway 504 error"
                        if degradation > 0
                        else f"Inquiry regarding {category.lower()}"
                    )

                    resolved_at = (
                        (t_time + timedelta(minutes=avg_resolution_time)).isoformat()
                        if current_time < (start_date + timedelta(hours=total_hours - 24))
                        else None
                    )

                    tickets.append(
                        {
                            "id": str(t_uuid),
                            "company_id": str(self.company_id),
                            "customer_id": cust["id"],
                            "category": category,
                            "priority": priority,
                            "status": "RESOLVED" if resolved_at else "OPEN",
                            "summary": summary,
                            "created_at": t_time.isoformat(),
                            "resolved_at": resolved_at,
                            "ticket_metadata": {
                                "channel": "web_portal",
                                "incident_linked": degradation > 0,
                            },
                        }
                    )

            if complaints_this_hour > 0 and (degradation > 0 or self.noise.random() < 0.08):
                complaint_sequence += 1
                cust = self.noise.choice(customers)
                c_time = current_time + timedelta(minutes=self.noise.uniform(0.0, 59.0))
                c_uuid = uuid.uuid5(self.company_id, f"complaint-{complaint_sequence:06d}")
                sev = "HIGH" if degradation > 0.4 else "MEDIUM"
                summary = (
                    "Failed transaction during checkout: cart reset without confirmation"
                    if degradation > 0
                    else "Delivery delay or package damage complaint"
                )

                complaints.append(
                    {
                        "id": str(c_uuid),
                        "company_id": str(self.company_id),
                        "customer_id": cust["id"],
                        "category": "Checkout" if degradation > 0 else "Shipping",
                        "severity": sev,
                        "summary": summary,
                        "created_at": c_time.isoformat(),
                        "resolved_at": (c_time + timedelta(hours=6)).isoformat(),
                        "complaint_metadata": {
                            "sentiment_score": -0.85 if degradation > 0 else -0.35
                        },
                    }
                )

            # -------------------------------------------------------------
            # OCCASIONAL BASELINE SYSTEM EVENTS
            # -------------------------------------------------------------
            if self.noise.random() < 0.05:
                event_sequence += 1
                ev_time = current_time + timedelta(minutes=self.noise.uniform(0.0, 59.0))
                ev_uuid = uuid.uuid5(self.company_id, f"event-routine-{event_sequence}")
                events.append(
                    {
                        "id": str(ev_uuid),
                        "company_id": str(self.company_id),
                        "event_type": self.noise.choice(
                            ["SERVICE_RESTART", "CACHE_CLEAR", "CONFIG_RELOAD", "HEALTH_CHECK"]
                        ),
                        "severity": "INFO",
                        "service": self.noise.choice(
                            ["catalog-service", "auth-service", "notification-service"]
                        ),
                        "environment": "production",
                        "message": "Routine maintenance task executed successfully",
                        "timestamp": ev_time.isoformat(),
                        "event_metadata": {
                            "host": f"ip-10-0-1-{10 + (event_sequence % 40)}.internal"
                        },
                        "created_at": ev_time.isoformat(),
                    }
                )

        return metrics, orders, order_items, events, tickets, complaints

    def _create_incident_events(self, win: Any) -> list[dict[str, Any]]:
        """Creates causal system events pinpointing the root-cause timeline."""
        incident_events = [
            (
                win.deployment_time,
                "DEPLOYMENT_STARTED",
                "INFO",
                "checkout-service",
                "Deployment checkout-service v4.8.2 initiated by CI/CD runner",
                {"version": "v4.8.2"},
            ),
            (
                win.deployment_time + timedelta(minutes=1),
                "DEPLOYMENT_COMPLETED",
                "INFO",
                "checkout-service",
                "Deployment checkout-service v4.8.2 rolling update completed (5 pods ready)",
                {"version": "v4.8.2"},
            ),
            (
                win.latency_start,
                "DATABASE_WARNING",
                "WARNING",
                "checkout-service",
                "HikariCP connection pool reaching threshold: 5/5 active connections in use",
                {"active_connections": 5, "max_connections": 5, "pending_requests": 14},
            ),
            (
                win.error_start,
                "DATABASE_ERROR",
                "CRITICAL",
                "checkout-service",
                "HikariPool-1 - Connection is not available, request timed out after 30000ms",
                {"exception": "SQLTransientConnectionException", "pool": "HikariPool-1"},
            ),
            (
                win.checkout_fail_start,
                "API_ERROR",
                "HIGH",
                "api-gateway",
                "Upstream gateway timeout: 504 Gateway Timeout returned for POST /api/v1/checkout",
                {"status_code": 504, "upstream": "checkout-service:8080"},
            ),
            (
                win.orders_fail_start,
                "CHECKOUT_FAILURE",
                "HIGH",
                "checkout-service",
                "Order checkout transaction aborted: could not acquire database connection",
                {"error_code": "ERR_DB_TIMEOUT"},
            ),
            (
                win.tickets_start,
                "ALERT_TRIGGERED",
                "CRITICAL",
                "monitoring-agent",
                "PagerDuty High Severity Incident: Checkout API Error Rate exceeded 10% threshold",
                {"alert_rule": "checkout_error_rate_high", "current_value": 0.142},
            ),
            (
                win.rollback_time - timedelta(minutes=2),
                "DEPLOYMENT_STARTED",
                "INFO",
                "checkout-service",
                "Emergency rollback deployment checkout-service v4.8.1 initiated by SRE on-call",
                {"target_version": "v4.8.1"},
            ),
            (
                win.rollback_time,
                "DEPLOYMENT_COMPLETED",
                "INFO",
                "checkout-service",
                "Rollback deployment checkout-service v4.8.1 completed",
                {"version": "v4.8.1"},
            ),
            (
                win.rollback_time + timedelta(minutes=10),
                "DATABASE_INFO",
                "INFO",
                "checkout-service",
                "HikariCP connection pool normalized: max_connections restored to 50",
                {"active_connections": 6, "max_connections": 50},
            ),
            (
                win.recovery_end_time,
                "ALERT_RESOLVED",
                "INFO",
                "monitoring-agent",
                "Checkout API Error Rate returned to baseline (<0.5%)",
                {"resolved": True},
            ),
        ]

        result = []
        for i, (ts, ev_type, sev, srv, msg, meta) in enumerate(incident_events):
            ev_uuid = uuid.uuid5(self.company_id, f"incident-event-{i}")
            result.append(
                {
                    "id": str(ev_uuid),
                    "company_id": str(self.company_id),
                    "event_type": ev_type,
                    "severity": sev,
                    "service": srv,
                    "environment": "production",
                    "message": msg,
                    "timestamp": ts.isoformat(),
                    "event_metadata": meta,
                    "created_at": ts.isoformat(),
                }
            )
        return result
