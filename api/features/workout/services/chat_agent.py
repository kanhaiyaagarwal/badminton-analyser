"""Workout chat agent — handles all workout-phase conversations.

Contexts: pre_workout, post_set, rest, post_workout.
Uses the existing llm_service for LLM calls, falls back to templates.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PRE_WORKOUT_SYSTEM = """You are Coach, a friendly AI fitness coach. The user is about to start their workout.
You can help them review and modify today's plan, AND answer any fitness or exercise questions.

Today's plan:
{plan_summary}

If the user asks HOW to do an exercise, explain the proper form in 2-3 concise bullet points.
If the user asks a general fitness question, answer helpfully.
If the user wants to modify the plan, use the appropriate action.

Available actions you can return (only when modifying the plan):
- swap_exercise: {{"type": "swap_exercise", "params": {{"old_slug": "...", "new_slug": "..."}}}}
- adjust_set: {{"type": "adjust_next_set", "params": {{"exercise_id": "...", "weight_kg": N, "reps": N}}}}
- remove_exercise: {{"type": "remove_exercise", "params": {{"exercise_id": "..."}}}}
- begin_workout: {{"type": "begin_workout", "params": {{}}}}

Respond in JSON:
{{
  "response": "Your message",
  "action": null,
  "suggested_buttons": [{{"label": "...", "action": "..."}}]
}}

Keep responses short but helpful. Be encouraging."""

REST_SYSTEM = """You are Coach, a friendly AI fitness coach. The user just finished a set and is resting.

Last set info: {last_set}
Current exercise: {exercise_name}
Workout progress: {progress}

The user may report how the set felt or ask to adjust weight/reps.

Available actions:
- adjust_next_set: {{"type": "adjust_next_set", "params": {{"exercise_id": "...", "weight_kg": N, "reps": N}}}}
- skip_exercise: {{"type": "skip_exercise", "params": {{"exercise_id": "..."}}}}

Respond in JSON:
{{
  "response": "Your message",
  "action": null,
  "suggested_buttons": [{{"label": "...", "action": "..."}}]
}}

If easy → suggest bumping weight 2.5-5kg. If hard → suggest dropping. Be brief."""

POST_WORKOUT_SYSTEM = """You are Coach, a friendly AI fitness coach. The user just finished their workout.

Session summary: {summary}

