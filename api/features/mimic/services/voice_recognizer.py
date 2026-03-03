"""Offline voice command recognition using Vosk.

Recognises a small grammar of playback commands (pause, play, slower, faster)
from 16 kHz mono PCM audio streamed over the mimic WebSocket.  The ~40 MB
model is loaded once (singleton) and shared across sessions; only the
per-session KaldiRecognizer is instantiated per connection.
"""

import json
import logging
import os

from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "weights", "vosk-model-small-en-us"
)

# Grammar-restricted vocabulary — Vosk only considers these tokens.
GRAMMAR = '["pause", "stop", "play", "start", "go", "slower", "slow", "faster", "fast", "[unk]"]'


class VoiceRecognizer:
    """Per-session Vosk recognizer with grammar-restricted command matching."""

    _model: Model | None = None  # singleton, loaded once

    @classmethod
    def load_model(cls) -> Model:
        if cls._model is None:
            path = os.path.normpath(VOSK_MODEL_PATH)
            if not os.path.isdir(path):
                raise FileNotFoundError(f"Vosk model not found at {path}")
            cls._model = Model(path)
            logger.info("Vosk model loaded from %s", path)
        return cls._model

    def __init__(self) -> None:
        model = self.load_model()
        self.rec = KaldiRecognizer(model, 16000, GRAMMAR)

    def feed(self, pcm_bytes: bytes) -> str | None:
        """Feed PCM16 audio. Returns command string if recognised, else None."""
        if self.rec.AcceptWaveform(pcm_bytes):
            result = json.loads(self.rec.Result())
            text = result.get("text", "").strip()
            return self._match_command(text)
        # Check partial for faster response
        partial = json.loads(self.rec.PartialResult())
        text = partial.get("partial", "").strip()
        return self._match_command(text, clear=True)

    def _match_command(self, text: str, clear: bool = False) -> str | None:
        if not text:
            return None
        cmd = None
        if "pause" in text or "stop" in text:
            cmd = "pause"
        elif "play" in text or "start" in text or "go" in text:
            cmd = "play"
        elif "slow" in text:
            cmd = "slower"
        elif "fast" in text:
            cmd = "faster"
        if cmd and clear:
            self.rec.Reset()  # clear partial buffer to avoid double-firing
        return cmd

    def close(self) -> None:
        self.rec = None
