"""Distributed Trace Span Deduplication Engine."""

import hashlib
import time
from collections import OrderedDict


class TraceDeduplicator:
    """Sliding window deduplicator for streaming trace spans."""

    def __init__(self, max_entries: int = 50000, ttl_seconds: float = 600.0) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, float] = OrderedDict()
        self.duplicate_count = 0

    def compute_fingerprint(
        self,
        source: str,
        trace_id: str,
        span_id: str,
        timestamp_start_iso: str,
    ) -> str:
        """Generates deterministic SHA-256 fingerprint for a span."""
        raw_key = f"{source}|{trace_id}|{span_id}|{timestamp_start_iso}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def is_duplicate(self, fingerprint: str) -> bool:
        """Checks if span fingerprint was recently seen within TTL."""
        now = time.time()
        self._prune(now)

        if fingerprint in self._cache:
            self.duplicate_count += 1
            self._cache.move_to_end(fingerprint)
            return True

        self._cache[fingerprint] = now
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)

        return False

    def _prune(self, now: float) -> None:
        """Removes expired entries from the cache head."""
        while self._cache:
            first_key, added_time = next(iter(self._cache.items()))
            if now - added_time > self.ttl_seconds:
                self._cache.pop(first_key)
            else:
                break


# Global singleton instance for trace deduplication
trace_deduplicator = TraceDeduplicator()
