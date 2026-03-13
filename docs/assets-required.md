# Assets Required

> Inventory of all demo videos, animations, images, and audio clips needed.
> Last updated: 2026-03-11

---

## Exercise Demo Content (20 exercises)

### Video-Tracked Exercises (8)

Each needs a 10-15s looping demo video (side angle, showing full ROM) or animated SVG/Lottie alternative, plus a camera placement guide image.

| Exercise | Slug | Demo Video | Camera Guide | Status |
|----------|------|-----------|--------------|--------|
| Push-Up | `push-up` | Side angle, full ROM | Phone propped at floor level, 3-4ft away | Needed |
| Bodyweight Squat | `bodyweight-squat` | Side angle, ATG depth | Phone on shelf at hip height | Needed |
| Plank | `plank` | Side angle, showing alignment | Phone propped at floor level | Needed |
| Lunge | `lunges` | Side angle, alternating | Phone on shelf at hip height | Needed |
| Burpee | `burpee` | Side angle, all phases | Phone propped at floor level | Needed |
| Jump Squat | `jump-squat` | Side angle, jump + landing | Phone on shelf at hip height | Needed |
| Mountain Climber | `mountain-climber` | Side angle, alternating | Phone propped at floor level | Needed |
| Squat Hold | `squat-hold` | Side angle, hold position | Phone on shelf at hip height | Needed |

### Weighted/Manual Exercises (12)

Each needs a static demo image or short looping animation showing proper form.

| Exercise | Slug | Image/Animation | Status |
|----------|------|----------------|--------|
| Bench Press | `bench-press` | Side view with barbell path | Needed |
| Overhead Press | `shoulder-press` | Front/side view | Needed |
| Barbell Row | `barbell-row` | Side view | Needed |
| Deadlift | `deadlift` | Side view | Needed |
| Lat Pulldown | `lat-pulldown` | Front view | Needed |
| Bicep Curl | `bicep-curl` | Side view | Needed |
| Tricep Pushdown | `tricep-pushdown` | Side view | Needed |
| Leg Press | `leg-press` | Side view | Needed |
| Lateral Raise | `lateral-raise` | Front view | Needed |
| Calf Raise | `calf-raise` | Side view | Needed |
| Cable Fly | `cable-fly` | Front view | Needed |
| Leg Curl | `leg-curl` | Side view | Needed |

---

## Pre-Recorded Coach Audio (~55 MP3 clips)

Generated via `scripts/generate_coach_audio.py` using OpenAI TTS (voice: "coral").
Stored in `frontend/public/audio/coach/`.

### Form Corrections (15 clips)
| Filename | Text | Status |
|----------|------|--------|
| `go-deeper.mp3` | "Go deeper." | Generate |
| `core-tight.mp3` | "Keep your core tight." | Generate |
| `slow-down.mp3` | "Slow down. Control the movement." | Generate |
| `great-rep.mp3` | "Great rep!" | Generate |
| `keep-going.mp3` | "Keep going. You've got this." | Generate |
| `chest-to-floor.mp3` | "Chest to the floor." | Generate |
| `knees-back.mp3` | "Push your knees back." | Generate |
| `chest-up.mp3` | "Chest up. Stay tall." | Generate |
| `hips-up.mp3` | "Hips up. Don't let them sag." | Generate |
| `flatten-out.mp3` | "Flatten out. Keep your body straight." | Generate |
| `good-form.mp3` | "Good form. Keep it up." | Generate |
| `almost-there.mp3` | "Almost there!" | Generate |
| `nice-depth.mp3` | "Nice depth." | Generate |
| `stay-tight.mp3` | "Stay tight." | Generate |
| `breathe.mp3` | "Don't forget to breathe." | Generate |

### Transitions (10 clips)
| Filename | Text | Status |
|----------|------|--------|
| `start.mp3` | "Let's get started." | Generate |
| `rest-now.mp3` | "Rest now. You earned it." | Generate |
| `next-exercise.mp3` | "Moving on to the next exercise." | Generate |
| `workout-complete.mp3` | "Workout complete! Great job today." | Generate |
| `lets-go.mp3` | "Let's go!" | Generate |
| `ready.mp3` | "Ready? Let's do this." | Generate |
| `begin-set.mp3` | "Begin your set." | Generate |
| `last-set.mp3` | "Last set. Give it everything." | Generate |
| `cooldown-time.mp3` | "Time to cool down." | Generate |
| `well-done.mp3` | "Well done." | Generate |

### Rep Counting (5 clips)
| Filename | Text | Status |
|----------|------|--------|
| `one-more.mp3` | "One more!" | Generate |
| `two-more.mp3` | "Two more!" | Generate |
| `three-more.mp3` | "Three more!" | Generate |
| `five-more.mp3` | "Five more!" | Generate |
| `halfway.mp3` | "Halfway there!" | Generate |

### RPE Feedback (10 clips)
| Filename | Text | Status |
|----------|------|--------|
| `solid-set.mp3` | "Solid set." | Generate |
| `right-on-target.mp3` | "Right on target." | Generate |
| `above-target.mp3` | "Above target. Strong work." | Generate |
| `tough-set-rest-well.mp3` | "Tough set. Rest well before the next one." | Generate |
| `consider-adding-weight.mp3` | "That felt easy. Consider adding weight next time." | Generate |
| `new-pr.mp3` | "New personal record!" | Generate |
| `matching-your-best.mp3` | "Matching your personal best." | Generate |
| `every-rep-counts.mp3` | "Every rep counts." | Generate |
| `strong-finish.mp3` | "Strong finish!" | Generate |
| `personal-best.mp3` | "Personal best! You're getting stronger." | Generate |

### Encouragement (5 clips)
| Filename | Text | Status |
|----------|------|--------|
| `you-got-this.mp3` | "You got this!" | Generate |
| `keep-pushing.mp3` | "Keep pushing." | Generate |
| `great-work.mp3` | "Great work today." | Generate |
| `consistency-wins.mp3` | "Consistency wins. Keep showing up." | Generate |
| `stronger-than-yesterday.mp3` | "Stronger than yesterday." | Generate |

**To generate all clips:**
```bash
OPENAI_API_KEY=sk-... python scripts/generate_coach_audio.py
```

---

## Mascot Variations (Otter)

Currently: single `otter-mascot.png` used everywhere.

| Variation | Usage | Status |
|-----------|-------|--------|
| Default (current) | Coach bubble, general | Exists |
| Celebration (confetti) | Summary screen, PR achieved | Needed |
| Thinking (planning) | Brief screen, plan generation | Needed |
| Encouraging (thumbs up) | Rest timer, mid-workout | Needed |
| Resting (sleep) | Rest day, cooldown | Needed |

---

## UI Assets

| Asset | Usage | Status |
|-------|-------|--------|
| Camera position guide overlays | Exercise intro for trackable exercises | Needed |
| Form scoring arc/badge | ActiveSet camera HUD | Built (CSS) |
| Mic/speaker icons | Voice UI, mute button | Built (SVG inline) |
| Share card background template | M6 social sharing | Needed |
