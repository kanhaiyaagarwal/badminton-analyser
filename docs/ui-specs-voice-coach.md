# UI Specs — Voice-First AI Coach Companion

## Design System Reference

**Theme**: Sage & Cream Cozy
- **Page background**: `#F5F2EB` (warm cream)
- **Card background**: `#FDFCF9` (off-white)
- **Primary color (Sage)**: `#7C8B6F` → gradient `#7C8B6F → #A5B08D`
- **Text primary**: `#2D2A26` (warm black)
- **Text secondary**: `#706860` (warm gray)
- **Text muted**: `#B0A99F` (light gray)
- **Destructive**: `#C44B3D` (warm red)
- **Success**: `#6B7A5E` (deep sage)
- **Warning/Gold**: `#D4A843`
- **Secondary/Terracotta**: `#C4613D`
- **Font**: DM Sans
- **Border radius**: sm=8px, md=12px, lg=16px, xl=20px
- **App frame**: max-width 430px (mobile-first), centered on desktop with `#E8E4DC` background
- **Mascot**: Otter character (`/mascot/otter-mascot.png`)

---

## Shared Component: CoachChat

Used across Onboarding, Pre-Workout, Rest Timer, and Summary screens.

### Layout
```
┌─────────────────────────────────┐
│  [Scrollable Message Area]      │
│                                 │
│  ┌──────────────────────┐       │
│  │ 🦦 Coach message     │       │
│  │ text goes here...    │       │
│  └──────────────────────┘       │
│                                 │
│          ┌──────────────────┐   │
│          │ User reply here  │   │
│          └──────────────────┘   │
│                                 │
│  ┌──────────────────────┐       │
│  │ 🦦 Next question...  │       │
│  └──────────────────────┘       │
│                                 │
│  ┌────────┐ ┌────────┐ ┌─────┐ │
│  │Option 1│ │Option 2│ │Opt 3│ │  ← Option cards (horizontal scroll)
│  └────────┘ └────────┘ └─────┘ │
│                                 │
├─────────────────────────────────┤
│  ┌─────────────────────┐  🎤   │  ← Input bar
│  │ Type a message...   │  ( )  │
│  └─────────────────────┘       │
└─────────────────────────────────┘
```

### Coach Message Bubble
- Aligned left
- Otter mascot avatar (28×28px, rounded) to the left
- Bubble: `bg: var(--bg-card)`, `border: 1px solid var(--border-color)`, `border-radius: 0 16px 16px 16px`
- Text: 14px DM Sans, `color: var(--text-primary)`, line-height 1.5
- Max-width: 85% of container
- Subtle fade-in animation (0.3s)

### User Message Bubble
- Aligned right
- Bubble: `bg: var(--color-primary-light)`, `border-radius: 16px 0 16px 16px`
- Text: 14px DM Sans, `color: var(--text-primary)`
- Max-width: 75% of container

### Option Cards
- Appear below the most recent coach message
- Horizontal scroll container (no scrollbar visible)
- Each card: `bg: var(--bg-card)`, `border: 2px solid var(--border-color)`, `border-radius: 12px`
- Padding: 12px 16px
- Text: 14px, font-weight 600, `color: var(--text-primary)`
- Optional icon/emoji above text (24px)
- On tap: border turns sage (`var(--color-primary)`), brief scale animation (1.0 → 0.95 → 1.0)
- Selected state: `border-color: var(--color-primary)`, `bg: var(--color-primary-light)`
- Cards have min-width 100px, gap 8px between them

### Mic Button
- Circular, 48×48px, positioned right of text input
- **Idle**: `bg: var(--gradient-primary)`, white mic icon (24px SVG)
- **Listening**: `bg: #C44B3D` (red), white mic icon, pulsing ring animation (0→16px outward, 1.5s loop, `rgba(196,75,61,0.3)`)
- **Processing**: `bg: var(--color-primary)`, spinning circle icon (replaces mic)
- Tap toggles listening on/off

