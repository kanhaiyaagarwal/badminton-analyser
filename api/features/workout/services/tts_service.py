"""TTS service — pre-recorded clips first, dynamic OpenAI TTS fallback.

Most coaching phrases are predictable. Pre-generated clips cover ~90% of
coach speech. Only dynamic personalized text hits the OpenAI TTS API.
"""

import hashlib
import logging
import os
from functools import lru_cache
from typing import Optional

from ....config import get_settings

logger = logging.getLogger(__name__)

# Pre-recorded clip mapping: keyword/phrase -> filename
# Clips live in frontend/public/audio/coach/
PRERECORDED_CLIPS = {
    # Form corrections
    "go deeper": "go-deeper.mp3",
    "core tight": "core-tight.mp3",
    "slow down": "slow-down.mp3",
    "great rep": "great-rep.mp3",
    "keep going": "keep-going.mp3",
    "chest to floor": "chest-to-floor.mp3",
    "knees back": "knees-back.mp3",
    "chest up": "chest-up.mp3",
    "hips up": "hips-up.mp3",
    "good form": "good-form.mp3",
    "almost there": "almost-there.mp3",
    "nice depth": "nice-depth.mp3",
    "stay tight": "stay-tight.mp3",
    "breathe": "breathe.mp3",

    # Transitions
    "rest now": "rest-now.mp3",
    "workout complete": "workout-complete.mp3",
    "let's go": "lets-go.mp3",
    "ready": "ready.mp3",
    "last set": "last-set.mp3",
    "well done": "well-done.mp3",
    "next exercise": "next-exercise.mp3",

    # RPE feedback
    "solid set": "solid-set.mp3",
    "right on target": "right-on-target.mp3",
    "tough set": "tough-set-rest-well.mp3",
    "consider adding weight": "consider-adding-weight.mp3",
    "new pr": "new-pr.mp3",
    "new personal record": "new-pr.mp3",
    "personal best": "personal-best.mp3",
    "every rep counts": "every-rep-counts.mp3",

    # Encouragement
    "you got this": "you-got-this.mp3",
    "keep pushing": "keep-pushing.mp3",
    "great work": "great-work.mp3",
    "consistency wins": "consistency-wins.mp3",
    "stronger than yesterday": "stronger-than-yesterday.mp3",
}


def match_prerecorded(coach_says: str) -> Optional[str]:
    """Try to match coach_says text to a pre-recorded clip.

    Returns the clip path (relative to /audio/coach/) or None.
    """
    if not coach_says:
        return None

    text_lower = coach_says.lower()

    # Exact phrase match first (longest match wins)
    best_match = None
    best_len = 0
    for phrase, filename in PRERECORDED_CLIPS.items():
        if phrase in text_lower and len(phrase) > best_len:
            best_match = filename
            best_len = len(phrase)

    return f"/audio/coach/{best_match}" if best_match else None


async def generate_speech(text: str, voice: str = None) -> Optional[bytes]:
    """Generate TTS audio via OpenAI API. Returns MP3 bytes or None."""
    settings = get_settings()

    if not settings.tts_enabled:
        return None

    if not settings.openai_api_key:
        logger.debug("TTS: No OpenAI API key")
        return None

    voice = voice or settings.tts_voice

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="mp3",
        )

        audio_bytes = response.content
        logger.info(f"TTS generated: {len(audio_bytes)} bytes for '{text[:50]}...'")
        return audio_bytes

    except Exception as e:
        logger.warning(f"TTS generation failed: {e}")
        return None


def get_audio_url_for_coach(coach_says: str) -> Optional[str]:
    """Get the audio URL for a coach message.

    1. Try pre-recorded clip match
    2. For dynamic text, return a TTS endpoint URL the frontend can fetch

    Returns a URL path or None.
    """
    if not coach_says:
        return None

    # Try pre-recorded first
    clip_path = match_prerecorded(coach_says)
    if clip_path:
        return clip_path

    # For dynamic text, return TTS endpoint URL
    # Frontend will fetch /api/v1/workout/tts/{hash} which generates on demand
    settings = get_settings()
    if settings.tts_enabled and settings.openai_api_key:
        text_hash = hashlib.md5(coach_says.encode()).hexdigest()[:12]
        return f"/api/v1/workout/tts/{text_hash}?text={coach_says[:200]}"

    return None
