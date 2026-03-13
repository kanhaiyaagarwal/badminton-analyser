# PRD: AI Fitness Coach

> **Status:** Draft v1.0 — milestones, UX flows, competitive positioning
> **Last updated:** 2026-03-11
> **Owner:** Kanhaiya

---

## 1. Vision

### One-liner
A phone-based AI coach that **sees** your form, **speaks** to you mid-workout, and **plans** your training — no hardware, no human trainer, just your phone.

### The gap we fill
The market is fragmented into four tiers — and nobody does it all:

| Category | Examples | What they do | What they miss |
|----------|----------|-------------|----------------|
| Plan generators | Fitbod, FitnessAI, Freeletics | Smart workout plans, progressive overload | Blind and mute during the actual workout |
| Camera form checkers | Gymscore, SHRED, FormFix | See your form, score it | Mostly post-workout analysis; no planning, no voice |
| Content platforms | Peloton, NTC, Centr, Ladder | Polished trainer-led videos | No AI, no personalization, no form correction |
| Voice coaches | Ray, Flaims, Apple Workout Buddy | Talk to you during workouts | Watch-only or early stage; no camera form check |

**We are the first phone-only app that combines all four: plan + camera + voice + personalization.**

### Who is it for

| Persona | Description | What they need |
|---------|-------------|---------------|
| **The Beginner** | New to working out, intimidated by gym, scared of bad form | Form guidance, simple plans, lots of encouragement |
| **The Self-Trainer** | Works out regularly, no trainer, wants structure | Progressive overload, scheduling, accountability |
| **The Home Warrior** | Exercises at home, bodyweight/minimal equipment | Camera tracking, rep counting, variety |
| **The Cardio Seeker** | Prefers dance, Zumba, yoga — fun over grinding | MoveMatch follow-along, scored sessions, music |

### Competitive positioning

```
                    Plan Gen    Camera    Voice     Personalized    Phone-only
                    (AI)        (Form)    (Coach)   (History)       (No HW)
──────────────────────────────────────────────────────────────────────────────
Fitbod                ✅          ❌         ❌          ✅              ✅
SHRED                 ⚠️          ✅         ⚠️          ⚠️              ✅
Tempo                 ⚠️          ✅         ✅          ✅              ❌ ($2K)
Peloton               ⚠️          ⚠️         ✅          ⚠️              ❌ (HW)
Ray                   ⚠️          ✅         ✅          ⚠️              ✅
──────────────────────────────────────────────────────────────────────────────
Us                    ✅          ✅         ✅          ✅              ✅
```

**Pricing:** $8-15/mo ($96-180/yr). Free tier with basic tracking, premium unlocks AI coach + voice + form correction.

---

## 2. Design Language

Before diving into screens, here's the visual system that governs every screen.

### Palette (Sage & Cream — already implemented)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#F5F2EB` (warm cream) | App background |
| `--bg-card` | `#FDFCF9` (off-white) | Cards, sheets, modals |
| `--color-primary` | `#7C8B6F` (sage green) | Primary buttons, active states, coach accent |
| `--color-secondary` | `#C4613D` (terracotta) | Accents, warnings, streaks |
| `--text-primary` | `#2D2A26` (warm black) | Headings, primary text |
| `--text-secondary` | `#706860` (warm gray) | Body text, descriptions |
| `--text-muted` | `#B0A99F` (light gray) | Labels, hints |
| `--color-success` | `#6B7A5E` (dark sage) | Completed states, good form |
| `--color-destructive` | `#C44B3D` (warm red) | End/stop actions, bad form |
| `--color-warning` | `#D4A843` (gold) | Caution, partial form |

### Typography
- **Font:** DM Sans (clean, friendly, modern)
- **Headings:** 700 weight, `--text-primary`
- **Body:** 400 weight, `--text-secondary`
- **Stats/numbers:** 700 weight, tabular-nums, `--color-primary`
- **Coach speech:** Italic or quoted, `--color-primary` accent

### Component patterns
- **Cards:** `--bg-card`, 1.25rem radius, 1px `--border-color`, subtle shadow on hover
- **Buttons (primary):** Sage gradient, cream text, rounded-md
- **Buttons (secondary):** Cream bg, sage border, sage text
- **Buttons (destructive):** Transparent bg, red border, red text
- **Bottom sheets:** Slide up from bottom, backdrop blur, rounded top corners
- **Toast notifications:** Float at top-center, 1.2s auto-dismiss, semi-transparent bg
- **Coach bubble:** Rounded card with sage left-border, italic text, play button for audio
- **Progress rings/bars:** Sage fill on cream track
- **Active camera overlay:** Dark gradient at top/bottom edges, white icons/text

### Motion
- Page transitions: fade + 4px translateY (0.2s ease)
- Card entrances: staggered v-motion, 50ms delay between items
- Coach bubble: slide-up from bottom (0.3s ease-out)
- Rest timer: circular progress ring animation
- Stat counters: count-up animation on mount

### Iconography
- Feather-style (stroke-based, 2px weight, round caps)
- 24x24 base size, scaled contextually
- Otter mascot for empty states, celebrations, onboarding

---

## 3. App Structure & Navigation

### Information Architecture

```
[Home]          [Workout]         [Explore]        [Profile]
  │                │                  │                │
  ├─ Today's       ├─ Start Today's   ├─ Challenges    ├─ Account
  │  Plan          │  Session         │  (pushup,      ├─ Coach Settings
  ├─ Week View     ├─ Exercise        │   plank,squat) ├─ Goals & Body
  ├─ Coach         │  Library         ├─ Zumba/Dance   ├─ Equipment
  │  Message       ├─ History/        ├─ Yoga Flows    ├─ Wearables
  ├─ Quick Stats   │  Progress        ├─ Badminton     └─ Notifications
  └─ Streak        └─ Calendar          (existing)
```

### Bottom Navigation

```
┌─────────────────────────────────────┐
│  🏠 Home   💪 Workout   🧭 Explore   👤 Profile │
└─────────────────────────────────────┘
```

- Active tab: sage fill + bold label
- Inactive: muted icon + text
- Hidden during: active workout session (fullscreen), onboarding
- Safe area padding for iOS notch

---

## 4. Milestones

### Overview

| Milestone | Name | Core Deliverable | Depends On | Status |
|-----------|------|-----------------|------------|--------|
| **M0** | Foundation | Data models, exercise DB, onboarding, basic home screen | — | Done |
| **M1** | The Workout | Full workout session flow with manual logging | M0 | Done |
| **M2** | The Eye | Camera form tracking + scoring for bodyweight exercises | M1 | Done |
| **M3** | The Voice | TTS coach speech + STT voice input | M1 | Done |
| **M4** | The Brain | AI plan generation, progressive overload, adaptation | M1 | Done |
| **M5** | Dance & Cardio | MoveMatch-powered Zumba/yoga follow-along | M1 | Planned |
| **M6** | Social & Polish | Personas, streaks, sharing, audio ducking | M3, M4 | Planned |

### Dependency graph

```
M0 (Foundation)
 └─► M1 (The Workout)
      ├─► M2 (The Eye)       ─── can be parallel ───┐
      ├─► M3 (The Voice)     ─── can be parallel ───┤
      ├─► M4 (The Brain)     ─── can be parallel ───┤
      └─► M5 (Dance/Cardio)  ─── can be parallel ───┘
                                                      │
                                          M6 (Social & Polish)
```

M2, M3, M4, M5 can all be developed in parallel after M1.

---

### M0: Foundation

**What:** Data models, exercise database, onboarding flow, skeleton home screen. The bones everything else plugs into.

#### Backend

**New tables:**

```sql
exercises
  id, name, slug, muscle_groups (JSON), equipment (JSON),
  type (compound/isolation/bodyweight/cardio),
  tracking_mode (video/voice/movematch),
  demo_video_url, form_cues (JSON), common_mistakes (JSON),
  difficulty (1-5), created_at

user_profiles
  user_id (FK), age, height_cm, weight_kg, fitness_level (beginner/intermediate/advanced),
  injuries (JSON), equipment_available (JSON), workout_days (JSON),
  session_duration_min, goal, goal_target, created_at, updated_at

workout_plans
  id, user_id (FK), week_start, status (active/completed/skipped),
  plan_data (JSON — array of daily workouts), created_at

workout_sessions
  id, user_id (FK), plan_id (FK), date, status (planned/active/completed/skipped),
  workout_type (push/pull/legs/full/cardio/yoga), duration_sec,
  total_volume, notes, summary_text, created_at

exercise_sets
  id, session_id (FK), exercise_id (FK), set_number,
  reps, weight_kg, duration_sec (for holds/planks),
  rpe (1-10), form_score (0-100), tracking_mode (video/voice/manual),
  created_at

user_goals
  id, user_id (FK), goal_type (strength/endurance/weight_loss/consistency),
  target_value, current_value, target_date, milestones (JSON),
  created_at, updated_at

coach_preferences
  user_id (FK), persona (default), voice_id,
  chattiness (minimal/moderate/full), mute_during_sets (bool),
  auto_listen_rest (bool), created_at, updated_at
```

