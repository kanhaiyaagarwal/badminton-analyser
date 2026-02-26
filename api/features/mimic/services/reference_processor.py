"""
Background job: process a reference video into a pose timeline.

Opens the video with cv2, runs PoseDetector on each frame, stores
the resulting landmark+angle timeline as JSON on the MimicChallenge row.
Also generates an annotated video with skeleton overlay for admin review.
"""

import cv2
import logging
import shutil
import subprocess
import threading
from pathlib import Path
from typing import List, Optional

from ....core.streaming.pose_detector import PoseDetector, SKELETON_CONNECTIONS

logger = logging.getLogger(__name__)


def process_reference_video(challenge_id: int):
    """
    Background job entry point.

    Spawns a daemon thread so the upload endpoint returns immediately.
    """
    t = threading.Thread(
        target=_process, args=(challenge_id,), daemon=True
    )
    t.start()


def _process(challenge_id: int):
    """Run pose extraction on the reference video."""
    from ....database import SessionLocal
    from ..db_models.mimic import MimicChallenge, MimicProcessingStatus

    db = SessionLocal()
    try:
        challenge = db.query(MimicChallenge).filter(
            MimicChallenge.id == challenge_id
        ).first()
        if not challenge:
            logger.error(f"Mimic challenge {challenge_id} not found")
            return

        # Find the video file
        video_path = challenge.video_local_path
        if not video_path or not Path(video_path).exists():
            logger.error(f"Video file not found for challenge {challenge_id}")
            challenge.processing_status = MimicProcessingStatus.FAILED
            db.commit()
            return

        challenge.processing_status = MimicProcessingStatus.PROCESSING
        db.commit()

        timeline = _extract_pose_timeline(video_path)

        if timeline is None:
            challenge.processing_status = MimicProcessingStatus.FAILED
            db.commit()
            return

        # Extract thumbnail at ~2 second mark
        thumbnail_path = _extract_thumbnail(video_path, challenge_id)

        challenge.pose_timeline = timeline["frames"]
        challenge.total_frames = timeline["total_frames"]
        challenge.video_duration = timeline["duration"]
        challenge.video_fps = timeline["fps"]
        challenge.processing_status = MimicProcessingStatus.READY

        if thumbnail_path:
            challenge.thumbnail_local_path = thumbnail_path

        # Generate annotated video with skeleton overlay
        annotated_path = _generate_annotated_video(
            video_path, timeline["frames"], challenge_id
        )
        if annotated_path:
            challenge.annotated_video_local_path = annotated_path

        db.commit()
        logger.info(
            f"Processed mimic challenge {challenge_id}: "
            f"{timeline['total_frames']} frames, {timeline['duration']:.1f}s"
        )

    except Exception as e:
        logger.error(f"Failed to process mimic challenge {challenge_id}: {e}")
        try:
            challenge.processing_status = MimicProcessingStatus.FAILED
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _extract_pose_timeline(video_path: str) -> Optional[dict]:
    """Extract pose landmarks from every frame of a video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    detector = PoseDetector(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.4,
    )

    frames = []
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            t = frame_idx / fps
            result = detector.detect(frame)

            if result.player_detected and result.landmark_list:
                lm_compact = [
                    [round(lm["nx"], 4), round(lm["ny"], 4), round(lm["visibility"], 3)]
                    for lm in result.landmark_list
                ]

                # Compute key angles for this frame
                angles = _compute_frame_angles(result.landmark_list)

                frames.append({
                    "t": round(t, 3),
                    "lm": lm_compact,
                    "angles": angles,
                })
            else:
                # No pose detected — store null entry so timing stays correct
                frames.append({"t": round(t, 3), "lm": None, "angles": None})

            frame_idx += 1

    finally:
        detector.close()
        cap.release()

    duration = frame_idx / fps if fps > 0 else 0

    return {
        "frames": frames,
        "total_frames": frame_idx,
        "duration": round(duration, 3),
        "fps": round(fps, 2),
    }


def _compute_frame_angles(landmark_list: list) -> dict:
    """Compute key joint angles from a landmark list."""
    from .pose_similarity import ANGLE_DEFINITIONS

    angles = {}
    n = len(landmark_list)

    for name, a_idx, b_idx, c_idx in ANGLE_DEFINITIONS:
        if a_idx >= n or b_idx >= n or c_idx >= n:
            continue
        a = (landmark_list[a_idx]["nx"], landmark_list[a_idx]["ny"])
        b = (landmark_list[b_idx]["nx"], landmark_list[b_idx]["ny"])
        c = (landmark_list[c_idx]["nx"], landmark_list[c_idx]["ny"])
        angles[name] = round(PoseDetector.angle_between(a, b, c), 1)

    return angles


def _extract_thumbnail(video_path: str, challenge_id: int) -> Optional[str]:
    """Extract a thumbnail frame at the 2-second mark."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    target_frame = int(2.0 * fps)

    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None

    thumb_dir = Path(video_path).parent
    thumb_path = str(thumb_dir / f"mimic_{challenge_id}_thumb.jpg")
    cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return thumb_path


def _generate_annotated_video(
    video_path: str, timeline: List[dict], challenge_id: int
) -> Optional[str]:
    """
    Generate a copy of the reference video with skeleton overlay drawn
    on each frame where pose was detected.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video for annotation: {video_path}")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_dir = Path(video_path).parent
    raw_path = str(out_dir / f"mimic_{challenge_id}_annotated_raw.mp4")
    final_path = str(out_dir / f"mimic_{challenge_id}_annotated.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(raw_path, fourcc, fps, (width, height))

    frame_idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Draw skeleton if we have pose data for this frame
            if frame_idx < len(timeline):
                entry = timeline[frame_idx]
                lm = entry.get("lm")
                if lm:
                    _draw_skeleton(frame, lm, width, height)

            out.write(frame)
            frame_idx += 1
    finally:
        cap.release()
        out.release()

    # Re-encode to H.264 for browser playback
    if shutil.which("ffmpeg"):
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_path,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                final_path,
            ],
            capture_output=True, timeout=300,
        )
        Path(raw_path).unlink(missing_ok=True)
        if result.returncode != 0:
            logger.warning(f"ffmpeg re-encode failed for annotated video: {result.stderr[:500]}")
            if not Path(final_path).exists():
                return None
    else:
        # No ffmpeg — use raw mp4v file
        Path(raw_path).rename(final_path)

    if not Path(final_path).exists():
        return None

    logger.info(f"Generated annotated video for challenge {challenge_id}")
    return final_path


def _draw_skeleton(
    frame, landmarks: list, frame_width: int, frame_height: int
):
    """Draw skeleton connections and joint circles on a frame."""
    joint_color = (0, 255, 0)       # green
    bone_color = (0, 200, 0)        # darker green
    joint_radius = 4
    bone_thickness = 2

    # Convert normalized landmarks to pixel coords
    points = []
    for lm in landmarks:
        x = int(lm[0] * frame_width)
        y = int(lm[1] * frame_height)
        vis = lm[2] if len(lm) > 2 else 0.0
        points.append((x, y, vis))

    # Draw connections
    for a_idx, b_idx in SKELETON_CONNECTIONS:
        if a_idx >= len(points) or b_idx >= len(points):
            continue
        ax, ay, a_vis = points[a_idx]
        bx, by, b_vis = points[b_idx]
        if a_vis < 0.3 or b_vis < 0.3:
            continue
        cv2.line(frame, (ax, ay), (bx, by), bone_color, bone_thickness)

    # Draw joints
    for x, y, vis in points:
        if vis < 0.3:
            continue
        cv2.circle(frame, (x, y), joint_radius, joint_color, -1)
