"""
Offline video comparison: extract poses from an uploaded video, compare
frame-by-frame against a reference pose timeline, and persist results.

Generates a side-by-side comparison video with skeleton overlays.

Runs in a background thread (same pattern as reference_processor).
"""

import cv2
import logging
import numpy as np
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from ....core.streaming.pose_detector import PoseDetector, SKELETON_CONNECTIONS
from .pose_similarity import compute_all_similarities, generate_feedback
from .reference_processor import _processing_semaphore

logger = logging.getLogger(__name__)

# Target height for each panel in the side-by-side video
_PANEL_HEIGHT = 480


def compare_video(challenge_id: int, video_path: str, session_id: int):
    """
    Background job entry point.

    Spawns a daemon thread so the upload endpoint returns immediately.
    """
    t = threading.Thread(
        target=_compare, args=(challenge_id, video_path, session_id), daemon=True
    )
    t.start()


def _compare(challenge_id: int, video_path: str, session_id: int):
    """Run pose extraction on the user video and compare against reference."""
    from ....database import SessionLocal
    from ..db_models.mimic import (
        MimicChallenge, MimicSession, MimicRecord,
        MimicSessionStatus,
    )

    _processing_semaphore.acquire()
    db = SessionLocal()
    try:
        challenge = db.query(MimicChallenge).filter(
            MimicChallenge.id == challenge_id
        ).first()
        session = db.query(MimicSession).filter(
            MimicSession.id == session_id
        ).first()

        if not challenge or not session:
            logger.error(f"Compare: challenge {challenge_id} or session {session_id} not found")
            return

        ref_timeline = challenge.pose_timeline or []
        ref_duration = challenge.video_duration or 1.0

        if not ref_timeline:
            logger.error(f"Compare: no reference timeline for challenge {challenge_id}")
            session.status = MimicSessionStatus.ENDED
            session.ended_at = datetime.utcnow()
            db.commit()
            return

        # Capture status before overwriting — needed for force-compare re-entry
        is_force_compare = session.status == MimicSessionStatus.AUDIO_MISMATCH

        session.status = MimicSessionStatus.ACTIVE
        db.commit()

        # Compute audio-based time offset for alignment
        from .audio_sync import compute_audio_offset
        ref_video_path = challenge.video_local_path

        # On re-entry from force-compare (AUDIO_MISMATCH), skip audio check
        if is_force_compare:
            audio_offset = 0.0
            logger.info(f"Force-compare for session {session_id}: using offset=0")
        elif ref_video_path:
            audio_offset, audio_confidence = compute_audio_offset(ref_video_path, video_path)
            session.audio_offset = audio_offset
            session.audio_confidence = audio_confidence
            logger.info(
                f"Audio offset for session {session_id}: {audio_offset:.3f}s, "
                f"confidence={audio_confidence:.1f}"
            )

            if audio_confidence < 5.0:
                session.status = MimicSessionStatus.AUDIO_MISMATCH
                db.commit()
                logger.info(
                    f"Audio mismatch for session {session_id}: "
                    f"confidence={audio_confidence:.1f} < 5.0, awaiting user decision"
                )
                return
        else:
            audio_offset = 0.0

        report, comparison_video_path = _process_user_video(
            video_path, ref_timeline, ref_duration, audio_offset,
            ref_video_path=ref_video_path,
            session_id=session_id,
        )

        # Persist results
        session.status = MimicSessionStatus.ENDED
        session.ended_at = datetime.utcnow()
        session.overall_score = report.get("overall_score", 0)
        session.duration_seconds = report.get("duration_seconds", 0)
        session.frames_compared = report.get("frames_compared", 0)
        session.score_breakdown = report.get("score_breakdown")
        session.frame_scores = report.get("frame_scores")
        session.comparison_video_path = comparison_video_path

        # Update personal best
        record = db.query(MimicRecord).filter(
            MimicRecord.user_id == session.user_id,
            MimicRecord.challenge_id == challenge_id,
        ).first()

        if record:
            record.attempt_count += 1
            if session.overall_score > record.best_score:
                record.best_score = session.overall_score
        else:
            record = MimicRecord(
                user_id=session.user_id,
                challenge_id=challenge_id,
                best_score=session.overall_score,
                attempt_count=1,
            )
            db.add(record)

        db.commit()
        logger.info(
            f"Compared video for session {session_id}: "
            f"score={session.overall_score:.1f}, frames={session.frames_compared}"
            f"{', video=' + comparison_video_path if comparison_video_path else ''}"
        )

    except Exception as e:
        logger.error(f"Failed to compare video for session {session_id}: {e}")
        try:
            session.status = MimicSessionStatus.ENDED
            session.ended_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
        _processing_semaphore.release()