**New API endpoints:**

```
POST   /api/onboarding/profile     — save profile + goals + schedule
GET    /api/exercises               — list all exercises, filterable
GET    /api/exercises/:slug         — single exercise detail
GET    /api/workout/today           — today's planned workout (or empty)
GET    /api/workout/week            — this week's plan overview
GET    /api/progress/stats          — streaks, PRs, volume trends
```

**Exercise seed data:** 20 exercises (see Appendix A) with form cues, muscle groups, equipment tags, difficulty ratings. No demo videos yet (placeholder images).

#### UX Flows

##### Onboarding (5 screens — shown once, after signup)

```
Screen 1: WELCOME
┌─────────────────────────────────┐
│                                 │
│         🦦 (otter mascot)       │
│                                 │
│     Meet your AI coach          │
│                                 │
│  I'll build your workouts,     │
│  watch your form, and keep     │
│  you on track.                  │
│                                 │
│    [Set Up My Plan →]           │
│                                 │
│    [Just Start Working Out]     │
│                                 │
└─────────────────────────────────┘
• Mascot uses v-motion entrance (scale + fade, 0.4s)
• "Set Up My Plan" = sage gradient primary button → goes to onboarding Screen 2
• "Just Start Working Out" = secondary text link → skips to Quick Start (see below)
• Warm cream background with subtle decorative circles
```

```
Screen 2: ABOUT YOU
┌─────────────────────────────────┐
│  ← Back              Step 1/4   │
├─────────────────────────────────┤
│                                 │
│  Tell me about yourself         │
│                                 │
│  Fitness Level                  │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │Begin-│ │Inter-│ │Advan-│   │
│  │ner   │ │mediat│ │ced   │   │
│  └──────┘ └──────┘ └──────┘   │
│                                 │
│  Age       [  28  ]             │
│  Height    [  175 ] cm          │
│  Weight    [  72  ] kg          │
│                    (optional)   │
│                                 │
│  Any injuries or limitations?   │
│  ┌──────────────────────────┐  │
│  │ e.g., bad knee, lower    │  │
│  │ back pain (optional)     │  │
│  └──────────────────────────┘  │
│                                 │
│        [Continue →]             │
└─────────────────────────────────┘
• Fitness level: pill-shaped toggle buttons, sage fill on selected
• Number inputs: large touch targets, +/- steppers on mobile
• Injuries: free text, optional — coach uses this to filter exercises
• Weight marked "(optional)" — sensitive, never forced
```

```
Screen 3: YOUR GOALS
┌─────────────────────────────────┐
│  ← Back              Step 2/4   │
├─────────────────────────────────┤
│                                 │
│  What's your goal?              │
│                                 │
│  ┌─────────────────────────┐   │
│  │ 💪 Build Muscle          │   │
│  │ Get stronger & bigger    │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │ 🔥 Lose Weight           │   │
│  │ Burn fat, get leaner     │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │ 🏃 Stay Active           │   │
│  │ Consistent movement      │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │ 🎯 Specific Target       │   │
│  │ e.g., 50 pushups, run 5K│   │
│  └─────────────────────────┘   │
│                                 │
│        [Continue →]             │
└─────────────────────────────────┘
• Goal cards: single-select, sage border + light sage fill when selected
• "Specific Target" expands to show text input for custom goal
• Each card: emoji icon left, title bold, subtitle muted below
```

```
Screen 4: YOUR SCHEDULE
┌─────────────────────────────────┐
│  ← Back              Step 3/4   │
├─────────────────────────────────┤
│                                 │
│  When can you work out?         │
│                                 │
│  ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐│
│  │Mon││Tue││Wed││Thu││Fri││Sat││Sun││
│  │ ✓ ││   ││ ✓ ││   ││ ✓ ││ ✓ ││   ││
│  └───┘└───┘└───┘└───┘└───┘└───┘└───┘│
│                                 │
│  Session length                 │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │30 min│ │45 min│ │60 min│   │
│  └──────┘ └──────┘ └──────┘   │
│                                 │
│  Where do you train?            │
│  ┌──────────┐ ┌──────────┐    │
│  │ 🏠 Home   │ │ 🏋️ Gym    │    │
│  └──────────┘ └──────────┘    │
│                                 │
│  Equipment (if home)            │
│  [✓] Dumbbells  [ ] Barbell    │
│  [ ] Pull-up bar [ ] Bands     │
│  [ ] Bench      [✓] Mat        │
│                                 │
│        [Continue →]             │
└─────────────────────────────────┘
• Day picker: round circles, sage fill = selected, tap to toggle
• Session length: pill toggle, single-select
• Train location: two big cards, multi-select OK (home + gym)
• Equipment: checkbox grid, only shown if "Home" selected
• "Gym" assumes full equipment available
```

```
Screen 5: YOUR PLAN (generated)
┌─────────────────────────────────┐
│  ← Back              Step 4/4   │
├─────────────────────────────────┤
│                                 │
│  Here's your first week         │
│                                 │
│  🦦 "Based on your goals and    │
│  schedule, I've set up a Push/  │
│  Pull/Legs split. Let's start   │
│  strong!"                       │
│                                 │
│  ┌─────────────────────────┐   │
│  │ MON — Push Day           │   │
│  │ Pushup · Bench · OHP ·  │   │
│  │ Tricep Pushdown          │   │
│  ├─────────────────────────┤   │
│  │ WED — Pull Day           │   │
│  │ Row · Pulldown · Curl ·  │   │
│  │ Deadlift                 │   │
│  ├─────────────────────────┤   │
│  │ FRI — Leg Day            │   │
│  │ Squat · Lunge · Leg Pr · │   │
│  │ Calf Raise               │   │
│  ├─────────────────────────┤   │
│  │ SAT — Cardio / Active    │   │
│  │ Zumba or Yoga (optional) │   │
│  └─────────────────────────┘   │
│                                 │
│  [Looks Good — Let's Go! →]    │
│  [Adjust Plan]                  │
│                                 │
└─────────────────────────────────┘
• Plan generated by LLM (M4) or template-based (M0 uses templates)
• Coach bubble at top with mascot + personalized message
• Day cards: collapsible, show exercise names as pills
• "Adjust Plan" → bottom sheet to swap exercises or change days
• "Let's Go" → navigates to Home screen, plan is now active
```

##### Three Workout Modes

The app supports three ways to start a workout. Users aren't locked into one — they can use all three on different days.

**Mode A: Coached Plan** (full onboarding → weekly plan → guided sessions)
The structured path. User completes onboarding, coach generates a weekly plan, each session is pre-built with exercises/sets/reps/rest. Coach briefs you before, guides you during, summarizes after. This is the default for users who tap "Set Up My Plan" on the welcome screen.

**Mode B: Quick Start** (skip everything, just work out)
For the user who opens the app and thinks "I want to do pushups right now." No onboarding, no plan, no schedule. They pick exercises (or just one), start, and the app tracks everything — reps, form (if camera), time. Coach still watches form and counts reps, but doesn't prescribe what to do. Everything gets logged and feeds into history/stats. If the user later decides to set up a plan, all this data is already there.

**Mode C: Flex Session** (have a plan, but adjust on the fly)
The middle ground. User has a plan but wants to modify today's session — swap exercises, add something, remove something, change the order. The "Adjust Plan" and time picker on the Pre-Workout Brief screen enable this. The coach adapts: "I see you swapped OHP for dumbbell press — good call, similar muscles. I'll track it."

```
┌───────────────────────────────────────────────────┐
│                                                     │
│  Welcome Screen                                     │
│  ┌────────────────┐  ┌──────────────────────────┐ │
│  │ Set Up My Plan │  │ Just Start Working Out   │ │
│  │ (→ onboarding) │  │ (→ Quick Start)          │ │
│  └───────┬────────┘  └────────────┬─────────────┘ │
│          │                         │                │
│          ▼                         ▼                │
│   Onboarding (4 screens)    Quick Start screen      │
│          │                         │                │
│          ▼                         │                │
│   Home Screen ◄────────────────────┘                │
│   (plan active)              (no plan, still works) │
│          │                         │                │
│          ▼                         ▼                │
│   ┌──────────┐              ┌──────────┐           │
│   │ Mode A:  │              │ Mode B:  │           │
│   │ Start    │              │ Quick    │           │
│   │ Today's  │              │ Start    │           │
│   │ Workout  │              │ (pick    │           │
│   │ (guided) │              │  exercise│           │
│   │          │              │  & go)   │           │
│   │ Mode C:  │              │          │           │
│   │ Adjust   │              │          │           │
│   │ & Start  │              │          │           │
│   └──────────┘              └──────────┘           │
│          │                         │                │
│          └────────┬────────────────┘                │
│                   ▼                                  │
│          Same session flow                           │
│          (exercise → set → rest → repeat)            │
│          Same logging, same form tracking             │
│          Same post-workout summary                    │
│                                                     │
└───────────────────────────────────────────────────┘
```

