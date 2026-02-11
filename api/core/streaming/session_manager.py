"""
Generic session manager — routes sessions to feature-specific analyzers.

Replaces the badminton-only StreamSessionManager for the multi-feature
platform.  Each session stores its feature_type so the WebSocket handler
can instantiate the correct analyzer.
"""

import logging
from typing import Dict, List, Optional

from .base_analyzer import BaseStreamAnalyzer

logger = logging.getLogger(__name__)


class GenericSessionManager:
    """
    Manages active streaming sessions across all features.

    Each session is keyed by session_id and holds:
      - feature_type  (e.g. "badminton", "challenge_squat")
      - analyzer      (a BaseStreamAnalyzer subclass instance)
    """

    def __init__(self):
        self._sessions: Dict[int, BaseStreamAnalyzer] = {}
        self._feature_types: Dict[int, str] = {}

    def register_session(
        self,
        session_id: int,
        feature_type: str,
        analyzer: BaseStreamAnalyzer,
    ):
        """Register a new session with its analyzer."""
        if session_id in self._sessions:
            self._sessions[session_id].close()

        self._sessions[session_id] = analyzer
        self._feature_types[session_id] = feature_type
        logger.info(f"Session {session_id} registered (feature={feature_type})")

    def get_session(self, session_id: int) -> Optional[BaseStreamAnalyzer]:
        return self._sessions.get(session_id)

    def get_feature_type(self, session_id: int) -> Optional[str]:
        return self._feature_types.get(session_id)

    def end_session(self, session_id: int) -> Optional[Dict]:
        """End a session and return its final report."""
        analyzer = self._sessions.pop(session_id, None)
        self._feature_types.pop(session_id, None)
        if analyzer:
            report = analyzer.get_final_report()
            analyzer.close()
            return report
        return None

    def get_active_sessions(self) -> List[int]:
        return list(self._sessions.keys())

    def close_all(self):
        for sid in list(self._sessions.keys()):
            self.end_session(sid)


# Global instance
_generic_session_manager: Optional[GenericSessionManager] = None


def get_generic_session_manager() -> GenericSessionManager:
    global _generic_session_manager
    if _generic_session_manager is None:
        _generic_session_manager = GenericSessionManager()
    return _generic_session_manager
