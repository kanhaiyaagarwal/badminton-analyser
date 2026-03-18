"""Workout chat agent — handles all workout-phase conversations.

Contexts: pre_workout, post_set, rest, post_workout.
Uses the existing llm_service for LLM calls, falls back to templates.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

PRE_WORKOUT_SYSTEM = """You are Coach, a friendly AI fitness coach. The user is about to start their workout.
You can help them review and modify today's plan, AND answer any fitness or exercise questions.

Today's plan:
{plan_summary}

Available replacement exercises (same muscle groups):
{alternatives}

If the user asks HOW to do an exercise, explain the proper form in 2-3 concise bullet points.
If the user asks a general fitness question, answer helpfully.
If the user wants to modify the plan, use the appropriate action.

Available actions you can return (only when modifying the plan):
- swap_exercise: {{"type": "swap_exercise", "params": {{"old_slug": "...", "new_slug": "..."}}}}
- remove_exercise: {{"type": "remove_exercise", "params": {{"slug": "..."}}}}
- adjust_set: {{"type": "adjust_next_set", "params": {{"slug": "...", "sets": N, "reps": "N"}}}}
- begin_workout: {{"type": "begin_workout", "params": {{}}}}

IMPORTANT: For swap_exercise, new_slug MUST be from the replacement exercises list above.
IMPORTANT: When returning an action, also include a natural response confirming the change.