All three modes feed into the **same workout session engine** (M1). The difference is how the exercise list gets built:
- Mode A: from the weekly plan
- Mode B: user picks manually (or tells the coach)
- Mode C: starts from plan, user modifies

##### Quick Start Screen (Mode B)

```
┌─────────────────────────────────┐
│  ← Back                         │
├─────────────────────────────────┤
│                                 │
│  What do you want to do?        │
│                                 │
│  ┌─────────────────────────┐   │
│  │ 💬 Tell your coach...    │   │
│  │ "pushups and squats"     │   │
│  │ "upper body for 20 min"  │   │
│  │ "just plank"             │   │
│  └─────────────────────────┘   │
│                                 │
│  OR PICK EXERCISES              │
│                                 │
│  POPULAR                        │
│  ┌───────┐┌───────┐┌───────┐  │
│  │Pushup ││ Squat ││ Plank │  │
│  │  📷   ││  📷   ││  📷   │  │
│  └───────┘└───────┘└───────┘  │
│  ┌───────┐┌───────┐┌───────┐  │
│  │Bench  ││Deadlft││ OHP   │  │
│  │  🎤   ││  🎤   ││  🎤   │  │
│  └───────┘└───────┘└───────┘  │
│                                 │
│  [Browse All Exercises →]       │
│                                 │
│  QUICK COMBOS                   │
│  ┌─────────────────────────┐   │
│  │ 🔥 HIIT Blast (15 min)  │   │
│  │ Burpee · Squat · Plank  │   │
│  ├─────────────────────────┤   │
│  │ 💪 Upper Body (20 min)  │   │
│  │ Pushup · Bench · OHP    │   │
│  ├─────────────────────────┤   │
│  │ 🦵 Leg Day (20 min)     │   │
│  │ Squat · Lunge · Leg Pr  │   │
│  └─────────────────────────┘   │
│                                 │
├─ SELECTED (2) ──────────────────┤
│  Pushup (3×15) · Squat (3×12)  │
│  [Adjust sets]    ~12 min       │
│                                 │
│  [Start Workout →]              │
│                                 │
└─────────────────────────────────┘
```

**UX details:**
- **Chat input at top:** user can type (or in M3, speak) a natural language request. "I want to do pushups now" → coach adds pushup with default sets/reps. "Upper body, 20 minutes" → coach picks 3-4 upper body exercises within time. Uses LLM in M4, keyword matching in M1.
- **Exercise grid:** tap to add/remove. Sage border = selected. Shows tracking mode badge.
- **Quick combos:** pre-built mini-workouts for common needs. Tap to select all exercises at once.
- **Selected tray (bottom):** sticky, shows what's queued. Tap "Adjust sets" to change sets/reps per exercise. Live time estimate.
- **Default sets/reps:** when user picks an exercise with no plan context, use smart defaults based on exercise type and user's history (if any). First time: 3×10 for compounds, 3×15 for bodyweight.
- **"Start Workout"** → goes straight to Exercise Intro → Active Set (same session flow as Mode A)
- **Everything is logged** — even without a plan, all sets/reps/form data go into `workout_sessions` and `exercise_sets`. Feeds into history, PRs, streaks.
- Users who started with Quick Start get a gentle nudge after 3 sessions: "You've been consistent! Want me to build you a plan based on what you've been doing?"

##### Home Screen — supports all three modes

```
┌─────────────────────────────────┐
│  PushUp Pro              🏅 12  │
├─────────────────────────────────┤
│                                 │
│  Good morning, Kanhaiya         │
│  Day 12 · 4-day streak 🔥      │
│                                 │
├─ TODAY'S WORKOUT ───────────────┤  ← Mode A (if plan exists)
│  ┌─────────────────────────┐   │
│  │  Push Day         ~45m  │   │
│  │                         │   │
│  │  Pushup · Bench Press · │   │
│  │  OHP · Tricep Pushdown  │   │
│  │  · Lateral Raise        │   │
│  │                         │   │
│  │  ┌───────────────────┐  │   │
│  │  │ Start Workout →   │  │   │
│  │  └───────────────────┘  │   │
│  └─────────────────────────┘   │
│                                 │
├─ QUICK START ───────────────────┤  ← Mode B (always visible)
│  ┌─────────────────────────┐   │
│  │ 💬 "I want to do..."    │   │
│  │                         │   │
│  │  [Pushup] [Squat] [+]  │   │
│  └─────────────────────────┘   │
│                                 │
├─ THIS WEEK ─────────────────────┤
│  M     T     W     T     F     │
│  ✅    ✅    ✅    ●     ○     │
│                   3/4 complete  │
│                                 │
├─ COACH ─────────────────────────┤
│  ┌─────────────────────────┐   │
│  │ 🦦 "You've been crushing │   │
│  │ it this week. Today      │   │
│  │ let's try 42.5kg on      │   │
│  │ bench — you're ready."   │   │
│  │                   ▶ Play │   │
│  └─────────────────────────┘   │
│                                 │
├─ RECENT WINS ───────────────────┤
│  🏆 New PR: Bench 42.5kg       │
│  📈 Volume up 8% this week     │
│  🔥 4-day streak (best: 12)    │
│                                 │
└─────────────────────────────────┘
│  🏠     💪     🧭     👤       │
└─────────────────────────────────┘
```

**Home screen UX — how the three modes surface:**
- **Mode A (Coached):** "TODAY'S WORKOUT" card — prominent, top of screen. Only shows if user has an active plan.
- **Mode B (Quick Start):** Always visible below the plan card (or at the top if no plan). Chat input + popular exercise chips. Tap any chip → adds to quick session. Tap chat → goes to full Quick Start screen. Even users with a plan can Quick Start a different workout.
- **Mode C (Flex):** Tap "Start Workout" on the plan card → Pre-Workout Brief → adjust time, swap exercises, then start. This is the existing flow with the time picker and "Adjust Plan" option.
- **No plan yet?** "TODAY'S WORKOUT" card is replaced with: "Set up your plan — let the coach build your week" CTA. Quick Start is still available below.
- **Plan exists but rest day?** Card says "Rest Day" with stretch suggestions. Quick Start still available: "Feel like doing something anyway?"

```
┌─────────────────────────────────┐
│  PushUp Pro              🏅 12  │
├─────────────────────────────────┤
│                                 │
│  Good morning, Kanhaiya         │
│  Day 12 · 4-day streak 🔥      │
│                                 │
├─ TODAY'S WORKOUT ───────────────┤
│  ┌─────────────────────────┐   │
│  │  Push Day         ~45m  │   │
│  │                         │   │
│  │  Pushup · Bench Press · │   │
│  │  OHP · Tricep Pushdown  │   │
│  │  · Lateral Raise        │   │
│  │                         │   │
│  │  ┌───────────────────┐  │   │
│  │  │ Start Workout →   │  │   │
│  │  └───────────────────┘  │   │
│  └─────────────────────────┘   │
│                                 │
├─ THIS WEEK ─────────────────────┤
│  M     T     W     T     F     │
│  ✅    ✅    ✅    ●     ○     │
│ Push  Pull  Legs  Push  Rest   │
│                  (today)        │
│                   3/4 complete  │
│                                 │
├─ COACH ─────────────────────────┤
│  ┌─────────────────────────┐   │
│  │ 🦦 "You've been crushing │   │
│  │ it this week. Today      │   │
│  │ let's try 42.5kg on      │   │
│  │ bench — you're ready."   │   │
│  │                   ▶ Play │   │
│  └─────────────────────────┘   │
│                                 │
├─ RECENT WINS ───────────────────┤
│  🏆 New PR: Bench 42.5kg       │
│  📈 Volume up 8% this week     │
│  🔥 4-day streak (best: 12)    │
│                                 │
└─────────────────────────────────┘
│  🏠     💪     🧭     👤       │
└─────────────────────────────────┘
```

**Home screen UX details:**
- Greeting changes by time: "Good morning" / "Good afternoon" / "Ready for the evening grind?"
- Streak badge (🏅 12) at top-right — tap to see streak calendar
- Today's workout card: sage gradient border-left, cream bg, exercise names as gray pills
- Week dots: ✅ completed (sage), ● today (pulsing sage outline), ○ future (muted)
- Coach bubble: sage left-border, mascot mini-avatar, italic text, ▶ Play button generates TTS audio
- Recent wins: compact list, emoji + text, ordered by recency

##### Exercise Library (browse/search)

