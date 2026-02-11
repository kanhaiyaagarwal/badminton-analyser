"""Base stream analyzer — abstract interface for all feature-specific analyzers."""

from abc import ABC, abstractmethod
from typing import Dict


class BaseStreamAnalyzer(ABC):
    """
    Abstract base class for real-time stream analyzers.

    Each feature (badminton, challenges, workout) implements its own
    subclass that processes frames from a live camera/stream.
    """

    @abstractmethod
    def process_frame(self, frame_data: bytes, timestamp: float) -> Dict:
        """
        Process a single frame from the stream.

        Args:
            frame_data: JPEG-encoded frame bytes.
            timestamp: Frame timestamp in seconds.

        Returns:
            Dict with feature-specific result keys.
        """

    @abstractmethod
    def get_final_report(self) -> Dict:
        """Generate a summary report when the session ends."""

    @abstractmethod
    def reset(self):
        """Reset analyzer state for a new session."""

    @abstractmethod
    def close(self):
        """Release resources (models, GPU memory, etc.)."""