### Text Input
- `bg: var(--bg-input)`, `border: 1px solid var(--border-input)`, `border-radius: 24px`
- Placeholder: "Type or tap mic...", `color: var(--text-muted)`
- Height: 44px, padding: 0 16px
- Focus: `border-color: var(--color-primary)`

### Typing Indicator
- Shown while waiting for coach response
- Three dots bouncing animation in a coach-style bubble
- Dots: 6px circles, `bg: var(--text-muted)`, staggered bounce (0.4s each, 0.15s delay)

### Coach Speaking Indicator
- While TTS is playing, a small sound wave icon (3 bars animating) appears next to the coach avatar
- Subtle pulsing glow on the avatar border

---

## Screen 1: Conversational Onboarding

**Route**: `/workout/onboarding`
**When**: First-time user, or after reset

### Layout
```
┌─────────────────────────────────┐
│                        [Skip →] │  ← Top right, text link
│                                 │
│         ┌──────────┐            │
│         │  🦦      │            │  ← Otter mascot (80×80px)
│         │  mascot  │            │
│         └──────────┘            │
│     AI Fitness Coach            │  ← Title: 18px bold, sage color
│                                 │
│  ┌──────────────────────────┐   │
│  │ 🦦 Hey there! I'm your  │   │
│  │ AI coach. Let's set up   │   │
│  │ your plan — takes about  │   │
│  │ a minute!                │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌──────────────────────────┐   │
│  │ How would you describe   │   │
│  │ your fitness level?      │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌──────────┐ ┌──────────┐     │
│  │ 🌱       │ │ 💪       │     │
│  │ Beginner │ │Intermed. │     │
│  └──────────┘ └──────────┘     │
│              ┌──────────┐       │
│              │ 🔥       │       │
│              │ Advanced │       │
│              └──────────┘       │
│                                 │
├─────────────────────────────────┤
│  ┌─────────────────────┐  🎤   │
│  │ Type or tap mic...  │  ( )  │
│  └─────────────────────┘       │
└─────────────────────────────────┘
```

### States & Transitions

**State 1: Welcome + Fitness Level**
- Mascot image centered at top (80×80, rounded corners)
- Title "AI Fitness Coach" below mascot (18px, bold, sage)
- Coach bubble: greeting + fitness level question
- 3 option cards in a 2+1 grid (or horizontal scroll)
- Each card: emoji + label, ~120px wide, 80px tall
- Mic button pulsing gently to invite voice input

**State 2: About You (Optional)**
- Previous answer shown as user bubble ("Beginner")
- Coach: "Got it! Any injuries or things I should know? Age, height — whatever you're comfortable sharing."
- No option cards — free-form input area
- "Skip this" as a subtle text link below input
- User speaks: "I'm 28, 180cm, bad knees" → appears as user bubble

**State 3: Goals**
- Coach: "What are you training for? Pick as many as you like."
- 4 option cards in 2×2 grid:
  - "Build Muscle 💪" / "Lose Fat 🔥" / "Get Stronger 🏋️" / "Stay Active 🏃"
- Multi-select: cards can be selected simultaneously (border turns sage, checkmark appears)
- "Next" button appears after 1+ selected

**State 4: Schedule**
- Coach: "How many days a week can you train?"
- Day circle buttons: M T W T F S S (42×42px circles)
  - Unselected: `bg: transparent`, `border: 2px solid var(--border-color)`, `color: var(--text-muted)`
  - Selected: `bg: var(--color-primary)`, `color: white`
  - Tap toggles
- Coach follow-up: "And how long per session?"
- Duration pills: 20 / 30 / 45 / 60 min (horizontal, pill-shaped buttons)
  - Same selected/unselected styling as day circles but pill-shaped
- Coach: "Gym or home?"
- Two cards: "🏠 Home" / "🏋️ Gym" (single select)

**State 5: Equipment** (only if gym selected)
- Coach: "What equipment do you have access to?"
- Checkbox-style cards in 2-column grid:
  - Barbell / Dumbbells / Bench / Squat Rack / Cable Machine / Kettlebell / Resistance Bands / Yoga Mat
  - Each: 48px height, icon + label, toggleable
