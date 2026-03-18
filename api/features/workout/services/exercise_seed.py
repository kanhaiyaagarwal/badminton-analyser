"""Seed data for the exercise library — 120 exercises across all categories.

ADDING A NEW EXERCISE:
1. Add a dict to EXERCISE_SEED_DATA below with all required fields.
2. muscle_groups MUST include primary_muscle AND at least one plan-generator
   target muscle: chest, back, shoulders, biceps, triceps, quads, hamstrings,
   glutes, calves, core, rear delts. Otherwise the exercise won't appear in
   generated plans.
3. If the exercise is similar to an existing one (e.g., another deadlift
   variant), add its slug to the matching SIMILARITY_GROUPS list in
   plan_generator.py so both don't appear on the same day.
4. If the exercise supports camera tracking, add its slug to:
   - api/features/workout/services/camera_tracking.py (TRACKABLE_EXERCISES)
   - frontend/src/views/workout/session/ActiveSet.vue (TRACKABLE_SLUGS)
   - frontend/src/views/workout/session/ExerciseIntro.vue (TRACKABLE_SLUGS)
5. Optional: add a YouTube demo URL in api/database.py (_migrate_exercise_demo_video).
6. Optional: add slug to combo pools in frontend QuickStartView.vue.
"""

import logging

logger = logging.getLogger(__name__)