Give a brief, encouraging summary. Respond in JSON:
{{
  "response": "Your message",
  "action": null,
  "suggested_buttons": [{{"label": "Thanks!", "action": "dismiss"}}]
}}"""

# Template fallback responses
TEMPLATES = {
    "pre_workout": {
        "greeting": "{day_label} — {exercise_count} exercises, ~{estimated_minutes} min. Ready to go, or want to make changes?",
        "buttons": [
            {"label": "Let's go!", "action": "begin_workout"},
            {"label": "Swap exercise", "action": "swap_exercise"},
            {"label": "Make it shorter", "action": "make_shorter"},
        ],
    },
    "post_set": {
        "responses": {
            "easy": "Easy? Let's bump it up next set — you've got more in the tank.",
            "just_right": "Perfect weight. Keep that form locked in.",
            "hard": "Tough set! Let's keep the weight the same or drop it slightly.",
            "default": "How'd that feel? Let me know if you want to adjust anything.",
        },
        "buttons": [
            {"label": "Felt easy", "action": "report_easy"},
            {"label": "Just right", "action": "report_right"},
            {"label": "Really hard", "action": "report_hard"},
        ],
    },
    "rest": {
        "response": "Take your time. Ready when you are.",
        "buttons": [{"label": "Skip Rest", "action": "skip_rest"}],
    },
    "post_workout": {
        "response": "Great work today! You crushed it.",
        "buttons": [{"label": "Thanks!", "action": "dismiss"}],
    },
}


async def process_chat(
    user_message: str,
    context: str,
    session_data: Optional[dict] = None,
    user_context: Optional[dict] = None,
) -> dict:
    """Process a workout chat message. Returns dict matching ChatResponse shape."""
    session_data = session_data or {}
    user_context = user_context or {}

    # Try LLM
    result = await _try_llm_chat(user_message, context, session_data, user_context)
    if result:
        return result

    # Template fallback
    return _template_chat(user_message, context, session_data)


async def _try_llm_chat(user_message: str, context: str, session_data: dict, user_context: dict) -> Optional[dict]:
    """Try LLM for chat response."""
    try:
        from .llm_service import chat as llm_chat
        system_prompt = _build_system_prompt(context, session_data, user_context)
        if not system_prompt:
            return None

        opening = "Greet the user briefly and present today's workout plan. Ask if they're ready or want to make changes."
        result = await llm_chat(system_prompt, user_message or opening)
        if not result:
            return None

        actions = []
        action = result.get("action")
        if action and isinstance(action, dict) and action.get("type"):
            actions.append({"type": action["type"], "params": action.get("params", {})})

        suggested_options = [
            {"label": b.get("label", ""), "value": b.get("action", "")}
            for b in result.get("suggested_buttons", [])
        ]

        return {
            "response": result.get("response", ""),
            "actions": actions,
            "suggested_options": suggested_options,
        }
    except Exception as e:
        logger.warning("LLM chat failed: %s", e)
        return None


def _build_system_prompt(context: str, session_data: dict, user_context: dict) -> Optional[str]:
    if context == "pre_workout":
        exercises = session_data.get("exercises", [])
        plan_lines = []
        for i, ex in enumerate(exercises, 1):
            name = ex.get("name", ex.get("slug", "?"))
            sets = ex.get("sets", "?")
            reps = ex.get("reps", "?")
            plan_lines.append(f"{i}. {name} — {sets}x{reps}")
        return PRE_WORKOUT_SYSTEM.format(
            plan_summary="\n".join(plan_lines) if plan_lines else "No exercises loaded"
        )
    elif context in ("post_set", "rest"):
        return REST_SYSTEM.format(
            last_set=str(session_data.get("last_set", {})),
            exercise_name=session_data.get("exercise_name", "current exercise"),
            progress=str(session_data.get("progress", {})),
        )
    elif context == "post_workout":
        return POST_WORKOUT_SYSTEM.format(summary=str(session_data.get("summary", {})))
    return None


def _template_chat(user_message: str, context: str, session_data: dict) -> dict:
    """Generate response using templates (LLM fallback)."""
    msg_lower = user_message.lower().strip()

    if context == "pre_workout":
        tmpl = TEMPLATES["pre_workout"]
        exercises = session_data.get("exercises", [])
        actions = []
        buttons = tmpl["buttons"]

        if any(kw in msg_lower for kw in ("let's go", "lets go", "start", "begin", "ready")):
            actions = [{"type": "begin_workout", "params": {}}]
            response = "Let's do this!"

        elif any(kw in msg_lower for kw in ("swap", "replace", "change", "different")):
            ex_names = [e.get("name", e.get("slug", "?")) for e in exercises]
            if ex_names:
                response = "Which exercise would you like to swap? You have: " + ", ".join(ex_names) + "."
            else:
                response = "I don't see any exercises loaded yet. Try starting the workout first."
            buttons = [{"label": name, "action": f"swap_{e.get('slug', '')}"} for e, name in zip(exercises[:4], ex_names[:4])]

        elif any(kw in msg_lower for kw in ("shorter", "less time", "quick", "fewer", "reduce")):
            if len(exercises) > 2:
                removed = exercises[-1]
                response = f"I can drop {removed.get('name', 'the last exercise')} to make it shorter. Or I can reduce sets. What do you prefer?"
                buttons = [
                    {"label": f"Drop {removed.get('name', 'last')}", "action": "remove_last"},
                    {"label": "Fewer sets", "action": "reduce_sets"},
                    {"label": "Keep it", "action": "dismiss"},
                ]
            else:
                response = "The workout is already pretty short! Want to reduce sets instead?"
                buttons = [
                    {"label": "Fewer sets", "action": "reduce_sets"},
                    {"label": "Keep it", "action": "dismiss"},
                ]

        elif any(kw in msg_lower for kw in ("how do", "how to", "explain", "what is", "show me", "form", "technique", "tips")):
            # Exercise question — try to find form cues from session exercises
            response = _answer_exercise_question(msg_lower, exercises)
            buttons = [
                {"label": "Got it, let's go!", "action": "begin_workout"},
                {"label": "Ask another", "action": "dismiss"},
            ]

        else:
            # Default: show greeting with standard buttons
            response = tmpl["greeting"].format(
                day_label=session_data.get("day_label", "Today's workout"),
                exercise_count=len(exercises),
                estimated_minutes=session_data.get("estimated_minutes", 45),
            )

        return {
            "response": response,
            "actions": actions,
            "suggested_options": [{"label": b["label"], "value": b.get("action", b.get("value", ""))} for b in buttons],
        }

    elif context == "post_set":
        tmpl = TEMPLATES["post_set"]
        actions = []
        suggested = [{"label": b["label"], "value": b["action"]} for b in tmpl["buttons"]]

        if "easy" in msg_lower or "light" in msg_lower:
            response = tmpl["responses"]["easy"]
            exercise_id = session_data.get("exercise_id")
            current_weight = session_data.get("current_weight_kg", 0)
            if exercise_id and current_weight:
                new_weight = current_weight + 2.5
                actions = [{"type": "adjust_next_set", "params": {
                    "exercise_id": exercise_id, "weight_kg": new_weight,
                }}]
                suggested = [
                    {"label": f"Yes, go to {new_weight}kg", "value": "confirm_adjust"},
                    {"label": "Keep it", "value": "dismiss"},
                ]
        elif "hard" in msg_lower or "heavy" in msg_lower or "tough" in msg_lower:
            response = tmpl["responses"]["hard"]
        elif "right" in msg_lower or "good" in msg_lower or "perfect" in msg_lower:
            response = tmpl["responses"]["just_right"]
        else:
            response = tmpl["responses"]["default"]

        return {"response": response, "actions": actions, "suggested_options": suggested}

    elif context == "rest":
        return {
            "response": TEMPLATES["rest"]["response"],
            "actions": [],
            "suggested_options": [{"label": b["label"], "value": b["action"]} for b in TEMPLATES["rest"]["buttons"]],
        }

    elif context == "post_workout":
        total_sets = session_data.get("total_sets", 0)
        total_exercises = session_data.get("total_exercises", 0)
        duration_min = session_data.get("duration_minutes", 0)
        if total_sets > 0:
            response = f"Great work! {total_exercises} exercises, {total_sets} sets in {duration_min} minutes."
        else:
            response = TEMPLATES["post_workout"]["response"]
        return {"response": response, "actions": [], "suggested_options": [{"label": "Thanks!", "value": "dismiss"}]}

    return {"response": "I'm here if you need anything!", "actions": [], "suggested_options": []}


def _answer_exercise_question(msg: str, session_exercises: list) -> str:
    """Try to answer an exercise question using seed data form cues."""
    from ..db_models.workout import Exercise
    from ....database import SessionLocal

    db = SessionLocal()
    try:
        # Find which exercise the user is asking about
        exercises = db.query(Exercise).all()
        matched = None
        for ex in exercises:
            name_lower = ex.name.lower()
            slug_lower = ex.slug.replace("-", " ")
            if name_lower in msg or slug_lower in msg:
                matched = ex
                break
        # Fuzzy: check if any word from exercise name appears
        if not matched:
            for ex in exercises:
                words = ex.name.lower().split()
                if any(w in msg for w in words if len(w) > 3):
                    matched = ex
                    break

        if matched and matched.form_cues:
            cues = matched.form_cues if isinstance(matched.form_cues, list) else []
            cue_text = "\n".join(f"• {c}" for c in cues[:4])
            mistakes = ""
            if matched.common_mistakes:
                m_list = matched.common_mistakes if isinstance(matched.common_mistakes, list) else []
                if m_list:
                    mistakes = "\n\nAvoid: " + "; ".join(m_list[:2]) + "."
            return f"Here's how to do {matched.name}:\n{cue_text}{mistakes}"
        elif matched:
            return f"{matched.name}: {matched.description or 'No detailed form guide yet — focus on controlled movement and proper range of motion.'}"
        else:
            return "I'm not sure which exercise you mean. Could you be more specific? I can explain form for any exercise in your plan."
    except Exception as e:
        logger.debug("Exercise question lookup failed: %s", e)
        return "Sorry, I couldn't look that up right now. Try asking again!"
    finally:
        db.close()
