#!/usr/bin/env python3
"""
Analyze squat challenge session pose data (refined JSON export).

Works for squat_half, squat_full, and squat_hold.

Usage:
    python scripts/session_analysis/analyze_squat.py <path_to_json>

Outputs:
    - Session overview (score, duration, end reason)
    - Per-rep timing and angle analysis
    - False-positive detection (confidence collapse, ankle-above-knee, walking gait)
    - Form quality (knee cave, forward lean)
    - Fatigue curve
"""

import json
import math
import sys

# MediaPipe landmark indices
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28


def load_data(path):
    with open(path) as f:
        return json.load(f)


def avg_visibility(lm, indices):
    """Average visibility of given landmark indices."""
    vals = []
    for i in indices:
        if i < len(lm):
            vals.append(lm[i][2] if len(lm[i]) > 2 else 0)
    return sum(vals) / len(vals) if vals else 0


def knee_angle_from_lm(lm):
    """Compute average knee angle from landmarks [nx, ny, vis]."""
    if len(lm) < 29:
        return None
    # hip-knee-ankle angle
    angles = []
    for hip_i, knee_i, ankle_i in [(L_HIP, L_KNEE, L_ANKLE), (R_HIP, R_KNEE, R_ANKLE)]:
        hip = lm[hip_i]
        knee = lm[knee_i]
        ankle = lm[ankle_i]
        ba = (hip[0] - knee[0], hip[1] - knee[1])
        bc = (ankle[0] - knee[0], ankle[1] - knee[1])
        dot = ba[0] * bc[0] + ba[1] * bc[1]
        mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
        mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)
        if mag_ba * mag_bc == 0:
            continue
        cos = max(-1, min(1, dot / (mag_ba * mag_bc)))
        angles.append(math.degrees(math.acos(cos)))
    return sum(angles) / len(angles) if angles else None


def analyze_rep_frames(frames):
    """Analyze full-data rep frames for false-positive signals."""
    if not frames:
        return {}

    angles = [f.get("angle") for f in frames if f.get("angle") is not None]
    lm_frames = [f for f in frames if f.get("lm") and len(f["lm"]) >= 29]

    result = {
        "frame_count": len(frames),
        "angle_min": min(angles) if angles else None,
        "angle_max": max(angles) if angles else None,
        "angle_range": (max(angles) - min(angles)) if angles else 0,
    }

    # Confidence analysis
    lower_body = [L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE]
    confidences = []
    for f in lm_frames:
        conf = avg_visibility(f["lm"], lower_body)
        confidences.append(conf)
    if confidences:
        result["conf_min"] = round(min(confidences), 2)
        result["conf_mean"] = round(sum(confidences) / len(confidences), 2)
    else:
        result["conf_min"] = None
        result["conf_mean"] = None

    # Ankle-above-knee violations
    ankle_above = 0
    for f in lm_frames:
        lm = f["lm"]
        l_ankle_y = lm[L_ANKLE][1]
        r_ankle_y = lm[R_ANKLE][1]
        l_knee_y = lm[L_KNEE][1]
        r_knee_y = lm[R_KNEE][1]
        if l_ankle_y < l_knee_y - 0.02 or r_ankle_y < r_knee_y - 0.02:
            ankle_above += 1
    result["ankle_above_knee"] = ankle_above
    result["ankle_above_pct"] = round(ankle_above / max(len(lm_frames), 1) * 100, 1)

    # Hip CX drift (lateral translation)
    if lm_frames:
        hip_cxs = []
        for f in lm_frames:
            lm = f["lm"]
            cx = (lm[L_HIP][0] + lm[R_HIP][0]) / 2
            hip_cxs.append(cx)
        result["hip_cx_drift"] = round(max(hip_cxs) - min(hip_cxs), 3)

        # Monotonic drift direction (walking signal)
        right_moves = sum(1 for i in range(1, len(hip_cxs)) if hip_cxs[i] > hip_cxs[i - 1])
        left_moves = sum(1 for i in range(1, len(hip_cxs)) if hip_cxs[i] < hip_cxs[i - 1])
        total_moves = right_moves + left_moves
        if total_moves > 0:
            result["hip_drift_monotonic"] = round(max(right_moves, left_moves) / total_moves * 100, 1)
        else:
            result["hip_drift_monotonic"] = 0
    else:
        result["hip_cx_drift"] = 0
        result["hip_drift_monotonic"] = 0

    # Hip CY off-screen
    if lm_frames:
        hip_cys = [(f["lm"][L_HIP][1] + f["lm"][R_HIP][1]) / 2 for f in lm_frames]
        result["hip_cy_max"] = round(max(hip_cys), 3)
        result["hip_offscreen_frames"] = sum(1 for y in hip_cys if y > 1.0)
    else:
        result["hip_cy_max"] = 0
        result["hip_offscreen_frames"] = 0

    # Max angle velocity
    if len(angles) >= 2:
        timestamps = [f["t"] for f in frames if f.get("angle") is not None]
        max_vel = 0
        for i in range(1, len(angles)):
            dt = timestamps[i] - timestamps[i - 1]
            if dt > 0:
                vel = abs(angles[i] - angles[i - 1]) / dt
                max_vel = max(max_vel, vel)
        result["max_angle_velocity"] = round(max_vel, 0)
    else:
        result["max_angle_velocity"] = 0

    # Knee Y asymmetry at minimum angle (walking gait indicator)
    if lm_frames and angles:
        min_angle_idx = angles.index(min(angles))
        if min_angle_idx < len(lm_frames):
            lm = lm_frames[min_angle_idx]["lm"]
            asym = abs(lm[L_KNEE][1] - lm[R_KNEE][1])
            result["knee_y_asymmetry"] = round(asym, 3)
        else:
            result["knee_y_asymmetry"] = 0
    else:
        result["knee_y_asymmetry"] = 0

    return result


