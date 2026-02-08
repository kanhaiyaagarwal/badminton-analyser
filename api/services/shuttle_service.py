"""Service wrapper for shuttle tracking."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ShuttleService:
    """Thin wrapper around ShuttleTracker for the API layer."""

    @staticmethod
    def is_available() -> bool:
        """Check if shuttle tracking dependencies (torch, weights) are available."""
        try:
            import torch  # noqa: F401
            from shuttle_tracking.shuttle_tracker import DEFAULT_WEIGHTS_PATH
            return DEFAULT_WEIGHTS_PATH.exists()
        except ImportError:
            return False

    @staticmethod
    def create_tracker(device: str = "auto"):
        """Create a ShuttleTracker instance.

        Returns:
            ShuttleTracker or None if unavailable.
        """
        try:
            from shuttle_tracking.shuttle_tracker import ShuttleTracker
            return ShuttleTracker(device=device)
        except Exception as e:
            logger.warning(f"Failed to create ShuttleTracker: {e}")
            return None
