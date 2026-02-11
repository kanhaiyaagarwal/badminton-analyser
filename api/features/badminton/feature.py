"""
Badminton feature — thin wrapper around the existing badminton analysis code.

No files are moved in this iteration; this module simply re-exports the
existing routers and services so the feature registry can treat badminton
like any other feature.
"""

from typing import List, Optional, Type

from fastapi import APIRouter

from ...features.base import BaseFeature
from ...core.streaming.base_analyzer import BaseStreamAnalyzer


class BadmintonFeature(BaseFeature):
    """Wraps the existing badminton analysis pipeline."""

    @property
    def feature_id(self) -> str:
        return "badminton"

    @property
    def display_name(self) -> str:
        return "Badminton Analysis"

    @property
    def description(self) -> str:
        return "Upload videos or stream live for real-time shot detection, movement tracking, and coaching insights."

    def get_routers(self) -> List[APIRouter]:
        # Existing badminton routers are already registered directly in
        # main.py — we return an empty list to avoid double-registration.
        # In a future iteration the routers will be moved here.
        return []

    def get_stream_analyzer_class(self) -> Optional[Type[BaseStreamAnalyzer]]:
        # StreamAnalyzer doesn't extend BaseStreamAnalyzer yet.
        # The existing WebSocket path in main.py handles badminton
        # streaming directly.  We'll migrate in a future iteration.
        return None