def classify_rep(rep_num, duration, analysis):
    """Classify a rep as REAL or FALSE with reason."""
    reasons = []

    if analysis.get("conf_min") is not None and analysis["conf_min"] < 0.5:
        reasons.append(f"low confidence ({analysis['conf_min']})")

    if analysis.get("ankle_above_pct", 0) > 5:
        reasons.append(f"ankle above knee ({analysis['ankle_above_pct']}%)")

    if analysis.get("max_angle_velocity", 0) > 500:
        reasons.append(f"impossible angle velocity ({analysis['max_angle_velocity']} deg/s)")

    if analysis.get("hip_cx_drift", 0) > 0.03:
        reasons.append(f"lateral drift ({analysis['hip_cx_drift']})")

    if analysis.get("hip_drift_monotonic", 0) > 85:
        reasons.append(f"monotonic drift ({analysis['hip_drift_monotonic']}%)")

    if analysis.get("hip_offscreen_frames", 0) > 0:
        reasons.append(f"hips offscreen ({analysis['hip_offscreen_frames']} frames)")

    if duration < 1.0:
        reasons.append(f"too fast ({duration:.1f}s)")

    if analysis.get("knee_y_asymmetry", 0) > 0.03:
        reasons.append(f"knee asymmetry ({analysis['knee_y_asymmetry']})")

    if reasons:
        return "FALSE", reasons
    return "REAL", []


