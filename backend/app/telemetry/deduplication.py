"""
Telemetry event deduplication engine providing idempotency guarantees.
Prevents duplicate metrics and events from contaminating analytics.
"""

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Optional


class TelemetryDeduplicator:
    """In-memory sliding window deduplicator for streaming telemetry records."""

    def __init__(self, max_entries: int = 50000, ttl_seconds: float = 600.0) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        # Mapping: hash -> timestamp_added
        self._cache: OrderedDict[str, float] = OrderedDict()
        self.duplicate_count = 0

    def compute_fingerprint(
        self,
        source: str,
        timestamp_iso: str,
        service: str,
        metric_name: Optional[str] = None,
        event_id: Optional[str] = None,
        dimensions: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generates deterministic SHA-256 hash identifying the telemetry event."""
        dims_str = ""
        if dimensions:
            dims_str = json.dumps(dimensions, sort_keys=True, default=str)

        key_parts = [
            source,
            timestamp_iso,
            service,
            metric_name or "",
            event_id or "",
            dims_str,
        ]
        raw_key = "|".join(key_parts)
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def is_duplicate(self, fingerprint: str) -> bool:
        """Checks if fingerprint was recently processed within TTL."""
        now = time.time()
        self._prune(now)

        if fingerprint in self._cache:
            self.duplicate_count += 1
            # Refresh entry position in OrderedDict
            self._cache.move_to_end(fingerprint)
            return True

        self._cache[fingerprint] = now
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)

        return False

    def _prune(self, now: float) -> None:
        """Removes expired entries from the head of the cache."""
        while self._cache:
            first_key, added_time = next(iter(self._cache.items()))
            if now - added_time > self.ttl_seconds:
                self._cache.pop(first_key)
            else:
                break

    def clear(self) -> None:
        """Clears cache for test isolation."""
        self._cache.clear()
        self.duplicate_count = 0


# Global singleton instance
deduplicator = TelemetryDeduplicator()
