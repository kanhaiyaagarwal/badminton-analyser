"""DogStatsD singleton with no-op fallback for local dev."""

import os
import logging
import threading

logger = logging.getLogger(__name__)


class _NoOpStatsd:
    """Silent stub when DD_AGENT_HOST is unset — all calls are no-ops."""

    def increment(self, *a, **kw): pass
    def decrement(self, *a, **kw): pass
    def gauge(self, *a, **kw): pass
    def histogram(self, *a, **kw): pass
    def distribution(self, *a, **kw): pass
    def set(self, *a, **kw): pass
    def timing(self, *a, **kw): pass
    def timed(self, *a, **kw):
        # Return a passthrough decorator/context-manager
        import contextlib
        return contextlib.nullcontext()


def _create_client():
    host = os.environ.get("DD_AGENT_HOST")
    if not host:
        logger.info("DD_AGENT_HOST not set — using no-op statsd client")
        return _NoOpStatsd()

    try:
        from datadog import DogStatsd

        port = int(os.environ.get("DD_DOGSTATSD_PORT", "8125"))
        client = DogStatsd(
            host=host,
            port=port,
            namespace="pushuppro",
        )
        env = os.environ.get("DD_ENV", "unknown")
        logger.info(f"DogStatsD client initialized — {host}:{port} (env={env})")
        return client
    except ImportError:
        logger.warning("datadog package not installed — using no-op statsd client")
        return _NoOpStatsd()
    except Exception as e:
        logger.warning(f"Failed to create DogStatsD client: {e} — using no-op")
        return _NoOpStatsd()


# Module-level singleton
statsd = _create_client()

# ---------------------------------------------------------------------------
# Active session gauge tracking (thread-safe, single-worker process)
# ---------------------------------------------------------------------------

_session_lock = threading.Lock()
_active_sessions: dict[str, int] = {}  # challenge_type -> count


def session_opened(challenge_type: str):
    with _session_lock:
        _active_sessions[challenge_type] = _active_sessions.get(challenge_type, 0) + 1
        statsd.gauge(
            "challenge.session.active",
            _active_sessions[challenge_type],
            tags=[f"challenge_type:{challenge_type}"],
        )


def session_closed(challenge_type: str):
    with _session_lock:
        _active_sessions[challenge_type] = max(0, _active_sessions.get(challenge_type, 0) - 1)
        statsd.gauge(
            "challenge.session.active",
            _active_sessions[challenge_type],
            tags=[f"challenge_type:{challenge_type}"],
        )