- "That's all" button to proceed

**State 6: Plan Generation**
- Coach: "Perfect! Let me build your plan..."
- Loading state: otter mascot with thinking animation (dots or subtle bounce)
- After ~2-3s: Coach bubble appears with plan summary
  - "Here's your **Push-Pull-Legs** plan — 4 days/week, ~45 min sessions."
  - Plan summary card appears inline:
    ```
    ┌─────────────────────────┐
    │ Push-Pull-Legs Plan     │
    │ 4 days/week · ~45 min   │
    │                         │
    │ Mon: Push (Chest/Tri)   │
    │ Tue: Pull (Back/Bi)     │
    │ Thu: Legs               │
    │ Fri: Push (Shoulders)   │
    └─────────────────────────┘
    ```
    Card: `bg: var(--bg-card)`, `border: 1px solid var(--color-primary)`, rounded
- Two buttons below: "Let's go! →" (primary, full-width) and "Regenerate" (text link)

### Animations
- Messages slide in from bottom (translateY 20px → 0, opacity 0→1, 0.3s ease)
- Option cards stagger in (0.1s delay each)
- Auto-scroll to bottom on each new message
- Mascot at top shrinks as conversation grows (80px → 48px after 3 exchanges)

### Skip Flow
- "Skip →" link in top-right corner
- Tapping skip: confirmation bottom sheet "Skip setup? You can always set up later."
- Two buttons: "Skip for now" → navigate to `/workout` / "Continue setup"

---

## Screen 2: Welcome-Back Home

**Route**: `/workout`
**When**: Returning user (onboarded, has plan)

### Layout
```
┌─────────────────────────────────┐
│ [header: PushUp Pro + admin]    │
├─────────────────────────────────┤
│                                 │
│      WELCOME BACK,              │  ← 28px, bold, text-primary
│        CHAMP! 🔥                │  ← Rotated greeting, centered
│                                 │
│  ┌─────────────────────────────┐│
│  │ 🦦  "You've been showing   ││  ← Coach insight bubble
│  │     up consistently —      ││
│  │     4 workouts this week.  ││
│  │     Bench is up 5kg since  ││
│  │     you started!"          ││
│  └─────────────────────────────┘│
│                                 │
│  ┌─────────────────────────────┐│
│  │ TODAY: Push Day        45m ││  ← Today's workout card
│  │                            ││
│  │ [Bench] [OHP] [Tri Push]   ││  ← Exercise pills
│  │ [Lat Raise] [Flies]        ││
│  │                            ││
│  │ ┌─────────────────────────┐││
│  │ │    Start Workout →      │││  ← Primary button
│  │ └─────────────────────────┘││
│  └─────────────────────────────┘│
│                                 │
│  M  T  W  T  F  S  S           │  ← Week strip
│  ✓  ✓  ·  •  ○  ○  ○           │
│                                 │
│  ┌───────────┐ ┌───────────┐   │
│  │Build Your │ │  Browse   │   │  ← Quick start buttons
│  │   Own     │ │  Library  │   │
│  └───────────┘ └───────────┘   │
│                                 │
├─────────────────────────────────┤
│ [Home] [Workout] [Explore] [Me] │  ← Bottom nav
└─────────────────────────────────┘
```

### Big Greeting
- Full-width, centered
- Text: 28px, font-weight 800, `color: var(--text-primary)`, uppercase
- Subtle text-shadow for depth
- Rotated messages (one per day, deterministic based on date):
  - "WELCOME BACK, CHAMP!"
  - "READY TO CRUSH IT?"
  - "LET'S GET AFTER IT, [NAME]!"
  - "DAY [N] — KEEP IT GOING!"
  - "GOOD [MORNING], [NAME]!"
  - "STRONGER EVERY DAY!"
