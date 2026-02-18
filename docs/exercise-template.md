# Exercise Feature Template

Reference for adding new exercise types to the fitness challenge system.

## 9 Required Capabilities

Every exercise must implement these capabilities:

### 1. Ready Gate
Before counting reps/hold time, verify the user is in the correct starting position.
- Visibility gating: key landmark groups must have visibility >= 0.5
- Position check: exercise-specific (horizontal for pushup, standing for squat, etc.)
- Camera angle check: side-facing for pushup/plank, front-facing OK for squat
- Feedback: guide user into position ("Get into pushup position" -> "Ready! Start your pushups")
- Set `self._ready = True` and call `self.mark_active(timestamp)` when ready

### 2. Rich Pose Data
`_process_pose()` must return a dict with exercise-specific metrics:
```python
{
    "angle": float,           # primary angle (knee, elbow, etc.)
    "state": str,             # state machine state ("up"/"down", "in_plank", etc.)
    "secondary_angle": float, # optional secondary metric
    "form_indicator": bool,   # e.g. legs_straight, knees_caving
}
```

### 3. Feedback Strings (~15 messages)
Cover these categories:
- **Visibility** (3): per body-part group ("Shoulders not visible", "Legs not visible")
- **Position** (2): camera angle, body position ("Place camera to the side")
- **Exercise cues** (3): depth/range prompts ("Go lower!", "Push up!")
- **Form corrections** (2): common mistakes ("Straighten your legs", "Keep chest up")
- **Rep/hold count** (1): "Rep N!" or "Good plank form!"
- **Auto-end** (3): collapse, stood up, position break
- **Ready** (1): "Ready! Start your [exercise]"

### 4. Collapse Detection (3 signals)
End the session automatically when the user can't continue:
- **Signal 1**: Exercise-specific failure (body on ground, sat down, etc.)
- **Signal 2**: Stuck too long (in DOWN state > timeout, form break > timeout)
- **Signal 3**: Left frame (key landmarks not visible > timeout)
- **Grace period**: `first_rep_grace` (30s default) before any auto-end triggers
- Set `self._session_ended = True` and `self._end_reason = "reason"`

### 5. Form Quality Tracking
Count frames with form issues throughout the session:
```python
self._total_active_frames = 0   # frames after ready
self._specific_issue_frames = 0 # e.g. legs_bent, knees_caving, lean
self._partial_count = 0         # partial reps (didn't meet threshold)
```

### 6. form_summary (in get_final_report)
Override `get_final_report()` to add a `form_summary` dict:
```python
report["form_summary"] = {
    "total_attempts": int,       # good + partial
    "good_reps": int,            # reps meeting criteria
    "partial_count": int,        # reps that didn't meet depth/range
    "issue_pct": float,          # percentage of frames with form issue
    "form_score": int,           # 0-100, weighted combination
}
```

### 7. Results View
In `ChallengeResultsView.vue`, add a form detail block:
```html
<div v-if="result.challenge_type === 'your_type'" class="form-details">
  <!-- Show form_summary fields -->
</div>
```
Update `TYPE_LABELS`, `scoreUnit`, and share text.

### 8. Session View
In `ChallengeSessionView.vue`, add entry to `CHALLENGE_META`:
```javascript
your_type: { title: 'Display Name', hint: 'Setup instructions', scoreLabel: 'Reps', unit: 'reps' }
```
Update placement guide steps, TTS behavior, and any type-specific HUD elements.

### 9. Config Defaults
In `rep_counter.py` `CHALLENGE_DEFAULTS`, add entry with all tunable thresholds.

## Touch Points Checklist

When adding a new exercise type, update these files:

### Backend
| File | What to add |
|------|-------------|
| `api/features/challenges/services/your_analyzer.py` | New analyzer class extending `RepCounterAnalyzer` |
| `api/features/challenges/services/rep_counter.py` | `CHALLENGE_DEFAULTS["your_type"]` entry |
| `api/features/challenges/routers/challenges.py` | Add to `VALID_TYPES` set, `ANALYZER_MAP` dict, import analyzer |
| `api/database.py` | Add to `FEATURES` dict in `seed_feature_access()` |
| `api/db_models/user.py` | Add to `ALL_FEATURES` list |

### Frontend
| File | What to add |
|------|-------------|
| `frontend/src/views/ChallengeSelectorView.vue` | Card in `challenges` array |
| `frontend/src/views/ChallengeHomeView.vue` | Entry in `CHALLENGE_META` |
| `frontend/src/views/ChallengeSessionView.vue` | Entry in `CHALLENGE_META`, placement guide steps, TTS logic |
| `frontend/src/views/ChallengeResultsView.vue` | `TYPE_LABELS`, `scoreUnit`, form detail block, share text |
| `frontend/src/views/AdminView.vue` | `allFeatures` array, session filter `<option>` |
| `frontend/src/router/index.js` | Wildcard `:type` routes already handle new types |

### Database
- `ChallengeConfig` row seeded automatically from `CHALLENGE_DEFAULTS`
- `FeatureAccess` row seeded automatically from `FEATURES` dict
- No schema changes needed (`challenge_type` is a string field)

## Architecture Notes

- **Analyzer base class**: `RepCounterAnalyzer` handles frame decode, pose detection, auto-end checks, recording, screenshots, and the process_frame loop. Subclasses only implement `_process_pose()` and optionally override `get_final_report()`.
- **Score field**: For rep-based exercises `score = self.reps`. For hold-based exercises `score = int(self.hold_seconds)`. The base class checks `challenge_type != "plank"` to decide — update this logic if adding more hold-based types.
- **Config system**: Admin can tune thresholds via `/admin/config/{type}`. Analyzer reads from `ChallengeConfig.thresholds` (falls back to `CHALLENGE_DEFAULTS`).
- **Feature access**: `FeatureAccess` controls visibility per user. Set `default_on_signup: True` to auto-enable for new users.

## Variant Pattern (Squat Example)

For exercises with variants (e.g. squat_hold, squat_half, squat_full):
- Each variant is a separate `challenge_type` string
- Same analyzer class can serve multiple variants via different config defaults
- Frontend groups them under one card in the selector, with a sub-selection page
- Session history and leaderboards are per-variant