EXERCISE_SEED_DATA = [
    # ===== COMPOUNDS (8) =====
    {
        "name": "Bench Press",
        "slug": "bench-press",
        "category": "compound",
        "muscle_groups": ["chest", "triceps", "shoulders"],
        "primary_muscle": "chest",
        "equipment": ["barbell", "bench"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "The king of chest exercises. Lie on a flat bench and press a barbell from chest to lockout.",
        "form_cues": [
            "Retract shoulder blades and arch upper back slightly",
            "Grip slightly wider than shoulder-width",
            "Lower bar to mid-chest with elbows at ~45 degrees",
            "Drive feet into floor for stability",
            "Press bar up and slightly back toward face"
        ],
        "common_mistakes": [
            "Flaring elbows to 90 degrees — stresses shoulders",
            "Bouncing bar off chest instead of controlled touch",
            "Lifting hips off the bench"
        ],
    },
    {
        "name": "Shoulder Press",
        "slug": "shoulder-press",
        "category": "compound",
        "muscle_groups": ["shoulders", "triceps"],
        "primary_muscle": "shoulders",
        "equipment": ["barbell"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Standing or seated overhead press. Builds strong shoulders and core stability.",
        "form_cues": [
            "Start with bar at collarbone height",
            "Brace core and squeeze glutes",
            "Press bar straight up, moving head slightly back to clear the bar path",
            "Lock out overhead with bar over mid-foot"
        ],
        "common_mistakes": [
            "Excessive lower back arch — brace core harder",
            "Pressing the bar too far forward instead of straight up",
            "Using leg drive on strict press"
        ],
    },
    {
        "name": "Barbell Squat",
        "slug": "barbell-squat",
        "category": "compound",
        "muscle_groups": ["quads", "glutes", "hamstrings", "core"],
        "primary_muscle": "quads",
        "equipment": ["barbell", "squat rack"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Back squat with barbell. The fundamental lower body compound movement.",
        "form_cues": [
            "Bar on upper traps, not on neck",
            "Feet shoulder-width apart, toes slightly out",
            "Break at hips and knees simultaneously",
            "Keep chest up and knees tracking over toes",
            "Squat to at least parallel (hip crease below knee)"
        ],
        "common_mistakes": [
            "Knees caving inward — push knees out",
            "Rising hips faster than chest (good morning squat)",
            "Not hitting depth — work on ankle/hip mobility"
        ],
    },
    {
        "name": "Deadlift",
        "slug": "deadlift",
        "category": "compound",
        "muscle_groups": ["hamstrings", "glutes", "back", "core"],
        "primary_muscle": "back",
        "equipment": ["barbell"],
        "tracking_mode": "reps",
        "difficulty": "advanced",
        "description": "Conventional deadlift. Builds total body strength from the floor.",
        "form_cues": [
            "Bar over mid-foot, shins close to bar",
            "Grip just outside knees, pull slack out of bar",
            "Flat back — chest up, lats engaged",
            "Drive through the floor, hips and shoulders rise together",
            "Lock out with hips, don't hyperextend"
        ],
        "common_mistakes": [
            "Rounding lower back — use lighter weight, brace hard",
            "Starting with hips too low (turning it into a squat)",
            "Jerking the bar off the floor instead of smooth pull"
        ],
    },
    {
        "name": "Barbell Row",
        "slug": "barbell-row",
        "category": "compound",
        "muscle_groups": ["back", "biceps", "rear delts"],
        "primary_muscle": "back",
        "equipment": ["barbell"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Bent-over barbell row. Builds a thick, strong back.",
        "form_cues": [
            "Hinge at hips to ~45 degree torso angle",
            "Pull bar to lower chest / upper abdomen",
            "Squeeze shoulder blades together at the top",
            "Control the eccentric — don't just drop the weight"
        ],
        "common_mistakes": [
            "Using too much body english / momentum",
            "Standing too upright — maintain the hip hinge",
            "Pulling to belly button instead of chest"
        ],
    },
    {
        "name": "Leg Press",
        "slug": "leg-press",
        "category": "compound",
        "muscle_groups": ["quads", "glutes", "hamstrings"],
        "primary_muscle": "quads",
        "equipment": ["leg press machine"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Machine leg press. Great for building leg strength with back support.",
        "form_cues": [
            "Place feet shoulder-width on platform",
            "Lower sled until knees are at ~90 degrees",
            "Press through full foot, don't let heels lift",
            "Don't lock knees completely at the top"
        ],
        "common_mistakes": [
            "Going too deep and letting lower back round off the pad",
            "Placing feet too high or too low on platform",
            "Locking knees hard at top of movement"
        ],
    },
    {
        "name": "Romanian Deadlift",
        "slug": "romanian-deadlift",
        "category": "compound",
        "muscle_groups": ["hamstrings", "glutes", "back"],
        "primary_muscle": "hamstrings",
        "equipment": ["barbell"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Hip-hinge focused deadlift variation. Targets hamstrings and glutes.",
        "form_cues": [
            "Start standing with bar at hip height",
            "Push hips back, maintaining soft knee bend",
            "Lower bar along thighs until you feel hamstring stretch",
            "Keep back flat throughout the movement",
            "Squeeze glutes to drive hips forward at the top"
        ],
        "common_mistakes": [
            "Bending knees too much — this isn't a squat",
            "Rounding back at the bottom",
            "Going too low past knee level"
        ],
    },
    {
        "name": "Lunges",
        "slug": "lunges",
        "category": "compound",
        "muscle_groups": ["quads", "glutes", "hamstrings"],
        "primary_muscle": "quads",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Walking or stationary lunges. Builds single-leg strength and balance.",
        "form_cues": [
            "Take a controlled step forward, landing heel first",
            "Lower until both knees are at ~90 degrees",
            "Keep torso upright, core braced",
            "Front knee tracks over but not past toes",
            "Push through front heel to return"
        ],
        "common_mistakes": [
            "Knee collapsing inward on front leg",
            "Taking too short a step — not enough range of motion",
            "Leaning torso too far forward"
        ],
    },

    # ===== BODYWEIGHT (4) =====
    {
        "name": "Push-Up",
        "slug": "push-up",
        "category": "bodyweight",
        "muscle_groups": ["chest", "triceps", "shoulders", "core"],
        "primary_muscle": "chest",
        "equipment": ["none"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Classic bodyweight push-up. The foundation of upper body fitness.",
        "form_cues": [
            "Hands slightly wider than shoulders",
            "Body in straight line from head to heels",
            "Lower chest to just above the floor",
            "Elbows at ~45 degrees, not flared out",
            "Full lockout at the top"
        ],
        "common_mistakes": [
            "Sagging hips — squeeze glutes and brace core",
            "Half reps — go to full depth",
            "Flaring elbows to 90 degrees"
        ],
    },
    {
        "name": "Bodyweight Squat",
        "slug": "bodyweight-squat",
        "category": "bodyweight",
        "muscle_groups": ["quads", "glutes", "hamstrings"],
        "primary_muscle": "quads",
        "equipment": ["none"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Air squat. No equipment needed — great for warmups and high-rep work.",
        "form_cues": [
            "Feet shoulder-width, toes slightly out",
            "Arms forward for balance",
            "Sit back and down as if sitting in a chair",
            "Keep chest up, knees tracking over toes",
            "Go to at least parallel"
        ],
        "common_mistakes": [
            "Rising onto toes — keep weight on heels",
            "Knees caving inward",
            "Not going deep enough"
        ],
    },
    {
        "name": "Plank",
        "slug": "plank",
        "category": "bodyweight",
        "muscle_groups": ["core", "shoulders"],
        "primary_muscle": "core",
        "equipment": ["none"],
        "tracking_mode": "hold",
        "difficulty": "beginner",
        "description": "Isometric core hold. Builds core endurance and stability.",
        "form_cues": [
            "Forearms on ground, elbows under shoulders",
            "Body in straight line from head to heels",
            "Squeeze glutes and brace abs",
            "Don't let hips sag or pike up",
            "Breathe steadily — don't hold your breath"
        ],
        "common_mistakes": [
            "Hips sagging toward floor",
            "Piking hips too high",
            "Holding breath instead of breathing normally"
        ],
    },
    {
        "name": "Mountain Climber",
        "slug": "mountain-climber",
        "category": "bodyweight",
        "muscle_groups": ["core", "shoulders", "quads"],
        "primary_muscle": "core",
        "equipment": ["none"],
        "tracking_mode": "timed",
        "difficulty": "beginner",
        "description": "Dynamic plank variation. High-intensity core and cardio exercise.",
        "form_cues": [
            "Start in high plank position",
            "Drive one knee toward chest at a time",
            "Keep hips level — don't bounce up and down",
            "Maintain tight core throughout"
        ],
        "common_mistakes": [
            "Hips bouncing up and down",
            "Not fully extending the back leg",
            "Going too fast and losing form"
        ],
    },

    # ===== ISOLATION (6) =====
    {
        "name": "Bicep Curl",
        "slug": "bicep-curl",
        "category": "isolation",
        "muscle_groups": ["biceps"],
        "primary_muscle": "biceps",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Standing dumbbell curl. The classic arm builder.",
        "form_cues": [
            "Stand tall, elbows pinned to sides",
            "Curl weight up with controlled motion",
            "Squeeze biceps at the top",
            "Lower slowly — don't just drop the weight"
        ],
        "common_mistakes": [
            "Swinging the body for momentum",
            "Moving elbows forward during the curl",
            "Not controlling the negative"
        ],
    },
    {
        "name": "Tricep Pushdown",
        "slug": "tricep-pushdown",
        "category": "isolation",
        "muscle_groups": ["triceps"],
        "primary_muscle": "triceps",
        "equipment": ["cable machine"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Cable rope or bar pushdown. Isolates the triceps for arm development.",
        "form_cues": [
            "Stand close to cable, slight forward lean",
            "Elbows pinned to sides throughout",
            "Extend arms fully, squeezing triceps at bottom",
            "Control the return — don't let cable yank hands up"
        ],
        "common_mistakes": [
            "Elbows drifting forward or flaring out",
            "Using too much weight and compensating with body",
            "Not fully locking out at the bottom"
        ],
    },
    {
        "name": "Lateral Raise",
        "slug": "lateral-raise",
        "category": "isolation",
        "muscle_groups": ["shoulders"],
        "primary_muscle": "shoulders",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Dumbbell lateral raise. Builds wider shoulders and capped delts.",
        "form_cues": [
            "Stand with dumbbells at sides, slight elbow bend",
            "Raise arms out to sides until parallel with floor",
            "Lead with elbows, not hands",
            "Lower with control — 2-3 second eccentric"
        ],
        "common_mistakes": [
            "Using momentum / swinging the weight up",
            "Raising dumbbells too high (above shoulder level)",
            "Shrugging traps up during the lift"
        ],
    },
    {
        "name": "Cable Fly",
        "slug": "cable-fly",
        "category": "isolation",
        "muscle_groups": ["chest"],
        "primary_muscle": "chest",
        "equipment": ["cable machine"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Cable crossover / fly. Constant tension for chest isolation.",
        "form_cues": [
            "Set cables at chest height",
            "Step forward for slight stretch at start",
            "Bring hands together in a hugging arc motion",
            "Squeeze chest hard at peak contraction"
        ],
        "common_mistakes": [
            "Bending arms too much — keep the arc shape",
            "Using too much weight and turning it into a press",
            "Not getting full stretch at the start position"
        ],
    },
    {
        "name": "Leg Curl",
        "slug": "leg-curl",
        "category": "isolation",
        "muscle_groups": ["hamstrings"],
        "primary_muscle": "hamstrings",
        "equipment": ["leg curl machine"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Lying or seated leg curl. Isolates the hamstrings.",
        "form_cues": [
            "Adjust pad to sit just above heels",
            "Curl weight up by bending knees",
            "Squeeze hamstrings at the top",
            "Lower with slow control"
        ],
        "common_mistakes": [
            "Lifting hips off the pad during the curl",
            "Using momentum to swing the weight",
            "Not going through full range of motion"
        ],
    },
    {
        "name": "Calf Raise",
        "slug": "calf-raise",
        "category": "isolation",
        "muscle_groups": ["calves"],
        "primary_muscle": "calves",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Standing calf raise. Builds calf size and ankle strength.",
        "form_cues": [
            "Stand on edge of step for full range of motion",
            "Rise up on toes as high as possible",
            "Pause and squeeze at the top",
            "Lower slowly below the step for full stretch"
        ],
        "common_mistakes": [
            "Bouncing at the bottom without pausing",
            "Not going through full range of motion",
            "Bending knees during the movement"
        ],
    },

    # ===== COMPOUND (batch 2) =====
    {
        "name": "Pull-Up",
        "slug": "pull-up",
        "category": "compound",
        "muscle_groups": ["back", "biceps", "core"],
        "primary_muscle": "back",
        "equipment": ["pull-up bar"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Overhand grip pull-up. The ultimate bodyweight back builder.",
        "form_cues": [
            "Grip bar slightly wider than shoulder-width, palms facing away",
            "Start from dead hang with arms fully extended",
            "Pull until chin clears the bar, driving elbows down",
            "Lower with control — full range of motion"
        ],
        "common_mistakes": [
            "Kipping or swinging for momentum",
            "Half reps — not going to full hang at the bottom",
            "Craning neck over bar instead of pulling chest up"
        ],
    },
    {
        "name": "Hip Thrust",
        "slug": "hip-thrust",
        "category": "compound",
        "muscle_groups": ["glutes", "hamstrings"],
        "primary_muscle": "glutes",
        "equipment": ["barbell", "bench"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Barbell hip thrust. The best exercise for glute strength and size.",
        "form_cues": [
            "Upper back on bench, feet flat on floor hip-width apart",
            "Roll barbell over hips with pad for comfort",
            "Drive hips up until torso is parallel to floor",
            "Squeeze glutes hard at the top, hold briefly",
            "Lower under control — don't drop"
        ],
        "common_mistakes": [
            "Hyperextending lower back at the top",
            "Feet too far from or too close to bench",
            "Pushing through toes instead of heels"
        ],
    },
    {
        "name": "Incline Bench Press",
        "slug": "incline-bench-press",
        "category": "compound",
        "muscle_groups": ["chest", "shoulders", "triceps"],
        "primary_muscle": "chest",
        "equipment": ["barbell", "bench"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Incline barbell press at 30-45 degrees. Targets upper chest.",
        "form_cues": [
            "Set bench to 30-45 degree angle",
            "Grip slightly wider than shoulder-width",
            "Lower bar to upper chest / collarbone area",
            "Press up and slightly back",
            "Keep shoulder blades retracted"
        ],
        "common_mistakes": [
            "Bench angle too steep — turns into a shoulder press",
            "Flaring elbows out to 90 degrees",
            "Lifting hips off the bench"
        ],
    },
    {
        "name": "Dips",
        "slug": "dips",
        "category": "compound",
        "muscle_groups": ["chest", "triceps", "shoulders"],
        "primary_muscle": "chest",
        "equipment": ["dip bars"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Parallel bar dips. Builds chest and triceps with bodyweight.",
        "form_cues": [
            "Grip bars, arms straight, body slightly forward",
            "Lower until upper arms are parallel to floor",
            "Lean forward slightly for chest emphasis, upright for triceps",
            "Press up to full lockout"
        ],
        "common_mistakes": [
            "Going too deep — stresses shoulders",
            "Swinging legs for momentum",
            "Not controlling the descent"
        ],
    },
    {
        "name": "Kettlebell Swing",
        "slug": "kettlebell-swing",
        "category": "compound",
        "muscle_groups": ["glutes", "hamstrings", "core", "shoulders"],
        "primary_muscle": "glutes",
        "equipment": ["kettlebell"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Russian kettlebell swing. Explosive hip hinge for power and conditioning.",
        "form_cues": [
            "Feet shoulder-width apart, kettlebell slightly in front",
            "Hike bell between legs with hip hinge",
            "Snap hips forward explosively to swing bell to chest height",
            "Arms are just along for the ride — power comes from hips",
            "Control the backswing, don't round your back"
        ],
        "common_mistakes": [
            "Squatting instead of hinging — keep shins vertical",
            "Using arms to lift the bell instead of hip drive",
            "Hyperextending back at the top"
        ],
    },

    # ===== BODYWEIGHT (batch 2) =====
    {
        "name": "Burpee",
        "slug": "burpee",
        "category": "bodyweight",
        "muscle_groups": ["full body", "chest", "quads", "core"],
        "primary_muscle": "full body",
        "equipment": ["none"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Full burpee with push-up and jump. Total body conditioning.",
        "form_cues": [
            "Start standing, drop hands to floor",
            "Jump or step feet back to plank",
            "Perform a push-up, then jump feet to hands",
            "Explode up with a jump and clap overhead"
        ],
        "common_mistakes": [
            "Skipping the push-up — full range of motion",
            "Snaking up from the floor instead of a clean push-up",
            "Landing with locked knees on the jump"
        ],
    },
    {
        "name": "Crunch",
        "slug": "crunch",
        "category": "bodyweight",
        "muscle_groups": ["core"],
        "primary_muscle": "core",
        "equipment": ["none"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Basic abdominal crunch. Isolates the upper abs.",
        "form_cues": [
            "Lie on back, knees bent, feet flat on floor",
            "Hands behind head or crossed on chest",
            "Curl shoulders off floor by contracting abs",
            "Hold briefly at the top, lower with control"
        ],
        "common_mistakes": [
            "Pulling on neck with hands",
            "Using momentum to swing up",
            "Coming up too high — it's a curl, not a sit-up"
        ],
    },
    {
        "name": "Russian Twist",
        "slug": "russian-twist",
        "category": "bodyweight",
        "muscle_groups": ["core", "obliques"],
        "primary_muscle": "core",
        "equipment": ["none"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Seated twist for obliques. Can be done with or without weight.",
        "form_cues": [
            "Sit with knees bent, lean back to ~45 degrees",
            "Lift feet slightly off floor for extra challenge",
            "Rotate torso side to side, touching floor beside hips",
            "Keep core tight and move with control"
        ],
        "common_mistakes": [
            "Moving just the arms without rotating torso",
            "Rounding the back — maintain neutral spine",
            "Going too fast and losing control"
        ],
    },
    {
        "name": "Hanging Leg Raise",
        "slug": "hanging-leg-raise",
        "category": "bodyweight",
        "muscle_groups": ["core", "hip flexors"],
        "primary_muscle": "core",
        "equipment": ["pull-up bar"],
        "tracking_mode": "reps",
        "difficulty": "intermediate",
        "description": "Hang from a bar and raise legs. Builds lower abs and grip strength.",
        "form_cues": [
            "Hang from bar with overhand grip, arms straight",
            "Raise legs until parallel or higher",
            "Control the descent — don't swing",
            "Keep slight posterior pelvic tilt to target abs"
        ],
        "common_mistakes": [
            "Swinging and using momentum",
            "Only raising knees instead of straight legs",
            "Dropping legs uncontrolled"
        ],
    },
    {
        "name": "Jump Rope",
        "slug": "jump-rope",
        "category": "bodyweight",
        "muscle_groups": ["calves", "shoulders", "core"],
        "primary_muscle": "calves",
        "equipment": ["jump rope"],
        "tracking_mode": "timed",
        "difficulty": "beginner",
        "description": "Jump rope for cardio and coordination. Great warm-up or finisher.",
        "form_cues": [
            "Keep elbows close to body, rotate from wrists",
            "Jump just high enough to clear the rope",
            "Stay on balls of feet, soft knees",
            "Maintain steady breathing rhythm"
        ],
        "common_mistakes": [
            "Jumping too high — wastes energy",
            "Using arms to swing rope instead of wrists",
            "Landing flat-footed"
        ],
    },

    # ===== ISOLATION (batch 2) =====
    {
        "name": "Face Pull",
        "slug": "face-pull",
        "category": "isolation",
        "muscle_groups": ["rear delts", "rotator cuff", "traps"],
        "primary_muscle": "rear delts",
        "equipment": ["cable machine"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Cable face pull. Essential for shoulder health and posture.",
        "form_cues": [
            "Set cable at upper chest height with rope attachment",
            "Pull rope toward face, separating ends past ears",
            "Squeeze shoulder blades together, externally rotate",
            "Hold the contraction for a second"
        ],
        "common_mistakes": [
            "Using too much weight and leaning back",
            "Pulling to chest instead of face",
            "Not externally rotating at the end"
        ],
    },
    {
        "name": "Glute Kickback",
        "slug": "glute-kickback",
        "category": "isolation",
        "muscle_groups": ["glutes"],
        "primary_muscle": "glutes",
        "equipment": ["cable machine"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Cable or bodyweight glute kickback. Isolates the glutes.",
        "form_cues": [
            "On all fours or standing at cable machine",
            "Extend one leg straight back, squeezing glute",
            "Don't arch lower back — keep core tight",
            "Control the return, don't swing"
        ],
        "common_mistakes": [
            "Arching lower back to get more range",
            "Swinging the leg with momentum",
            "Not squeezing the glute at the top"
        ],
    },
    {
        "name": "Reverse Fly",
        "slug": "reverse-fly",
        "category": "isolation",
        "muscle_groups": ["rear delts", "upper back"],
        "primary_muscle": "rear delts",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Bent-over or seated reverse dumbbell fly. Targets rear delts.",
        "form_cues": [
            "Hinge forward at hips with flat back",
            "Arms hanging below with slight elbow bend",
            "Raise arms out to sides, squeezing shoulder blades",
            "Lower with control — 2-3 second eccentric"
        ],
        "common_mistakes": [
            "Using too much weight and swinging",
            "Straightening arms fully — keep slight bend",
            "Not hinging forward enough"
        ],
    },
    {
        "name": "Hammer Curl",
        "slug": "hammer-curl",
        "category": "isolation",
        "muscle_groups": ["biceps", "forearms"],
        "primary_muscle": "biceps",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Neutral-grip dumbbell curl. Targets the brachialis and forearms.",
        "form_cues": [
            "Stand tall with palms facing each other (neutral grip)",
            "Curl weight up keeping thumbs on top",
            "Keep elbows pinned to sides",
            "Lower slowly and controlled"
        ],
        "common_mistakes": [
            "Swinging the body for momentum",
            "Rotating wrists during the curl",
            "Not controlling the negative"
        ],
    },
    {
        "name": "Overhead Tricep Extension",
        "slug": "overhead-tricep-extension",
        "category": "isolation",
        "muscle_groups": ["triceps"],
        "primary_muscle": "triceps",
        "equipment": ["dumbbells"],
        "tracking_mode": "reps",
        "difficulty": "beginner",
        "description": "Seated or standing overhead tricep extension with dumbbell.",
        "form_cues": [
            "Hold dumbbell overhead with both hands",
            "Lower weight behind head by bending elbows",
            "Keep upper arms close to ears, elbows pointing up",
            "Extend arms fully, squeezing triceps"
        ],
        "common_mistakes": [
            "Flaring elbows out to sides",
            "Arching lower back — brace core",
            "Using too heavy a weight and losing control"
        ],
    },

    # ===== FLEXIBILITY / RECOVERY =====
    {
        "name": "Hip Flexor Stretch",
        "slug": "hip-flexor-stretch",
        "category": "cardio",
        "muscle_groups": ["hip flexors", "quads"],
        "primary_muscle": "hip flexors",
        "equipment": ["none"],
        "tracking_mode": "hold",
        "difficulty": "beginner",
        "description": "Kneeling or standing hip flexor stretch. Essential for desk workers.",
        "form_cues": [
            "Kneel on one knee, front foot flat on floor",
            "Push hips forward gently until you feel a stretch",
            "Keep torso upright, core braced",
            "Hold 30-60 seconds each side"
        ],
        "common_mistakes": [
            "Leaning torso forward instead of staying upright",
            "Not pushing hips far enough forward",
            "Bouncing instead of holding steady"
        ],
    },
    {
        "name": "Foam Roll / Child's Pose",
        "slug": "foam-roll",
        "category": "cardio",
        "muscle_groups": ["full body"],
        "primary_muscle": "full body",
        "equipment": ["yoga mat"],
        "tracking_mode": "timed",
        "difficulty": "beginner",
        "description": "Recovery and cooldown. Foam rolling and child's pose for flexibility.",
        "form_cues": [
            "Roll slowly over tight areas, pausing on tender spots",
            "For child's pose: kneel, sit back on heels, arms extended forward",
            "Breathe deeply and relax into each position",
            "Spend 1-2 minutes per muscle group"
        ],
        "common_mistakes": [
            "Rolling too fast — go slow to release tension",
            "Rolling directly on joints or bones",
            "Holding breath instead of breathing through it"
        ],
    },

    # ===== LEGS — QUADS (batch 3) =====
    {
        "name": "Bulgarian Split Squat", "slug": "bulgarian-split-squat", "category": "compound",
        "muscle_groups": ["quads", "glutes"], "primary_muscle": "quads",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Single-leg squat with rear foot elevated. Builds quad strength and balance.",
        "form_cues": ["Rear foot on bench, front foot 2-3 feet ahead", "Lower until front thigh is parallel", "Keep torso upright, core tight", "Drive through front heel"],
        "common_mistakes": ["Front foot too close to bench", "Knee caving inward", "Leaning torso too far forward"],
    },
    {
        "name": "Front Squat", "slug": "front-squat", "category": "compound",
        "muscle_groups": ["quads", "core", "glutes"], "primary_muscle": "quads",
        "equipment": ["barbell", "squat rack"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Barbell front squat. More quad-dominant than back squat, demands core stability.",
        "form_cues": ["Bar in front rack position on shoulders", "Elbows high, upper arms parallel to floor", "Sit straight down, knees forward over toes", "Keep torso as upright as possible"],
        "common_mistakes": ["Elbows dropping — lose the bar forward", "Not hitting depth", "Rounding upper back"],
    },
    {
        "name": "Hack Squat", "slug": "hack-squat", "category": "compound",
        "muscle_groups": ["quads", "glutes"], "primary_muscle": "quads",
        "equipment": ["hack squat machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Machine hack squat. Safe way to load quads heavily with back support.",
        "form_cues": ["Back flat against pad, shoulders under pads", "Feet shoulder-width on platform", "Lower until knees at 90 degrees", "Press through full foot"],
        "common_mistakes": ["Heels lifting off platform", "Knees caving inward", "Not going deep enough"],
    },
    {
        "name": "Leg Extension", "slug": "leg-extension", "category": "isolation",
        "muscle_groups": ["quads"], "primary_muscle": "quads",
        "equipment": ["leg extension machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Machine leg extension. Isolates the quadriceps.",
        "form_cues": ["Adjust pad to sit on lower shin", "Extend legs fully, squeezing quads", "Lower with control — 2-3 seconds", "Don't swing or use momentum"],
        "common_mistakes": ["Using momentum to swing weight up", "Not fully extending", "Going too heavy and stressing knees"],
    },
    {
        "name": "Step-Up", "slug": "step-up", "category": "compound",
        "muscle_groups": ["quads", "glutes"], "primary_muscle": "quads",
        "equipment": ["dumbbells", "box"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Dumbbell step-up onto box or bench. Builds single-leg strength.",
        "form_cues": ["Place entire foot on box", "Drive through top foot to stand up", "Don't push off the bottom foot", "Control the step down"],
        "common_mistakes": ["Box too high — start lower", "Pushing off rear foot for momentum", "Leaning forward excessively"],
    },
    {
        "name": "Box Jump", "slug": "box-jump", "category": "bodyweight",
        "muscle_groups": ["quads", "glutes", "calves"], "primary_muscle": "quads",
        "equipment": ["box"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Explosive jump onto a box. Builds lower body power.",
        "form_cues": ["Stand facing box, feet hip-width", "Swing arms and jump explosively", "Land softly on top of box with both feet", "Stand up fully, then step down"],
        "common_mistakes": ["Landing too hard — absorb with knees", "Stepping down backward — turn and step", "Box too high for your ability"],
    },
    {
        "name": "Jump Squat", "slug": "jump-squat", "category": "bodyweight",
        "muscle_groups": ["quads", "glutes", "calves"], "primary_muscle": "quads",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Bodyweight squat with explosive jump at the top. Builds power.",
        "form_cues": ["Squat down to parallel", "Explode up into a jump", "Land softly with bent knees", "Immediately flow into next rep"],
        "common_mistakes": ["Landing with locked knees", "Not squatting deep enough", "Poor landing mechanics"],
    },
    {
        "name": "Wall Sit", "slug": "wall-sit", "category": "bodyweight",
        "muscle_groups": ["quads"], "primary_muscle": "quads",
        "equipment": ["none"], "tracking_mode": "hold", "difficulty": "beginner",
        "description": "Isometric wall sit. Builds quad endurance.",
        "form_cues": ["Back flat against wall, slide down to 90 degrees", "Knees over ankles, shins vertical", "Keep core tight, breathe steadily", "Hold position as long as possible"],
        "common_mistakes": ["Thighs not reaching parallel", "Hands on knees for support", "Letting hips slide down too low"],
    },
    {
        "name": "Sumo Squat", "slug": "sumo-squat", "category": "compound",
        "muscle_groups": ["quads", "glutes", "inner thighs"], "primary_muscle": "quads",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Wide-stance squat targeting inner thighs and glutes.",
        "form_cues": ["Feet wider than shoulder-width, toes pointed out 45 degrees", "Hold dumbbell between legs", "Squat straight down, knees tracking over toes", "Squeeze glutes at the top"],
        "common_mistakes": ["Knees caving inward", "Leaning forward instead of staying upright", "Not going deep enough"],
    },
    {
        "name": "Sissy Squat", "slug": "sissy-squat", "category": "bodyweight",
        "muscle_groups": ["quads"], "primary_muscle": "quads",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Advanced quad isolation. Lean back while squatting on toes.",
        "form_cues": ["Hold onto support for balance", "Rise onto toes, lean torso back", "Bend knees deeply while keeping hips extended", "Return by driving through toes"],
        "common_mistakes": ["Bending at the hips instead of keeping them extended", "Going too deep too fast", "Not having balance support"],
    },

    # ===== LEGS — GLUTES =====
    {
        "name": "Glute Bridge", "slug": "glute-bridge", "category": "bodyweight",
        "muscle_groups": ["glutes", "hamstrings"], "primary_muscle": "glutes",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Bodyweight glute bridge. Great activation exercise and beginner hip thrust.",
        "form_cues": ["Lie on back, knees bent, feet flat on floor", "Drive hips up by squeezing glutes", "Hold at top for a second", "Lower with control"],
        "common_mistakes": ["Pushing through toes instead of heels", "Hyperextending lower back", "Not squeezing glutes at top"],
    },
    {
        "name": "Sumo Deadlift", "slug": "sumo-deadlift", "category": "compound",
        "muscle_groups": ["glutes", "quads", "hamstrings"], "primary_muscle": "glutes",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Wide-stance deadlift. More glute and quad emphasis than conventional.",
        "form_cues": ["Wide stance, toes pointed out", "Grip bar inside knees", "Push knees out, chest up", "Drive through the floor, lock hips at top"],
        "common_mistakes": ["Hips shooting up first", "Knees caving inward", "Rounding the back"],
    },
    {
        "name": "Fire Hydrant", "slug": "fire-hydrant", "category": "bodyweight",
        "muscle_groups": ["glutes"], "primary_muscle": "glutes",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "On all fours, lift knee out to the side. Targets glute medius.",
        "form_cues": ["On all fours, hands under shoulders, knees under hips", "Lift one knee out to the side keeping 90 degree bend", "Squeeze glute at the top", "Lower with control"],
        "common_mistakes": ["Rotating torso — keep hips square", "Lifting too high and losing form", "Rushing reps"],
    },
    {
        "name": "Donkey Kick", "slug": "donkey-kick", "category": "bodyweight",
        "muscle_groups": ["glutes"], "primary_muscle": "glutes",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "On all fours, kick one leg back and up. Targets glute max.",
        "form_cues": ["On all fours, core tight", "Kick one leg back and up, keeping knee bent 90 degrees", "Squeeze glute at the top", "Don't arch lower back"],
        "common_mistakes": ["Arching the lower back", "Swinging the leg with momentum", "Not squeezing at the top"],
    },
    {
        "name": "Abductor Machine", "slug": "abductor-machine", "category": "isolation",
        "muscle_groups": ["glutes", "outer thighs"], "primary_muscle": "glutes",
        "equipment": ["abductor machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Machine hip abduction. Targets outer glutes and thighs.",
        "form_cues": ["Sit with pads on outer thighs", "Push legs apart against resistance", "Squeeze and hold briefly", "Return with control"],
        "common_mistakes": ["Using momentum", "Leaning forward", "Going too heavy"],
    },
    {
        "name": "Adductor Machine", "slug": "adductor-machine", "category": "isolation",
        "muscle_groups": ["inner thighs"], "primary_muscle": "inner thighs",
        "equipment": ["adductor machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Machine hip adduction. Targets inner thigh muscles.",
        "form_cues": ["Sit with pads on inner thighs", "Squeeze legs together against resistance", "Hold briefly at the close", "Open with control"],
        "common_mistakes": ["Using too much weight", "Jerky movements", "Not controlling the eccentric"],
    },

    # ===== LEGS — HAMSTRINGS =====
    {
        "name": "Nordic Curl", "slug": "nordic-curl", "category": "bodyweight",
        "muscle_groups": ["hamstrings"], "primary_muscle": "hamstrings",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Eccentric hamstring exercise. One of the best for injury prevention.",
        "form_cues": ["Kneel with feet anchored behind you", "Lower body forward slowly with control", "Use hamstrings to resist gravity", "Catch yourself with hands, push back up"],
        "common_mistakes": ["Falling forward uncontrolled", "Bending at the hips instead of staying straight", "Not going slow enough on the eccentric"],
    },
    {
        "name": "Good Morning", "slug": "good-morning", "category": "compound",
        "muscle_groups": ["hamstrings", "glutes", "back"], "primary_muscle": "hamstrings",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Barbell good morning. Hip hinge movement for posterior chain.",
        "form_cues": ["Bar on upper back like a squat", "Soft knee bend, hinge forward at hips", "Lower torso until roughly parallel to floor", "Drive hips forward to stand up"],
        "common_mistakes": ["Rounding the back", "Going too heavy before mastering form", "Bending knees too much"],
    },
    {
        "name": "Seated Leg Curl", "slug": "seated-leg-curl", "category": "isolation",
        "muscle_groups": ["hamstrings"], "primary_muscle": "hamstrings",
        "equipment": ["seated leg curl machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Seated hamstring curl machine. Isolates hamstrings in a seated position.",
        "form_cues": ["Adjust pad to sit above heels", "Curl weight down by bending knees", "Squeeze hamstrings at bottom", "Return with control"],
        "common_mistakes": ["Using momentum", "Not going through full range", "Lifting hips off seat"],
    },
    {
        "name": "Stiff-Leg Deadlift", "slug": "stiff-leg-deadlift", "category": "compound",
        "muscle_groups": ["hamstrings", "glutes", "back"], "primary_muscle": "hamstrings",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Deadlift with minimal knee bend. Maximum hamstring stretch.",
        "form_cues": ["Stand with bar at hip height, legs nearly straight", "Hinge forward keeping legs almost locked", "Lower bar along legs until deep hamstring stretch", "Drive hips forward to return"],
        "common_mistakes": ["Rounding the lower back", "Bending knees too much — keep them nearly straight", "Jerking the weight up"],
    },

    # ===== LEGS — CALVES =====
    {
        "name": "Seated Calf Raise", "slug": "seated-calf-raise", "category": "isolation",
        "muscle_groups": ["calves"], "primary_muscle": "calves",
        "equipment": ["seated calf raise machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Seated calf raise. Targets the soleus muscle (inner calf).",
        "form_cues": ["Sit with pads on lower thighs", "Push up on toes as high as possible", "Pause at the top", "Lower slowly for full stretch"],
        "common_mistakes": ["Bouncing at the bottom", "Not going through full range", "Going too fast"],
    },
    {
        "name": "Single-Leg Calf Raise", "slug": "single-leg-calf-raise", "category": "bodyweight",
        "muscle_groups": ["calves"], "primary_muscle": "calves",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "One-leg calf raise for balanced development. Hold wall for support.",
        "form_cues": ["Stand on one leg on edge of step", "Rise up as high as possible", "Pause and squeeze", "Lower slowly below step level"],
        "common_mistakes": ["Not using full range of motion", "Going too fast", "Not balancing properly"],
    },
    {
        "name": "Donkey Calf Raise", "slug": "donkey-calf-raise", "category": "isolation",
        "muscle_groups": ["calves"], "primary_muscle": "calves",
        "equipment": ["machine"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Donkey calf raise. Deep stretch position for maximum calf development.",
        "form_cues": ["Bend at hips with pad on lower back", "Feet on edge of platform", "Rise up on toes fully", "Lower for deep stretch"],
        "common_mistakes": ["Not getting full stretch at bottom", "Bouncing reps", "Rounding the back"],
    },

    # ===== BACK =====
    {
        "name": "Chin-Up", "slug": "chin-up", "category": "compound",
        "muscle_groups": ["back", "biceps"], "primary_muscle": "back",
        "equipment": ["pull-up bar"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Underhand grip pull-up. More bicep involvement than pull-ups.",
        "form_cues": ["Grip bar with palms facing you, shoulder-width", "Pull chin over bar", "Squeeze back and biceps at top", "Lower with full control"],
        "common_mistakes": ["Kipping for momentum", "Half reps", "Not going to full hang at bottom"],
    },
    {
        "name": "Lat Pulldown", "slug": "lat-pulldown", "category": "compound",
        "muscle_groups": ["back", "biceps"], "primary_muscle": "back",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Cable lat pulldown. Great for building pull-up strength.",
        "form_cues": ["Grip bar slightly wider than shoulders", "Pull bar to upper chest", "Squeeze shoulder blades together", "Control the return — don't let it yank you up"],
        "common_mistakes": ["Leaning too far back", "Pulling bar behind neck — dangerous", "Using momentum"],
    },
    {
        "name": "Single-Arm Dumbbell Row", "slug": "single-arm-dumbbell-row", "category": "compound",
        "muscle_groups": ["back", "biceps"], "primary_muscle": "back",
        "equipment": ["dumbbells", "bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "One-arm dumbbell row on bench. Unilateral back builder.",
        "form_cues": ["One hand and knee on bench for support", "Pull dumbbell to hip, elbow driving back", "Squeeze shoulder blade at top", "Lower with control"],
        "common_mistakes": ["Rotating torso to heave weight up", "Pulling to chest instead of hip", "Not controlling the negative"],
    },
    {
        "name": "T-Bar Row", "slug": "t-bar-row", "category": "compound",
        "muscle_groups": ["back", "biceps", "rear delts"], "primary_muscle": "back",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "T-bar row for thick back development. Landmine or machine variation.",
        "form_cues": ["Straddle bar, grip close-grip handle", "Hinge at hips, flat back", "Pull bar to chest", "Squeeze back, lower with control"],
        "common_mistakes": ["Standing too upright", "Rounding the back", "Using too much momentum"],
    },
    {
        "name": "Seated Cable Row", "slug": "seated-cable-row", "category": "compound",
        "muscle_groups": ["back", "biceps"], "primary_muscle": "back",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Seated cable row with close-grip handle. Builds mid-back thickness.",
        "form_cues": ["Sit with chest up, slight knee bend", "Pull handle to lower chest/abdomen", "Squeeze shoulder blades together", "Return with control — don't let it yank you forward"],
        "common_mistakes": ["Rocking back and forth for momentum", "Rounding shoulders forward", "Not squeezing at the contraction"],
    },
    {
        "name": "Chest-Supported Row", "slug": "chest-supported-row", "category": "compound",
        "muscle_groups": ["back", "rear delts"], "primary_muscle": "back",
        "equipment": ["dumbbells", "bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Row with chest on incline bench. Eliminates cheating and lower back strain.",
        "form_cues": ["Lie face down on incline bench", "Let arms hang with dumbbells", "Row both dumbbells up, squeezing shoulder blades", "Lower with control"],
        "common_mistakes": ["Lifting chest off bench to cheat", "Not squeezing at the top", "Going too heavy"],
    },
    {
        "name": "Pendlay Row", "slug": "pendlay-row", "category": "compound",
        "muscle_groups": ["back", "biceps"], "primary_muscle": "back",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Strict barbell row from floor each rep. Builds explosive back strength.",
        "form_cues": ["Bar on floor, torso parallel to ground", "Pull bar explosively to lower chest", "Lower bar to floor each rep — dead stop", "Keep back flat throughout"],
        "common_mistakes": ["Not staying parallel to floor", "Using body english", "Not returning bar to floor each rep"],
    },

    # ===== LOWER BACK =====
    {
        "name": "Hyperextension", "slug": "hyperextension", "category": "isolation",
        "muscle_groups": ["lower back", "glutes"], "primary_muscle": "lower back",
        "equipment": ["hyperextension bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Back extension on Roman chair. Strengthens the lower back.",
        "form_cues": ["Lock feet, hips on pad", "Lower torso toward floor with control", "Rise up until body is straight — don't hyperextend", "Squeeze glutes at the top"],
        "common_mistakes": ["Hyperextending past neutral spine", "Going too fast", "Rounding the back at the bottom"],
    },
    {
        "name": "Superman", "slug": "superman", "category": "bodyweight",
        "muscle_groups": ["lower back", "glutes"], "primary_muscle": "lower back",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Lie face down, lift arms and legs simultaneously. Bodyweight back extension.",
        "form_cues": ["Lie face down, arms extended overhead", "Lift arms, chest, and legs off floor simultaneously", "Hold for 2-3 seconds at the top", "Lower with control"],
        "common_mistakes": ["Jerking up too fast", "Not holding at the top", "Straining the neck"],
    },

    # ===== CHEST (batch 3) =====
    {
        "name": "Decline Bench Press", "slug": "decline-bench-press", "category": "compound",
        "muscle_groups": ["chest", "triceps"], "primary_muscle": "chest",
        "equipment": ["barbell", "decline bench"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Decline barbell press. Targets lower chest fibers.",
        "form_cues": ["Set bench to 15-30 degree decline", "Grip slightly wider than shoulders", "Lower bar to lower chest", "Press up to lockout"],
        "common_mistakes": ["Decline too steep", "Bouncing off chest", "No spotter on heavy sets"],
    },
    {
        "name": "Incline Dumbbell Press", "slug": "incline-dumbbell-press", "category": "compound",
        "muscle_groups": ["chest", "shoulders", "triceps"], "primary_muscle": "chest",
        "equipment": ["dumbbells", "bench"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Incline dumbbell press. Greater range of motion than barbell for upper chest.",
        "form_cues": ["Set bench to 30-45 degrees", "Start with dumbbells at chest level", "Press up and together in an arc", "Lower with control to deep stretch"],
        "common_mistakes": ["Bench too steep", "Not going deep enough", "Dumbbells drifting too far apart"],
    },
    {
        "name": "Dumbbell Fly", "slug": "dumbbell-fly", "category": "isolation",
        "muscle_groups": ["chest"], "primary_muscle": "chest",
        "equipment": ["dumbbells", "bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Flat bench dumbbell fly. Chest isolation with deep stretch.",
        "form_cues": ["Lie on flat bench, dumbbells above chest", "Lower arms in wide arc with slight elbow bend", "Feel deep chest stretch at bottom", "Squeeze chest to bring dumbbells back together"],
        "common_mistakes": ["Going too heavy — this is an isolation exercise", "Straightening arms — keep slight bend", "Lowering too fast"],
    },
    {
        "name": "Incline Dumbbell Fly", "slug": "incline-dumbbell-fly", "category": "isolation",
        "muscle_groups": ["chest"], "primary_muscle": "chest",
        "equipment": ["dumbbells", "bench"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Incline fly for upper chest isolation.",
        "form_cues": ["Incline bench at 30-45 degrees", "Dumbbells above upper chest", "Lower in wide arc, feeling upper chest stretch", "Squeeze back together at top"],
        "common_mistakes": ["Bench too steep", "Too much weight — use light dumbbells", "Turning it into a press"],
    },
    {
        "name": "Diamond Push-Up", "slug": "diamond-push-up", "category": "bodyweight",
        "muscle_groups": ["chest", "triceps"], "primary_muscle": "chest",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Push-up with hands together in diamond shape. Targets inner chest and triceps.",
        "form_cues": ["Hands together forming a diamond under chest", "Lower chest to hands", "Keep elbows close to body", "Press up to lockout"],
        "common_mistakes": ["Flaring elbows wide", "Hips sagging", "Not touching chest to hands"],
    },
    {
        "name": "Wide-Grip Push-Up", "slug": "wide-grip-push-up", "category": "bodyweight",
        "muscle_groups": ["chest", "shoulders"], "primary_muscle": "chest",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Push-up with hands wider than shoulder-width. More chest emphasis.",
        "form_cues": ["Hands 1.5x shoulder-width apart", "Lower chest to floor", "Keep core tight, body straight", "Press up fully"],
        "common_mistakes": ["Hands too wide — stresses shoulders", "Sagging hips", "Half reps"],
    },
    {
        "name": "Pec Deck Machine", "slug": "pec-deck", "category": "isolation",
        "muscle_groups": ["chest"], "primary_muscle": "chest",
        "equipment": ["pec deck machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Machine chest fly. Constant tension for chest isolation.",
        "form_cues": ["Sit with back flat against pad", "Arms on pads at chest height", "Bring pads together, squeezing chest", "Return with control"],
        "common_mistakes": ["Using too much weight", "Shrugging shoulders", "Not squeezing at peak contraction"],
    },
    {
        "name": "Cable Crossover", "slug": "cable-crossover", "category": "isolation",
        "muscle_groups": ["chest"], "primary_muscle": "chest",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "High-to-low or low-to-high cable crossover for chest definition.",
        "form_cues": ["Set cables at desired height", "Step forward, slight lean", "Bring hands together in sweeping arc", "Squeeze chest at peak, control the return"],
        "common_mistakes": ["Using too much weight and pulling with arms", "Not getting full stretch", "Standing too far back"],
    },

    # ===== SHOULDERS (batch 3) =====
    {
        "name": "Arnold Press", "slug": "arnold-press", "category": "compound",
        "muscle_groups": ["shoulders", "triceps"], "primary_muscle": "shoulders",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Arnold Schwarzenegger's signature press. Rotational overhead press.",
        "form_cues": ["Start with dumbbells at chin, palms facing you", "Press up while rotating palms to face forward", "Lock out overhead", "Reverse rotation on the way down"],
        "common_mistakes": ["Not rotating fully", "Arching lower back", "Using momentum"],
    },
    {
        "name": "Upright Row", "slug": "upright-row", "category": "compound",
        "muscle_groups": ["shoulders", "traps"], "primary_muscle": "shoulders",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Barbell or dumbbell upright row. Builds shoulders and traps.",
        "form_cues": ["Grip bar narrower than shoulder-width", "Pull bar up along body to chin level", "Lead with elbows — keep them higher than hands", "Lower with control"],
        "common_mistakes": ["Going too narrow — stresses wrists", "Pulling too high — stop at chin", "Using momentum"],
    },
    {
        "name": "Front Raise", "slug": "front-raise", "category": "isolation",
        "muscle_groups": ["shoulders"], "primary_muscle": "shoulders",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Dumbbell front raise. Isolates the anterior deltoid.",
        "form_cues": ["Stand with dumbbells at sides", "Raise one or both arms straight in front to shoulder height", "Control the descent", "Don't swing or use momentum"],
        "common_mistakes": ["Swinging the weight up", "Raising above shoulder height", "Leaning back"],
    },
    {
        "name": "Cable Lateral Raise", "slug": "cable-lateral-raise", "category": "isolation",
        "muscle_groups": ["shoulders"], "primary_muscle": "shoulders",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Cable lateral raise. Constant tension throughout the movement.",
        "form_cues": ["Stand sideways to cable, handle in far hand", "Raise arm out to side to shoulder height", "Control the descent", "Keep slight elbow bend"],
        "common_mistakes": ["Using too much weight", "Shrugging traps", "Swinging body"],
    },
    {
        "name": "Barbell Shrug", "slug": "barbell-shrug", "category": "isolation",
        "muscle_groups": ["traps", "shoulders", "back"], "primary_muscle": "traps",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Barbell shrug for trap development.",
        "form_cues": ["Hold barbell at hip height", "Shrug shoulders straight up toward ears", "Squeeze and hold at top", "Lower with control"],
        "common_mistakes": ["Rolling shoulders — go straight up", "Using too much weight and bouncing", "Not holding at the top"],
    },
    {
        "name": "Dumbbell Shrug", "slug": "dumbbell-shrug", "category": "isolation",
        "muscle_groups": ["traps", "shoulders", "back"], "primary_muscle": "traps",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Dumbbell shrug. Allows greater range of motion than barbell.",
        "form_cues": ["Hold dumbbells at sides", "Shrug shoulders up toward ears", "Squeeze traps at top", "Lower slowly"],
        "common_mistakes": ["Rolling shoulders", "Using momentum", "Not pausing at top"],
    },

    # ===== BICEPS (batch 3) =====
    {
        "name": "Preacher Curl", "slug": "preacher-curl", "category": "isolation",
        "muscle_groups": ["biceps"], "primary_muscle": "biceps",
        "equipment": ["barbell", "preacher bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Preacher bench curl. Eliminates cheating for strict bicep isolation.",
        "form_cues": ["Arms flat on preacher pad", "Curl bar up, squeezing biceps", "Lower with control — full extension", "Don't let arms bounce at bottom"],
        "common_mistakes": ["Not going to full extension", "Lifting elbows off the pad", "Going too heavy and swinging"],
    },
    {
        "name": "Incline Dumbbell Curl", "slug": "incline-dumbbell-curl", "category": "isolation",
        "muscle_groups": ["biceps"], "primary_muscle": "biceps",
        "equipment": ["dumbbells", "bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Curl on incline bench for deep bicep stretch. Targets the long head.",
        "form_cues": ["Sit back on incline bench (45-60 degrees)", "Let arms hang straight down", "Curl up, keeping upper arms still", "Lower fully for maximum stretch"],
        "common_mistakes": ["Bringing elbows forward", "Not going to full extension", "Using momentum"],
    },
    {
        "name": "Concentration Curl", "slug": "concentration-curl", "category": "isolation",
        "muscle_groups": ["biceps"], "primary_muscle": "biceps",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Seated single-arm curl with elbow braced on inner thigh.",
        "form_cues": ["Sit on bench, elbow braced against inner thigh", "Curl dumbbell up, rotating pinky toward shoulder", "Squeeze bicep at the top", "Lower with control"],
        "common_mistakes": ["Swinging the weight", "Not bracing elbow properly", "Using too heavy a weight"],
    },
    {
        "name": "Cable Curl", "slug": "cable-curl", "category": "isolation",
        "muscle_groups": ["biceps"], "primary_muscle": "biceps",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Standing cable curl. Constant tension throughout the curl.",
        "form_cues": ["Stand facing cable with bar or rope attachment", "Curl up, keeping elbows pinned", "Squeeze biceps at top", "Lower with control"],
        "common_mistakes": ["Leaning back", "Moving elbows forward", "Using momentum"],
    },
    {
        "name": "Reverse Curl", "slug": "reverse-curl", "category": "isolation",
        "muscle_groups": ["forearms", "biceps"], "primary_muscle": "forearms",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Overhand grip curl. Targets forearms and brachioradialis.",
        "form_cues": ["Grip bar with palms facing down (overhand)", "Curl up, keeping wrists straight", "Squeeze at top", "Lower with control"],
        "common_mistakes": ["Bending wrists", "Using too much weight", "Swinging body"],
    },

    # ===== TRICEPS (batch 3) =====
    {
        "name": "Skull Crusher", "slug": "skull-crusher", "category": "isolation",
        "muscle_groups": ["triceps"], "primary_muscle": "triceps",
        "equipment": ["barbell", "bench"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Lying tricep extension with EZ bar. Great for tricep mass.",
        "form_cues": ["Lie on bench, arms extended above forehead", "Lower bar toward forehead by bending elbows only", "Upper arms stay vertical — don't flare", "Extend back to lockout"],
        "common_mistakes": ["Flaring elbows out", "Lowering bar to face instead of forehead/behind head", "Moving upper arms"],
    },
    {
        "name": "Close-Grip Bench Press", "slug": "close-grip-bench-press", "category": "compound",
        "muscle_groups": ["triceps", "chest"], "primary_muscle": "triceps",
        "equipment": ["barbell", "bench"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Bench press with narrow grip. Shifts focus from chest to triceps.",
        "form_cues": ["Grip bar shoulder-width or slightly narrower", "Lower bar to lower chest, elbows close to body", "Press up to lockout", "Keep shoulder blades retracted"],
        "common_mistakes": ["Grip too narrow — stresses wrists", "Flaring elbows", "Bouncing off chest"],
    },
    {
        "name": "Tricep Dip (Bench)", "slug": "tricep-dip-bench", "category": "bodyweight",
        "muscle_groups": ["triceps", "chest"], "primary_muscle": "triceps",
        "equipment": ["bench"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Bench dips. Bodyweight tricep exercise using a bench behind you.",
        "form_cues": ["Hands on bench edge behind you, fingers forward", "Feet on floor or elevated on second bench", "Lower body by bending elbows to ~90 degrees", "Press up to lockout"],
        "common_mistakes": ["Going too deep — stresses shoulders", "Flaring elbows outward", "Shrugging shoulders up"],
    },
    {
        "name": "Dumbbell Tricep Kickback", "slug": "dumbbell-tricep-kickback", "category": "isolation",
        "muscle_groups": ["triceps"], "primary_muscle": "triceps",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Bent-over dumbbell kickback. Isolates the triceps at full extension.",
        "form_cues": ["Hinge forward, upper arm parallel to floor", "Extend forearm back until arm is straight", "Squeeze tricep at full extension", "Lower with control"],
        "common_mistakes": ["Dropping the upper arm", "Swinging the weight", "Not fully extending"],
    },

    # ===== CORE / ABS (batch 3) =====
    {
        "name": "Bicycle Crunch", "slug": "bicycle-crunch", "category": "bodyweight",
        "muscle_groups": ["core", "obliques"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Alternating elbow-to-knee crunch. Targets obliques and rectus abdominis.",
        "form_cues": ["Lie on back, hands behind head", "Bring opposite elbow to opposite knee", "Extend the other leg straight", "Alternate sides in pedaling motion"],
        "common_mistakes": ["Pulling on neck", "Moving too fast without control", "Not fully extending the straight leg"],
    },
    {
        "name": "Ab Wheel Rollout", "slug": "ab-wheel-rollout", "category": "bodyweight",
        "muscle_groups": ["core", "shoulders"], "primary_muscle": "core",
        "equipment": ["ab wheel"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Ab wheel rollout. One of the most challenging core exercises.",
        "form_cues": ["Kneel with wheel in front of you", "Roll forward slowly, extending arms", "Go as far as you can with flat back", "Pull back using core — don't collapse hips"],
        "common_mistakes": ["Hyperextending lower back", "Going too far out too soon", "Using hip flexors instead of abs to pull back"],
    },
    {
        "name": "Side Plank", "slug": "side-plank", "category": "bodyweight",
        "muscle_groups": ["core", "obliques"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "hold", "difficulty": "beginner",
        "description": "Side plank hold. Targets obliques and lateral core stability.",
        "form_cues": ["Lie on side, forearm on ground, elbow under shoulder", "Lift hips off floor, body in straight line", "Top arm on hip or extended upward", "Hold, breathing steadily"],
        "common_mistakes": ["Hips sagging toward floor", "Rolling forward or backward", "Holding breath"],
    },
    {
        "name": "Dead Bug", "slug": "dead-bug", "category": "bodyweight",
        "muscle_groups": ["core"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Anti-extension core exercise. Great for learning core bracing.",
        "form_cues": ["Lie on back, arms pointing up, knees bent 90 degrees", "Lower opposite arm and leg toward floor", "Keep lower back pressed flat — don't arch", "Return and alternate sides"],
        "common_mistakes": ["Lower back lifting off floor", "Moving too fast", "Not coordinating opposite arm and leg"],
    },
    {
        "name": "V-Up", "slug": "v-up", "category": "bodyweight",
        "muscle_groups": ["core"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Full V-up. Raise arms and legs simultaneously to touch toes.",
        "form_cues": ["Lie flat, arms extended overhead", "Raise arms and legs simultaneously to form a V", "Touch toes at the top", "Lower with control — don't crash down"],
        "common_mistakes": ["Rounding the back excessively", "Not reaching full V position", "Using momentum"],
    },
    {
        "name": "Cable Crunch", "slug": "cable-crunch", "category": "isolation",
        "muscle_groups": ["core"], "primary_muscle": "core",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Kneeling cable crunch. Weighted ab exercise for progressive overload.",
        "form_cues": ["Kneel facing cable with rope behind head", "Crunch down, curling torso toward floor", "Squeeze abs at bottom", "Return with control"],
        "common_mistakes": ["Sitting back with hips instead of crunching", "Using arms to pull the weight", "Not controlling the eccentric"],
    },
    {
        "name": "Decline Sit-Up", "slug": "decline-sit-up", "category": "bodyweight",
        "muscle_groups": ["core"], "primary_muscle": "core",
        "equipment": ["decline bench"], "tracking_mode": "reps", "difficulty": "intermediate",
        "description": "Sit-up on decline bench for added resistance from gravity.",
        "form_cues": ["Lock feet under pads on decline bench", "Cross arms on chest or behind head", "Sit up by curling torso, not jerking", "Lower with control"],
        "common_mistakes": ["Using hip flexors instead of abs", "Jerking up with momentum", "Going too fast"],
    },
    {
        "name": "Hollow Body Hold", "slug": "hollow-body-hold", "category": "bodyweight",
        "muscle_groups": ["core"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "hold", "difficulty": "intermediate",
        "description": "Gymnastics hold. Arms and legs extended, lower back pressed to floor.",
        "form_cues": ["Lie on back, arms overhead, legs straight", "Lift arms, shoulders, and legs slightly off floor", "Press lower back firmly into floor", "Hold position, breathing steadily"],
        "common_mistakes": ["Lower back lifting off floor — means legs are too low", "Bending knees", "Holding breath"],
    },

    # ===== FULL BODY / CONDITIONING =====
    {
        "name": "High Knees", "slug": "high-knees", "category": "bodyweight",
        "muscle_groups": ["core", "quads", "calves"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "timed", "difficulty": "beginner",
        "description": "Running in place with high knee drive. Great cardio warm-up.",
        "form_cues": ["Stand tall, drive knees to hip height", "Pump arms in sync with legs", "Stay on balls of feet", "Maintain fast pace"],
        "common_mistakes": ["Leaning back", "Knees not reaching hip height", "Flat-footed landing"],
    },
    {
        "name": "Battle Ropes", "slug": "battle-ropes", "category": "compound",
        "muscle_groups": ["shoulders", "core", "arms"], "primary_muscle": "shoulders",
        "equipment": ["battle ropes"], "tracking_mode": "timed", "difficulty": "intermediate",
        "description": "Battle rope waves. Full body conditioning and shoulder endurance.",
        "form_cues": ["Stand in half squat, rope end in each hand", "Alternate arms making waves in the rope", "Keep core tight, drive from shoulders", "Maintain consistent wave amplitude"],
        "common_mistakes": ["Standing too upright", "Waves dying out — move faster", "Not bracing core"],
    },
    {
        "name": "Turkish Get-Up", "slug": "turkish-get-up", "category": "compound",
        "muscle_groups": ["shoulders", "core", "full body"], "primary_muscle": "shoulders",
        "equipment": ["kettlebell"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Full-body movement from lying to standing while holding weight overhead.",
        "form_cues": ["Lie on back, weight in one hand extended overhead", "Roll to elbow, then hand, keeping weight up", "Bridge hips, sweep leg through to kneeling", "Stand up, weight stays locked out overhead"],
        "common_mistakes": ["Bending the weight-bearing arm", "Rushing the movement — go slow", "Not keeping eyes on the weight"],
    },
    {
        "name": "Bear Crawl", "slug": "bear-crawl", "category": "bodyweight",
        "muscle_groups": ["core", "shoulders", "quads"], "primary_muscle": "core",
        "equipment": ["none"], "tracking_mode": "timed", "difficulty": "intermediate",
        "description": "Crawl on hands and feet with knees hovering off ground. Total body.",
        "form_cues": ["Start on all fours, lift knees 2 inches off ground", "Move opposite hand and foot forward together", "Keep hips low and level — don't bounce", "Maintain tight core throughout"],
        "common_mistakes": ["Hips too high in the air", "Moving same-side hand and foot", "Knees touching ground"],
    },
    {
        "name": "Jumping Jacks", "slug": "jumping-jacks", "category": "bodyweight",
        "muscle_groups": ["full body"], "primary_muscle": "full body",
        "equipment": ["none"], "tracking_mode": "timed", "difficulty": "beginner",
        "description": "Classic jumping jacks. Simple and effective cardio warm-up.",
        "form_cues": ["Start with feet together, arms at sides", "Jump feet apart while raising arms overhead", "Jump back to start position", "Maintain steady rhythm"],
        "common_mistakes": ["Not fully extending arms", "Landing flat-footed", "Going too slow to get cardio benefit"],
    },
    {
        "name": "Sled Push", "slug": "sled-push", "category": "compound",
        "muscle_groups": ["quads", "glutes", "calves", "core"], "primary_muscle": "quads",
        "equipment": ["sled"], "tracking_mode": "timed", "difficulty": "intermediate",
        "description": "Push a weighted sled across the floor. Total leg and conditioning work.",
        "form_cues": ["Grip handles at chest or waist height", "Drive through legs, staying low", "Take short, powerful steps", "Keep core braced, don't round back"],
        "common_mistakes": ["Standing too upright — stay low", "Steps too long", "Not driving through full foot"],
    },
    {
        "name": "Farmer's Walk", "slug": "farmers-walk", "category": "compound",
        "muscle_groups": ["traps", "forearms", "core"], "primary_muscle": "traps",
        "equipment": ["dumbbells"], "tracking_mode": "timed", "difficulty": "beginner",
        "description": "Walk with heavy weights in each hand. Builds grip, traps, and core.",
        "form_cues": ["Pick up heavy dumbbells, stand tall", "Shoulders back and down, chest up", "Take short, controlled steps", "Maintain tight core — don't lean side to side"],
        "common_mistakes": ["Leaning to one side", "Shrugging shoulders up", "Steps too long"],
    },
    {
        "name": "Power Clean", "slug": "power-clean", "category": "compound",
        "muscle_groups": ["full body", "back", "shoulders"], "primary_muscle": "full body",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Olympic lift variation. Explosive pull from floor to shoulders.",
        "form_cues": ["Start like a deadlift — bar over mid-foot", "Pull bar past knees, then explode hips", "Shrug and pull yourself under the bar", "Catch in front rack position with elbows high"],
        "common_mistakes": ["Pulling with arms instead of hip explosion", "Not getting under the bar", "Catching with elbows low"],
    },
    {
        "name": "Barbell Thruster", "slug": "barbell-thruster", "category": "compound",
        "muscle_groups": ["quads", "shoulders", "core"], "primary_muscle": "quads",
        "equipment": ["barbell"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Front squat into overhead press in one fluid movement.",
        "form_cues": ["Bar in front rack, perform a front squat", "Drive up explosively out of the squat", "Use momentum to press bar overhead", "Lock out overhead, then lower to rack position"],
        "common_mistakes": ["Pausing between squat and press", "Not hitting depth on the squat", "Pressing too early before standing"],
    },
    {
        "name": "Dumbbell Snatch", "slug": "dumbbell-snatch", "category": "compound",
        "muscle_groups": ["shoulders", "full body"], "primary_muscle": "shoulders",
        "equipment": ["dumbbells"], "tracking_mode": "reps", "difficulty": "advanced",
        "description": "Single-arm dumbbell snatch. Explosive power from floor to overhead.",
        "form_cues": ["Straddle dumbbell on floor, hinge and grip", "Explode hips, pulling dumbbell close to body", "Catch overhead with arm locked out", "Lower with control to start position"],
        "common_mistakes": ["Swinging dumbbell away from body", "Not using hip drive", "Catching with bent arm"],
    },

    # ===== FLEXIBILITY (batch 3) =====
    {
        "name": "Pigeon Pose", "slug": "pigeon-pose", "category": "cardio",
        "muscle_groups": ["hip flexors", "glutes"], "primary_muscle": "hip flexors",
        "equipment": ["none"], "tracking_mode": "hold", "difficulty": "beginner",
        "description": "Deep hip opener from yoga. Stretches glutes and hip flexors.",
        "form_cues": ["From all fours, bring one knee forward behind wrist", "Extend back leg straight behind you", "Lower hips toward floor", "Hold 30-60 seconds each side"],
        "common_mistakes": ["Hips not square — rotate to face forward", "Forcing depth too quickly", "Rounding the back"],
    },
    {
        "name": "Child's Pose", "slug": "childs-pose", "category": "cardio",
        "muscle_groups": ["back", "shoulders"], "primary_muscle": "back",
        "equipment": ["none"], "tracking_mode": "hold", "difficulty": "beginner",
        "description": "Restful yoga pose. Stretches back, hips, and shoulders.",
        "form_cues": ["Kneel, sit back on heels", "Extend arms forward on floor", "Rest forehead on the ground", "Breathe deeply and relax"],
        "common_mistakes": ["Not sitting back far enough", "Tension in shoulders", "Holding breath"],
    },
    {
        "name": "Cat-Cow Stretch", "slug": "cat-cow-stretch", "category": "cardio",
        "muscle_groups": ["back", "core"], "primary_muscle": "back",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Alternating spinal flexion and extension on all fours. Great warm-up.",
        "form_cues": ["On all fours, wrists under shoulders, knees under hips", "Cow: drop belly, lift chest and tailbone", "Cat: round back up, tuck chin", "Flow between positions with breath"],
        "common_mistakes": ["Moving too fast", "Not using full range of motion", "Not coordinating with breath"],
    },
    {
        "name": "World's Greatest Stretch", "slug": "worlds-greatest-stretch", "category": "cardio",
        "muscle_groups": ["hip flexors", "hamstrings", "shoulders", "core"], "primary_muscle": "hip flexors",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Dynamic stretch combining lunge, rotation, and hamstring stretch.",
        "form_cues": ["Step into deep lunge", "Place same-side hand on floor, rotate opposite arm to sky", "Return hand to floor, straighten front leg for hamstring stretch", "Step forward and repeat other side"],
        "common_mistakes": ["Rushing through positions", "Not rotating torso enough", "Rear knee dropping hard to floor"],
    },
    {
        "name": "Band Shoulder Dislocates", "slug": "band-shoulder-dislocates", "category": "cardio",
        "muscle_groups": ["shoulders", "rotator cuff"], "primary_muscle": "shoulders",
        "equipment": ["resistance band"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Shoulder mobility drill with band or dowel. Pass band from front to back overhead.",
        "form_cues": ["Hold band with wide grip in front of hips", "Raise arms overhead and behind you in an arc", "Keep arms straight throughout", "Use wider grip if mobility is limited"],
        "common_mistakes": ["Bending elbows to get around", "Grip too narrow causing shoulder pain", "Going too fast"],
    },
    {
        "name": "Ankle Mobility Drill", "slug": "ankle-mobility-drill", "category": "cardio",
        "muscle_groups": ["calves", "ankles"], "primary_muscle": "calves",
        "equipment": ["none"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Wall-facing ankle dorsiflexion drill. Improves squat depth.",
        "form_cues": ["Face wall, foot a few inches away", "Drive knee forward over toes toward wall", "Keep heel on ground", "Increase distance as mobility improves"],
        "common_mistakes": ["Heel lifting off ground", "Knee caving inward", "Not holding at end range"],
    },

    # ===== MACHINES =====
    {
        "name": "Smith Machine Squat", "slug": "smith-machine-squat", "category": "compound",
        "muscle_groups": ["quads", "glutes"], "primary_muscle": "quads",
        "equipment": ["smith machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Squat on Smith machine for guided bar path. Good for beginners.",
        "form_cues": ["Position bar on upper traps", "Feet slightly in front of bar", "Squat down to parallel", "Press up through heels"],
        "common_mistakes": ["Feet directly under bar — place them slightly forward", "Not going deep enough", "Relying entirely on the machine — learn free squats too"],
    },
    {
        "name": "Chest Press Machine", "slug": "chest-press-machine", "category": "compound",
        "muscle_groups": ["chest", "triceps"], "primary_muscle": "chest",
        "equipment": ["chest press machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Seated machine chest press. Safe and beginner-friendly chest builder.",
        "form_cues": ["Adjust seat so handles are at mid-chest", "Grip handles, press forward to full extension", "Return with control", "Keep back flat against pad"],
        "common_mistakes": ["Seat too high or low", "Arching back off pad", "Not using full range of motion"],
    },
    {
        "name": "Seated Row Machine", "slug": "seated-row-machine", "category": "compound",
        "muscle_groups": ["back", "biceps"], "primary_muscle": "back",
        "equipment": ["row machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Plate-loaded or selectorized seated row machine. Simple back builder.",
        "form_cues": ["Sit with chest against pad", "Grip handles, pull back squeezing shoulder blades", "Control the return", "Keep chest against pad throughout"],
        "common_mistakes": ["Pulling chest off pad to cheat", "Using momentum", "Not squeezing at contraction"],
    },
    {
        "name": "Cable Pull-Through", "slug": "cable-pull-through", "category": "compound",
        "muscle_groups": ["glutes", "hamstrings"], "primary_muscle": "glutes",
        "equipment": ["cable machine"], "tracking_mode": "reps", "difficulty": "beginner",
        "description": "Cable pull-through. Hip hinge with constant cable tension for glutes.",
        "form_cues": ["Face away from low cable, rope between legs", "Hinge at hips, letting cable pull hands back", "Drive hips forward explosively, squeezing glutes", "Stand tall at the top — don't hyperextend"],
        "common_mistakes": ["Squatting instead of hinging", "Using arms to pull", "Hyperextending at the top"],
    },

    # ===== CARDIO / MOVEMATCH (2) =====
    {
        "name": "Zumba / Dance",
        "slug": "zumba-dance",
        "category": "cardio",
        "muscle_groups": ["full body"],
        "primary_muscle": "full body",
        "equipment": ["none"],
        "tracking_mode": "timed",
        "difficulty": "beginner",
        "description": "Dance-based cardio workout. Use MoveMatch to follow along with choreography.",
        "form_cues": [
            "Follow the rhythm and have fun",
            "Keep your core engaged throughout",
            "Stay light on your feet",
            "Modify moves to your comfort level"
        ],
        "common_mistakes": [
            "Going too hard too fast — build up gradually",
            "Forgetting to breathe naturally",
            "Comparing yourself to the instructor"
        ],
    },
    {
        "name": "Yoga Flow",
        "slug": "yoga-flow",
        "category": "cardio",
        "muscle_groups": ["full body"],
        "primary_muscle": "full body",
        "equipment": ["yoga mat"],
        "tracking_mode": "timed",
        "difficulty": "beginner",
        "description": "Flowing yoga sequence. Improves flexibility, balance, and mindfulness.",
        "form_cues": [
            "Move with your breath — inhale to extend, exhale to fold",
            "Don't force flexibility — go to your edge, not past it",
            "Engage your core for balance poses",
            "Focus on alignment over depth"
        ],
        "common_mistakes": [
            "Holding breath during challenging poses",
            "Forcing deep stretches before warming up",
            "Rushing transitions between poses"
        ],
    },
]


def seed_exercises(engine):
    """Seed the exercises table with the exercise library. Upserts new exercises."""
    from sqlalchemy import text, inspect
    import json

    try:
        inspector = inspect(engine)
        if "exercises" not in inspector.get_table_names():
            return  # Table not created yet

        with engine.begin() as conn:
            # Get existing slugs
            rows = conn.execute(text("SELECT slug FROM exercises")).fetchall()
            existing_slugs = {row[0] for row in rows}

            inserted = 0
            for ex in EXERCISE_SEED_DATA:
                if ex["slug"] in existing_slugs:
                    continue  # Already exists

                conn.execute(text(
                    "INSERT INTO exercises "
                    "(name, slug, category, muscle_groups, primary_muscle, equipment, "
                    "tracking_mode, difficulty, form_cues, common_mistakes, description) "
                    "VALUES (:name, :slug, :category, :muscle_groups, :primary_muscle, "
                    ":equipment, :tracking_mode, :difficulty, :form_cues, :common_mistakes, "
                    ":description)"
                ), {
                    "name": ex["name"],
                    "slug": ex["slug"],
                    "category": ex["category"],
                    "muscle_groups": json.dumps(ex["muscle_groups"]),
                    "primary_muscle": ex["primary_muscle"],
                    "equipment": json.dumps(ex["equipment"]),
                    "tracking_mode": ex["tracking_mode"],
                    "difficulty": ex["difficulty"],
                    "form_cues": json.dumps(ex.get("form_cues", [])),
                    "common_mistakes": json.dumps(ex.get("common_mistakes", [])),
                    "description": ex.get("description", ""),
                })
                inserted += 1

            # Update muscle_groups for existing exercises (in case seed data changed)
            updated = 0
            for ex in EXERCISE_SEED_DATA:
                if ex["slug"] in existing_slugs:
                    conn.execute(text(
                        "UPDATE exercises SET muscle_groups = :muscle_groups "
                        "WHERE slug = :slug"
                    ), {
                        "slug": ex["slug"],
                        "muscle_groups": json.dumps(ex["muscle_groups"]),
                    })
                    updated += 1

            if inserted:
                logger.info(f"Seeded {inserted} new exercises (total library: {len(EXERCISE_SEED_DATA)})")
            if updated:
                logger.info(f"Updated muscle_groups for {updated} existing exercises")
    except Exception as e:
        logger.warning(f"Failed to seed exercises: {e}")
