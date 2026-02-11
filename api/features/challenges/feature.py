"""Challenges feature — fitness challenges using pose detection."""

from typing import List

from fastapi import APIRouter

from ...features.base import BaseFeature
from .routers.challenges import router as challenges_router


class ChallengesFeature(BaseFeature):

    @property
    def feature_id(self) -> str:
        return "challenges"

    @property
    def display_name(self) -> str:
        return "Challenges"

    @property
    def description(self) -> str:
        return "Test your fitness with timed plank holds, max squat reps, and pushup challenges."

    def get_routers(self) -> List[APIRouter]:
        return [challenges_router]
