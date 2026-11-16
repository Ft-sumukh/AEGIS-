"""Preliminary business impact estimation engine."""

from collections.abc import Sequence
from decimal import Decimal

from app.analytics.models import BusinessImpactEstimate
from app.models.anomaly import Anomaly


class BusinessImpactEngine:
    """Estimates preliminary financial, transaction, and user blast radius from operational anomalies."""

    @staticmethod
    def estimate_impact(anomalies: Sequence[Anomaly]) -> BusinessImpactEstimate:
        """Calculates preliminary impact bounds across a set of correlated anomalies."""
        rev_loss = Decimal("0.00")
        affected_orders = 0
        affected_users = 0
        extra_tickets = 0
        extra_complaints = 0

        for a in anomalies:
            m_name = a.metric_name
            dev = a.deviation

            # 1. Financial Revenue Impact
            if m_name == "revenue" and dev < 0:
                loss = Decimal(str(round(abs(dev), 2)))
                rev_loss += loss

            # 2. Orders Lost / Failed
            elif m_name == "failed_orders" and dev > 0:
                affected_orders += int(round(dev))
            elif m_name == "orders" and dev < 0:
                # If orders were under expectation, count the deficit
                affected_orders += int(round(abs(dev)))

            # 3. Active Users Impaired
            elif m_name == "active_users" and dev < 0:
                affected_users += int(round(abs(dev)))

            # 4. Support Influx Impact
            elif m_name == "support_ticket_count" and dev > 0:
                extra_tickets += int(round(dev))
            elif m_name == "customer_complaint_count" and dev > 0:
                extra_complaints += int(round(dev))

        return BusinessImpactEstimate(
            estimated_revenue_impact=rev_loss,
            estimated_orders_affected=affected_orders,
            estimated_users_affected=affected_users,
            additional_support_tickets=extra_tickets,
            additional_complaints=extra_complaints,
            is_preliminary=True,
        )
