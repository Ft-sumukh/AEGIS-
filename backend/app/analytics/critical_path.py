"""Critical Path Analysis Engine for Distributed Traces."""

from typing import Optional
from app.models.trace import TraceSpan
from app.telemetry.trace_schemas import CriticalPathResponse, CriticalPathSegment


class CriticalPathAnalyzer:
    """Calculates the latency-determining critical path through a trace execution graph."""

    @classmethod
    def analyze(cls, spans: list[TraceSpan]) -> CriticalPathResponse:
        """Computes deterministic critical path accounting for concurrent/parallel spans and self-time."""
        if not spans:
            return CriticalPathResponse(
                trace_id="unknown",
                total_duration_ms=0.0,
                critical_path_duration_ms=0.0,
                segments=[],
                non_causal_assessment="No spans available for critical path calculation.",
            )

        trace_id = spans[0].trace_id

        # 1. Index spans by ID and parent relationship
        span_map: dict[str, TraceSpan] = {s.span_id: s for s in spans}
        children_map: dict[str, list[TraceSpan]] = {}
        for s in spans:
            p_id = s.parent_span_id or "ROOT"
            children_map.setdefault(p_id, []).append(s)

        # Sort children by start time
        for p_id in children_map:
            children_map[p_id].sort(key=lambda x: x.timestamp_start)

        # 2. Identify root span
        root_candidates = children_map.get("ROOT", [])
        if not root_candidates:
            # Fallback to spans whose parent is not in span_map
            root_candidates = [s for s in spans if s.parent_span_id not in span_map]

        if not root_candidates:
            # Fallback to earliest start time
            root_span = min(spans, key=lambda x: x.timestamp_start)
        else:
            root_span = min(root_candidates, key=lambda x: x.timestamp_start)

        # Overall trace duration
        min_start = min(s.timestamp_start for s in spans)
        max_end = max(s.timestamp_end for s in spans)
        total_trace_duration = max(0.1, (max_end - min_start).total_seconds() * 1000.0)

        # 3. Dynamic Programming / Recursion to find the path of maximum duration
        def _find_longest_path(current_span: TraceSpan) -> tuple[float, list[TraceSpan]]:
            children = children_map.get(current_span.span_id, [])
            if not children:
                return current_span.duration_ms, [current_span]

            # In distributed tracing, parallel children may execute concurrently.
            # We select the child branch that produces the maximum total timeline contribution.
            best_child_duration = 0.0
            best_child_path: list[TraceSpan] = []

            for child in children:
                child_dur, child_path = _find_longest_path(child)
                if child_dur > best_child_duration:
                    best_child_duration = child_dur
                    best_child_path = child_path

            # The current span's path includes itself plus the best downstream branch
            path = [current_span] + best_child_path
            # Total path duration accounts for current span self-time + child duration
            current_self_time = max(0.0, current_span.duration_ms - best_child_duration)
            total_dur = current_self_time + best_child_duration

            return total_dur, path

        critical_path_duration, path_spans = _find_longest_path(root_span)
        critical_path_duration = max(critical_path_duration, root_span.duration_ms)

        # 4. Construct Segments with Self-Time and Contribution Percentages
        segments: list[CriticalPathSegment] = []
        for i, span in enumerate(path_spans):
            # Find next span on path that is a child of this span
            next_child_duration = 0.0
            if i + 1 < len(path_spans) and path_spans[i + 1].parent_span_id == span.span_id:
                next_child_duration = path_spans[i + 1].duration_ms

            self_time = max(0.0, span.duration_ms - next_child_duration)
            contrib_pct = round((self_time / critical_path_duration) * 100.0, 1) if critical_path_duration > 0 else 0.0

            desc = (
                f"Observed latency contribution: {self_time:.1f}ms ({contrib_pct}%) "
                f"in service '{span.service_name}' operation '{span.operation_name}'"
            )

            segments.append(
                CriticalPathSegment(
                    span_id=span.span_id,
                    service_name=span.service_name,
                    operation_name=span.operation_name,
                    duration_ms=span.duration_ms,
                    self_time_ms=round(self_time, 2),
                    contribution_percent=contrib_pct,
                    description=desc,
                )
            )

        # 5. Formulate Non-Causal Assessment
        slowest_seg = max(segments, key=lambda s: s.self_time_ms) if segments else None
        assessment = (
            f"Observed highest latency contribution was in service '{slowest_seg.service_name}' "
            f"({slowest_seg.self_time_ms:.1f}ms self-time, {slowest_seg.contribution_percent}% of critical path). "
            f"Critical path traversed {len(segments)} operations across {len({s.service_name for s in segments})} services "
            f"with total elapsed duration of {critical_path_duration:.1f}ms."
            if slowest_seg
            else "Critical path determined across 0 operations."
        )

        return CriticalPathResponse(
            trace_id=trace_id,
            total_duration_ms=round(total_trace_duration, 2),
            critical_path_duration_ms=round(critical_path_duration, 2),
            segments=segments,
            non_causal_assessment=assessment,
        )
