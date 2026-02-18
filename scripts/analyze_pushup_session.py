#!/usr/bin/env python3
"""
Analyze pushup challenge session pose data (refined JSON export).

Usage:
    python scripts/analyze_pushup_session.py <path_to_json>

Outputs:
    - Session overview (score, duration, end reason)
    - Per-rep timing analysis (flags slow/long reps)
    - Half-pushup rejection check
    - Fatigue curve (avg pace per phase)
    - Duration gap analysis (wall clock vs frame timestamps)
    - Frame-by-frame angle cycle verification (for full-data reps)
"""

import json
import sys


def load_data(path):
    with open(path) as f:
        return json.load(f)


def analyze_session(data):
    print("=" * 60)
    print("SESSION OVERVIEW")
    print("=" * 60)
    print(f"  Session ID:    {data['session_id']}")
    print(f"  Score (reps):  {data['score']}")
    print(f"  Duration:      {data['duration_seconds']:.1f}s ({data['duration_seconds']/60:.1f} min)")
    print(f"  Total frames:  {data['total_frames']}")
    print(f"  End reason:    {data['end_reason']}")
    print()

    segments = data["refined_timeline"]

    # ---- Find ready timestamp ----
    setup = segments[0] if segments[0].get("phase") == "setup" else None
    ready_ts = None
    if setup and "frames" in setup:
        for f in setup["frames"]:
            if f.get("fb") == "Ready! Start your pushups":
                ready_ts = f["t"]
                break

    first_ts = segments[0]["time_range"][0]
    last_ts = segments[-1]["time_range"][1]

    # ---- Duration gap analysis ----
    print("=" * 60)
    print("DURATION GAP ANALYSIS")
    print("=" * 60)
    active_time = last_ts - (ready_ts or first_ts)
    gap = data["duration_seconds"] - active_time
    print(f"  First frame:        {first_ts:.1f}s")
    print(f"  Ready at:           {ready_ts:.1f}s" if ready_ts else "  Ready at:           (not in full data)")
    print(f"  Last frame:         {last_ts:.1f}s")
    print(f"  Frame-based active: {active_time:.1f}s")
    print(f"  Reported duration:  {data['duration_seconds']:.1f}s")
    print(f"  Gap:                {gap:.1f}s")
    if gap > 30:
        print(f"  -> duration_seconds uses server wall clock (datetime.now() - ready_wall_time)")
        print(f"  -> gap = time between last frame and get_final_report() call")
        print(f"  -> user likely waited {gap:.0f}s after session auto-ended before finalizing")
    print()

    # ---- Segment continuity check ----
    print("=" * 60)
    print("FRAME CONTINUITY CHECK")
    print("=" * 60)
    prev_end = None
    has_gaps = False
    for seg in segments:
        start, end = seg["time_range"]
        if prev_end is not None:
            seg_gap = start - prev_end
            if seg_gap > 0.5:
                print(f"  GAP: {seg_gap:.1f}s between rep {seg['rep']-1} and rep {seg['rep']}")
                has_gaps = True
        prev_end = end
    if not has_gaps:
        print(f"  Frames continuous from {first_ts:.1f}s to {last_ts:.1f}s (no gaps > 0.5s)")
    print()

    # ---- Half-pushup rejection check ----
    print("=" * 60)
    print("HALF-PUSHUP REJECTION CHECK")
    print("=" * 60)
    rejected_count = 0
    hips_on_ground_segments = 0
    total_summary = 0

    for seg in segments:
        if seg["rep"] == 0:
            continue
        if seg["type"] == "full":
            fbs = [f["fb"] for f in seg.get("frames", []) if f.get("fb")]
        else:
            fbs = seg.get("feedback_samples", [])
            total_summary += 1

        for fb in fbs:
            if "Half pushup!" in (fb or ""):
                rejected_count += 1
                print(f"  Rep {seg['rep']}: HALF PUSHUP REJECTED")
        if any("Hips on ground" in (fb or "") for fb in fbs):
            hips_on_ground_segments += 1

    if rejected_count == 0:
        print(f"  None — zero reps rejected as half pushups")
    else:
        print(f"  {rejected_count} reps rejected as half pushups")
    print(f"  'Hips on ground' warning in {hips_on_ground_segments}/{total_summary} summary segments")
    print()

    # ---- Per-rep timing ----
    print("=" * 60)
    print("PER-REP TIMING")
    print("=" * 60)
    print(f"  {'Rep':>4}  {'Start':>7}  {'Dur':>6}  {'Frames':>6}  Notes")
    print("  " + "-" * 50)

    rep_durations = []
    for seg in segments:
        if seg["rep"] == 0:
            continue
        rep = seg["rep"]
        tr = seg["time_range"]
        dur = tr[1] - tr[0]
        fc = seg["frame_count"]
        rep_durations.append((rep, dur))

        notes = []
        if dur > 10:
            notes.append("VERY SLOW (rest break?)")
        elif dur > 6:
            notes.append("slow (fatigue)")

        # Always show first 5, last 5, and flagged reps
        if rep <= 5 or rep >= data["total_reps"] - 4 or dur > 6:
            print(f"  {rep:>4}  {tr[0]:>6.1f}s  {dur:>5.1f}s  {fc:>6}  {', '.join(notes)}")

    if len(rep_durations) > 10:
        print(f"  ... ({len(rep_durations) - 10} normal reps omitted)")
    print()

    # ---- Fatigue curve ----
    print("=" * 60)
    print("FATIGUE ANALYSIS (pace per phase)")
    print("=" * 60)
    total_reps = data["total_reps"]
    phase_size = max(1, total_reps // 4)
    phases = []
    for i in range(4):
        start_rep = i * phase_size + 1
        end_rep = min((i + 1) * phase_size, total_reps)
        if i == 3:
            end_rep = total_reps
        phases.append((f"Reps {start_rep}-{end_rep}", start_rep, end_rep))

    for label, sr, er in phases:
        phase_segs = [s for s in segments if sr <= s.get("rep", 0) <= er]
        if not phase_segs:
            continue
        t0 = phase_segs[0]["time_range"][0]
        t1 = phase_segs[-1]["time_range"][1]
        total_time = t1 - t0
        count = len(phase_segs)
        avg = total_time / count
        print(f"  {label:>15}: {total_time:>6.1f}s total, {avg:.1f}s/rep avg")
    print()

    # ---- Full-data rep angle analysis ----
    print("=" * 60)
    print("ANGLE CYCLE VERIFICATION (full-data reps only)")
    print("=" * 60)

    down_threshold = 90
    up_threshold = 145

    for seg in segments:
        if seg["type"] != "full" or seg["rep"] == 0:
            continue
        rep = seg["rep"]
        frames = seg["frames"]
        angles = [f["angle"] for f in frames if f.get("angle") is not None]
        if not angles:
            continue

        # Count complete cycles: below down_threshold then above up_threshold
        crossed_down = False
        cycles = 0
        for a in angles:
            if a < down_threshold:
                crossed_down = True
            elif crossed_down and a > up_threshold:
                cycles += 1
                crossed_down = False

        dur = frames[-1]["t"] - frames[0]["t"]
        half_rejects = sum(1 for f in frames if f.get("fb") and "Half pushup!" in f["fb"])

        # Sample angle curve for display
        step = max(1, len(angles) // 15)
        sampled = [f"{a:.0f}" for a in angles[::step]]

        print(f"  Rep {rep} ({dur:.1f}s): {cycles} cycle(s), {half_rejects} rejected")
        print(f"    Angle: {min(angles):.0f}-{max(angles):.0f}  curve: {' '.join(sampled)}")
    print()

    # ---- Long-rep analysis ----
    long_reps = [(r, d) for r, d in rep_durations if d > 8]
    if long_reps:
        print("=" * 60)
        print("LONG REP ANALYSIS (>8s per rep)")
        print("=" * 60)
        print("  These reps took unusually long. Possible explanations:")
        print("  - User resting between reps (fatigue)")
        print("  - Partial movements not crossing angle thresholds")
        print()
        for rep, dur in long_reps:
            seg = next(s for s in segments if s["rep"] == rep)
            amin = seg.get("angle_min") if seg["type"] == "summary" else min(
                f["angle"] for f in seg["frames"] if f.get("angle") is not None)
            amax = seg.get("angle_max") if seg["type"] == "summary" else max(
                f["angle"] for f in seg["frames"] if f.get("angle") is not None)
            print(f"  Rep {rep:>2}: {dur:.1f}s  angle range {amin}-{amax}")
        print()

    # ---- Verdict ----
    print("=" * 60)
    print("VERDICT")
    print("=" * 60)
    early_avg = sum(d for r, d in rep_durations if r <= 10) / min(10, len(rep_durations))
    late_avg = sum(d for r, d in rep_durations if r > total_reps - 10) / min(10, len(rep_durations))
    slowdown = late_avg / early_avg

    print(f"  Counted reps:       {data['score']}")
    print(f"  Half-pushup rejects: {rejected_count}")
    print(f"  Early pace (1-10):  {early_avg:.1f}s/rep")
    print(f"  Late pace (last 10): {late_avg:.1f}s/rep")
    print(f"  Slowdown factor:    {slowdown:.1f}x")
    print(f"  Frame continuity:   {'continuous' if not has_gaps else 'HAS GAPS'}")
    print(f"  Wall-clock gap:     {gap:.0f}s (post-session idle)")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_refined_pose_data.json>")
        sys.exit(1)

    data = load_data(sys.argv[1])
    if data.get("challenge_type") != "pushup":
        print(f"Warning: this is a {data.get('challenge_type')} session, not pushup")
    analyze_session(data)
