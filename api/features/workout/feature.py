"""Workout feature — placeholder for guided workouts."""

from typing import List

from fastapi import APIRouter

from ...features.base import BaseFeature


class WorkoutFeature(BaseFeature):

    @property
    def feature_id(self) -> str:
        return "workout"

    @property
    def display_name(self) -> str:
        return "Workout with Me"

    @property
    def description(self) -> str:
        return "Follow guided workout routines with real-time form feedback and rep counting. Coming soon."

    def get_routers(self) -> List[APIRouter]:
        return []
