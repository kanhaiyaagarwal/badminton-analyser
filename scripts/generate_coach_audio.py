#!/usr/bin/env python3
"""Batch-generate pre-recorded coach audio clips using OpenAI TTS.

Run once locally, commit the MP3s to frontend/public/audio/coach/.

Usage:
    python scripts/generate_coach_audio.py

Requires:
    - OPENAI_API_KEY environment variable
    - pip install openai
"""

import os
import sys
import asyncio
from pathlib import Path

# Audio clips to generate: filename -> text to speak
CLIPS = {
    # Form corrections
    "go-deeper.mp3": "Go deeper.",
    "core-tight.mp3": "Keep your core tight.",
    "slow-down.mp3": "Slow down. Control the movement.",
    "great-rep.mp3": "Great rep!",
    "keep-going.mp3": "Keep going. You've got this.",
    "chest-to-floor.mp3": "Chest to the floor.",
    "knees-back.mp3": "Push your knees back.",
    "chest-up.mp3": "Chest up. Stay tall.",
    "hips-up.mp3": "Hips up. Don't let them sag.",
    "flatten-out.mp3": "Flatten out. Keep your body straight.",
    "good-form.mp3": "Good form. Keep it up.",
    "almost-there.mp3": "Almost there!",
    "nice-depth.mp3": "Nice depth.",
    "stay-tight.mp3": "Stay tight.",
    "breathe.mp3": "Don't forget to breathe.",

    # Transitions
    "start.mp3": "Let's get started.",
    "rest-now.mp3": "Rest now. You earned it.",
    "next-exercise.mp3": "Moving on to the next exercise.",
    "workout-complete.mp3": "Workout complete! Great job today.",
    "lets-go.mp3": "Let's go!",
    "ready.mp3": "Ready? Let's do this.",
    "begin-set.mp3": "Begin your set.",
    "last-set.mp3": "Last set. Give it everything.",
    "cooldown-time.mp3": "Time to cool down.",
    "well-done.mp3": "Well done.",

    # Rep counting
    "one-more.mp3": "One more!",
    "two-more.mp3": "Two more!",
    "three-more.mp3": "Three more!",
    "five-more.mp3": "Five more!",
    "halfway.mp3": "Halfway there!",

    # RPE feedback
    "solid-set.mp3": "Solid set.",
    "right-on-target.mp3": "Right on target.",
    "above-target.mp3": "Above target. Strong work.",
    "tough-set-rest-well.mp3": "Tough set. Rest well before the next one.",
    "consider-adding-weight.mp3": "That felt easy. Consider adding weight next time.",
    "new-pr.mp3": "New personal record!",
    "matching-your-best.mp3": "Matching your personal best.",
    "every-rep-counts.mp3": "Every rep counts.",
    "strong-finish.mp3": "Strong finish!",
    "personal-best.mp3": "Personal best! You're getting stronger.",

    # Encouragement
    "you-got-this.mp3": "You got this!",
    "keep-pushing.mp3": "Keep pushing.",
    "great-work.mp3": "Great work today.",
    "consistency-wins.mp3": "Consistency wins. Keep showing up.",
    "stronger-than-yesterday.mp3": "Stronger than yesterday.",
}

VOICE = "coral"  # OpenAI TTS voice
OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "audio" / "coach"


async def generate_clip(client, filename: str, text: str):
    """Generate a single audio clip."""
    output_path = OUTPUT_DIR / filename

    if output_path.exists():
        print(f"  SKIP {filename} (exists)")
        return

    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice=VOICE,
            input=text,
            response_format="mp3",
        )

        output_path.write_bytes(response.content)
        print(f"  OK   {filename} ({len(response.content)} bytes)")

    except Exception as e:
        print(f"  FAIL {filename}: {e}")


async def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(CLIPS)} audio clips to {OUTPUT_DIR}")
    print(f"Voice: {VOICE}")
    print()

    # Generate in batches of 5 to avoid rate limits
    items = list(CLIPS.items())
    for i in range(0, len(items), 5):
        batch = items[i:i + 5]
        tasks = [generate_clip(client, fn, text) for fn, text in batch]
        await asyncio.gather(*tasks)

    print(f"\nDone! Generated clips in {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