- An emoji or small icon punctuates the greeting (fire, muscle, star — matched to message)
- Fade-in + slight scale animation (0.95→1.0, 0.4s ease)

### Coach Insight Bubble
- Otter avatar (36×36px) on the left
- Insight text in a card: `bg: var(--color-primary-light)`, `border-radius: 16px`, padding 14px 16px
- Text: 14px, `color: var(--text-primary)`, line-height 1.5
- Italic styling for the coach "voice"
- Rotating insight types (one per day):
  - **Progress**: "Bench press is up 5kg since you started. Push day PRs keep coming."
  - **Consistency**: "4 workouts this week — you're on fire. Keep this streak alive."
  - **Goals**: "At this rate, you'll hit your strength target in ~6 weeks."
  - **Recovery**: "You trained legs hard yesterday. Today's push day gives them rest."
  - **Encouragement**: "12 of the last 14 days — consistency beats intensity every time."
- Small speaker icon next to text (TTS plays this once per day, on first visit)

### Today's Workout Card
- `bg: var(--bg-card)`, `border-radius: 16px`, `shadow: var(--shadow-md)`
- Header row: day label (16px bold) + duration badge (pill, muted text)
- Exercise pills: horizontal wrap, each pill `bg: var(--color-primary-light)`, `border-radius: 20px`, padding 6px 12px, font-size 13px, font-weight 500
- Start Workout button: full-width, sage gradient, white text, 16px bold, 48px height, `border-radius: 12px`
- If rest day: card says "Rest Day — Recovery is part of the plan" with stretching otter illustration

### Week Strip (unchanged from current)
- 7 circles in a row, centered
- States: completed (sage bg, white check), today (sage border, dot), planned (dashed sage border), rest (gray)
- Day letter below each circle (11px, muted)

---

## Screen 3: Pre-Workout Conversation (replaces BriefPhase)

**Shown as**: First view in WorkoutSessionView when `view === 'brief'`

### Layout
```
┌─────────────────────────────────┐
│ [← Back]     Push Day     [···] │  ← Slim header
├─────────────────────────────────┤
│                                 │
│  TODAY'S PLAN                   │  ← Section label, 12px uppercase muted
│                                 │
│  ┌─────────────────────────────┐│
│  │ 1. Bench Press   4×10  60kg ││  ← Exercise list cards
│  │ 2. OHP           3×10  40kg ││     Scrollable if long
│  │ 3. Tricep Push   3×12       ││
│  │ 4. Lat Raise     3×15       ││
│  │ 5. Cable Flies   3×12       ││
│  └─────────────────────────────┘│
│  ~45 min                        │
│                                 │
│  ┌──────────────────────────┐   │
│  │ 🦦 Push Day — 5 exercises│   │  ← Coach chat area
│  │ ~45 min. Ready to go, or │   │
│  │ want to make changes?    │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌─────────┐ ┌─────────┐       │
│  │Let's go!│ │  Swap   │       │  ← Quick action buttons
│  └─────────┘ │exercise │       │
│  ┌─────────┐ └─────────┘       │
│  │ Shorter │                    │
│  └─────────┘                    │
│                                 │
│          (chat continues        │
│           if user modifies)     │
│                                 │
├─────────────────────────────────┤
│ ┌─────────────────────────┐ 🎤 │
│ │ "Add more chest work"   │ () │
│ └─────────────────────────┘    │
├─────────────────────────────────┤
│ ┌───────────────────────────┐   │
│ │     BEGIN WORKOUT →       │   │  ← Sticky bottom button
│ └───────────────────────────┘   │
└─────────────────────────────────┘
```

### Exercise List Cards
- Compact list, each row: order number (muted) + exercise name (14px bold) + sets×reps (muted) + weight (if any)
- `bg: var(--bg-card)`, `border-radius: 12px`, padding 12px
- Rows separated by subtle 1px border
- If an exercise is swapped, it animates: old slides out left, new slides in from right

