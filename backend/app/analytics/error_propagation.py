"""Error Propagation Analysis Engine for Distributed Traces."""

from typing import Optional
from app.models.trace import TraceSpan
from app.telemetry.trace_schemas import ErrorPropagationResponse, ErrorPropagationStep


class ErrorPropagationAnalyzer:
    """Discovers downstream error originations and traces their propagation upstream through call chains."""

    @classmethod
    def analyze(cls, spans: list[TraceSpan]) -> ErrorPropagationResponse:
        """Traces error propagation from downstream callee to upstream caller."""
        if not spans:
            return ErrorPropagationResponse(
                trace_id="unknown",
                has_errors=False,
                non_causal_assessment="No spans found for error propagation analysis.",
            )

        trace_id = spans[0].trace_id
        span_map: dict[str, TraceSpan] = {s.span_id: s for s in spans}

        # 1. Filter all spans with error status or 5xx code
        error_spans = [
            s for s in spans if s.status == "ERROR" or (s.http_status_code and s.http_status_code >= 500)
        ]

        if not error_spans:
            return ErrorPropagationResponse(
                trace_id=trace_id,
                has_errors=False,
                propagation_chain=[],
                non_causal_assessment="No failed spans observed in trace.",
            )

        # 2. Sort error spans by timestamp_start (earliest failure) and depth
        # To find depth:
        def _get_depth(s: TraceSpan) -> int:
            depth = 0
            curr = s
            visited = set()
            while curr.parent_span_id and curr.parent_span_id in span_map and curr.parent_span_id not in visited:
                visited.add(curr.span_id)
                curr = span_map[curr.parent_span_id]
                depth += 1
            return depth

        # The deepest downstream error is the prime candidate for origin
        deepest_error = max(error_spans, key=lambda s: (_get_depth(s), s.timestamp_start))

        # 3. Trace propagation path from deepest error up to the root span
        chain_spans: list[TraceSpan] = []
        curr: Optional[TraceSpan] = deepest_error
        visited_ids = set()

        while curr and curr.span_id not in visited_ids:
            visited_ids.add(curr.span_id)
            chain_spans.append(curr)
            if curr.parent_span_id and curr.parent_span_id in span_map:
                curr = span_map[curr.parent_span_id]
            else:
                break

        # Order from downstream origin -> intermediate -> ingress (reverse the climbed tree)
        # Deepest is first, root is last
        steps: list[ErrorPropagationStep] = []
        for i, s in enumerate(chain_spans):
            is_origin = i == 0
            steps.append(
                ErrorPropagationStep(
                    span_id=s.span_id,
                    service_name=s.service_name,
                    operation_name=s.operation_name,
                    status=s.status,
                    http_status_code=s.http_status_code,
                    timestamp=s.timestamp_start,
                    error_message=s.status_message,
                    is_deepest_error=is_origin,
                )
            )

        root_service = deepest_error.service_name
        chain_services = [step.service_name for step in steps]
        ingress_service = steps[-1].service_name if steps else root_service

        assessment = (
            f"Observed error propagation pattern: Downstream service '{root_service}' encountered "
            f"{'HTTP ' + str(deepest_error.http_status_code) if deepest_error.http_status_code else 'ERROR status'} "
            f"in operation '{deepest_error.operation_name}'. Failure was observed propagating upstream through "
            f"{' -> '.join(chain_services)} to edge ingress service '{ingress_service}'."
        )

        return ErrorPropagationResponse(
            trace_id=trace_id,
            has_errors=True,
            root_error_service=root_service,
            root_error_span_id=deepest_error.span_id,
            root_error_status_code=deepest_error.http_status_code,
            root_error_message=deepest_error.status_message,
            propagation_chain=steps,
            non_causal_assessment=assessment,
        )
