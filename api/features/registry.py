"""Feature registry — discovers and registers all platform features."""

import logging
from typing import Dict, List

from fastapi import FastAPI

from .base import BaseFeature

logger = logging.getLogger(__name__)


class FeatureRegistry:
    """
    Central registry for platform features.

    Features are registered manually (not auto-discovered via filesystem)
    to keep things explicit and avoid import-side-effects.
    """

    def __init__(self):
        self._features: Dict[str, BaseFeature] = {}

    def register(self, feature: BaseFeature):
        fid = feature.feature_id
        if fid in self._features:
            logger.warning(f"Feature '{fid}' already registered — skipping")
            return
        self._features[fid] = feature
        logger.info(f"Registered feature: {fid} ({feature.display_name})")

    def get(self, feature_id: str) -> BaseFeature:
        return self._features[feature_id]

    def list_features(self) -> List[dict]:
        return [f.to_dict() for f in self._features.values()]

    def install_routers(self, app: FastAPI):
        """Include every feature's routers in the FastAPI app."""
        for fid, feature in self._features.items():
            for router in feature.get_routers():
                app.include_router(router)
                logger.info(f"Installed router from feature '{fid}'")


def build_registry() -> FeatureRegistry:
    """
    Construct and populate the global feature registry.

    Import each feature module here so that registration order is
    deterministic and missing optional dependencies fail gracefully.
    """
    registry = FeatureRegistry()

    # --- Badminton (wraps existing code) ---
    try:
        from .badminton.feature import BadmintonFeature
        registry.register(BadmintonFeature())
    except Exception as e:
        logger.warning(f"Failed to register badminton feature: {e}")

    # --- Challenges ---
    try:
        from .challenges.feature import ChallengesFeature
        registry.register(ChallengesFeature())
    except Exception as e:
        logger.warning(f"Failed to register challenges feature: {e}")

    # --- Workout (placeholder) ---
    try:
        from .workout.feature import WorkoutFeature
        registry.register(WorkoutFeature())
    except Exception as e:
        logger.warning(f"Failed to register workout feature: {e}")

    # --- Mimic Challenge ---
    try:
        from .mimic.feature import MimicFeature
        registry.register(MimicFeature())
    except Exception as e:
        logger.warning(f"Failed to register mimic feature: {e}")

    return registry