Respond in JSON:
{{
  "response": "Your message",
  "action": null or {{"type": "...", "params": {{...}}}},
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
    db=None,
    session_id: Optional[int] = None,
    user_id: Optional[int] = None,
    conversation_id: Optional[str] = None,
) -> dict:
    """Process a workout chat message. Returns dict matching ChatResponse shape."""
    session_data = session_data or {}
    user_context = user_context or {}

    # --- Conversation persistence ---
    cid = None
    if db and user_id:
        try:
            from .conversation_service import ConversationService
            cid = ConversationService.get_or_create(
                db, user_id, conversation_id, context, session_id,
            )
            # Log the user message
            ConversationService.add_message(
                db, cid, "user", user_message, context=context, source="user",
            )
        except Exception as e:
            logger.warning("Conversation persistence failed (pre): %s", e)
            cid = conversation_id  # fall through without persistence

    # Build conversation history for LLM
    history = None
    if db and cid:
        try:
            from .conversation_service import ConversationService
            history = ConversationService.get_history(db, cid)
        except Exception:
            pass

    # For action-pattern messages (swap, remove, begin, shorter, confirm_swap),
    # skip LLM and use templates directly — they have carefully designed
    # multi-step flows with proper exercise pills.
    source = "template"
    use_template = _is_action_pattern(user_message, context)

    if use_template:
        result = _template_chat(user_message, context, session_data)
    else:
        # Try LLM (with history) for freeform questions
        result = await _try_llm_chat(user_message, context, session_data, user_context, history=history)
        if result:
            source = "llm"
        else:
            result = _template_chat(user_message, context, session_data)

    # Execute any plan-modifying actions directly in DB
    if db and session_id and result.get("actions"):
        result = _execute_actions(db, session_id, user_id, result, session_data)

    # Log assistant response
    if db and cid:
        try:
            from .conversation_service import ConversationService
            ConversationService.add_message(
                db, cid, "assistant", result.get("response", ""),
                context=context, source=source,
                actions=result.get("actions"),
            )
        except Exception as e:
            logger.warning("Conversation persistence failed (post): %s", e)

    # Attach conversation_id so frontend can persist it
    result["conversation_id"] = cid or conversation_id
    return result


def _execute_actions(db, session_id: int, user_id: int, result: dict, session_data: dict) -> dict:
    """Execute plan-modifying actions from chat and return updated result."""
    from ..db_models.workout import WorkoutSession, Exercise

    session = db.query(WorkoutSession).filter(
        WorkoutSession.id == session_id,
    ).first()
    if not session or not session.planned_exercises:
        return result

    planned = list(session.planned_exercises)
    modified = False

    for action in result.get("actions", []):
        action_type = action.get("type")
        params = action.get("params", {})

        if action_type == "swap_exercise":
            old_slug = params.get("old_slug", "")
            new_slug = params.get("new_slug", "")
            if old_slug and new_slug:
                # Look up the new exercise in DB
                new_ex = db.query(Exercise).filter(Exercise.slug == new_slug).first()
                if new_ex:
                    for i, ex in enumerate(planned):
                        if ex.get("slug") == old_slug:
                            planned[i] = {
                                **ex,
                                "slug": new_ex.slug,
                                "name": new_ex.name,
                                "exercise_id": new_ex.id,
                            }
                            modified = True
                            break

        elif action_type == "remove_exercise":
            slug = params.get("slug") or params.get("exercise_slug", "")
            exercise_id = params.get("exercise_id")
            if len(planned) > 1:
                new_planned = [
                    ex for ex in planned
                    if ex.get("slug") != slug and (not exercise_id or ex.get("exercise_id") != exercise_id)
                ]
                if len(new_planned) < len(planned):
                    planned = new_planned
                    modified = True

        elif action_type == "adjust_next_set":
            slug = params.get("slug", "")
            exercise_id = params.get("exercise_id")
            for i, ex in enumerate(planned):
                if ex.get("slug") == slug or (exercise_id and ex.get("exercise_id") == exercise_id):
                    if "sets" in params:
                        planned[i] = {**planned[i], "sets": int(params["sets"])}
                    if "reps" in params:
                        planned[i] = {**planned[i], "reps": str(params["reps"])}
                    modified = True
                    break

    if modified:
        # Recompute order
        for i, ex in enumerate(planned):
            planned[i] = {**ex, "order": i}
        session.planned_exercises = planned
        db.commit()

        # Add a plan_updated action so frontend refreshes the exercise list
        result["actions"] = [{"type": "plan_updated", "params": {"exercises": planned}}]
    else:
        # Clear actions that couldn't be executed
        result["actions"] = []

    return result


async def _try_llm_chat(
    user_message: str, context: str, session_data: dict, user_context: dict,
    history: Optional[list] = None,
) -> Optional[dict]:
    """Try LLM for chat response."""
    try:
        from .llm_service import chat as llm_chat
        system_prompt = _build_system_prompt(context, session_data, user_context)
        if not system_prompt:
            return None

        opening = "Greet the user briefly and present today's workout plan. Ask if they're ready or want to make changes."
        user_prompt = user_message or opening

        # If we have conversation history, pass it as multi-turn messages
        messages = None
        if history and len(history) > 1:
            # history already includes the current user message as the last entry
            messages = history

        result = await llm_chat(system_prompt, user_prompt, messages=messages)
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


def _is_action_pattern(user_message: str, context: str) -> bool:
    """Return True if the message matches a known action pattern that templates
    handle better than the LLM (multi-step swap/remove flows with proper pills)."""
    if not user_message:
        return False
    msg = user_message.lower().strip()
    if context == "pre_workout":
        # Swap/replace flow, remove flow, begin, make shorter, confirm_swap
        action_keywords = (
            "swap", "replace", "change", "different", "switch",
            "remove", "delete", "drop", "skip",
            "let's go", "lets go", "start", "begin", "ready",
            "shorter", "less time", "quick", "fewer", "reduce",
        )
        if msg.startswith("confirm_swap "):
            return True
        if any(kw in msg for kw in action_keywords):
            return True
    return False


def _build_system_prompt(context: str, session_data: dict, user_context: dict) -> Optional[str]:
    if context == "pre_workout":
        exercises = session_data.get("exercises", [])
        plan_lines = []
        for i, ex in enumerate(exercises, 1):
            name = ex.get("name", ex.get("slug", "?"))
            sets = ex.get("sets", "?")
            reps = ex.get("reps", "?")
            plan_lines.append(f"{i}. {name} (slug: {ex.get('slug', '?')}) — {sets}x{reps}")

        # Build alternatives list
        alternatives = session_data.get("alternatives_text", "No alternatives loaded.")

        return PRE_WORKOUT_SYSTEM.format(
            plan_summary="\n".join(plan_lines) if plan_lines else "No exercises loaded",
            alternatives=alternatives,
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

        elif any(kw in msg_lower for kw in ("remove", "delete", "drop", "skip")):
            # Try to find which exercise the user wants to remove
            matched = _match_exercise_in_message(msg_lower, exercises)
            if matched and len(exercises) > 1:
                response = f"Done! Removed {matched['name']} from the plan."
                actions = [{"type": "remove_exercise", "params": {"slug": matched["slug"]}}]
                buttons = [
                    {"label": "Let's go!", "action": "begin_workout"},
                    {"label": "Remove another", "action": "remove_another"},
                ]
            elif len(exercises) <= 1:
                response = "You only have one exercise — can't remove it!"
                buttons = [{"label": "Let's go!", "action": "begin_workout"}]
            else:
                # Ask which one
                ex_names = [e.get("name", "?") for e in exercises]
                response = "Which exercise would you like to remove?"
                buttons = [
                    {"label": name, "action": f"remove {name.lower()}"}
                    for name in ex_names
                ]

        elif msg_lower.startswith("confirm_swap "):
            # User confirmed a swap: "confirm_swap old-slug new-slug"
            # Must be checked BEFORE swap keywords since the message contains "swap"
            parts = msg_lower.split()
            if len(parts) >= 3:
                old_slug = parts[1]
                new_slug = parts[2]
                old_ex = next((e for e in exercises if e.get("slug") == old_slug), None)
                old_name = old_ex.get("name", old_slug) if old_ex else old_slug
                actions = [{"type": "swap_exercise", "params": {"old_slug": old_slug, "new_slug": new_slug}}]
                response = f"Swapped {old_name}!"
                buttons = [
                    {"label": "Let's go!", "action": "begin_workout"},
                    {"label": "More changes", "action": "swap_exercise"},
                ]
            else:
                response = "Something went wrong with the swap. Try again?"
                buttons = tmpl["buttons"]

        elif any(kw in msg_lower for kw in ("swap", "replace", "change", "different", "switch")):
            matched = _match_exercise_in_message(msg_lower, exercises)
            alternatives = session_data.get("alternatives", [])

            if matched and alternatives:
                # User specified which exercise — show same-muscle-group alternatives
                muscle = matched.get("primary_muscle", "")
                alts = [a for a in alternatives if a.get("primary_muscle") == muscle and a.get("slug") != matched["slug"]]
                if not alts:
                    alts = alternatives[:5]  # fallback to any alternatives
                alts = alts[:5]

                if alts:
                    response = f"Replace {matched['name']} with:"
                    buttons = [
                        {"label": a["name"], "action": f"confirm_swap {matched['slug']} {a['slug']}"}
                        for a in alts
                    ]
                else:
                    response = f"I don't have alternative exercises for {matched['name']} right now. You can use the Edit button above to customize your plan."
                    buttons = [{"label": "OK", "action": "dismiss"}]
            elif matched and not alternatives:
                response = f"I don't have alternative exercises loaded right now. Use the Edit button above to customize your plan manually."
                buttons = [{"label": "OK", "action": "dismiss"}]
            else:
                # Ask which one to swap
                ex_names = [e.get("name", "?") for e in exercises]
                response = "Which exercise would you like to swap?"
                buttons = [
                    {"label": name, "action": f"swap {name.lower()}"}
                    for name in ex_names
                ]

        elif any(kw in msg_lower for kw in ("shorter", "less time", "quick", "fewer", "reduce")):
            if len(exercises) > 2:
                removed = exercises[-1]
                response = f"I'll drop {removed.get('name', 'the last exercise')} to make it shorter."
                actions = [{"type": "remove_exercise", "params": {"slug": removed.get("slug", "")}}]
                buttons = [
                    {"label": "Let's go!", "action": "begin_workout"},
                    {"label": "Even shorter", "action": "make_shorter"},
                    {"label": "Undo", "action": "undo"},
                ]
            else:
                response = "The workout is already pretty short! Want to reduce sets instead?"
                buttons = [
                    {"label": "Fewer sets", "action": "reduce_sets"},
                    {"label": "Keep it", "action": "dismiss"},
                ]

        elif any(kw in msg_lower for kw in ("how do", "how to", "explain", "what is", "show me", "form", "technique", "tips")):
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


def _match_exercise_in_message(msg: str, exercises: list) -> Optional[dict]:
    """Try to find which exercise from the plan the user is referring to."""
    msg = msg.lower()

    # Exact name match
    for ex in exercises:
        name = ex.get("name", "").lower()
        if name and name in msg:
            return ex

    # Slug match (e.g., "bench-press" or "bench press")
    for ex in exercises:
        slug = ex.get("slug", "").lower()
        if slug and (slug in msg or slug.replace("-", " ") in msg):
            return ex

    # Fuzzy: any significant word from exercise name
    for ex in exercises:
        name = ex.get("name", "").lower()
        words = [w for w in name.split() if len(w) > 3]
        if any(w in msg for w in words):
            return ex

    return None


def _answer_exercise_question(msg: str, session_exercises: list) -> str:
    """Try to answer an exercise question using seed data form cues."""
    from ..db_models.workout import Exercise
    from ....database import SessionLocal

    db = SessionLocal()
    try:
        exercises = db.query(Exercise).all()
        matched = None
        for ex in exercises:
            name_lower = ex.name.lower()
            slug_lower = ex.slug.replace("-", " ")
            if name_lower in msg or slug_lower in msg:
                matched = ex
                break
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
