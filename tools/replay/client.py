"""Authenticated HTTP client for REST session lifecycle."""

import json
import logging
from typing import Optional

import requests

from .config import ReplayConfig

logger = logging.getLogger(__name__)


class AuthenticatedClient:
    def __init__(self, config: ReplayConfig):
        self.config = config
        self.session = requests.Session()
        self.token: Optional[str] = None

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}{path}"

    def login(self) -> str:
        """Login via OAuth2 form POST; returns JWT access token."""
        resp = self.session.post(
            self._url("/api/v1/auth/login"),
            data={"username": self.config.email, "password": self.config.password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        logger.info("Logged in successfully")
        return self.token

    # -- Badminton stream lifecycle --

    def create_stream_session(self) -> int:
        """POST /api/v1/stream/create → session_id."""
        resp = self.session.post(
            self._url("/api/v1/stream/create"),
            json={
                "frame_rate": self.config.fps,
                "quality": "medium",
                "stream_mode": self.config.stream_mode,
                "enable_tuning_data": self.config.enable_tuning,
                "enable_shuttle_tracking": self.config.enable_shuttle,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        session_id = data["session_id"]
        logger.info(f"Created stream session {session_id}")
        return session_id

    def setup_court(self, session_id: int, court_boundary: dict):
        """POST /api/v1/stream/{id}/setup-court."""
        resp = self.session.post(
            self._url(f"/api/v1/stream/{session_id}/setup-court"),
            json={"court_boundary": court_boundary},
        )
        resp.raise_for_status()
        logger.info(f"Court boundary set for session {session_id}")

    def start_stream(self, session_id: int):
        """POST /api/v1/stream/{id}/start."""
        resp = self.session.post(
            self._url(f"/api/v1/stream/{session_id}/start"),
        )
        resp.raise_for_status()
        logger.info(f"Stream started for session {session_id}")

    def start_recording(self, session_id: int):
        """POST /api/v1/stream/{id}/recording/start — sets DB flag + analyzer."""
        resp = self.session.post(
            self._url(f"/api/v1/stream/{session_id}/recording/start"),
        )
        resp.raise_for_status()
        logger.info(f"Recording started for session {session_id}")

    def end_stream(self, session_id: int) -> dict:
        """POST /api/v1/stream/{id}/end — saves recording + final report."""
        resp = self.session.post(
            self._url(f"/api/v1/stream/{session_id}/end"),
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Stream session {session_id} ended via REST")
        return data

    # -- Challenge lifecycle --

    def create_challenge_session(self) -> int:
        """POST /api/v1/challenges/sessions → session_id."""
        resp = self.session.post(
            self._url("/api/v1/challenges/sessions"),
            json={"challenge_type": self.config.challenge_type},
        )
        resp.raise_for_status()
        data = resp.json()
        session_id = data["session_id"]
        logger.info(f"Created challenge session {session_id} ({self.config.challenge_type})")
        return session_id

    def start_challenge_recording(self, session_id: int):
        """POST /api/v1/challenges/sessions/{id}/recording/start."""
        resp = self.session.post(
            self._url(f"/api/v1/challenges/sessions/{session_id}/recording/start"),
        )
        resp.raise_for_status()
        logger.info(f"Challenge recording started for session {session_id}")

    def end_challenge_session(self, session_id: int) -> dict:
        """POST /api/v1/challenges/sessions/{id}/end — persists score + personal best."""
        resp = self.session.post(
            self._url(f"/api/v1/challenges/sessions/{session_id}/end"),
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Challenge session {session_id} ended via REST")
        return data
