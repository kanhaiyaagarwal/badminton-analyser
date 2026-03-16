"""STT service — transcribe audio via OpenAI Whisper API."""

import logging
from typing import Optional

from ....config import get_settings

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/webm") -> Optional[str]:
    """Transcribe audio bytes using OpenAI Whisper API.

    Returns transcribed text or None on failure.
    """
    settings = get_settings()

    if not settings.stt_enabled:
        return None

    if not settings.openai_api_key:
        logger.debug("STT: No OpenAI API key")
        return None

    # Map content type to file extension for OpenAI
    ext_map = {
        "audio/webm": "webm",
        "audio/webm;codecs=opus": "webm",
        "audio/mp4": "m4a",
        "audio/ogg": "ogg",
        "audio/ogg;codecs=opus": "ogg",
        "audio/wav": "wav",
        "audio/mpeg": "mp3",
    }
    ext = ext_map.get(content_type.split(";")[0].strip(), "webm")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(f"audio.{ext}", audio_bytes),
            language="en",
        )

        text = response.text.strip()
        logger.info("STT transcribed: '%s' (%d bytes audio)", text[:80], len(audio_bytes))
        return text if text else None

    except Exception as e:
        logger.warning("STT transcription failed: %s", e)
        return None
