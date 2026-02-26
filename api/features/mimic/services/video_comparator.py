"""
Offline video comparison: extract poses from an uploaded video, compare
frame-by-frame against a reference pose timeline, and persist results.

Runs in a background thread (same pattern as reference_processor).
"""

import cv2
import logging
import threading
from datetime import datetime
from typing import Optional

from ....core.streaming.pose_detector import PoseDetector
from .pose_similarity import compute_all_similarities, generate_feedback

logger = logging.getLogger(__name__)


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

        session.status = MimicSessionStatus.ACTIVE
        db.commit()

        report = _process_user_video(video_path, ref_timeline, ref_duration)

        # Persist results
        session.status = MimicSessionStatus.ENDED
        session.ended_at = datetime.utcnow()
        session.overall_score = report.get("overall_score", 0)
        session.duration_seconds = report.get("duration_seconds", 0)
        session.frames_compared = report.get("frames_compared", 0)
        session.score_breakdown = report.get("score_breakdown")
        session.frame_scores = report.get("frame_scores")

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


def _process_user_video(
    video_path: str,
    ref_timeline: list,
    ref_duration: float,
) -> dict:
    """Extract poses from user video and compare against reference timeline."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open user video: {video_path}")
        return _empty_report()

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    detector = PoseDetector(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.4,
    )

    frame_scores = []
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            elapsed = frame_idx / fps
            result = detector.detect(frame)

            # Time alignment: map user elapsed to reference (wrap around)
            ref_time = elapsed % ref_duration if ref_duration > 0 else 0
            ref_idx = _find_closest_ref_frame(ref_timeline, ref_time)
            ref_entry = ref_timeline[ref_idx] if ref_idx is not None else None

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
                frame_scores.append({
                    "t": round(elapsed, 3),
                    "ref_t": round(ref_time, 3),
                    **scores,
                })

            frame_idx += 1
    finally:
        detector.close()
        cap.release()

    return _build_report(frame_scores, frame_idx, fps)


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


def _build_report(frame_scores: list, total_frames: int, fps: float) -> dict:
    """Build the same report structure as MimicAnalyzer.get_final_report()."""
    if not frame_scores:
        return _empty_report()

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
