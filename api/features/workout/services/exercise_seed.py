"""Seed data for the exercise library — 20 exercises across 4 categories."""

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
    """Seed the exercises table with the exercise library. Idempotent."""
    from sqlalchemy import text, inspect

    try:
        inspector = inspect(engine)
        if "exercises" not in inspector.get_table_names():
            return  # Table not created yet

        with engine.begin() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM exercises")).scalar()
            if count > 0:
                return  # Already seeded

            for ex in EXERCISE_SEED_DATA:
                import json
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

            logger.info(f"Seeded {len(EXERCISE_SEED_DATA)} exercises")
    except Exception as e:
        logger.warning(f"Failed to seed exercises: {e}")
