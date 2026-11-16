"""HTTP Middleware for request tracing, correlation ID, and latency measurement."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, request_id_ctx

logger = get_logger("aegis.middleware")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts or generates an X-Request-ID and tracks execution latency."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Honor client provided X-Request-ID or generate new UUID4
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

            # Only log detailed requests for non-health checks or errors to keep logs clean
            if not request.url.path.endswith("/health"):
                logger.info(
                    f"{request.method} {request.url.path} returned {response.status_code} in {duration_ms:.2f}ms"
                )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                f"Unhandled exception during {request.method} {request.url.path} after {duration_ms:.2f}ms: {exc}"
            )
            raise
        finally:
            request_id_ctx.reset(token)
