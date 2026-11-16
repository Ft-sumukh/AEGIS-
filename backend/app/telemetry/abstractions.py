"""
Abstract interfaces and resilience primitives for telemetry sources and adapters.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional, TypeVar

from app.core.logging import get_logger
from app.telemetry.schemas import SourceHealthStatus, SourceStatus, TelemetryRecord, TelemetrySourceType

logger = get_logger("aegis.telemetry.abstractions")

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when an external telemetry provider circuit is OPEN."""
    pass


class CircuitBreaker:
    """Lightweight circuit breaker for protecting Aegis from failing telemetry backends."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Executes call wrapped in circuit breaker protection."""
        now = time.time()

        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (now - self.last_failure_time) > self.cooldown_seconds:
                logger.info(f"Circuit breaker '{self.name}' transitioning from OPEN to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker for source '{self.name}' is OPEN. Request suppressed."
                )

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as exc:
            self.on_failure(exc)
            raise

    def on_success(self) -> None:
        """Handles successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' probe succeeded. State reset to CLOSED.")
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def on_failure(self, error: Exception) -> None:
        """Handles call failure and updates state."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            f"Circuit breaker '{self.name}' recorded failure #{self.failure_count}: {error}"
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker '{self.name}' reached {self.failure_count} failures. Circuit OPEN."
            )


class TelemetryAdapter(ABC):
    """Abstract adapter transforming vendor-specific payloads into normalized TelemetryRecords."""

    @abstractmethod
    def validate(self, raw_data: Any) -> tuple[bool, list[str]]:
        """Validates incoming raw payload structure."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> list[TelemetryRecord]:
        """Transforms validated raw payload into list of normalized TelemetryRecord instances."""
        pass


class TelemetrySource(ABC):
    """Abstract interface for external or local telemetry sources."""

    def __init__(self, name: str, source_type: TelemetrySourceType) -> None:
        self.name = name
        self.source_type = source_type
        self.circuit_breaker = CircuitBreaker(name=name)

    @abstractmethod
    def fetch(self, since: Optional[datetime] = None) -> list[TelemetryRecord]:
        """Pulls telemetry records from the source since the specified timestamp."""
        pass

    @abstractmethod
    def check_health(self) -> SourceHealthStatus:
        """Evaluates operational connectivity and returns structured health status."""
        pass