### Quick Action Buttons
- Horizontal scroll strip, pill-shaped buttons
- `bg: var(--bg-card)`, `border: 1px solid var(--border-color)`, `border-radius: 20px`
- Text: 13px, font-weight 600
- Options: "Let's go!" (sage bg, white text) / "Swap exercise" / "Make it shorter" / "Add more [muscle]"
- Tapping sends the label as a chat message

### Conversation Flow Example
1. Coach: "Push Day — 5 exercises, ~45 min. Ready?"
2. User taps "Swap exercise" or says "Can we swap bench for dumbbell press?"
3. Coach: "Done — swapped Bench for Dumbbell Press, same 4×10. Anything else?"
4. Exercise list updates with animation
5. User: "Let's go!" → triggers begin_workout

### Begin Workout Button
- Sticky at bottom, always visible
- Full-width, sage gradient, white text, 48px height
- Semi-transparent background behind it (blur) so content scrolls under

---

## Screen 4: Enhanced Rest Timer (Post-Set Conversation)

**Shown as**: RestTimer view with embedded mini-chat

### Layout
```
┌─────────────────────────────────┐
│ [⏸]     2:34     🔇  3/7       │  ← Top bar (existing)
├─────────────────────────────────┤
│                                 │
│  ┌──────────────────────────┐   │
│  │ "Nice — 10 reps at 65kg. │   │  ← Coach feedback (top)
│  │  That's a new PR!"       │   │
│  └──────────────────────────┘   │
│                                 │
│            REST                 │  ← "REST" label, 14px uppercase muted
│                                 │
│        ┌──────────┐             │
│        │          │             │
│        │    72    │             │  ← Countdown number inside ring
│        │          │             │
│        └──────────┘             │  ← Circular countdown SVG ring
│                                 │
│  How'd that feel?               │  ← Coach question, 15px bold
│                                 │
│  ┌───────┐ ┌───────┐ ┌───────┐ │
│  │ Easy  │ │ Good  │ │ Hard  │ │  ← Response cards (large)
│  │  😌   │ │  💪   │ │  😤   │ │
│  └───────┘ └───────┘ └───────┘ │
│                                 │
│  ┌──────────────────────────┐   │
│  │ 🦦 "Easy? Let's bump to │   │  ← Coach adapts (only after response)
│  │ 70kg next set."          │   │
│  │                          │   │
│  │ [Yes →] [Keep 65kg]      │   │  ← Inline action buttons
│  └──────────────────────────┘   │
│                                 │
│  Next: Bench Press — Set 3/4   │  ← Next set preview
│                                 │
├─────────────────────────────────┤
│  ┌─────────────────────┐  🎤   │
│  │ Ask your coach...   │  ()   │
│  └─────────────────────┘       │
│                                 │
│  ┌───────────────────────────┐  │
│  │       SKIP REST →         │  │  ← Skip button
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### Response Cards (How'd That Feel?)
- 3 large cards in a row, equal width
- Height: 72px, `border-radius: 12px`
- Each has: emoji (24px) + label (13px bold)
- **Easy**: `bg: var(--color-success-light)`, label "Easy", emoji 😌
- **Good**: `bg: var(--color-primary-light)`, label "Good", emoji 💪
- **Hard**: `bg: var(--color-destructive-light)`, label "Hard", emoji 😤
- On tap: card fills with color (smooth 0.2s transition), sends to chat
- Selected card stays highlighted

### Coach Adaptation Response
- Appears after user responds (fade in from bottom)
- Same coach bubble styling as CoachChat
- Inline action buttons within the bubble:
  - Small pill buttons, side by side
  - Primary action: sage bg, white text ("Yes →")
  - Secondary: transparent, border, muted text ("Keep 65kg")

### Countdown Ring
- SVG circle, 120×120px
- Background ring: `stroke: var(--border-color)`, stroke-width 6
- Progress ring: `stroke: var(--color-primary)`, stroke-width 6, dasharray animation
- Number inside: 48px, font-weight 800, `color: var(--text-primary)`, tabular-nums
- Drains clockwise from full to empty

### Next Set Preview
- Bottom of card area, above input
- Text: 13px, `color: var(--text-muted)`
- Format: "Next: [Exercise Name] — Set X/Y"

---

## Screen 5: Active Set (minor voice enhancements)

**Mostly unchanged from current design.**

### Camera Mode Layout (unchanged)
```
┌─────────────────────────────────┐
│ [⏸]     1:23     🔇  3/7       │
├─────────────────────────────────┤
│                                 │
│  ┌─────┐                       │
│  │  8  │          ← Rep counter │
│  │reps │                       │
│  └─────┘                       │
│                                 │
│      ┌─────────────────┐       │
│      │                 │       │
│      │   CAMERA FEED   │       │
│      │   (mirrored)    │       │
│      │                 │       │
│      │  + pose overlay │       │
│      │                 │       │
│      └─────────────────┘       │
│                                 │
│  ┌─────────────────────────┐   │
│  │  "Great depth! Keep it  │   │  ← Form feedback toast
│  │   up."                  │   │
│  └─────────────────────────┘   │
│                                 │
│  Set 2/4            1:23        │  ← Info bar
│                                 │
│  ┌───────────────────────────┐  │
│  │          DONE             │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### What changes for voice:
- Coach speaks set introduction when entering: "Set 2. Push-ups. 12 reps. Let's go!" (TTS)
- During camera tracking, form feedback is spoken as well as shown as toast
- "DONE" button remains primary interaction (user is exercising, can't talk)
- No mic button during active set

### Manual Mode Layout (unchanged)
```
┌─────────────────────────────────┐
│                                 │
│      Set 2 of 4                 │  ← Set label
│      Bench Press                │  ← Exercise name
│                                 │
│          10                     │  ← Target reps (64px bold)
│         reps                    │
│                                 │
│      Target: 65kg               │  ← Weight target (if any)
│                                 │
│        1:23                     │  ← Elapsed timer
│                                 │
│  "Keep your elbows at 45°"      │  ← Coach tip
│                                 │
│  ┌───────────────────────────┐  │
│  │      COMPLETE SET         │  │
│  └───────────────────────────┘  │
│                                 │
│  (expands to log form on tap)   │
│                                 │
└─────────────────────────────────┘
```

### Log Form (appears after "Complete Set")
```
┌─────────────────────────────────┐
│  LOG SET                        │
│                                 │
│  Reps     [-]  10  [+]         │
│  Weight   [-] 65.0 [+]  kg    │
│                                 │
│  Effort                         │
│  [1] [3] [5] [7] [9] [10]     │  ← RPE buttons (circles)
│                                 │
│  ┌───────────────────────────┐  │
│  │          SAVE             │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```
No changes to log form — it works well with taps.

---

## Screen 6: Exercise Intro (minor voice enhancement)

### Layout (unchanged, just adds TTS)
```
┌─────────────────────────────────┐
│ [⏸]     3:45     🔇  3/7       │
├─────────────────────────────────┤
│  ━━━━━━━━━━━━━━━━━░░░░░░░░░░░  │  ← Progress bar (exercise 3 of 7)
│                                 │
│      Bench Press                │  ← Exercise name, 22px bold
│      4 sets × 10 reps          │  ← Sets × reps, muted
│                                 │
│  📷 Camera Tracking             │  ← Badge if trackable
│                                 │
│  FORM CUES                      │  ← Section label
│  • Keep elbows at 45 degrees    │
│  • Touch chest to floor         │
│  • Engage your core             │
│                                 │
│  LAST SESSION                   │  ← History section
│  Best: 12 reps @ 60kg          │
│  🏆 PR: 65kg                    │
│                                 │
│  ┌──────────────────────────┐   │
│  │ 🦦 "Bench press — your   │   │
│  │ favorite. Last time you  │   │
│  │ hit 60kg. Ready to push  │   │
│  │ for 65?"                 │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌───────────────────────────┐  │
│  │       BEGIN SET →         │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │      Skip Exercise        │  │  ← Outline button
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### Voice Enhancement
- Coach speaks the intro on mount: exercise name + form cue + motivation
- No mic button here — user is about to exercise
- TTS auto-plays, then user taps "Begin Set"

---

## Screen 7: Summary (post-workout chat option)

### Layout
```
┌─────────────────────────────────┐
│                                 │
│         ✓                       │  ← Green check circle (64px)
│   Workout Complete!             │  ← 22px bold
│                                 │
│  ┌────────┐ ┌────────┐ ┌─────┐ │
│  │ 32 min │ │5 exerc.│ │18set│ │  ← Stat cards
│  │Duration│ │Exercises│ │Sets │ │
│  └────────┘ └────────┘ └─────┘ │
│                                 │
│  HIGHLIGHTS                     │
│  • New PR: Bench Press 65kg     │
│  • Completed all planned sets   │
│  • Total volume: 2,450kg        │
│                                 │
│  🔥 5 day streak!               │  ← Streak badge
│                                 │
│  ┌──────────────────────────┐   │
│  │ 🦦 "Great session! You   │   │
│  │ hit a new bench PR and   │   │
│  │ crushed all 5 exercises. │   │
│  │ Rest up — pull day       │   │
│  │ tomorrow!"               │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌─────────────────────┐  🎤   │  ← Optional chat input
│  │ Ask your coach...   │  ()   │
│  └─────────────────────┘       │
│                                 │
│  ┌───────────────────────────┐  │
│  │          DONE →           │  │
│  └───────────────────────────┘  │
│  [Share Results]                │  ← Text link
└─────────────────────────────────┘
```

### Post-Workout Chat (Optional)
- Small input bar + mic below coach bubble
- User can ask: "How did I compare to last week?" / "What should I focus on next?"
- Coach responds via chat + TTS
- "DONE" button always visible — chat is optional

---

## Mic Button Component Spec

A standalone component used across all screens.

### Sizes
- **Large** (onboarding, rest timer): 56×56px
- **Medium** (chat input): 44×44px
- **Small** (summary): 36×36px

### States

**Idle**
- `bg: var(--gradient-primary)`
- White mic SVG icon (centered)
- No animation

**Listening**
- `bg: #C44B3D` (warm red)
- White mic icon
- Pulsing ring: 3 concentric rings expanding outward (0→20px, 0.5s stagger)
- Ring color: `rgba(196, 75, 61, 0.15)` each ring
- Live transcript text appears above/below button: 14px italic, `color: var(--text-secondary)`

**Processing (waiting for response)**
- `bg: var(--color-primary)`
- Mic icon replaced with 3-dot loading animation
- Ring stops pulsing

**Disabled (no browser support)**
- `bg: var(--border-color)`
- Mic icon with strikethrough line
- `cursor: not-allowed`
- Tooltip: "Voice not supported in this browser"

---

## Animation & Motion Guidelines

- **Messages**: slide up + fade in (translateY: 16px→0, opacity: 0→1, 300ms ease-out)
- **Option cards**: stagger in (100ms delay each card, same slide+fade)
- **Coach bubble appearing**: slight scale (0.95→1.0) + fade
- **Selected card**: brief press (scale 0.97, 100ms) then expand back
- **View transitions**: existing fade transition (200ms)
- **Greeting text**: slow fade in (600ms) + gentle scale (0.9→1.0)
- **Countdown ring**: smooth CSS animation (linear, matches remaining seconds)
- **Mic pulse**: infinite loop, 1.5s period, ease-in-out

---

## Responsive Notes

- All screens designed for 430px max-width (mobile-first)
- On desktop: centered in app-frame with cream background surround
- Chat bubbles: max-width 85% (coach) / 75% (user) of container
- Option cards: horizontal scroll if they overflow (snap scrolling)
- Mic button: always in thumb-reach zone (bottom-center or bottom-right)
- Safe area insets respected for bottom elements (iPhone notch)
- Keyboard: chat input area slides up with virtual keyboard (resize behavior)
