"""Mimic Challenge feature — mimic reference video poses in real-time."""

from typing import List, Optional, Type

from fastapi import APIRouter

from ...features.base import BaseFeature
from ...core.streaming.base_analyzer import BaseStreamAnalyzer
from .routers.mimic import router as mimic_router
from .services.mimic_analyzer import MimicAnalyzer


class MimicFeature(BaseFeature):

    @property
    def feature_id(self) -> str:
        return "mimic"

    @property
    def display_name(self) -> str:
        return "Mimic Challenge"

    @property
    def description(self) -> str:
        return "Watch a reference video and mimic the movements — get scored on pose similarity in real-time."

    def get_routers(self) -> List[APIRouter]:
        return [mimic_router]

    def get_stream_analyzer_class(self) -> Optional[Type[BaseStreamAnalyzer]]:
        return MimicAnalyzer
