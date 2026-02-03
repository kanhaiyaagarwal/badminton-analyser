"""WebSocket handler for real-time progress updates."""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ProgressWebSocketManager:
    """Manages WebSocket connections for progress updates."""

    def __init__(self):
        # job_id -> set of websocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, job_id: int):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        async with self._lock:
            if job_id not in self._connections:
                self._connections[job_id] = set()
            self._connections[job_id].add(websocket)

        logger.info(f"WebSocket connected for job {job_id}")

    async def disconnect(self, websocket: WebSocket, job_id: int):
        """Remove a WebSocket connection."""
        async with self._lock:
            if job_id in self._connections:
                self._connections[job_id].discard(websocket)
                if not self._connections[job_id]:
                    del self._connections[job_id]

        logger.info(f"WebSocket disconnected for job {job_id}")

    async def send_progress(self, job_id: int, progress: float, message: str):
        """Send progress update to all connections for a job."""
        if job_id not in self._connections:
            return

        data = json.dumps({
            "type": "progress",
            "job_id": job_id,
            "progress": progress,
            "message": message
        })

        # Copy set to avoid modification during iteration
        async with self._lock:
            connections = self._connections.get(job_id, set()).copy()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket, job_id)

    async def send_completion(self, job_id: int, success: bool, message: str):
        """Send completion notification."""
        if job_id not in self._connections:
            return

        data = json.dumps({
            "type": "complete" if success else "error",
            "job_id": job_id,
            "success": success,
            "message": message
        })

        async with self._lock:
            connections = self._connections.get(job_id, set()).copy()

        for websocket in connections:
            try:
                await websocket.send_text(data)
            except Exception:
                pass

    def get_connection_count(self, job_id: int) -> int:
        """Get number of active connections for a job."""
        return len(self._connections.get(job_id, set()))


# Singleton instance
_ws_manager: ProgressWebSocketManager = None


def get_ws_manager() -> ProgressWebSocketManager:
    """Get the WebSocket manager singleton."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = ProgressWebSocketManager()
    return _ws_manager
