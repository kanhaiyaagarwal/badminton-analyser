"""Base feature class — interface every feature must implement."""

from abc import ABC, abstractmethod
from typing import List, Optional, Type

from fastapi import APIRouter

from ..core.streaming.base_analyzer import BaseStreamAnalyzer


class BaseFeature(ABC):
    """
    Abstract base for a platform feature.

    Each feature provides:
      - metadata (id, display name, description)
      - FastAPI routers to be registered on the app
      - (optionally) a stream analyzer class for live sessions
    """

    @property
    @abstractmethod
    def feature_id(self) -> str:
        """Unique slug, e.g. 'badminton', 'challenges'."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in the UI."""

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    def get_routers(self) -> List[APIRouter]:
        """Return FastAPI routers to be included in the app."""

    def get_stream_analyzer_class(self) -> Optional[Type[BaseStreamAnalyzer]]:
        """Return the analyzer class for live streaming, or None."""
        return None

    def to_dict(self) -> dict:
        return {
            "feature_id": self.feature_id,
            "display_name": self.display_name,
            "description": self.description,
            "has_streaming": self.get_stream_analyzer_class() is not None,
        }
