# Testing & Next Steps Guide

> Complete guide for verifying M2 (Eye), M3 (Voice), M4 (Brain) implementation and remaining work.
> Last updated: 2026-03-11

---

## Table of Contents

1. [Current Status Overview](#1-current-status-overview)
2. [Prerequisites & Setup](#2-prerequisites--setup)
3. [Testing M4 (Brain)](#3-testing-m4-brain)
4. [Testing M2 (Eye)](#4-testing-m2-eye)
5. [Testing M3 (Voice)](#5-testing-m3-voice)
6. [End-to-End Walkthrough](#6-end-to-end-walkthrough)
7. [Known Gaps & Remaining Work](#7-known-gaps--remaining-work)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Current Status Overview

| Milestone | Feature | Code Status | Needs Testing |
|-----------|---------|-------------|---------------|
| **M4** | LLM service (OpenAI/Anthropic/Ollama) | Done | Yes |
| **M4** | AI workout plan generation | Done | Yes |
| **M4** | Progressive overload engine | Done | Yes |
| **M4** | LLM coach feedback | Done | Yes |
| **M4** | Session agent (7 actions) | Done | Yes |
| **M2** | Camera tracking (reuses challenge WS) | Done | Yes |
| **M2** | Form scoring | Done | Yes |
| **M2** | ActiveSet camera mode + manual mode | Done | Yes |
| **M3** | TTS (pre-recorded + dynamic OpenAI) | Done | Yes — audio clips not generated yet |
| **M3** | STT voice commands | Done | Yes |
| **M3** | Voice output (auto-play coach audio) | Done | Yes |
| **M3** | Voice input (RestTimer) | Done | Yes |

### Files Created (new)

```
api/features/workout/services/llm_service.py
api/features/workout/services/ai_plan_generator.py
api/features/workout/services/progressive_overload.py
api/features/workout/services/camera_tracking.py
api/features/workout/services/form_scoring.py
api/features/workout/services/tts_service.py
api/features/workout/services/voice_command.py
frontend/src/composables/useCameraTracking.js
frontend/src/composables/useVoiceOutput.js
frontend/src/composables/useVoiceInput.js
scripts/generate_coach_audio.py
docs/assets-required.md
```

### Files Modified

```
api/config.py                                         # LLM + TTS config fields
api/database.py                                       # ExerciseProgression migration
api/features/workout/db_models/workout.py             # ExerciseProgression model, form_score
api/features/workout/models/workout.py                # audio_url in AgentResponse
api/features/workout/services/workout_service.py      # AI plan integration
api/features/workout/services/coach_feedback.py       # LLM feedback + exercise history
api/features/workout/services/session_agent.py        # LLM feedback + progression + audio_url
api/features/workout/routers/workout.py               # start-tracking, camera-result, TTS endpoints
api/main.py                                           # Removed custom workout WS (reuses challenge WS)
frontend/src/views/workout/session/ActiveSet.vue      # Camera mode + manual mode
frontend/src/views/workout/session/ExerciseIntro.vue  # Tracking badge
frontend/src/views/workout/session/RestTimer.vue      # Voice input
frontend/src/views/workout/WorkoutSessionView.vue     # Voice output + mute
```

---

## 2. Prerequisites & Setup

### 2.1 Environment Variables

Your `.env` already has `OPENAI_API_KEY` set. This single key powers:
- LLM plan generation + coach feedback (via `gpt-4o-mini`)
- Dynamic TTS audio generation (via OpenAI TTS API)

Optional additions:
```env
# To use Anthropic instead of OpenAI for LLM (not TTS):
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...

# To use free local models (no API key needed):
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3
# OLLAMA_BASE_URL=http://localhost:11434

# To disable AI features and use template fallbacks:
# LLM_ENABLED=false

# To disable audio entirely:
# TTS_ENABLED=false
```

### 2.2 Install Dependencies

```bash
source venv/bin/activate
pip install openai anthropic   # if not already installed
```

Verify:
```bash
python -c "import openai; print('openai:', openai.__version__)"
python -c "import anthropic; print('anthropic:', anthropic.__version__)"
```

### 2.3 Start Backend

```bash
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**What to check on startup:**
- No import errors in logs
- `init_db()` runs — look for migration logs
- `exercise_progressions` table created (if first run)
- `exercises` table seeded

### 2.4 Start Frontend

```bash
cd frontend && npm run dev
```

Dev server: `https://localhost:5173` (HTTPS required for camera API)

### 2.5 Generate Coach Audio Clips (one-time)

```bash
source venv/bin/activate
OPENAI_API_KEY=sk-... python scripts/generate_coach_audio.py
```

This generates ~55 MP3 files in `frontend/public/audio/coach/`. Takes ~2-3 minutes. Cost: ~$0.10.

Without this step, pre-recorded audio won't play — the system falls back to:
1. Dynamic OpenAI TTS (slower, costs per request)
2. Browser `speechSynthesis` (free, robotic)

---

## 3. Testing M4 (Brain)

### 3.1 Database Migration

**Goal:** Verify `exercise_progressions` table and `form_score` column exist.

```bash
# SQLite
source venv/bin/activate
python -c "
from api.database import SessionLocal
db = SessionLocal()
result = db.execute('PRAGMA table_info(exercise_progressions)').fetchall()
print('exercise_progressions columns:', [r[1] for r in result])
result2 = db.execute('PRAGMA table_info(exercise_sets)').fetchall()
print('exercise_sets columns:', [r[1] for r in result2])
db.close()
"
```

**Expected:** Both tables exist. `exercise_sets` has `form_score` column. `exercise_progressions` has `user_id, exercise_id, current_weight_kg, current_reps, weeks_at_current, last_progression_date, progression_history`.

### 3.2 LLM Service

**Goal:** Verify the LLM service can call OpenAI and return structured JSON.

```bash
source venv/bin/activate
python -c "
import asyncio
from api.features.workout.services.llm_service import chat

async def test():
    result = await chat(
        'You are a test bot. Return JSON.',
        'Return {\"status\": \"ok\", \"number\": 42}',
        json_mode=True
    )
    print('LLM response:', result)

asyncio.run(test())
"
```

**Expected:** `{'status': 'ok', 'number': 42}` (or similar).

**Test fallback:** Temporarily set `LLM_ENABLED=false` in `.env` and restart — should return `None`.

### 3.3 AI Plan Generation (via Onboarding)

**Goal:** Verify that onboarding creates an AI-generated plan instead of a template plan.

1. Open `https://localhost:5173/workout`
2. If not onboarded, you'll be redirected to `/workout/onboarding`
3. Complete the 4-step form:
   - Step 1: Select fitness level (e.g., "Intermediate")
   - Step 2: Enter profile (age, weight, etc.)
   - Step 3: Select goals (e.g., "Build Muscle", "Lose Fat")
   - Step 4: Select days/week (e.g., 4), duration (e.g., 45 min), equipment
4. Submit

**Check backend logs for:**
```
INFO: AI plan generated successfully for user X
```
or
```
WARNING: AI plan generation failed, falling back to template
```

**Verify via API:**
```bash
# Get your JWT token from browser DevTools → Application → localStorage → token
TOKEN="your-jwt-here"
curl -s http://localhost:8000/api/v1/workout/today \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:** A workout plan with exercise names, sets, reps. If AI-generated, the plan should be personalized to your goals/equipment.

### 3.4 Template Fallback

**Goal:** Verify fallback works when LLM is unavailable.

1. Temporarily remove `OPENAI_API_KEY` from `.env`
2. Restart backend
3. Delete existing user profile (or use a new account):
   ```bash
   # In SQLite
   python -c "
   from api.database import SessionLocal
   db = SessionLocal()
   # Delete profile to force re-onboarding
   db.execute('DELETE FROM user_profiles WHERE user_id = YOUR_USER_ID')
   db.execute('DELETE FROM workout_plans WHERE user_id = YOUR_USER_ID')
   db.commit()
   "
   ```
4. Re-onboard
5. Check logs: should say "falling back to template"
6. Restore `OPENAI_API_KEY` and restart

### 3.5 Progressive Overload

**Goal:** Verify progression targets appear and update after completing sets.

This is best tested after a full workout session (see Section 6). After completing a workout:

```bash
source venv/bin/activate
python -c "
from api.database import SessionLocal
from api.features.workout.db_models.workout import ExerciseProgression
db = SessionLocal()
progs = db.query(ExerciseProgression).all()
for p in progs:
    print(f'Exercise {p.exercise_id}: {p.current_weight_kg}kg x{p.current_reps}, weeks={p.weeks_at_current}')
db.close()
"
```

**Expected:** After completing all sets of an exercise at RPE <= 7, the next session should show increased weight (+2.5kg for compound) or reps (+1-2 for isolation).

### 3.6 LLM Coach Feedback

**Goal:** Verify personalized coach feedback instead of template text.

1. Start a workout session (Section 6)
2. Complete a set
3. Check the `coach_says` text on the rest timer screen

**With LLM:** Feedback references your specific exercise, reps, and history (e.g., "Great push-ups! You did 12 reps, 2 more than last time.")
**Without LLM:** Generic template (e.g., "Good set! Keep it up.")

Check backend logs for: `Smart set feedback generated` or `LLM set feedback failed, using template`.

---

## 4. Testing M2 (Eye)

### 4.1 Camera Tracking Setup

**Goal:** Verify the start-tracking endpoint creates a challenge session.

```bash
TOKEN="your-jwt-here"

# First, start a workout session
curl -s -X POST http://localhost:8000/api/v1/workout/sessions/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool

# Note the session_id from the response, then:
SESSION_ID=123  # replace with actual

curl -s -X POST http://localhost:8000/api/v1/workout/sessions/$SESSION_ID/start-tracking \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"exercise_slug": "push-up"}' | python -m json.tool
```

**Expected response:**
```json
{
  "challenge_session_id": 456,
  "challenge_type": "pushup",
  "ws_url": "/ws/challenge/456"
}
```

### 4.2 Trackable Exercises

**Goal:** Verify the correct exercises show camera mode.

| Exercise Slug | Analyzer Type | Should Show Camera |
|---|---|---|
| `push-up` | pushup | Yes |
| `bodyweight-squat` | squat_full | Yes |
| `plank` | plank | Yes |
| `squat-hold` | squat_hold | Yes |
| `jump-squat` | squat_full | Yes |
| `burpee` | pushup | Yes |
| `bench-press` | — | No (manual mode) |
| `deadlift` | — | No (manual mode) |

### 4.3 Camera Mode in ActiveSet

**Goal:** Test the full camera tracking flow in the UI.

1. Start a workout that includes push-ups or squats
2. Navigate through Brief → Exercise Intro
3. On Exercise Intro, verify the "Camera Tracking" badge appears for trackable exercises
4. Tap "Begin Set"
5. **ActiveSet should show:**
   - Camera feed (mirrored)
   - Red/green ready indicator circle (red until body detected, green when ready)
   - Rep counter (top-left) — starts at 0
   - Set info bar (bottom) — "Set 1/3" + timer
6. Do some reps in front of camera
7. **Verify:**
   - Rep counter increments
   - Form feedback toasts appear (e.g., "Go deeper", "Good form")
   - Pose skeleton overlay on canvas
8. Tap "Done"
9. **Should transition to Rest Timer** with the camera-detected rep count

### 4.4 Plank (Hold-Based) Camera Mode

**Goal:** Verify hold-based exercises use frame dropping and count seconds.

1. Start a workout that includes plank
2. Navigate to plank's ActiveSet
3. **Verify:**
   - Counter shows "sec" label (not "reps")
   - Hold timer counts up while in plank position
   - Timer pauses when form breaks
   - Frame dropping keeps the connection smooth (no lag)

### 4.5 Manual Mode Fallback

**Goal:** Verify non-trackable exercises show manual input.

1. Start a workout with bench press or deadlift
2. Navigate to ActiveSet
3. **Verify:**
   - No camera feed — shows target reps + timer instead
   - "Complete Set" button opens inline form
   - Form has reps stepper, weight stepper, RPE selector
   - "Save" submits the set

### 4.6 Camera-Result Submission

**Goal:** Verify camera results feed back into the workout session agent.

After completing a camera-tracked set, check the backend logs:
```
INFO: complete_set — exercise_id=X, reps=Y, form_score=Z
```

And verify the rest timer shows appropriate coach feedback that references the camera-detected rep count.

---

## 5. Testing M3 (Voice)

### 5.1 Pre-Recorded Audio Clips

**Goal:** Verify clips exist and match.

First, generate them (if not done):
```bash
source venv/bin/activate
python scripts/generate_coach_audio.py
```

Then verify:
```bash
ls frontend/public/audio/coach/ | wc -l
# Expected: ~55 files

# Check a specific clip:
file frontend/public/audio/coach/go-deeper.mp3
# Expected: MPEG audio
```

### 5.2 TTS Pre-Recorded Matching

**Goal:** Verify the TTS service matches coach text to pre-recorded clips.

```bash
source venv/bin/activate
python -c "
from api.features.workout.services.tts_service import match_prerecorded, get_audio_url_for_coach

# Should match pre-recorded
print('Match \"Go deeper\":', match_prerecorded('Go deeper.'))
print('Match \"Keep going\":', match_prerecorded('Keep going. You have got this.'))
print('Match \"Great rep\":', match_prerecorded('Great rep!'))

# Should NOT match (dynamic text)
print('Match dynamic:', match_prerecorded('You did 15 push-ups today, 3 more than last week!'))

# Full URL resolution
print('URL for static:', get_audio_url_for_coach('Go deeper.'))
print('URL for dynamic:', get_audio_url_for_coach('You crushed 20 squats at 80kg!'))
"
```

**Expected:**
- Static phrases → `/audio/coach/go-deeper.mp3` etc.
- Dynamic phrases → `/api/v1/workout/tts/{hash}?text=...` or `None` (if TTS disabled)

### 5.3 Dynamic TTS Endpoint

**Goal:** Verify the TTS endpoint generates audio on the fly.

```bash
# This should return an MP3 audio file:
curl -s -o /tmp/test-tts.mp3 \
  "http://localhost:8000/api/v1/workout/tts/test123?text=Great%20workout%20today"
file /tmp/test-tts.mp3
# Expected: MPEG audio

# Play it (macOS):
afplay /tmp/test-tts.mp3
```

**Note:** This endpoint has no auth (by design — audio elements can't send JWT headers).

### 5.4 Voice Output (Auto-Play Coach Audio)

**Goal:** Verify coach audio plays automatically during workout.

1. Start a workout session
2. On the Brief screen, check if coach audio plays (coach_says text)
3. Complete a set → Rest Timer should play coach tip audio
4. **Mute button test:**
   - Tap the speaker icon in the top bar
   - Audio should stop and icon should change to muted
   - Refresh page — mute state should persist (localStorage)
   - Unmute — audio resumes on next view change

### 5.5 Voice Input (RestTimer)

**Goal:** Verify voice commands work during rest periods.

1. Complete a set to reach Rest Timer
2. Tap "Voice Command" button
3. **Verify:**
   - Pulsing green dot appears with "Listening..."
   - Say "skip rest" or "next" or "go"
   - Should advance to next set
4. Tap "Stop Listening" to disable

**Browser support:** Chrome (desktop + Android) and Safari (iOS 14.5+). Firefox does not support Web Speech API.

### 5.6 Voice Command Parser (Unit Test)

```bash
source venv/bin/activate
python -c "
from api.features.workout.services.voice_command import parse_voice_command

tests = [
    ('done', {}),
    ('12 reps', {}),
    ('10 at 60 kg', {}),
    ('skip rest', {}),
    ('RPE 7', {}),
    ('end workout', {}),
    ('what is the weather', {}),
]
for text, ctx in tests:
    result = parse_voice_command(text, ctx)
    print(f'  \"{text}\" → {result}')
"
```

**Expected:**
```
  "done" → ('complete_set', {})
  "12 reps" → ('complete_set', {'reps': 12})
  "10 at 60 kg" → ('complete_set', {'reps': 10, 'weight_kg': 60.0})
  "skip rest" → ('skip_rest', {})
  "RPE 7" → ('complete_set', {'rpe': 7})
  "end workout" → ('end_workout', {})
  "what is the weather" → None
```

---

## 6. End-to-End Walkthrough

This is the full happy-path test covering all three milestones.

### Step 1: Fresh Start

```bash
# Terminal 1: Backend
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Step 2: Create Account & Onboard

1. Open `https://localhost:5173`
2. Sign up / log in
3. Navigate to `/workout` (or "Workout" in FeatureHub)
4. Complete onboarding (4 steps)
5. **Verify:** Plan is created (check backend logs for "AI plan generated" or "template fallback")

### Step 3: View Today's Workout

1. After onboarding, you land on Workout Home
2. **Verify:**
   - Today's workout card shows exercise list
   - Streak counter visible
   - "Start Workout" button visible
   - Coach message from otter mascot

### Step 4: Start Workout → Brief Phase

1. Tap "Start Workout"
2. **Verify Brief Phase:**
   - Exercise list with sets/reps
   - Time budget (e.g., "~45 min")
   - "Begin Workout" button
   - Coach audio plays (if audio clips generated)

### Step 5: Exercise Intro

1. Tap "Begin Workout"
2. **Verify Exercise Intro:**
   - Exercise name + target (e.g., "Push-Up — 3 x 12")
   - Camera tracking badge (if trackable)
   - Form cues (e.g., "Hands shoulder-width apart")
   - Last session history + PRs (if any)
   - "Begin Set" + "Skip Exercise" buttons

### Step 6: Active Set (Camera Mode — Push-Up)

1. Tap "Begin Set" on a trackable exercise
2. **Verify Camera Mode:**
   - Camera feed appears (mirrored)
   - Red circle → position yourself
   - Green circle → body detected, ready
   - Do push-ups → rep counter increments
   - Form feedback toasts appear
   - Pose skeleton overlay visible
3. Tap "Done"
4. **Verify:** Transitions to Rest Timer with your rep count

### Step 7: Rest Timer

1. **Verify Rest Timer:**
   - Circular countdown (e.g., 90 seconds)
   - Feedback badge from last set
   - "Next Up" preview (next exercise/set)
   - Coach tip bubble with otter avatar
   - "Skip Rest" button
   - Coach audio plays
2. **Test voice input:**
   - Tap "Voice Command"
   - Say "skip rest"
   - Should advance to next set

### Step 8: Active Set (Manual Mode — Bench Press)

1. When you reach a non-trackable exercise (e.g., bench press)
2. **Verify Manual Mode:**
   - Target display (reps)
   - Timer counting up
   - Progression hint (if returning user: "Target: 62.5kg x 10")
   - "Complete Set" → opens log form
   - Reps/Weight/RPE steppers
   - "Save" submits

### Step 9: Complete Workout → Summary

1. Complete all exercises (or tap pause → "End Workout")
2. **Verify Summary Phase:**
   - Total exercises, sets, total reps, total volume
   - Duration
   - PRs achieved (if any)
   - Highlights section
   - Streak count
   - Coach summary (AI-generated or template)
   - Progression updates (e.g., "+2.5kg for next bench press")
   - "Home" button

### Step 10: Verify Persistence

1. Go back to Workout Home
2. **Verify:**
   - Streak updated
   - Today's workout shows "Completed" state
   - Progress stats updated
3. Start another workout
4. **Verify progression:**
   - Exercise Intro shows updated targets from progressive overload

---

## 7. Known Gaps & Remaining Work

### 7.1 Must Do (Blocking)

| Item | Description | How to Fix |
|------|-------------|------------|
| **Generate audio clips** | `frontend/public/audio/coach/` is empty — 55 pre-recorded clips need generating | Run `python scripts/generate_coach_audio.py` with `OPENAI_API_KEY` set. Cost: ~$0.10 |

### 7.2 Should Do (Quality)

| Item | Description | Effort |
|------|-------------|--------|
| **Unit tests for progressive overload** | Edge cases: deload trigger, bodyweight holds, first-time user | 2 hours |
| **Unit tests for voice commands** | Fuzzy matching, number word parsing, edge cases | 1 hour |
| **Unit tests for form scoring** | Weight calculation, empty timeline, all-bad-form | 1 hour |
| **Integration test: onboarding → plan** | Verify full flow with mock LLM | 2 hours |
| **Error states in UI** | Camera denied, WS disconnect, LLM timeout — show user-friendly messages | 2 hours |
| **Rate limiting on TTS endpoint** | The `/tts/` endpoint has no auth — add rate limiting to prevent abuse | 30 min |

### 7.3 Nice to Have (Polish)

| Item | Description | Effort |
|------|-------------|--------|
| **Exercise demo videos/images** | 20 exercises need demo content (see `docs/assets-required.md`) | Art/content work |
| **Mascot variations** | Celebration, thinking, encouraging, resting otter poses | Art work |
| **Camera position guides** | Overlay images showing where to place phone | Art work |
| **Share card background** | For social sharing in M6 | Art work |
| **Sound effects** | Rep pop, set complete, workout complete chimes | Audio work |
| **Haptic feedback** | Vibrate on rep detection, set complete | 30 min |
| **Offline mode** | Cache workout plan, allow offline sets, sync later | 4 hours |

### 7.4 Not Started (Future Milestones)

| Milestone | Description |
|-----------|-------------|
| **M5: Dance & Cardio** | MoveMatch integration, cardio templates, HIIT timers |
| **M6: Social & Polish** | Leaderboards, sharing, streaks gamification, PWA improvements |

---

## 8. Troubleshooting

### Backend won't start

```
ModuleNotFoundError: No module named 'openai'
```
**Fix:** `pip install openai anthropic` in the venv.

### "AI plan generation failed, falling back to template"

**Causes:**
- `OPENAI_API_KEY` not set or invalid
- Network issue reaching OpenAI API
- LLM returned invalid JSON (rare with gpt-4o-mini)

**Debug:** Check full traceback in backend logs. The system still works — it uses template plans.

### Camera not working in ActiveSet

**Causes:**
- Not using HTTPS (camera API requires secure context)
- Camera permission denied
- Browser doesn't support getUserMedia

**Fix:** Use `https://localhost:5173` (Vite serves HTTPS in dev). Grant camera permission when prompted.

### Voice commands not recognized

**Causes:**
- Browser doesn't support Web Speech API (Firefox)
- Microphone permission denied
- Ambient noise

**Fix:** Use Chrome. Grant mic permission. Speak clearly. Commands are: "done", "skip rest", "next", "12 reps", "10 at 60 kg", "RPE 7".

### TTS endpoint returns 503

**Cause:** OpenAI API key missing or invalid.

**Fix:** Set `OPENAI_API_KEY` in `.env`. Or set `TTS_ENABLED=false` to disable dynamic TTS (pre-recorded clips still work).

### "No analyzer for this session" on camera tracking

**Cause:** The challenge session was created but the analyzer wasn't registered in `GenericSessionManager`.

**Debug:** Check if `POST /start-tracking` returned successfully. Check backend logs for analyzer creation errors.

### Form score always 0

**Old issue (now fixed):** `form_scoring.py` was reading wrong field names. Now reads `fb` and `state` from the analyzer's actual frame_timeline format.

### Hold timer not counting (plank/squat_hold)

**Old issue (now fixed):** The workout WS endpoint used sequential processing only. Now reuses `/ws/challenge/` which has proper hold-based frame dropping with decoupled producer/consumer.

---

## Quick Reference: API Endpoints

### Workout REST API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/workout/onboarding` | Save onboarding profile + generate plan |
| GET | `/api/v1/workout/profile` | Get profile status (onboarded?) |
| GET | `/api/v1/workout/exercises` | List exercises (filters: muscle, equipment, category) |
| GET | `/api/v1/workout/exercises/{slug}` | Single exercise detail |
| GET | `/api/v1/workout/today` | Today's workout + streak + coach message |
| GET | `/api/v1/workout/week` | 7-day view |
| GET | `/api/v1/workout/progress/stats` | Total workouts, streak, volume |
| POST | `/api/v1/workout/quick-start` | Create ad-hoc session from exercise slugs |
| POST | `/api/v1/workout/sessions/start` | Start workout session |
| POST | `/api/v1/workout/sessions/{id}/action` | Send action to session agent |
| POST | `/api/v1/workout/sessions/{id}/start-tracking` | Create challenge session for camera tracking |
| POST | `/api/v1/workout/sessions/{id}/sets/{n}/camera-result` | Submit camera tracking results |
| GET | `/api/v1/workout/exercises/{slug}/history` | Exercise history for intro screen |
| GET | `/api/v1/workout/tts/{hash}?text=...` | Dynamic TTS audio (no auth) |

### Session Agent Actions

| Action | When | Params |
|--------|------|--------|
| `adjust_time` | Brief phase | `{minutes: N}` |
| `begin_workout` | Brief phase | `{}` |
| `complete_set` | Active set | `{exercise_id, set_number, reps, weight_kg?, rpe?, form_score?}` |
| `skip_exercise` | Exercise intro | `{exercise_id}` |
| `skip_rest` | Rest timer | `{exercise_id, set_number}` |
| `end_workout` | Any phase | `{}` |

### Session Views (returned by agent)

| View | Component | Description |
|------|-----------|-------------|
| `brief` | BriefPhase | Workout overview, time budget |
| `exercise_intro` | ExerciseIntro | Exercise details, form cues, history |
| `active_set` | ActiveSet | Camera or manual set logging |
| `rest_timer` | RestTimer | Countdown, next set preview, voice |
| `cooldown` | CooldownPhase | Stretch suggestions |
| `summary` | SummaryPhase | Session stats, PRs, progression |

### WebSocket Endpoints (reused)

| Path | Description |
|------|-------------|
| `/ws/challenge/{session_id}?token=...` | Camera tracking (reused by workout via start-tracking) |