def analyze_session(data):
    challenge_type = data.get("challenge_type", "squat")
    is_hold = challenge_type == "squat_hold"

    print("=" * 70)
    print("SESSION OVERVIEW")
    print("=" * 70)
    print(f"  Session ID:      {data['session_id']}")
    print(f"  Challenge type:  {challenge_type}")
    print(f"  Score:           {data['score']}{'s' if is_hold else ' reps'}")
    print(f"  Duration:        {data['duration_seconds']:.1f}s ({data['duration_seconds'] / 60:.1f} min)")
    print(f"  Total frames:    {data['total_frames']}")
    print(f"  End reason:      {data['end_reason']}")
    print()

    segments = data["refined_timeline"]

    # Find ready timestamp
    ready_ts = None
    setup = segments[0] if segments and segments[0].get("phase") == "setup" else None
    if setup and "frames" in setup:
        for f in setup["frames"]:
            fb = f.get("fb", "")
            if "Ready" in fb:
                ready_ts = f["t"]
                break

    first_ts = segments[0]["time_range"][0] if segments else 0
    last_ts = segments[-1]["time_range"][1] if segments else 0

    print("=" * 70)
    print("TIMING")
    print("=" * 70)
    active_time = last_ts - (ready_ts or first_ts)
    print(f"  First frame:     {first_ts:.1f}s")
    print(f"  Ready at:        {ready_ts:.1f}s" if ready_ts else "  Ready at:        (not found)")
    print(f"  Last frame:      {last_ts:.1f}s")
    print(f"  Active time:     {active_time:.1f}s")
    gap = data["duration_seconds"] - active_time
    if abs(gap) > 5:
        print(f"  Wall-clock gap:  {gap:.1f}s (idle after session end)")
    print()

    # Per-rep analysis
    print("=" * 70)
    print("PER-REP ANALYSIS")
    print("=" * 70)

    header = f"  {'Rep':>3}  {'Time':>12}  {'Dur':>5}  {'Angle':>11}  {'Conf':>9}  {'Flags':>6}  Verdict"
    print(header)
    print("  " + "-" * 75)

    rep_data = []
    real_count = 0
    false_count = 0

    for seg in segments:
        if seg.get("rep", 0) == 0:
            continue

        rep = seg["rep"]
        tr = seg["time_range"]
        dur = tr[1] - tr[0]

        if seg["type"] == "full" and "frames" in seg:
            analysis = analyze_rep_frames(seg["frames"])
        else:
            # Summary segment — limited info
            analysis = {
                "angle_min": seg.get("angle_min"),
                "angle_max": seg.get("angle_max"),
                "angle_range": (seg.get("angle_max", 0) or 0) - (seg.get("angle_min", 0) or 0),
                "conf_min": None,
                "conf_mean": None,
                "ankle_above_knee": 0,
                "ankle_above_pct": 0,
                "hip_cx_drift": 0,
                "hip_drift_monotonic": 0,
                "hip_offscreen_frames": 0,
                "max_angle_velocity": 0,
                "knee_y_asymmetry": 0,
                "frame_count": seg.get("frame_count", 0),
            }

        verdict, reasons = classify_rep(rep, dur, analysis)
        if verdict == "REAL":
            real_count += 1
        else:
            false_count += 1

        amin = f"{analysis['angle_min']:.0f}" if analysis.get("angle_min") is not None else "?"
        amax = f"{analysis['angle_max']:.0f}" if analysis.get("angle_max") is not None else "?"
        conf = f"{analysis['conf_min']:.2f}" if analysis.get("conf_min") is not None else "(sum)"
        flag_count = len(reasons)

        print(f"  {rep:>3}  {tr[0]:>5.1f}-{tr[1]:<5.1f}  {dur:>4.1f}s  {amin:>4}-{amax:<4}  {conf:>7}  {flag_count:>5}  {verdict}")

        rep_data.append({
            "rep": rep, "duration": dur, "analysis": analysis,
            "verdict": verdict, "reasons": reasons,
        })

    print()

    # Detail on false positives
    false_reps = [r for r in rep_data if r["verdict"] == "FALSE"]
    if false_reps:
        print("=" * 70)
        print(f"FALSE POSITIVE DETAIL ({len(false_reps)} reps)")
        print("=" * 70)
        for r in false_reps:
            print(f"\n  Rep {r['rep']} ({r['duration']:.1f}s):")
            for reason in r["reasons"]:
                print(f"    - {reason}")
            a = r["analysis"]
            if a.get("max_angle_velocity", 0) > 0:
                print(f"    angle velocity: {a['max_angle_velocity']:.0f} deg/s (max 400 is physiological)")
            if a.get("hip_cx_drift", 0) > 0:
                print(f"    hip CX drift: {a['hip_cx_drift']:.3f} (>0.03 = walking)")
            if a.get("hip_cy_max", 0) > 0.95:
                print(f"    hip CY max: {a['hip_cy_max']:.3f} (>1.0 = offscreen)")
        print()

    # Fatigue curve (real reps only)
    real_reps = [r for r in rep_data if r["verdict"] == "REAL"]
    if len(real_reps) >= 4:
        print("=" * 70)
        print("FATIGUE ANALYSIS")
        print("=" * 70)
        n = len(real_reps)
        half = n // 2
        early = real_reps[:half]
        late = real_reps[half:]
        early_avg = sum(r["duration"] for r in early) / len(early)
        late_avg = sum(r["duration"] for r in late) / len(late)
        slowdown = late_avg / early_avg if early_avg > 0 else 1
        print(f"  First half avg:  {early_avg:.1f}s/rep (reps 1-{half})")
        print(f"  Second half avg: {late_avg:.1f}s/rep (reps {half + 1}-{n})")
        print(f"  Slowdown factor: {slowdown:.2f}x")

        # Depth fatigue
        early_depths = [r["analysis"].get("angle_min") for r in early if r["analysis"].get("angle_min")]
        late_depths = [r["analysis"].get("angle_min") for r in late if r["analysis"].get("angle_min")]
        if early_depths and late_depths:
            print(f"  Early min angle: {sum(early_depths) / len(early_depths):.0f}° (deeper = better)")
            print(f"  Late min angle:  {sum(late_depths) / len(late_depths):.0f}°")
            if sum(late_depths) / len(late_depths) > sum(early_depths) / len(early_depths) + 10:
                print(f"  -> Depth fatigue detected: squats getting shallower")
        print()

    # Verdict
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    print(f"  Reported reps:   {data['score']}")
    print(f"  Real reps:       {real_count}")
    print(f"  False positives: {false_count}")
    if false_count > 0:
        print(f"  Corrected score: {real_count}")
        print(f"  Over-count:      +{false_count} ({', '.join(f'rep {r['rep']}' for r in false_reps)})")
    else:
        print(f"  Score accurate!")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_refined_pose_data.json>")
        sys.exit(1)

    data = load_data(sys.argv[1])
    ctype = data.get("challenge_type", "")
    if "squat" not in ctype:
        print(f"Warning: this is a {ctype} session, not a squat variant")
    analyze_session(data)
