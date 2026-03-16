"""Core business logic for the Workout / AI Fitness Coach feature."""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from ..db_models.workout import (
    Exercise, UserProfile, UserGoal, CoachPreferences,
    WorkoutPlan, WorkoutSession, ExerciseSet,
    PlanStatus, SessionStatus, SessionType,
)
from .plan_generator import generate_template_plan

logger = logging.getLogger(__name__)

# Day name mappings
DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABELS = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
    "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}

COACH_MESSAGES = [
    "Every rep counts. Let's build something today.",
    "You showed up — that's already a win. Let's go.",
    "Consistency beats intensity. Keep the streak alive.",
    "Your body is stronger than you think. Prove it today.",
    "Rest days make gains days. But today? Today we work.",
]


class WorkoutService:

    @staticmethod
    def save_onboarding(db: Session, user_id: int, data: dict) -> dict:
        """Save onboarding data: profile, goals, preferences, and generate plan."""
        # Upsert user profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)

        profile.fitness_level = data["fitness_level"]
        profile.age = data.get("age")
        profile.gender = data.get("gender")
        profile.height_cm = data.get("height_cm")
        profile.weight_kg = data.get("weight_kg")
        profile.injuries = data.get("injuries")
        profile.onboarding_completed = True
        profile.onboarding_completed_at = datetime.utcnow()

        # Replace goals
        db.query(UserGoal).filter(UserGoal.user_id == user_id).delete()
        for i, goal_type in enumerate(data.get("goals", [])):
            db.add(UserGoal(user_id=user_id, goal_type=goal_type, priority=i))

        # Upsert preferences
        prefs = db.query(CoachPreferences).filter(CoachPreferences.user_id == user_id).first()
        if not prefs:
            prefs = CoachPreferences(user_id=user_id)
            db.add(prefs)

        preferred_days = data.get("preferred_days", ["mon", "wed", "fri"])
        prefs.days_per_week = len(preferred_days)
        prefs.preferred_days = preferred_days
        prefs.session_duration_minutes = data.get("session_duration_minutes", 45)
        prefs.train_location = data.get("train_location", "gym")
        prefs.available_equipment = data.get("available_equipment")

        db.flush()

        # Generate plan — try AI first, fall back to template
        plan_data = None
        try:
            from .ai_plan_generator import generate_plan as ai_generate_plan
            plan_data = asyncio.get_event_loop().run_until_complete(
                ai_generate_plan(db, user_id)
            )
            if plan_data:
                logger.info(f"AI plan generated for user {user_id}")
        except RuntimeError:
            # No event loop running (called from sync context) — try creating one
            try:
                loop = asyncio.new_event_loop()
                from .ai_plan_generator import generate_plan as ai_generate_plan
                plan_data = loop.run_until_complete(ai_generate_plan(db, user_id))
                loop.close()
                if plan_data:
                    logger.info(f"AI plan generated for user {user_id}")
            except Exception as e:
                logger.debug(f"AI plan generation failed: {e}")
        except Exception as e:
            logger.debug(f"AI plan generation failed: {e}")

        if not plan_data:
            # Template fallback
            exercises = db.query(Exercise).all()
            exercise_dicts = [
                {
                    "slug": e.slug, "name": e.name, "category": e.category,
                    "muscle_groups": e.muscle_groups or [], "primary_muscle": e.primary_muscle,
                    "equipment": e.equipment or ["none"], "tracking_mode": e.tracking_mode,
                    "difficulty": e.difficulty,
                }
                for e in exercises
            ]

            plan_data = generate_template_plan(
                preferred_days=preferred_days,
                session_duration_minutes=prefs.session_duration_minutes,
                fitness_level=data["fitness_level"],
                train_location=prefs.train_location,
                available_equipment=prefs.available_equipment,
                exercises=exercise_dicts,
            )

        # Archive any existing active plan
        db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == PlanStatus.ACTIVE,
        ).update({"status": PlanStatus.ARCHIVED})

        plan = WorkoutPlan(
            user_id=user_id,
            name=plan_data["name"],
            split_type=plan_data["split_type"],
            plan_data=plan_data,
            status=PlanStatus.ACTIVE,
        )
        db.add(plan)
        db.flush()

        prefs.workout_split = plan_data["split_type"]

        # Create planned sessions for this week
        WorkoutService._create_week_sessions(db, user_id, plan, preferred_days)

        db.commit()

        return {
            "success": True,
            "plan_name": plan_data["name"],
            "split_type": plan_data["split_type"],
            "days_per_week": plan_data["days_per_week"],
            "message": f"Your {plan_data['name']} plan is ready! Let's get after it.",
        }

    @staticmethod
    def _create_week_sessions(
        db: Session, user_id: int, plan: WorkoutPlan, preferred_days: List[str]
    ):
        """Create planned sessions for the current week."""
        today = date.today()
        # Find start of this week (Monday)
        start_of_week = today - timedelta(days=today.weekday())

        for day_name in preferred_days:
            day_index = DAY_NAMES.index(day_name) if day_name in DAY_NAMES else 0
            session_date = start_of_week + timedelta(days=day_index)

            # Don't create sessions in the past (except today)
            if session_date < today:
                continue

            # Check if session already exists for this date
            existing = db.query(WorkoutSession).filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.plan_id == plan.id,
                WorkoutSession.scheduled_date == session_date,
            ).first()

            if not existing:
                db.add(WorkoutSession(
                    user_id=user_id,
                    plan_id=plan.id,
                    session_type=SessionType.COACHED,
                    status=SessionStatus.PLANNED,
                    scheduled_date=session_date,
                ))

    @staticmethod
    def get_profile(db: Session, user_id: int) -> Optional[dict]:
        """Get onboarding profile status."""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return {"onboarding_completed": False}

        goals = db.query(UserGoal).filter(UserGoal.user_id == user_id).all()
        prefs = db.query(CoachPreferences).filter(CoachPreferences.user_id == user_id).first()

        return {
            "onboarding_completed": profile.onboarding_completed,
            "fitness_level": profile.fitness_level,
            "age": profile.age,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "injuries": profile.injuries,
            "goals": [g.goal_type for g in goals],
            "preferred_days": prefs.preferred_days if prefs else [],
            "session_duration_minutes": prefs.session_duration_minutes if prefs else 45,
            "train_location": prefs.train_location if prefs else "gym",
        }

    @staticmethod
    def get_exercises(
        db: Session,
        muscle_group: Optional[str] = None,
        equipment: Optional[str] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple:
        """Get filtered exercise list. Returns (exercises, total_count)."""
        query = db.query(Exercise)

        if search:
            query = query.filter(Exercise.name.ilike(f"%{search}%"))

        if category:
            query = query.filter(Exercise.category == category)

        # JSON field filtering — done in Python for SQLite compatibility
        all_exercises = query.order_by(Exercise.name).all()

        if muscle_group:
            all_exercises = [
                e for e in all_exercises
                if muscle_group in (e.muscle_groups or [])
            ]

        if equipment:
            all_exercises = [
                e for e in all_exercises
                if equipment in (e.equipment or [])
            ]

        total = len(all_exercises)
        return all_exercises[offset:offset + limit], total

    @staticmethod
    def get_exercise_by_slug(db: Session, slug: str) -> Optional[Exercise]:
        """Get a single exercise by slug."""
        return db.query(Exercise).filter(Exercise.slug == slug).first()

    @staticmethod
    def get_today_workout(db: Session, user_id: int) -> dict:
        """Get today's workout: plan day, exercises, streak, coach message."""
        today = date.today()
        today_day_name = DAY_NAMES[today.weekday()]

        # Get active plan
        plan = db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == PlanStatus.ACTIVE,
        ).first()

        if not plan:
            return {
                "has_plan": False,
                "exercises": [],
                "estimated_minutes": 0,
                "streak": WorkoutService._compute_streak(db, user_id),
                "coach_message": "Set up your plan to get personalized workouts!",
            }

        # Find today's day in the plan
        plan_data = plan.plan_data or {}
        today_day = None
        for day in plan_data.get("days", []):
            if day.get("day") == today_day_name:
                today_day = day
                break

        if not today_day:
            return {
                "has_plan": True,
                "day_label": "Rest Day",
                "exercises": [],
                "estimated_minutes": 0,
                "streak": WorkoutService._compute_streak(db, user_id),
                "coach_message": "Rest day! Recovery is when gains happen.",
            }

        # Check if there's already a session for today
        session = db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.scheduled_date == today,
        ).first()

        streak = WorkoutService._compute_streak(db, user_id)
        import hashlib
        day_hash = int(hashlib.md5(str(today).encode()).hexdigest(), 16)
        coach_msg = COACH_MESSAGES[day_hash % len(COACH_MESSAGES)]

        return {
            "has_plan": True,
            "day_label": today_day.get("label", "Workout"),
            "exercises": today_day.get("exercises", []),
            "estimated_minutes": today_day.get("estimated_minutes", 30),
            "streak": streak,
            "coach_message": coach_msg,
            "session_id": session.id if session else None,
        }

    @staticmethod
    def get_week_view(db: Session, user_id: int) -> dict:
        """Get the week view with day statuses."""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        plan = db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.status == PlanStatus.ACTIVE,
        ).first()

        plan_days_set = set()
        plan_day_labels = {}
        if plan and plan.plan_data:
            for day in plan.plan_data.get("days", []):
                plan_days_set.add(day["day"])
                plan_day_labels[day["day"]] = day.get("label")

        # Get this week's sessions
        sessions = db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.scheduled_date >= start_of_week,
            WorkoutSession.scheduled_date < start_of_week + timedelta(days=7),
        ).all()

        session_map = {s.scheduled_date: s for s in sessions}

        days = []
        for i, day_name in enumerate(DAY_NAMES):
            day_date = start_of_week + timedelta(days=i)
            session = session_map.get(day_date)

            if day_date == today:
                status = "today"
            elif session and session.status == SessionStatus.COMPLETED:
                status = "completed"
            elif session and session.status == SessionStatus.SKIPPED:
                status = "skipped"
            elif day_date < today:
                status = "completed" if (session and session.status == SessionStatus.COMPLETED) else "rest"
            elif day_name in plan_days_set:
                status = "planned"
            else:
                status = "rest"

            days.append({
                "day": day_name,
                "label": plan_day_labels.get(day_name),
                "status": status,
            })

        return {
            "days": days,
            "plan_name": plan.name if plan else None,
            "week_number": plan.week_number if plan else 1,
        }

    @staticmethod
    def get_progress_stats(db: Session, user_id: int) -> dict:
        """Get progress stats: streaks, volume, workout count."""
        completed_sessions = db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatus.COMPLETED,
        ).all()

        total_workouts = len(completed_sessions)
        streak = WorkoutService._compute_streak(db, user_id)

        # This week's workouts
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        workouts_this_week = sum(
            1 for s in completed_sessions
            if s.scheduled_date and s.scheduled_date >= start_of_week
        )

        # Total volume from exercise sets
        sets = db.query(ExerciseSet).join(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
        ).all()

        total_volume = sum(
            (s.actual_reps or 0) * (s.weight_kg or 0)
            for s in sets
        )

        return {
            "total_workouts": total_workouts,
            "current_streak": streak,
            "best_streak": streak,  # simplified — track best_streak in profile later
            "total_volume_kg": round(total_volume, 1),
            "workouts_this_week": workouts_this_week,
            "recent_prs": [],
        }

    @staticmethod
    def create_quick_start_session(db: Session, user_id: int, exercise_slugs: List[str]) -> dict:
        """Create an ad-hoc quick start session from selected exercises."""
        exercises = db.query(Exercise).filter(Exercise.slug.in_(exercise_slugs)).all()

        if not exercises:
            return {"error": "No valid exercises found"}

        session = WorkoutSession(
            user_id=user_id,
            session_type=SessionType.QUICK_START,
            status=SessionStatus.PLANNED,
            scheduled_date=date.today(),
        )
        db.add(session)
        db.flush()

        summary = {
            "exercises": [
                {"slug": e.slug, "name": e.name}
                for e in exercises
            ],
        }
        session.summary = summary
        db.commit()

        return {
            "session_id": session.id,
            "exercises": summary["exercises"],
            "status": "planned",
        }

    @staticmethod
    def get_personalized_greeting(db: Session, user_id: int, user_name: str = "") -> dict:
        """Generate personalized greeting + coach insight for the home screen.

        Returns: {"greeting": str, "insight": str, "insight_type": str}
        """
        import hashlib
        import random

        name = user_name or "champ"
        now = datetime.utcnow()
        hour = now.hour
        time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        today = date.today()
        day_of_week = today.weekday()

        streak = WorkoutService._compute_streak(db, user_id)
        total_workouts = db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatus.COMPLETED,
        ).count()

        goals = [g.goal_type for g in db.query(UserGoal).filter(UserGoal.user_id == user_id).all()]

        # Greeting rotation
        greeting_templates = [
            f"Welcome back, {name}!",
            "Ready to crush it today?",
            f"Let's get after it, {name}!",
            f"Good {time_of_day}, {name}!",
            f"Back at it, {name}!",
        ]
        if streak > 1:
            greeting_templates.append(f"Day {streak} — keep it going!")

        # Deterministic but rotating selection based on date
        day_hash = int(hashlib.md5(str(today).encode()).hexdigest(), 16)
        greeting = greeting_templates[day_hash % len(greeting_templates)]

        # Insight rotation by day of week
        insight_types = ["progress", "performance", "streak", "goals", "recovery", "motivational", "progress"]
        insight_type = insight_types[day_of_week]

        insight_map = {
            "progress": [
                f"You've completed {total_workouts} workouts total. That's real consistency.",
                "Every session builds on the last. Keep stacking.",
            ],
            "performance": [
                "Your training volume is trending up. The work is paying off.",
                "Focus on form today. Quality reps beat junk volume.",
            ],
            "streak": [
                f"{streak} day streak — you're on fire." if streak > 0 else "Start a new streak today.",
                "Consistency is the real superpower. Keep showing up.",
            ],
            "goals": [
                f"Stay focused on {', '.join(goals[:2]) if goals else 'your goals'}. Every session counts.",
                "Building takes time, but you're putting in the work.",
            ],
            "recovery": [
                "Recovery is when gains happen. Listen to your body today.",
                "Your body grows during rest. Make today count.",
            ],
            "motivational": [
                "Consistency beats intensity. You're proving that.",
                "The hardest part is showing up. You've already done that.",
                "Every rep counts. Let's make today's count.",
            ],
        }

        insights = insight_map.get(insight_type, insight_map["motivational"])
        insight = insights[day_hash % len(insights)]

        return {
            "greeting": greeting,
            "insight": insight,
            "insight_type": insight_type,
        }

    @staticmethod
    def _compute_streak(db: Session, user_id: int) -> int:
        """Compute the current consecutive workout day streak."""
        completed = db.query(WorkoutSession).filter(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == SessionStatus.COMPLETED,
        ).order_by(WorkoutSession.scheduled_date.desc()).all()

        if not completed:
            return 0

        streak = 0
        check_date = date.today()

        # Get dates of completed sessions
        completed_dates = set()
        for s in completed:
            if s.scheduled_date:
                completed_dates.add(s.scheduled_date)

        # Count backwards from today (allow today or yesterday as start)
        if check_date not in completed_dates:
            check_date = check_date - timedelta(days=1)

        while check_date in completed_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return streak
