"""Request correlation IDs for HTTP and WebSocket."""

import contextvars
import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Holds the current request/WS correlation ID
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current correlation ID — safe to call from anywhere."""
    return request_id_var.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware that reads X-Request-ID or generates a UUID4,
    sets it in contextvars, and returns it in the response header.

    Note: BaseHTTPMiddleware only covers HTTP requests.
    WebSocket correlation IDs must be set manually in the handler.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)


class _CorrelationFilter(logging.Filter):
    """Injects request_id into every log record. Works alongside ddtrace's
    LogRecordFactory patching because filters are additive."""

    def filter(self, record):
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        return True


def install_log_correlation():
    """Add a filter to the root logger that injects ``request_id`` into every
    log record. Uses a Filter (not LogRecordFactory) so it doesn't conflict
    with ddtrace's own factory patching under ``ddtrace-run``."""
    logging.root.addFilter(_CorrelationFilter())