```
┌─────────────────────────────────┐
│  Exercise Library        🔍     │
├─────────────────────────────────┤
│  ┌─────────────────────────┐   │
│  │ Search exercises...      │   │
│  └─────────────────────────┘   │
│                                 │
│  FILTER BY MUSCLE GROUP         │
│  [All] [Chest] [Back] [Legs]   │
│  [Shoulders] [Arms] [Core]     │
│                                 │
├─ BODYWEIGHT (Video Tracked) ────┤
│  ┌────────────────────────────┐│
│  │ 📷 Pushup          Chest  ││
│  │     PR: 32 · Last: 28     ││
│  ├────────────────────────────┤│
│  │ 📷 Squat           Legs   ││
│  │     PR: 25 · Last: 20     ││
│  ├────────────────────────────┤│
│  │ 📷 Plank           Core   ││
│  │     PR: 1:45 · Last: 1:20 ││
│  └────────────────────────────┘│
│                                 │
├─ GYM (Voice / Manual) ─────────┤
│  ┌────────────────────────────┐│
│  │ 🎤 Bench Press      Chest  ││
│  │     PR: 60kg · Last: 55kg ││
│  ├────────────────────────────┤│
│  │ 🎤 Deadlift         Back  ││
│  │     PR: 80kg · Last: 75kg ││
│  └────────────────────────────┘│
│                                 │
├─ FOLLOW-ALONG (MoveMatch) ─────┤
│  ┌────────────────────────────┐│
│  │ 🎵 Zumba Cardio    Cardio ││
│  │     3 routines available   ││
│  ├────────────────────────────┤│
│  │ 🧘 Yoga Flows      Flex   ││
│  │     2 flows available      ││
│  └────────────────────────────┘│
└─────────────────────────────────┘
```

