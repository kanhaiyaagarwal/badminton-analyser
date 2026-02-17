# Plank Analyzer — State Machine & Thresholds

## Overview

The plank analyzer tracks the **shoulder-hip-ankle angle** (hip is the vertex) to determine if the user is in a valid plank. The timer only counts frames where this angle is within the "good form" range.

---

## Angle Measurement

```
Shoulder -------- Hip (vertex) -------- Ankle

angle = angle_between(shoulder, hip, ankle)
```

- `angle_between()` uses `acos` → **returns [0, 180] only**
- Perfect plank (straight body) → angle ~ 180
- Hips too high OR hips sagging → angle decreases (e.g. 120-150)

**Bug:** Since max output is 180, `good_angle_max=195` is unreachable. Effectively `good_form = (angle >= 150)`. The "Hips sagging" feedback on the `else` branch can never fire because `angle > 195` is impossible.

### Horizontal Check

```python
y_spread = max(shoulder_y, hip_y, ankle_y) - min(shoulder_y, hip_y, ankle_y)
is_horizontal = y_spread < 0.25   # normalized [0,1] coordinates
```

This determines if the body is roughly lying down (plank/floor) vs standing upright.

---

## State Machine — Full Lifecycle

### Phase 1: VISIBILITY GATE (pre-ready)

Before anything, all body groups must have visibility >= 0.5:

| Group | Landmarks | Message if missing |
|-------|-----------|-------------------|
| head | nose (0) | "Can't see your head — adjust camera" |
| shoulders | L/R shoulder (11,12) | "Shoulders not visible — step into frame" |
| torso | L/R hip (23,24) | "Torso not visible — show full body" |
| legs | L/R knee + ankle (25,26,27,28) | "Legs not visible — step back so full body is in frame" |

Feedback: shows the FIRST group that fails (checked in order: head → shoulders → torso → legs).

### Phase 2: READY GATE (pre-ready)

Once all body parts visible, the system waits for the user to get into plank:

```
Condition: is_horizontal AND good_form (angle >= 150)
```

- **Not met** → feedback: "Get into plank position", timer doesn't start
- **Met** → `_ready = True`, `_ready_since = timestamp`, latch ON (never goes back to false)

### Phase 3: ACTIVE SESSION (post-ready)

Once ready, every frame runs three checks in order:

#### A. Stood-Up Tracking

```python
if is_horizontal:
    _stood_up_since = 0       # reset stood-up timer
    mark_active(timestamp)     # refresh inactivity timer
else:
    _stood_up_since = timestamp  # start counting stood-up time
```