def _process_user_video(
    video_path: str,
    ref_timeline: list,
    ref_duration: float,
    audio_offset: float = 0.0,
    ref_video_path: Optional[str] = None,
    session_id: Optional[int] = None,
) -> Tuple[dict, Optional[str]]:
    """Extract poses from user video, compare against reference, and generate side-by-side video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open user video: {video_path}")
        return _empty_report(), None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Open reference video for side-by-side rendering
    ref_cap = None
    if ref_video_path and Path(ref_video_path).exists():
        ref_cap = cv2.VideoCapture(ref_video_path)
        if not ref_cap.isOpened():
            logger.warning(f"Cannot open reference video for comparison: {ref_video_path}")
            ref_cap = None
        else:
            logger.info(f"Opened reference video for side-by-side: {ref_video_path}")
    else:
        logger.warning(f"Reference video not available for side-by-side: {ref_video_path}")

    ref_fps = ref_cap.get(cv2.CAP_PROP_FPS) if ref_cap else 30.0

    detector = PoseDetector(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.4,
    )

    # Set up video writer for comparison output
    # Use "sbs_" prefix to avoid overwriting the user's uploaded video (compare_{id}.mp4)
    writer = None
    raw_out_path = None
    final_out_path = None
    if ref_cap and session_id is not None:
        out_dir = Path(video_path).parent
        raw_out_path = str(out_dir / f"sbs_{session_id}_raw.mp4")
        final_out_path = str(out_dir / f"sbs_{session_id}.mp4")

    frame_scores = []
    frame_idx = 0
    last_ref_frame = None
    recent_scores = []  # rolling buffer for median-smoothed video overlay

    try:
        while True:
            ret, user_frame = cap.read()
            if not ret:
                break

            elapsed = frame_idx / fps
            result = detector.detect(user_frame)

            # Time alignment: apply audio offset (no wrap — clamp to ref duration)
            ref_time = elapsed + audio_offset
            if ref_time < 0 or ref_time > ref_duration:
                # Outside reference range — skip scoring but still write frame
                ref_time = max(0.0, min(ref_time, ref_duration))
            ref_idx = _find_closest_ref_frame(ref_timeline, ref_time)
            ref_entry = ref_timeline[ref_idx] if ref_idx is not None else None

            # Compute score for this frame
            score = None
            if (
                result.player_detected
                and result.landmark_list
                and ref_entry
                and ref_entry.get("lm")
            ):
                ref_lm_dicts = [
                    {"nx": lm[0], "ny": lm[1], "visibility": lm[2]}
                    for lm in ref_entry["lm"]
                ]
                scores = compute_all_similarities(result.landmark_list, ref_lm_dicts)
                score = scores.get("angle_score", 0)
                frame_scores.append({
                    "t": round(elapsed, 3),
                    "ref_t": round(ref_time, 3),
                    **scores,
                })

            # Rolling median of last 15 scores for stable video overlay
            if score is not None:
                recent_scores.append(score)
                if len(recent_scores) > 15:
                    recent_scores.pop(0)
            if recent_scores:
                sorted_scores = sorted(recent_scores)
                mid = len(sorted_scores) // 2
                display_score = sorted_scores[mid] if len(sorted_scores) % 2 else (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
            else:
                display_score = None

            # Generate side-by-side frame
            if ref_cap is not None:
                # Seek reference video to matching time
                ref_frame_num = int(ref_time * ref_fps)
                ref_cap.set(cv2.CAP_PROP_POS_FRAMES, ref_frame_num)
                ref_ret, ref_frame = ref_cap.read()
                if ref_ret:
                    last_ref_frame = ref_frame
                elif last_ref_frame is not None:
                    ref_frame = last_ref_frame
                else:
                    ref_frame = np.zeros_like(user_frame)

                # Resize both panels to same height
                ref_panel = _resize_to_height(ref_frame, _PANEL_HEIGHT)
                user_panel = _resize_to_height(user_frame, _PANEL_HEIGHT)

                # Draw body mesh overlay (no skeleton lines)
                rh, rw = ref_panel.shape[:2]
                uh, uw = user_panel.shape[:2]

                if ref_entry and ref_entry.get("lm"):
                    _draw_body_mesh(ref_panel, ref_entry["lm"], rw, rh,
                                    color=(255, 150, 0), alpha=0.7)

                if result.player_detected and result.landmark_list:
                    user_lm = [
                        [lm["nx"], lm["ny"], lm["visibility"]]
                        for lm in result.landmark_list
                    ]
                    _draw_body_mesh(user_panel, user_lm, uw, uh,
                                    color=(0, 200, 0), alpha=0.7)

                # Concatenate side by side
                canvas = _make_canvas(ref_panel, user_panel, display_score)

                # Initialize writer on first frame
                if writer is None:
                    ch, cw = canvas.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(raw_out_path, fourcc, fps, (cw, ch))

                writer.write(canvas)

            frame_idx += 1
    finally:
        detector.close()
        cap.release()
        if ref_cap is not None:
            ref_cap.release()
        if writer is not None:
            writer.release()

    # Re-encode with ffmpeg for browser playback, muxing in the reference video's audio
    # Start audio from audio_offset so it matches the reference frames being shown
    comparison_path = None
    if raw_out_path and Path(raw_out_path).exists():
        comparison_path = _reencode_video(
            raw_out_path, final_out_path,
            audio_source=ref_video_path,
            audio_start=max(0.0, audio_offset),
        )

    return _build_report(frame_scores, frame_idx, fps), comparison_path


def _resize_to_height(frame, target_height: int):
    """Resize frame to target height, preserving aspect ratio."""
    h, w = frame.shape[:2]
    if h == target_height:
        return frame
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height))


def _make_canvas(ref_panel, user_panel, score: Optional[float] = None):
    """Concatenate two panels side-by-side with labels and score overlay."""
    rh, rw = ref_panel.shape[:2]
    uh, uw = user_panel.shape[:2]
    canvas_h = max(rh, uh)
    canvas_w = rw + uw

    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    canvas[:rh, :rw] = ref_panel
    canvas[:uh, rw:rw + uw] = user_panel

    # Draw separator line
    cv2.line(canvas, (rw, 0), (rw, canvas_h), (80, 80, 80), 2)

    # Labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(canvas, "Reference", (10, 30), font, 0.8, (255, 200, 0), 2)
    cv2.putText(canvas, "You", (rw + 10, 30), font, 0.8, (0, 255, 0), 2)

    # Score overlay at bottom center
    if score is not None:
        score_text = f"{score:.0f}%"
        text_size = cv2.getTextSize(score_text, font, 1.0, 2)[0]
        tx = (canvas_w - text_size[0]) // 2
        ty = canvas_h - 20

        # Semi-transparent background for readability
        cv2.rectangle(
            canvas,
            (tx - 10, ty - text_size[1] - 10),
            (tx + text_size[0] + 10, ty + 10),
            (0, 0, 0), -1,
        )
        # Color based on score (thresholds on 0-100 scale)
        if score >= 80:
            color = (0, 255, 0)
        elif score >= 50:
            color = (0, 200, 255)
        else:
            color = (0, 100, 255)
        cv2.putText(canvas, score_text, (tx, ty), font, 1.0, color, 2)

    return canvas


# Limb segment definitions: (start_idx, end_idx, width_start, width_end)
# Widths are fractions of shoulder distance — kept slim for clean overlay.
_LIMB_SEGMENTS = [
    (11, 13, 0.12, 0.09),  # L upper arm
    (12, 14, 0.12, 0.09),  # R upper arm
    (13, 15, 0.09, 0.06),  # L forearm
    (14, 16, 0.09, 0.06),  # R forearm
    (15, 19, 0.06, 0.04),  # L hand (wrist → index)
    (16, 20, 0.06, 0.04),  # R hand (wrist → index)
    (23, 25, 0.16, 0.12),  # L thigh
    (24, 26, 0.16, 0.12),  # R thigh
    (25, 27, 0.12, 0.07),  # L shin
    (26, 28, 0.12, 0.07),  # R shin
    (27, 31, 0.07, 0.04),  # L foot (ankle → foot index)
    (28, 32, 0.07, 0.04),  # R foot (ankle → foot index)
]


def _draw_body_mesh(
    frame, landmarks: list, frame_width: int, frame_height: int,
    color=(0, 200, 0), alpha: float = 0.25,
):
    """Draw translucent filled body silhouette (torso quad, limb trapezoids, head circle)."""
    if len(landmarks) < 33:
        return

    # Hand/foot landmarks get very low visibility from MediaPipe — use relaxed threshold
    _LOW_VIS = {17, 18, 19, 20, 21, 22, 29, 30, 31, 32}

    def _pt(idx):
        lm = landmarks[idx]
        vis = lm[2] if len(lm) > 2 else 0.0
        min_vis = 0.05 if idx in _LOW_VIS else 0.3
        if vis < min_vis:
            return None
        return (int(lm[0] * frame_width), int(lm[1] * frame_height))

    ls = _pt(11)
    rs = _pt(12)
    if not ls or not rs:
        return
    base_w = max(10, ((ls[0] - rs[0]) ** 2 + (ls[1] - rs[1]) ** 2) ** 0.5)

    overlay = frame.copy()

    # Torso: left_shoulder → right_shoulder → right_hip → left_hip
    lh = _pt(23)
    rh = _pt(24)
    if ls and rs and lh and rh:
        cv2.fillPoly(overlay, [np.array([ls, rs, rh, lh], dtype=np.int32)], color)

    # Limb trapezoids
    for a_idx, b_idx, wa_r, wb_r in _LIMB_SEGMENTS:
        pa = _pt(a_idx)
        pb = _pt(b_idx)
        if not pa or not pb:
            continue
        dx = pb[0] - pa[0]
        dy = pb[1] - pa[1]
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        nx = -dy / length
        ny = dx / length
        wa = base_w * wa_r
        wb = base_w * wb_r
        pts = np.array([
            [int(pa[0] + nx * wa), int(pa[1] + ny * wa)],
            [int(pa[0] - nx * wa), int(pa[1] - ny * wa)],
            [int(pb[0] - nx * wb), int(pb[1] - ny * wb)],
            [int(pb[0] + nx * wb), int(pb[1] + ny * wb)],
        ], dtype=np.int32)
        cv2.fillPoly(overlay, [pts], color)

    # Head circle around nose (landmark 0)
    nose = _pt(0)
    if nose:
        cv2.circle(overlay, nose, int(base_w * 0.30), color, -1)

    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)


def _draw_skeleton(
    frame, landmarks: list, frame_width: int, frame_height: int,
    joint_color=(0, 255, 0), bone_color=(0, 200, 0),
):
    """Draw skeleton connections and joint circles on a frame."""
    joint_radius = 4
    bone_thickness = 2

    points = []
    for lm in landmarks:
        x = int(lm[0] * frame_width)
        y = int(lm[1] * frame_height)
        vis = lm[2] if len(lm) > 2 else 0.0
        points.append((x, y, vis))

    for a_idx, b_idx in SKELETON_CONNECTIONS:
        if a_idx >= len(points) or b_idx >= len(points):
            continue
        ax, ay, a_vis = points[a_idx]
        bx, by, b_vis = points[b_idx]
        if a_vis < 0.3 or b_vis < 0.3:
            continue
        cv2.line(frame, (ax, ay), (bx, by), bone_color, bone_thickness)

    for x, y, vis in points:
        if vis < 0.3:
            continue
        cv2.circle(frame, (x, y), joint_radius, joint_color, -1)


def _reencode_video(
    raw_path: str,
    final_path: str,
    audio_source: Optional[str] = None,
    audio_start: float = 0.0,
) -> Optional[str]:
    """Re-encode to H.264 for browser playback, optionally muxing audio from another file.

    audio_start: seek position (seconds) into the audio source, so the muxed
    audio aligns with the reference video frames shown in the side-by-side canvas.
    """
    if shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-i", raw_path]
        if audio_source and Path(audio_source).exists():
            # -ss before -i seeks the audio input to the offset position
            cmd += ["-ss", f"{audio_start:.3f}", "-i", audio_source]
        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
        ]
        if audio_source and Path(audio_source).exists():
            # Map video from first input, audio from second (optional — won't fail if no audio track)
            cmd += ["-map", "0:v:0", "-map", "1:a:0?", "-c:a", "aac", "-shortest"]
        cmd.append(final_path)

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        Path(raw_path).unlink(missing_ok=True)
        if result.returncode != 0:
            logger.warning(f"ffmpeg re-encode failed for comparison video: {result.stderr[:500]}")
            if not Path(final_path).exists():
                return None
    else:
        Path(raw_path).rename(final_path)

    if not Path(final_path).exists():
        return None

    return final_path


def _find_closest_ref_frame(timeline: list, ref_time: float) -> Optional[int]:
    """Find the timeline frame closest to the given time."""
    if not timeline:
        return None

    best_idx = 0
    best_diff = abs(timeline[0].get("t", 0) - ref_time)

    for i, entry in enumerate(timeline):
        diff = abs(entry.get("t", 0) - ref_time)
        if diff < best_diff:
            best_diff = diff
            best_idx = i
        elif diff > best_diff:
            break

    return best_idx


def _apply_rolling_window(frame_scores: list, window_seconds: float = 1.0) -> None:
    """Apply time-based centered rolling window to smooth scores.

    Adds *_smoothed keys to each entry. Uses timestamps (not indices)
    so it works correctly even with dropped frames.
    """
    if not frame_scores:
        return

    half = window_seconds / 2.0
    keys = ("angle_score", "upper_body", "lower_body", "cosine_normalized")
    n = len(frame_scores)

    for i, entry in enumerate(frame_scores):
        t_center = entry["t"]
        t_lo = t_center - half
        t_hi = t_center + half

        # Expand window bounds using timestamps
        lo = i
        while lo > 0 and frame_scores[lo - 1]["t"] >= t_lo:
            lo -= 1
        hi = i
        while hi < n - 1 and frame_scores[hi + 1]["t"] <= t_hi:
            hi += 1

        count = hi - lo + 1
        for k in keys:
            total = sum(frame_scores[j][k] for j in range(lo, hi + 1))
            entry[f"{k}_smoothed"] = round(total / count, 1)


def _build_report(frame_scores: list, total_frames: int, fps: float) -> dict:
    """Build the same report structure as MimicAnalyzer.get_final_report()."""
    if not frame_scores:
        return _empty_report()

    _apply_rolling_window(frame_scores)

    n = len(frame_scores)
    avg = {
        "cosine_raw": round(sum(f["cosine_raw"] for f in frame_scores) / n, 1),
        "cosine_normalized": round(sum(f["cosine_normalized"] for f in frame_scores) / n, 1),
        "angle_score": round(sum(f["angle_score"] for f in frame_scores) / n, 1),
        "upper_body": round(sum(f["upper_body"] for f in frame_scores) / n, 1),
        "lower_body": round(sum(f["lower_body"] for f in frame_scores) / n, 1),
    }

    duration = total_frames / fps if fps > 0 else 0

    return {
        "overall_score": round(avg["angle_score"], 1),
        "duration_seconds": round(duration, 1),
        "frames_compared": n,
        "score_breakdown": avg,
        "frame_scores": frame_scores,
    }


def _empty_report() -> dict:
    return {
        "overall_score": 0,
        "duration_seconds": 0,
        "frames_compared": 0,
        "score_breakdown": {},
        "frame_scores": [],
    }