**UX details:**
- 📷 badge = video tracked, 🎤 = voice/manual, 🎵/🧘 = MoveMatch
- Each row shows: name, primary muscle group, PR, last session value
- Tap → exercise detail screen (demo, form cues, history chart)
- Filter pills: horizontal scroll, sage fill on active, multi-select
- Search: instant filter on name or muscle group
- Grouped by tracking mode (helps user understand what's different about each)

##### Exercise Detail Screen

```
┌─────────────────────────────────┐
│  ← Back                         │
├─────────────────────────────────┤
│  ┌─────────────────────────┐   │
│  │                         │   │
│  │   [Demo Video/Image]    │   │
│  │   16:9 aspect ratio     │   │
│  │                         │   │
│  └─────────────────────────┘   │
│                                 │
│  PUSHUP                  📷    │
│  Chest · Triceps · Core        │
│  Bodyweight · No equipment     │
│                                 │
├─ FORM CUES ─────────────────────┤
│  ✅ Hands shoulder-width apart  │
│  ✅ Elbows at 45° to body      │
│  ✅ Lower until chest near floor│
│  ✅ Keep core tight, no sag     │
│  ⚠️ Common: hips dropping      │
│  ⚠️ Common: not going deep     │
│                                 │
├─ YOUR HISTORY ──────────────────┤
│  ┌─────────────────────────┐   │
│  │  📈 (line chart)        │   │
│  │  Max reps over time     │   │
│  │  32 ─── PR              │   │
│  │  28 ── last session     │   │
│  │  ────────────────────   │   │
│  │  Feb    Mar              │   │
│  └─────────────────────────┘   │
│                                 │
│  Personal Best: 32 reps         │
│  Last Session: 28 reps          │
│  Total Volume: 486 reps (all)   │
│                                 │
│  [Add to Today's Workout]       │
└─────────────────────────────────┘
```

**UX details:**
- Demo area: video (if available) or static image. Loops silently.
- 📷 badge indicates tracking mode
- Form cues: ✅ for do-this, ⚠️ for common mistakes
- History chart: simple line chart, sage line on cream bg, PR highlighted
- "Add to Today's Workout" → adds as additional exercise to current plan

---

### M1: The Workout

**What:** The core workout session loop — from tapping "Start Workout" to seeing the post-workout summary. Manual input only (no camera, no voice yet). This is the foundation that M2 (eye) and M3 (voice) plug into.

**Depends on:** M0 (exercises, data models, home screen)

#### The Session Flow

All three modes (Coached, Quick Start, Flex) enter the same session engine:

```
Mode A (Coached):     [Start Workout] → Pre-Workout Brief → ...
Mode B (Quick Start): [Pick exercises] → Exercise Intro directly (skip brief)
Mode C (Flex):        [Start Workout] → Pre-Workout Brief (adjust) → ...

[Start Workout / Quick Start]
     │
     ▼
┌─ Pre-Workout Brief ──┐  (skipped in Quick Start if only 1-2 exercises)
│  Today's exercises    │
│  Time picker          │
│  Coach text message   │
└───────┬───────────────┘
        │
        ▼
┌─ Exercise Intro ──────┐◄──────────────────┐
│  Demo + form cues     │                    │
│  Set/rep target       │                    │
└───────┬───────────────┘                    │
        │                                     │
        ▼                                     │
┌─ Active Set ──────────┐                    │
│  Timer running        │                    │
│  Manual tap to log    │                    │
└───────┬───────────────┘                    │
        │                                     │
        ▼                                     │
┌─ Set Complete ────────┐                    │
│  Log reps/weight      │                    │
│  Coach feedback text  │                    │
└───────┬───────────────┘                    │
        │                                     │
        ▼                                     │
┌─ Rest Timer ──────────┐    More sets?      │
│  Countdown + tip      │────── Yes ──►──────┘
│  Next set preview     │       │ (back to Active Set)
└───────┬───────────────┘       │
        │ (last set)            │
        ▼                       │
   More exercises? ─── Yes ──►──┘ (back to Exercise Intro)
        │
        No
        ▼
┌─ Cool-down ───────────┐
│  Guided stretches     │
│  (optional, skippable)│
└───────┬───────────────┘
        │
        ▼
┌─ Post-Workout Summary ┐
│  Stats, PRs, coach msg│
│  [Share] [Done]        │
└───────────────────────┘
```

#### Screen: Pre-Workout Brief

```
┌─────────────────────────────────┐
│  ✕ (close)                      │
├─────────────────────────────────┤
│                                 │
│  🦦 PUSH DAY                    │
│     Thursday, March 11          │
│                                 │
│  ┌─────────────────────────┐   │
│  │ "Good to see you back.   │   │
│  │  Today we're hitting     │   │
│  │  chest and triceps. Your │   │
│  │  bench has been climbing │   │
│  │  — let's keep that going."│  │
│  └─────────────────────────┘   │
│                                 │
│  HOW MUCH TIME DO YOU HAVE?     │
│  ┌──────┐ ┌──────┐ ┌──────┐   │
│  │20 min│ │30 min│ │45 min│   │
│  └──────┘ └──────┘ └──────┘   │
│  ┌──────┐ ┌────────────────┐   │
│  │60 min│ │Full Plan (~45m)│   │
│  └──────┘ └────────────────┘   │
│                                 │
│  TODAY'S EXERCISES              │
│                                 │
│  1. Pushup         3×15   📷  │
│  2. Bench Press    4×10   🎤  │
│  3. OHP            3×10   🎤  │
│  4. Tricep Pushdn  3×12   🎤  │
│  5. Lateral Raise  3×12   🎤  │
│                                 │
│  ~45 min · 5 exercises · 16 sets│
│                                 │
│  [Start Warm-up →]              │
│  [Skip to First Exercise]       │
│                                 │
└─────────────────────────────────┘

When user selects a shorter time (e.g., 30 min):
┌─────────────────────────────────┐
│                                 │
│  🦦 "30 minutes — got it. I've  │
│  trimmed it to the essentials.  │
│  We'll hit compounds first."    │
│                                 │
│  TODAY'S EXERCISES (adjusted)   │
│                                 │
│  1. Pushup         3×15   📷  │
│  2. Bench Press    3×10   🎤  │
│  3. OHP            3×10   🎤  │
│  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌  │
│  Skipped: Tricep Pushdn,       │
│           Lateral Raise         │
│  [+ Add back an exercise]       │
│                                 │
│  ~28 min · 3 exercises · 9 sets │
│                                 │
│  [Start Warm-up →]              │
│  [Skip to First Exercise]       │
│                                 │
└─────────────────────────────────┘
```

**UX details:**
- **Time picker:** pill-shaped buttons at top, "Full Plan" is pre-selected (default). User can override before every session.
- **Adaptive trimming logic (when time < planned):**
  - Keep compound exercises, drop isolation first (lateral raise, tricep pushdown go first)
  - Reduce sets on remaining exercises (4×10 → 3×10) if still over time budget
  - Shorten rest periods slightly (90s → 75s) as last resort
  - Never drop below 2 exercises — suggest "Quick HIIT" alternative if under 15 min
- Coach explains what changed: "I've trimmed it to the essentials" — not just silently removing exercises
- Skipped exercises shown as muted list below the divider — user can tap "+ Add back" to override
- Time estimate updates live as user adjusts
- In M3 (voice): user can say "I only have 30 minutes" and coach adapts verbally
- In M4 (brain): LLM handles the trimming intelligently. In M1: rule-based (drop from bottom of list, reduce sets)
- Coach message: personalized based on history (templated in M1, LLM in M4)
- Exercise list: numbered, shows sets×reps and tracking mode badge
- Tap any exercise to see detail / swap
- Warm-up: shortened to 3 min if time-constrained (normally 5 min)
- "Skip to First Exercise" for users who warm up on their own
- ✕ close returns to home without starting session

#### Screen: Exercise Intro (shown before first set of each exercise)

```
┌─────────────────────────────────┐
│  Push Day           1/5         │
│  ━━━━░░░░░░░░░░░░░░░░          │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐   │
│  │                         │   │
│  │   [Demo Image/Video]    │   │
│  │   Looping, muted        │   │
│  │                         │   │
│  └─────────────────────────┘   │
│                                 │
│  PUSHUP                         │
│  3 sets · 15 reps               │
│                                 │
│  KEY CUES                       │
│  · Hands shoulder-width         │
│  · Lower until elbows <90°     │
│  · Keep core tight              │
│                                 │
│  📊 Last time: 3×12 (avg)      │
│  🏆 PR: 32 reps                │
│                                 │
│  [Begin Set 1 →]                │
│                                 │
│  [⏭ Skip Exercise]              │
└─────────────────────────────────┘
```

**UX details:**
- Progress bar at top: sage fill, shows exercise N/total
- Demo: auto-playing loop, no sound. Placeholder image if no video yet.
- Key cues: 3 max (most important), no information overload
- Last time / PR: gives context for what to aim for
- "Skip Exercise" is muted text, not prominent — discouraged but available
- First time doing this exercise: show all form cues. Returning user: show abbreviated.

#### Screen: Active Set (Manual Mode — M1 baseline)

```
┌─────────────────────────────────┐
│  PUSHUP           Set 2 of 3   │
├─────────────────────────────────┤
│                                 │
│                                 │
│                                 │
│            15                   │
│          TARGET                 │
│                                 │
│         0:34                    │
│      (set timer)                │
│                                 │
│                                 │
│                                 │
│                                 │
├─────────────────────────────────┤
│                                 │
│     [  ✓ Complete Set  ]        │
│                                 │
│  [⏸ Pause]          [⏭ Skip]  │
│                                 │
└─────────────────────────────────┘
```

**UX details:**
- Minimal UI during set — large target number, running timer
- "Complete Set" is the dominant action (large sage button)
- Timer runs up (how long the set took), shown in muted text
- In M2 (camera): this screen gets a camera feed overlay with rep counter
- In M3 (voice): "Complete Set" can be triggered by saying "done"
- Pause → freezes timer, shows resume/end options
- Skip → confirms, moves to next set or next exercise
- Background: cream, no distractions. User's focus is on exercising.

#### Screen: Set Complete (log results)

```
┌─────────────────────────────────┐
│  PUSHUP           Set 2 of 3   │
├─────────────────────────────────┤
│                                 │
│  How many reps?                 │
│                                 │
│    [ - ]     15     [ + ]       │
│                                 │
│  Weight (kg)                    │
│    [ - ]     BW     [ + ]       │
│             (bodyweight)        │
│                                 │
│  How did it feel?               │
│  ┌────┐┌────┐┌────┐┌────┐┌────┐│
│  │Easy││    ││ OK ││    ││Hard││
│  │ 😊 ││ 🙂 ││ 😐 ││ 😤 ││ 🥵 ││
│  └────┘└────┘└────┘└────┘└────┘│
│           (RPE 1-5)             │
│                                 │
│  ┌─────────────────────────┐   │
│  │ "Solid set. 2 more than │   │
│  │  last time. One more    │   │
│  │  set to go."            │   │
│  └─────────────────────────┘   │
│                                 │
│      [Save & Rest →]            │
│                                 │
└─────────────────────────────────┘
```

**UX details:**
- Reps: pre-filled with target, user adjusts with +/- or type
- Weight: pre-filled from last session or plan. "BW" for bodyweight.
- RPE (Rate of Perceived Exertion): emoji faces, 5-point scale. Quick tap, not a slider.
- Coach feedback: brief text comparing to previous performance
- "Save & Rest" → starts rest timer
- If last set of exercise: "Save & Next Exercise →"
- If last set of last exercise: "Save & Finish →"

#### Screen: Rest Timer

```
┌─────────────────────────────────┐
│  PUSHUP           Set 2 of 3   │
├─────────────────────────────────┤
│                                 │
│                                 │
│          ┌─────────┐            │
│          │         │            │
│          │  1:23   │            │
│          │         │            │
│          └─────────┘            │
│      (circular progress ring)   │
│                                 │
│  NEXT UP                        │
│  Set 3 of 3 · 15 reps          │
│                                 │
│  ┌─────────────────────────┐   │
│  │ "Last set you nailed 15.│   │
│  │  Focus on slow negatives│   │
│  │  this time — control    │   │
│  │  the descent."          │   │
│  └─────────────────────────┘   │
│                                 │
│      [Skip Rest →]              │
│                                 │
└─────────────────────────────────┘
```

**UX details:**
- Circular progress ring: sage stroke, animating counterclockwise
- Time: large, centered, counts down
- Rest duration: auto-set based on exercise type (60s isolation, 90s compound, 120s heavy compound). User can customize.
- Coach tip: contextual, templated. References last set's performance, gives tip for next set.
- "Skip Rest" → immediately starts next set
- When timer hits 0: gentle vibration + sound, transitions to next set
- In M3 (voice): coach speaks the tip, always-listening activates

#### Screen: Post-Workout Summary

```
┌─────────────────────────────────┐
│                                 │
│        WORKOUT COMPLETE         │
│            🦦 🎉                │
│                                 │
│  Push Day · 42 min              │
│                                 │
├─ STATS ─────────────────────────┤
│                                 │
│   5           16        3,240   │
│   exercises   sets      volume  │
│                         (kg)    │
│                                 │
├─ HIGHLIGHTS ────────────────────┤
│                                 │
│  🏆 New PR: Pushup 18 reps     │
│  📈 Bench: 42.5kg (up from 40) │
│  ✅ All sets completed          │
│                                 │
├─ COACH SAYS ────────────────────┤
│  ┌─────────────────────────┐   │
│  │ "Strong session. Your   │   │
│  │  pushup depth was       │   │
│  │  consistent today and   │   │
│  │  bench is climbing.     │   │
│  │  Tomorrow is rest —     │   │
│  │  Friday is Pull day."   │   │
│  │                  ▶ Play │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────┐  ┌─────────┐     │
│  │ 📤 Share │  │ ✓ Done  │     │
│  └─────────┘  └─────────┘     │
│                                 │
└─────────────────────────────────┘
```

**UX details:**
- Celebration: mascot + confetti animation (brief, 1.5s)
- Stats row: 3 big numbers, centered
- Highlights: auto-detected PRs, improvements, achievements. Sage accent.
- Coach summary: LLM-generated in M4, templated in M1. Audio playable in M3.
- Share: generates an Instagram-story-style card (workout name, date, stats, branding)
- Done: returns to home screen, plan updated with completed session
- If form tracking was on (M2): includes form score average

---

### M2: The Eye

**What:** Camera-based form tracking + real-time form scoring for the 8 bodyweight exercises. Plugs into the Active Set screen from M1.

**Depends on:** M1 (workout session flow exists)

#### What changes in the Active Set screen

The "manual mode" Active Set from M1 gets a camera overlay when the exercise supports video tracking:

```
┌─────────────────────────────────┐
│  PUSHUP           Set 2 of 3   │
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │                             │ │
│ │      [Camera Feed]          │ │
│ │                             │ │
│ │  ┌──────────────────┐      │ │
│ │  │  ● 12 reps       │      │ │
│ │  │  Form: 87/100    │      │ │
│ │  └──────────────────┘      │ │
│ │                             │ │
│ │  ⚠️ "Go deeper"            │ │
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│  ┌─────┐  ┌─────┐  ┌─────┐    │
│  │ 🔴  │  │ 🔊  │  │ End │    │
│  │ Rec  │  │Sound│  │     │    │
│  └─────┘  └─────┘  └─────┘    │
└─────────────────────────────────┘
```

**UX details:**
- Camera fills most of screen (existing fullscreen camera UI from current app)
- Rep counter: large, top-left, sage background pill
- Form score: updates per-rep, 0-100. Color: green (80+), gold (60-79), red (<60)
- Form correction toast: appears at bottom of camera when form breaks threshold
  - "Go deeper" — depth insufficient
  - "Core tight" — hip sag detected
  - "Slow down" — too fast
- Toast auto-dismisses after 2s, max 1 at a time (no stacking)
- Bottom bar: record, sound, end (existing from current challenge UI)
- Set auto-completes when user stops for 3+ seconds after reps detected (or manual tap)
- No skeleton overlay by default (clean camera). Toggle available in settings.

#### Form scoring system

```
Per-rep score (0-100):
  Depth:      0-30 points  (joint angle vs target threshold)
  Alignment:  0-30 points  (back straightness, hip position)
  Tempo:      0-20 points  (controlled motion, not jerky)
  Full ROM:   0-20 points  (complete range of motion)

Set score = average of per-rep scores
Session score = weighted average of all set scores
```

- Score shown live as it updates each rep
- Post-set: "Form Score: 87 — Great depth, watch your hip alignment"
- Post-workout summary includes average form score per exercise
- History tracks form score over time (separate from weight/reps)

#### Exercise-specific detection rules (pose thresholds)

| Exercise | Key Landmarks | Correction Triggers |
|----------|--------------|-------------------|
| Pushup | Shoulders, elbows, hips, ankles | Elbow angle > 110° ("go deeper"), hip-shoulder-ankle angle < 160° ("core tight"), hip above shoulder line ("lower your hips") |
| Squat | Hips, knees, ankles | Hip below knee line not reached ("go deeper"), knees past toes > 3cm ("knees back"), torso lean > 45° ("chest up") |
| Plank | Shoulders, hips, ankles | Hip sag > 10° ("hips up"), hip pike > 10° ("flatten out"), shoulder not over wrists ("shift forward") |
| Lunge | Front knee, back knee, torso | Front knee angle > 100° ("lower"), back knee not near floor ("drop the back knee"), torso lean > 15° ("stay upright") |
| Burpee | Full body across phases | Pushup phase: same as pushup rules. Jump phase: hip extension at top. |
| Jump Squat | Hips, knees, ankles | Squat depth before jump, hip extension at peak, soft landing (deceleration) |
| Mountain Climber | Shoulders, hips, knees | Plank alignment maintained, knee drives past hip line |
| Squat Hold | Hips, knees, ankles | Same as squat, plus hold time tracking |

#### M2 Implementation Notes (Completed)

| File | Action | Purpose |
|------|--------|---------|
| `api/features/workout/services/camera_tracking.py` | Created | Exercise-to-analyzer mapping (is_trackable, create_workout_analyzer) |
| `api/features/workout/services/form_scoring.py` | Created | Aggregate per-frame form quality into 0-100 score |
| `frontend/src/composables/useCameraTracking.js` | Created | Camera init, WS connect, frame capture, pose overlay composable |
| `api/main.py` | Modified | New `/ws/workout/{session_id}/track` WebSocket endpoint |
| `api/features/workout/routers/workout.py` | Modified | `POST /sessions/{id}/sets/{n}/camera-result` endpoint |
| `frontend/src/views/workout/session/ActiveSet.vue` | Modified | Camera mode vs manual mode based on exercise slug |
| `frontend/src/views/workout/session/ExerciseIntro.vue` | Modified | Camera tracking badge for trackable exercises |

**Key decisions:**
- Reuses existing challenge analyzers (PushupAnalyzer, SquatAnalyzer, PlankAnalyzer) rather than duplicating code
- Camera mode auto-detects from exercise slug via TRACKABLE_SLUGS constant (synced front+back)
- Sequential frame processing (not frame-dropping) since bodyweight exercises are rep-based
- Form score stored in `exercise_sets.form_score` column (new migration)

---

### M3: The Voice

**What:** The coach speaks (TTS) and listens (STT). Pre-workout briefs become audio. Between-set tips are spoken. Voice input replaces manual tapping for gym exercises.

**Depends on:** M1 (workout session flow exists)

#### What the voice adds to each phase

| Phase | What Coach Says | How |
|-------|----------------|-----|
| Pre-workout brief | "Today is Push day. We've got..." (personalized) | LLM → TTS (streamed, ~2s) |
| Exercise intro | "Next up: bench press, 4 sets of 10 at 40kg" | Template → pre-generated clip |
| During set (video) | "Good rep" / "Go deeper" / "3 more" | Pre-generated clips (<100ms) |
| Set complete | "Nice, 15 reps. That's 2 more than last time." | Template → TTS (~300ms) |
| Rest period | "Focus on slow negatives next set" | Template → TTS. Always-listening ON. |
| Post-workout | "Strong session. Your bench is climbing..." | LLM → TTS (streamed) |

#### Voice input UX (gym exercises)

For exercises in voice mode (bench press, OHP, etc.), the Active Set screen changes:

```
┌─────────────────────────────────┐
│  BENCH PRESS      Set 2 of 4   │
├─────────────────────────────────┤
│                                 │
│                                 │
│           10 × 40kg             │
│            TARGET               │
│                                 │
│           0:34                  │
│        (set timer)              │
│                                 │
│                                 │
│                                 │
├─────────────────────────────────┤
│                                 │
│     [  ✓ Complete Set  ]        │
│                                 │
│     [ 🎤 Hold to speak ]        │
│     "did 10 at 40" / "done"    │
│                                 │
└─────────────────────────────────┘

During REST (always-listening active):
┌─────────────────────────────────┐
│          REST   1:23            │
│                                 │
│     🎤 Listening...             │
│     (pulsing mic indicator)     │
│                                 │
│  "That felt heavy"              │
│  Coach: "Yeah, 42.5kg is a     │
│  jump. Want to drop to 40 for  │
│  the last set?"                 │
│                                 │
│     [Skip Rest →]               │
└─────────────────────────────────┘
```

**UX details:**
- PTT button: hold to speak. Release → processes. Confirmation toast.
- Voice commands recognized: "done", "complete", "12 reps", "12 at 60", "skip", "pause"
- Always-listening during rest: pulsing mic icon at center, conversation appears as chat bubbles
- If STT doesn't understand: "Sorry, didn't catch that. Tap to complete instead."
- Mute button always available — one tap silences coach, hides mic

#### Audio flow architecture

```
                    ┌──────────────┐
Form correction ──► │ Pre-generated │ ──► Play instantly (0ms)
                    │ audio clips   │
                    └──────────────┘

                    ┌──────────────┐
Set complete,   ──► │ Template +    │ ──► TTS API call (~200ms)
rest tips           │ fill values   │     Stream first words
                    └──────────────┘

                    ┌──────────────┐
Pre/post brief, ──► │ LLM call +    │ ──► TTS API call (~1-2s)
conversation        │ generate text │     Stream audio
                    └──────────────┘
```

#### M3 Implementation Notes (Completed)

| File | Action | Purpose |
|------|--------|---------|
| `api/features/workout/services/tts_service.py` | Created | Pre-recorded clip matching + OpenAI TTS fallback |
| `api/features/workout/services/voice_command.py` | Created | Parse speech text to (action, params) tuples |
| `scripts/generate_coach_audio.py` | Created | Batch-generate ~55 pre-recorded MP3 clips |
| `frontend/src/composables/useVoiceOutput.js` | Created | Audio queue, mute toggle, browser speechSynthesis fallback |
| `frontend/src/composables/useVoiceInput.js` | Created | Web Speech API recognition composable |
| `frontend/src/views/workout/WorkoutSessionView.vue` | Modified | Mute button in topbar, auto-play coach audio |
| `frontend/src/views/workout/session/RestTimer.vue` | Modified | Voice command button + listening indicator |
| `api/features/workout/routers/workout.py` | Modified | `GET /tts/{cache_key}` dynamic TTS endpoint |
| `api/main.py` | Modified | Voice message type on workout WS |
| `api/config.py` | Modified | tts_enabled, tts_voice, stt_enabled settings |

**Key decisions:**
- Pre-recorded clips first (0ms latency), dynamic TTS only for personalized text with numbers/names
- Web Speech API for STT instead of server-side Vosk (simpler, no audio streaming needed)
- Audio URL auto-resolved from coach_says text in _agent_response helper
- Mute state persisted in localStorage

---

### M4: The Brain

**What:** AI-powered workout plan generation, progressive overload, adaptive rescheduling. The coach becomes intelligent about *what* you should do, not just *how* you're doing it.

**Depends on:** M1 (session data being collected)

#### Plan generation

**Input to LLM:**
```json
{
  "profile": { "fitness_level": "intermediate", "goal": "build_muscle", ... },
  "equipment": ["barbell", "dumbbells", "cables", "machines"],
  "schedule": { "days": ["mon", "wed", "fri", "sat"], "duration_min": 45 },
  "exercise_library": [ ... 20 exercises with metadata ... ],
  "recent_performance": { "bench_press": { "last_weight": 40, "trend": "improving" }, ... },
  "injuries": ["lower_back_mild"]
}
```

**Output (structured JSON):**
```json
{
  "split_type": "push_pull_legs",
  "weeks": [{
    "mon": {
      "type": "push",
      "exercises": [
        { "slug": "pushup", "sets": 3, "reps": 15, "weight_kg": null },
        { "slug": "bench_press", "sets": 4, "reps": 10, "weight_kg": 42.5 },
        ...
      ],
      "warmup": { "duration_min": 5, "type": "dynamic_stretch" },
      "cooldown": { "duration_min": 5, "type": "static_stretch" }
    },
    ...
  }],
  "coach_note": "Moved deadlift to pull day to protect your lower back. Keeping weight moderate this week."
}
```

#### Progressive overload logic

```
After each session, for each exercise:

1. Did user complete all prescribed sets/reps?
   YES → flag for progression next session
   NO  → keep same weight, adjust reps down if RPE was high

2. Progression rules:
   - Compound lifts: +2.5kg when all sets completed at RPE ≤ 7
   - Isolation: +1-2 reps per set before increasing weight
   - Bodyweight: increase target reps by 1-2 when form score > 80
   - Holds (plank): increase target by 5-10 seconds

3. Deload: after 4 weeks of progression, or if RPE consistently > 8
   → reduce weight by 10%, reduce volume by 20% for 1 week
```

#### Adaptive rescheduling & time constraints

**Per-session time adjustment (pre-workout):**
- User selects available time before every session (20/30/45/60 min or "Full Plan")
- Coach trims intelligently: drop isolation first → reduce sets on compounds → shorten rest
- LLM explains tradeoffs: "With 30 min, I'm prioritizing bench and OHP. We'll catch up on isolation Friday."
- Skipped exercises can be redistributed to later sessions in the week

**Weekly adaptation:**
- Missed Monday? Coach moves Monday's workout to Tuesday, shifts rest day.
- Missed 2+ days? Coach rebuilds rest of week, prioritizing compounds.
- User says "I'm tired today"? Coach offers: lighter version, swap for mobility/yoga, or skip.
- Injury reported mid-week? Coach immediately removes contraindicated exercises, suggests alternatives.
- Consistently short on time? Coach suggests switching from 5-day to 3-day split, or from PPL to Full Body.

#### What changes in the UX

Home screen "COACH SAYS" becomes truly personalized:
- References actual numbers: "Your bench went from 40 to 42.5 this month"
- Suggests today's focus: "Let's push for 3×12 on pushups today — you've been hitting 10 consistently"
- Weekly summaries generated by LLM: volume trends, adherence rate, goal progress

Plan screen becomes editable:
```
┌─────────────────────────────────┐
│  This Week's Plan        [Edit] │
├─────────────────────────────────┤
│  MON — Push Day            ✅  │
│  TUE — Rest                     │
│  WED — Pull Day            ✅  │
│  THU — Rest                     │
│  FRI — Leg Day             ●   │ ← today
│  SAT — Cardio/Yoga              │
│  SUN — Rest                     │
├─────────────────────────────────┤
│  [Edit] → swap days, swap       │
│  exercises, change sets/reps    │
│                                 │
│  Coach: "I've bumped your       │
│  bench to 42.5kg this week      │
│  based on last week's          │
│  performance."                  │
└─────────────────────────────────┘
```

#### M4 Implementation Notes (Completed)

| File | Action | Purpose |
|------|--------|---------|
| `api/features/workout/services/llm_service.py` | Created | Multi-provider LLM service (OpenAI/Anthropic/Ollama) with retry + fallback |
| `api/features/workout/services/ai_plan_generator.py` | Created | LLM-powered plan gen with exercise catalog + user history context |
| `api/features/workout/services/progressive_overload.py` | Created | Auto-adjust weight/reps: compound +2.5kg, isolation +reps, bodyweight +reps, deload after 4 weeks |
| `api/features/workout/db_models/workout.py` | Modified | ExerciseProgression model, form_score on ExerciseSet |
| `api/database.py` | Modified | `_migrate_exercise_progression()` for new table + form_score column |
| `api/features/workout/services/workout_service.py` | Modified | Try AI plan gen first, fall back to template |
| `api/features/workout/services/coach_feedback.py` | Modified | `try_smart_set_feedback()` and `try_smart_summary()` with LLM + template fallback |
| `api/features/workout/services/session_agent.py` | Modified | LLM feedback, progression targets in active_set, audio_url in responses |
| `api/features/workout/models/workout.py` | Modified | audio_url field on AgentResponse |
| `api/config.py` | Modified | llm_provider, openai_api_key, anthropic_api_key, ollama_base_url, llm_model, llm_enabled |
| `requirements-web.txt` | Modified | openai>=1.30.0, anthropic>=0.42.0 |

**Key decisions:**
- Multi-provider: OpenAI (default, cheapest), Anthropic, Ollama (free local) — selected via config
- Graceful fallback chain: LLM call fails -> template generator -> still works
- Progressive overload runs at session end, updates ExerciseProgression table
- Sync wrappers around async LLM calls (new_event_loop) since session_agent is sync

---

### M5: Dance & Cardio

**What:** Zumba and yoga follow-along via MoveMatch. Fun cardio option alongside strength training.

**Depends on:** M1 (session infrastructure)

#### Browse & Start Flow

```
┌─────────────────────────────────┐
│  Explore > Zumba & Dance        │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐   │
│  │  🔥🔥🔥                  │   │
│  │  [Thumbnail]             │   │
│  │  Beginner Zumba Cardio   │   │
│  │  15 min · Easy · 🎵      │   │
│  │  Avg score: 72/100       │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │  [Thumbnail]             │   │
│  │  Latin Dance HIIT        │   │
│  │  20 min · Medium · 🎵    │   │
│  │  Not yet tried           │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │  [Thumbnail]             │   │
│  │  Morning Yoga Flow       │   │
│  │  10 min · Easy · 🧘      │   │
│  │  Avg score: 85/100       │   │
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

#### Live Follow-Along Screen

```
┌─────────────────────────────────┐
│ ┌──────────────┬──────────────┐ │
│ │  Reference   │   You        │ │
│ │  Video       │  (Camera)    │ │
│ │              │              │ │
│ │              │              │ │
│ └──────────────┴──────────────┘ │
│                                 │
│        Score: 78/100            │
│  ━━━━━━━━━━━━━━━░░░░░           │
│                                 │
│  "Great timing! Arms wider"    │
│                                 │
│     2:34 / 15:00                │
│                                 │
│  [⏸ Pause]           [✕ End]  │
└─────────────────────────────────┘
```

**UX details:**
- Split screen: reference video left, user camera right (existing MoveMatch UI)
- Live similarity score updating in real-time
- Score bar: sage fill, animating
- Coach tips: text toasts based on pose comparison ("arms wider", "bend more")
- In M3: coach tips are spoken via pre-generated clips
- Post-session: same summary screen as strength workouts, with score + highlights
- Can be included in weekly plan as "Cardio" day

---

### M6: Social & Polish

**What:** Coach personas, streak mechanics, shareable summaries, audio ducking. The polish that makes the app sticky.

**Depends on:** M3 (voice infrastructure), M4 (plan intelligence)

#### Coach Personas

```
┌─────────────────────────────────┐
│  Profile > Coach Settings       │
├─────────────────────────────────┤
│                                 │
│  YOUR COACH                     │
│                                 │
│  ┌─────────────────────────┐   │
│  │  😤 Drill Sergeant       │   │
│  │  "5 more. No excuses."   │   │
│  │  Voice: Male, firm       │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │  😊 Supportive Friend  ✓│   │
│  │  "You're doing great,    │   │
│  │   take your time"        │   │
│  │  Voice: Female, warm     │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │  🧘 Calm Yogi            │   │
│  │  "Breathe in... push...  │   │
│  │   exhale"                │   │
│  │  Voice: Neutral, soft    │   │
│  └─────────────────────────┘   │
│  ┌─────────────────────────┐   │
│  │  🔥 Hype Beast           │   │
│  │  "LET'S GO! That's what  │   │
│  │   I'm talking about!"    │   │
│  │  Voice: Male, energetic  │   │
│  └─────────────────────────┘   │
│                                 │
│  COACH NAME                     │
│  [ Coach ]                      │
│                                 │
│  CHATTINESS                     │
│  Minimal ──●────── Full         │
│                                 │
│  [🔇 Don't Talk] quick toggle  │
│                                 │
└─────────────────────────────────┘
```

#### Shareable Summary Card

```
┌─────────────────────────────────┐
│                                 │
│  ┌─────────────────────────┐   │
│  │  🦦 PushUp Pro           │   │
│  │                         │   │
│  │  PUSH DAY               │   │
│  │  March 11, 2026         │   │
│  │                         │   │
│  │  42 min · 5 exercises   │   │
│  │  16 sets · 3,240 vol    │   │
│  │                         │   │
│  │  🏆 PR: Pushup 18 reps  │   │
│  │  📈 Bench: 42.5kg       │   │
│  │  🔥 Day 12 streak       │   │
│  │                         │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━  │   │
│  │  pushuppro.app           │   │
│  └─────────────────────────┘   │
│                                 │
│  [Instagram] [WhatsApp] [Copy] │
│                                 │
└─────────────────────────────────┘
```

- Generated as image (canvas → PNG)
- Cream background, sage accent, branded
- Instagram story format (9:16) and square (1:1)
- Deep link back to app

#### Streak Mechanics

- Day counts as "active" if any workout completed (even partial)
- Streak displayed on home screen, profile, share cards
- Milestones: 7 days, 14 days, 30 days, 60 days, 100 days
- Coach acknowledges milestones: "14 days in a row. You're building a habit."
- Freeze: 1 free streak freeze per week (miss a day without breaking streak)
- Rest days don't break streaks (only scheduled workout days count)

---

## 5. Technical Architecture

### System diagram

```
┌─────────────────────────────────────────────────┐
│                    PHONE (PWA)                    │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Vue 3    │  │ MediaPipe│  │ Vosk (STT)   │  │
│  │ Frontend │  │ Pose     │  │ On-device    │  │
│  │          │  │ (WASM)   │  │ speech-to-   │  │
│  │          │  │          │  │ text         │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │                │          │
│       │    WebSocket (frames)         │          │
│       │              │                │          │
└───────┼──────────────┼────────────────┼──────────┘
        │              │                │
        │ REST API     │                │
        ▼              ▼                │
┌───────────────────────────────────────┼──────────┐
│              BACKEND (FastAPI)         │          │
│                                        │          │
│  ┌──────────┐  ┌──────────┐  ┌───────▼───────┐ │
│  │ Workout  │  │ Pose     │  │ Voice Intent  │ │
│  │ Engine   │  │ Analysis │  │ Parser        │ │
│  │ (plans,  │  │ + Form   │  │ (parse "12 at│ │
│  │  overload│  │ Scoring  │  │  60" → data)  │ │
│  │  sched.) │  │          │  │               │ │
│  └────┬─────┘  └──────────┘  └───────────────┘ │
│       │                                          │
│  ┌────▼─────┐  ┌──────────┐  ┌───────────────┐ │
│  │ Database │  │ LLM      │  │ TTS           │ │
│  │ MySQL/   │  │ (Claude) │  │ (OpenAI)      │ │
│  │ SQLite   │  │ Plans,   │  │ Dynamic       │ │
│  │          │  │ briefs,  │  │ coaching      │ │
│  │          │  │ chat     │  │ audio         │ │
│  └──────────┘  └──────────┘  └───────────────┘ │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │ Pre-generated Audio Clips (S3/local)       │  │
│  │ ~100 form correction phrases, cached on    │  │
│  │ device at first launch                     │  │
│  └────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

### What we already have vs. what we build

| Component | Status | Milestone |
|-----------|--------|-----------|
| Pose detection (MediaPipe) | ✅ Built | — |
| Rep counting (pushup, squat, plank) | ✅ Built | — |
| WebSocket live sessions | ✅ Built | — |
| MoveMatch (pose comparison) | ✅ Built | M5 integrates |
| User auth (JWT, Google, OTP) | ✅ Built | — |
| Vue 3 + Vite + PWA | ✅ Built | — |
| Sage & Cream theme | ✅ Built | — |
| Bottom nav + mobile shell | ✅ Built | — |
| Exercise database + seed | ✅ Built | M0 |
| User profile + onboarding | ✅ Built | M0 |
| Workout plan data model | ✅ Built | M0 |
| Session logging (sets/reps/weight) | ✅ Built | M1 |
| Rest timer + session flow | ✅ Built | M1 |
| Form scoring rules | ✅ Built | M2 |
| Form correction toasts (visual) | ✅ Built | M2 |
| Camera-enabled ActiveSet (WS) | ✅ Built | M2 |
| Pre-generated audio script | ✅ Built | M3 |
| TTS integration (OpenAI) | ✅ Built | M3 |
| STT integration (Web Speech API) | ✅ Built | M3 |
| Voice commands during rest | ✅ Built | M3 |
| Mute/unmute toggle | ✅ Built | M3 |
| LLM service (multi-provider) | ✅ Built | M4 |
| AI plan generation | ✅ Built | M4 |
| Progressive overload engine | ✅ Built | M4 |
| LLM coach feedback | ✅ Built | M4 |
| ExerciseProgression model | ✅ Built | M4 |
| Zumba/yoga browse + session | 🔨 Build | M5 |
| Coach personas + voice selection | 🔨 Build | M6 |
| Share cards (canvas → image) | 🔨 Build | M6 |
| Streak mechanics | 🔨 Build | M6 |

### Cost model (at scale)

| Component | 1K DAU/mo | 10K DAU/mo | 100K DAU/mo |
|-----------|-----------|------------|-------------|
| OpenAI TTS (dynamic coaching) | $30-50 | $300-500 | $3-5K |
| Claude LLM (plans, briefs, chat) | $50-100 | $500-1K | $5-10K |
| Pre-generated audio | $0 | $0 | $0 |
| Vosk STT (on-device) | $0 | $0 | $0 |
| AWS infra (ECS, S3, DB) | $100-200 | $500-1K | $3-5K |
| **Total** | **~$200-350** | **~$1.5-2.5K** | **~$12-20K** |

At $10/mo subscription, 100K DAU with 5% conversion = 5K paying users = $50K/mo revenue vs $12-20K cost. Healthy margins.

---

## 6. Open Questions

| # | Question | Options | Decision |
|---|----------|---------|----------|
| 1 | How prescriptive is the plan? | Coach dictates / Coach suggests + user swaps | **Coach suggests, user can swap.** "Adjust Plan" on plan screen. |
| 2 | Track bodyweight over time? | Yes (optional) / No | **Yes, optional, never forced.** Useful for weight loss goal tracking. |
| 3 | Exercises we can't camera-track? | Voice only / Ignore | **Voice + manual tap.** Coach trusts user-reported numbers. |
| 4 | Monetization | Freemium / Trial → sub | **Freemium.** Free: basic logging, limited coach. Premium ($10/mo): full AI coach, voice, form, plans. |
| 5 | LLM for plans/chat? | Claude / GPT-4o | **Claude** (our existing stack). Structured JSON output for plans. |
| 6 | On-device vs cloud form correction? | On-device / Cloud | **On-device** (MediaPipe in browser). <100ms required. Backend stores results. |
| 7 | PWA vs native? | PWA / Capacitor / Native | **PWA for MVP.** Capacitor wrap in M6 for audio ducking. |
| 8 | Exercise demo videos? | Record / License / AI-generated / 3D | **Placeholder images for M0-M1.** Record/license for M2+. 3D (TresJS) as stretch goal. |
| 9 | TTS provider? | See Appendix C | **Resolved:** Pre-generated clips + OpenAI gpt-4o-mini-tts. |
| 10 | Voice input mode? | See Appendix B | **Resolved:** PTT during sets + always-listening during rest. |
| 11 | Exercise list at launch? | See Appendix A | **Resolved:** 20 exercises across 3 tracking modes. |

---

## Appendix A: Exercise Library

*(Unchanged from previous version — 8 video, 10 voice, 2 MoveMatch categories. See full detail in git history or expand below.)*

### The 20 MVP Exercises

**Video Mode (8):** Pushup, Squat, Squat Hold, Plank, Lunge, Burpee, Jump Squat, Mountain Climber

**Voice Mode (10):** Bench Press, Overhead Press, Barbell Row, Deadlift, Lat Pulldown, Bicep Curl, Tricep Pushdown, Leg Press, Lateral Raise, Calf Raise

**MoveMatch Mode (2):** Zumba/Dance Cardio, Yoga Flows

### Coverage by split
| Split | Exercises |
|-------|-----------|
| Push | Pushup, Bench Press, OHP, Tricep Pushdown, Lateral Raise |
| Pull | Barbell Row, Lat Pulldown, Bicep Curl, Deadlift |
| Legs | Squat, Lunge, Jump Squat, Leg Press, Calf Raise |
| Core | Plank, Mountain Climber |
| HIIT | Burpee, Jump Squat, Mountain Climber, Pushup, Squat |
| Cardio | Zumba/Dance (MoveMatch) |
| Flexibility | Yoga Flows (MoveMatch) |

### V2 expansion
Pull-up, Dips, Romanian Deadlift, Hip Thrust, Face Pull, Side Plank, Boxing combos

---

## Appendix B: Voice Input Design

*(Unchanged — PTT during sets, always-listening during rest. See Appendix B in git history.)*

---

## Appendix C: TTS Provider Decision

*(Unchanged — Pre-generated clips for form corrections, OpenAI gpt-4o-mini-tts for dynamic coaching. See Appendix C in git history.)*

---

## Appendix D: Competitor Analysis

*(Unchanged — full competitive breakdown. See Appendix D in git history.)*

Key positioning summary:

```
                    Plan    Camera   Voice   Personal   Phone-only
Fitbod               ✅       ❌       ❌       ✅          ✅
SHRED                 ⚠️       ✅       ⚠️       ⚠️          ✅
Tempo                 ⚠️       ✅       ✅       ✅          ❌ ($2K HW)
Ray                   ⚠️       ✅       ✅       ⚠️          ✅
Us                    ✅       ✅       ✅       ✅          ✅
```

---

*This is a living document. Ready for deep-dive on any milestone, flow, or screen.*