**Key issue:** `mark_active()` is ONLY called when `is_horizontal`, NOT when `good_form`. So even with good angle, if not horizontal (shouldn't happen in plank, but edge cases), inactivity timer keeps ticking.

#### B. Hold Timer (the timer the user sees)

```python
if good_form:   # angle in [150, 195] — effectively angle >= 150
    hold_seconds += dt          # TIMER COUNTS
    _form_break_since = 0       # reset form-break tracker
    feedback: "Good plank form!"
else:
    _form_break_since = timestamp (if not already set)
    TIMER PAUSES — no hold_seconds increment
    feedback: (see below)
```

**This is the "pauses too aggressively" issue.** Any frame where angle < 150 stops the timer immediately. A wobble from 152 to 148 pauses the counter.

##### Form Break Feedback Logic

| Condition | Feedback |
|-----------|----------|
| `hold < 15s` AND break < 3s | "Hips too high — straighten your body" (always this, since sagging can't fire) |
| `hold < 15s` AND break >= 3s | "Get back in position! (Xs)" countdown from 8s |
| `hold >= 15s` | "Hips too high — straighten your body" (session ends after 1.5s) |

#### C. Auto-End Detection

Only active after `grace_expired`:
```python
grace_expired = (hold_seconds > 0) OR (time since ready >= 30s)
```

So: either the user has accumulated ANY hold time, OR 30s have passed since getting into plank with no hold time at all.

##### End Signal 1: TORSO ON GROUND

```python
wrist_y - shoulder_y < 0.03 AND wrist_y - hip_y < 0.06
```

Triggers when shoulders AND hips are near wrist level (wrists are on the ground in a plank). This detects full collapse to the floor.

##### End Signal 2: FORM BREAK TOO LONG

```python
if hold_seconds < 15:    # "recovery window"
    limit = 8 seconds     # form_break_timeout
else:
    limit = 1.5 seconds   # ← THE AGGRESSIVE ONE
```

**This is likely why sessions end too fast.** After accumulating just 15s of hold time, ANY form break of 1.5s immediately ends the session. A brief wobble or angle flickering to 148-149 for 1.5s = session over.

##### End Signal 3: STOOD UP

```python
if hold_seconds < 5:
    timeout = 10 seconds     # stood_up_early_timeout
else:
    timeout = 1.5 seconds    # stood_up_timeout
```

User must be `not is_horizontal` (y_spread >= 0.25) for this duration.

##### End Signal 4: INACTIVITY (from base class)

```python
inactivity_timeout = 10 seconds
```

Fires when `mark_active()` hasn't been called for 10s. Since `mark_active()` is only called when `is_horizontal`, this fires after 10s of being non-horizontal even with good form angle.

**Note:** This is SEPARATE from the form_break auto-end. Both can trigger.

##### End Signal 5: MAX DURATION (from base class)

```python
max_duration = 300 seconds (5 minutes)
```

---

## All Thresholds Summary

| Threshold | Default | What it controls |
|-----------|---------|-----------------|
| `good_angle_min` | 150 | Min angle to count as "good form" (timer ticks) |
| `good_angle_max` | 195 | Max angle for good form — **DEAD** (angle_between max is 180) |
| `is_horizontal` threshold | 0.25 | Max y-spread of shoulder/hip/ankle to be "lying down" |
| `first_rep_grace` | 30s | Delay before auto-end signals activate (if no hold time yet) |
| `recovery_window` | 15s | Hold time threshold for generous vs strict form break limits |
| `form_break_grace` | 3s | Within recovery window: form can break this long before countdown |
| `form_break_timeout` | 8s | Within recovery window: total break time before session ends |
| **Post-recovery form break** | **1.5s** | **After 15s hold: ANY form break > 1.5s ends session** |
| `stood_up_timeout` | 1.5s | Non-horizontal time to end (after 5s hold) |
| `stood_up_early_timeout` | 10s | Non-horizontal time to end (first 5s of hold) |
| `collapse_gap` | 0.03 | Shoulder-to-wrist y-gap for collapse detection |
| `collapse_hip_gap` | 0.06 | Hip-to-wrist y-gap for collapse detection |
| `inactivity_timeout` | 10s | Base class: time without `mark_active()` call |
| `max_duration` | 300s | Hard cap on session length |
| `VISIBILITY_THRESHOLD` | 0.5 | Min landmark visibility to pass ready gate |

---

## Identified Issues

### 1. Timer pauses on slight wobble (angle 148-149)
The 150 threshold is binary — 150.1 counts, 149.9 doesn't. No tolerance band or smoothing. A small wobble pauses the counter every other frame.

**Possible fixes:**
- Lower `good_angle_min` to 140-145 (more forgiving)
- Add hysteresis: once in good_form, only exit when angle < 140 (different entry/exit thresholds)
- Add angle smoothing: average last N frames instead of using raw per-frame angle

### 2. Session ends after 1.5s form break (post 15s hold)
The hardcoded 1.5s limit after `recovery_window` (15s hold time) is very aggressive. A user who has been planking for 60s gets the same 1.5s tolerance as someone at 16s.

**Possible fixes:**
- Make post-recovery limit configurable (and higher, e.g. 5s)
- Scale tolerance with hold time (longer plank = more forgiveness, since muscles fatigue)
- Only end on SUSTAINED bad form, not brief flickers

### 3. `good_angle_max = 195` is dead code
Since `angle_between` returns [0, 180], the upper bound never triggers. This means hips-sagging is invisible to the angle check. The "Hips sagging" feedback can never appear.

**Possible fix:** Use signed angle or compare hip_y to the shoulder-ankle midpoint to distinguish sagging vs pike.

### 4. Inactivity timeout overlaps with form break
Both `inactivity_timeout=10s` (base class, needs `mark_active()` which requires `is_horizontal`) and `form_break` (PlankAnalyzer, needs `good_form`) can end the session. A user with slightly bad form who IS horizontal still gets killed by form_break, while a user with good form who is NOT horizontal (edge case) gets killed by inactivity. These dual overlapping timers make behavior unpredictable.

### 5. `mark_active()` not called during good form
`mark_active()` only fires when `is_horizontal`, not when `good_form`. This means the inactivity timer ticks even during perfect plank form if the horizontal check fails (y_spread >= 0.25).
