"""
Backpressure and rate-limiting safeguards for telemetry ingestion.
Prevents upstream telemetry storms from starving operational incident processing.
"""

import time
from typing import Optional
from fastapi import HTTPException, status


class IngestionRateLimiter:
    """Sliding-window counter rate limiter for telemetry ingestion endpoints."""

    def __init__(self, max_requests_per_minute: int = 120, max_batch_size: int = 500) -> None:
        self.max_requests_per_minute = max_requests_per_minute
        self.max_batch_size = max_batch_size
        self._requests: dict[str, list[float]] = {}

    def check_rate_limit(self, client_key: str) -> None:
        """Verifies client is within requests-per-minute budget."""
        now = time.time()
        window_start = now - 60.0

        if client_key not in self._requests:
            self._requests[client_key] = []

        # Retain only timestamps within the last 60 seconds
        self._requests[client_key] = [
            ts for ts in self._requests[client_key] if ts > window_start
        ]

        if len(self._requests[client_key]) >= self.max_requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Telemetry ingestion rate limit exceeded ({self.max_requests_per_minute} req/min). Please back off.",
            )

        self._requests[client_key].append(now)

    def validate_batch_size(self, items_count: int) -> None:
        """Enforces maximum batch size for bulk ingestion."""
        if items_count > self.max_batch_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Batch size {items_count} exceeds maximum allowed batch size of {self.max_batch_size}.",
            )


# Global singleton instance
ingestion_rate_limiter = IngestionRateLimiter()
