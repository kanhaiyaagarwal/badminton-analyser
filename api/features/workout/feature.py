"""Workout feature — AI Fitness Coach with exercise library, plans, and coaching."""

from typing import List

from fastapi import APIRouter

from ...features.base import BaseFeature
from .routers.workout import router as workout_router


class WorkoutFeature(BaseFeature):

    @property
    def feature_id(self) -> str:
        return "workout"

    @property
    def display_name(self) -> str:
        return "AI Fitness Coach"

    @property
    def description(self) -> str:
        return "Personalized workout plans, exercise library, and AI coaching for your fitness journey."

    def get_routers(self) -> List[APIRouter]:
        return [workout_router]
