"""
Audio-based alignment for upload-to-compare mimic sessions.

Extracts audio tracks from reference and user videos, then uses
cross-correlation of the actual waveform (downsampled to 4kHz) to find
the time offset that best aligns the two recordings.

The amplitude-envelope approach was too lossy — it averaged out all the
distinctive timing information. Using the waveform directly preserves
pitch and rhythm, giving exact alignment.
"""

import logging
import os
import subprocess
import tempfile
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Max seconds of audio to analyse (keeps FFT fast)
_MAX_AUDIO_SECONDS = 30
# Downsample from 16kHz to 4kHz — keeps waveform shape while being 16x cheaper
_ANALYSIS_RATE = 4000
_EXTRACT_RATE = 16000
_DS_FACTOR = _EXTRACT_RATE // _ANALYSIS_RATE  # 4


def extract_audio_wav(video_path: str) -> Optional[str]:
    """
    Extract mono 16kHz WAV audio from a video file using ffmpeg.

    Returns path to a temporary WAV file, or None if extraction fails
    (e.g. no audio track, ffmpeg not found).
    """
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ac", "1",
                "-ar", str(_EXTRACT_RATE),
                "-vn",
                "-f", "wav",
                wav_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.debug(
                f"ffmpeg audio extraction failed for {video_path}: "
                f"{result.stderr[:200] if result.stderr else 'no stderr'}"
            )
            os.unlink(wav_path)
            return None
        return wav_path
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f"ffmpeg audio extraction error: {e}")
        try:
            os.unlink(wav_path)
        except OSError:
            pass
        return None


def compute_audio_offset(ref_video: str, user_video: str) -> tuple:
    """
    Compute the time offset (in seconds) between reference and user video audio.

    Positive offset means the user video audio starts later in the song
    than the reference — so user elapsed time should be shifted forward
    when looking up the reference frame.

    Uses FFT-based cross-correlation of the actual waveform (downsampled
    to 4kHz) for accurate alignment. The old amplitude-envelope approach
    was too lossy and gave wrong offsets.

    Returns (offset, confidence) tuple. Confidence is peak/mean correlation
    ratio — values >= 5.0 indicate a strong match. Returns (0.0, 0.0) on
    any failure (graceful fallback to naive alignment).
    """
    from scipy.io import wavfile
    from scipy.signal import fftconvolve

    ref_wav = None
    user_wav = None

    try:
        ref_wav = extract_audio_wav(ref_video)
        user_wav = extract_audio_wav(user_video)

        if not ref_wav or not user_wav:
            logger.info("Audio extraction failed for one or both videos, using offset=0")
            return (0.0, 0.0)

        ref_rate, ref_data = wavfile.read(ref_wav)
        user_rate, user_data = wavfile.read(user_wav)

        if ref_rate != user_rate:
            logger.warning(f"Sample rate mismatch: ref={ref_rate}, user={user_rate}")
            return (0.0, 0.0)

        sample_rate = ref_rate

        # Convert to float and cap at _MAX_AUDIO_SECONDS
        max_samples = _MAX_AUDIO_SECONDS * sample_rate
        ref_f = ref_data[:max_samples].astype(np.float32)
        user_f = user_data[:max_samples].astype(np.float32)

        if len(ref_f) == 0 or len(user_f) == 0:
            return (0.0, 0.0)

        # Downsample to _ANALYSIS_RATE for speed (keeps waveform shape)
        ref_ds = ref_f[::_DS_FACTOR]
        user_ds = user_f[::_DS_FACTOR]
        ds_rate = sample_rate / _DS_FACTOR

        # Normalize to zero-mean unit-variance for robust peak detection
        ref_n = (ref_ds - np.mean(ref_ds)) / (np.std(ref_ds) + 1e-10)
        user_n = (user_ds - np.mean(user_ds)) / (np.std(user_ds) + 1e-10)

        # FFT-based cross-correlation (O(N log N), fast for 120k samples)
        corr = fftconvolve(ref_n, user_n[::-1], mode="full")
        peak_idx = int(np.argmax(corr))

        # Convert peak index to time offset
        # For fftconvolve(a, b_reversed, 'full'), lag = peak_idx - (len(b) - 1)
        offset = (peak_idx - len(user_n) + 1) / ds_rate

        # Clamp to reasonable range
        ref_duration = len(ref_f) / sample_rate
        offset = max(-ref_duration, min(ref_duration, offset))

        # Confidence: ratio of peak to mean correlation
        corr_abs = np.abs(corr)
        confidence = corr[peak_idx] / (np.mean(corr_abs) + 1e-10)

        logger.info(
            f"Audio cross-correlation: offset={offset:.3f}s, "
            f"confidence={confidence:.1f}, "
            f"ref_dur={ref_duration:.1f}s, user_dur={len(user_f)/sample_rate:.1f}s"
        )

        return (offset, confidence)

    except Exception as e:
        logger.warning(f"Audio offset computation failed: {e}")
        return (0.0, 0.0)

    finally:
        for path in (ref_wav, user_wav):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
