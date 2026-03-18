"""Multi-turn conversational onboarding agent.

Manages in-memory conversation state. Each turn calls the existing
llm_service (if available) or uses a template sequence to collect
onboarding fields one-by-one.
"""

import asyncio
import logging
import re
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# TTL for conversations (30 minutes)
_CONVERSATION_TTL = 30 * 60

# In-memory conversation store: conversation_id -> ConversationState
_conversations: dict[str, "ConversationState"] = {}

REQUIRED_FIELDS = ["fitness_level", "goals", "preferred_days", "session_duration_minutes", "train_location"]
OPTIONAL_FIELDS = ["age", "height_cm", "weight_kg", "injuries", "available_equipment"]

SYSTEM_PROMPT = """You are a friendly AI fitness coach named Coach helping a new user set up their workout plan.
You're having a casual, encouraging conversation to learn about them.

Current collected data: {collected}
Still needed fields: {still_needed}

Rules:
- Ask about ONE topic at a time
- Keep responses short (1-2 sentences), warm, and encouraging
- When the user responds, extract any structured data you can
- Suggest 2-4 tappable options when relevant
- For goals, allow multiple selections
- For preferred_days, use day abbreviations: mon, tue, wed, thu, fri, sat, sun
- For train_location, use: gym or home
- For fitness_level, use: beginner, intermediate, advanced
- For session_duration_minutes, use: 20, 30, 45, or 60

Respond in this JSON format:
{{
  "response": "Your conversational message",
  "extracted_data": {{}},
  "suggested_options": [{{"label": "Display Text", "value": "actual_value"}}],
  "all_collected": false
}}

Set all_collected to true ONLY when all required fields are collected."""


class ConversationState:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.collected: dict = {}
        self.messages: list[dict] = []
        self.created_at = time.time()
        self.step = 0  # For template fallback

    @property
    def still_needed(self) -> list[str]:
        return [f for f in REQUIRED_FIELDS if f not in self.collected]

    @property
    def all_collected(self) -> bool:
        return len(self.still_needed) == 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > _CONVERSATION_TTL


# Template fallback sequence (when LLM is unavailable)
TEMPLATE_STEPS = [
    {
        "response": "Hey! I'm your AI fitness coach. Let's get you set up — takes about a minute. How would you describe your fitness level?",
        "field": "fitness_level",
        "options": [
            {"label": "Beginner", "value": "beginner"},
            {"label": "Intermediate", "value": "intermediate"},
            {"label": "Advanced", "value": "advanced"},
        ],
    },
    {
        "response": "Anything about yourself I should know? Age, height, injuries? Feel free to skip if you'd rather not say.",
        "field": None,  # Free-form optional step
        "options": [{"label": "Skip this", "value": "__skip__"}],
    },
    {
        "response": "What are you training for? Pick all that apply.",
        "field": "goals",
        "multi": True,
        "options": [
            {"label": "Build Muscle", "value": "build_muscle"},
            {"label": "Lose Fat", "value": "lose_fat"},
            {"label": "Get Stronger", "value": "get_stronger"},
            {"label": "Stay Active", "value": "stay_active"},
        ],
    },
    {
        "response": "Which days do you want to train?",
        "field": "preferred_days",
        "multi": True,
        "options": [
            {"label": "Mon", "value": "mon"},
            {"label": "Tue", "value": "tue"},
            {"label": "Wed", "value": "wed"},
            {"label": "Thu", "value": "thu"},
            {"label": "Fri", "value": "fri"},
            {"label": "Sat", "value": "sat"},
            {"label": "Sun", "value": "sun"},
        ],
    },
    {
        "response": "How long per session?",
        "field": "session_duration_minutes",
        "options": [
            {"label": "20 min", "value": "20"},
            {"label": "30 min", "value": "30"},
            {"label": "45 min", "value": "45"},
            {"label": "60 min", "value": "60"},
            {"label": "Flexible", "value": "flexible"},
        ],
    },
    {
        "response": "Gym or home workouts?",
        "field": "train_location",
        "options": [
            {"label": "Gym", "value": "gym"},
            {"label": "Home", "value": "home"},
        ],
    },
    {
        "response": "What equipment do you have access to?",
        "field": "available_equipment",
        "options": [
            {"label": "Full gym", "value": "barbell,dumbbells,bench,squat_rack,cable_machine"},
            {"label": "Dumbbells only", "value": "dumbbells"},
            {"label": "Bodyweight only", "value": "none"},
            {"label": "Skip", "value": "__skip__"},
        ],
    },
]


def cleanup_expired():
    """Remove expired conversations."""
    now = time.time()
    expired = [cid for cid, state in _conversations.items() if state.is_expired]
    for cid in expired:
        del _conversations[cid]


def get_or_create_conversation(conversation_id: Optional[str] = None) -> ConversationState:
    cleanup_expired()
    if conversation_id and conversation_id in _conversations:
        state = _conversations[conversation_id]
        if not state.is_expired:
            return state
    state = ConversationState()
    _conversations[state.id] = state
    return state


async def process_turn(conversation_id: Optional[str], user_message: str) -> dict:
    """Process one turn of onboarding conversation.

    Returns dict with: response, suggested_options, data_collected, onboarding_complete, conversation_id
    """
    state = get_or_create_conversation(conversation_id)

    # Opening turn (empty message)
    if not user_message and not state.messages:
        return await _opening_turn(state)

    state.messages.append({"role": "user", "content": user_message})
    logger.info("Onboarding turn [step=%d]: user='%s', collected_so_far=%s", state.step, user_message[:100], state.collected)

    # Always try to extract optional fields (age, height, weight, injuries)
    # from every message, regardless of which step we're on
    _extract_freeform(state, user_message)

    # For multi-select steps (goals, days), skip LLM — templates handle
    # these with proper multi-select pills that the LLM can't replicate
    use_template = False
    if state.step < len(TEMPLATE_STEPS) and TEMPLATE_STEPS[state.step].get("multi"):
        use_template = True

    if not use_template:
        # Try LLM first
        result = await _try_llm_turn(state, user_message)
        if result:
            logger.info("Onboarding LLM result: collected=%s, complete=%s", result.get("data_collected"), result.get("onboarding_complete"))
            # Safety net: if LLM didn't extract the current step's field,
            # try template extraction so we don't lose the user's input
            if state.step < len(TEMPLATE_STEPS):
                current = TEMPLATE_STEPS[state.step]
                field = current.get("field")
                if field and field not in state.collected:
                    _extract_template_data(state, current, user_message)
                    if field in state.collected:
                        logger.info("Template extraction rescued field '%s' from LLM miss", field)
                        result["data_collected"] = state.collected
            return result

    # Template fallback (or forced for multi-select steps)
    result = _template_turn(state, user_message)
    logger.info("Onboarding template result: collected=%s, complete=%s", result.get("data_collected"), result.get("onboarding_complete"))
    return result


async def _opening_turn(state: ConversationState) -> dict:
    """Generate the opening greeting."""
    result = await _try_llm_opening(state)
    if result:
        return result

    step = TEMPLATE_STEPS[0]
    state.messages.append({"role": "assistant", "content": step["response"]})
    return {
        "response": step["response"],
        "suggested_options": [{"label": o["label"], "value": o["value"]} for o in step["options"]],
        "data_collected": state.collected,
        "onboarding_complete": False,
        "conversation_id": state.id,
    }


async def _try_llm_opening(state: ConversationState) -> Optional[dict]:
    """Try LLM for the opening turn."""
    try:
        from .llm_service import chat as llm_chat
        prompt = SYSTEM_PROMPT.format(collected="{}", still_needed=str(REQUIRED_FIELDS))
        result = await llm_chat(prompt, "Start the conversation with a warm greeting and ask about fitness level.")
        if not result:
            return None

        state.messages.append({"role": "assistant", "content": result.get("response", "")})
        return {
            "response": result.get("response", TEMPLATE_STEPS[0]["response"]),
            "suggested_options": result.get("suggested_options", TEMPLATE_STEPS[0]["options"]),
            "data_collected": state.collected,
            "onboarding_complete": False,
            "conversation_id": state.id,
        }
    except Exception as e:
        logger.debug("LLM opening failed: %s", e)
        return None


async def _try_llm_turn(state: ConversationState, user_message: str) -> Optional[dict]:
    """Try LLM for a conversation turn."""
    try:
        from .llm_service import chat as llm_chat
        prompt = SYSTEM_PROMPT.format(
            collected=str(state.collected),
            still_needed=str(state.still_needed),
        )
        # Build conversation as single user prompt (since llm_service.chat takes system + user)
        convo_text = "\n".join(
            f"{'Coach' if m['role'] == 'assistant' else 'User'}: {m['content']}"
            for m in state.messages[-6:]  # Last 6 messages for context
        )
        result = await llm_chat(prompt, convo_text)
        if not result:
            return None

        logger.info("LLM raw response: %s", {k: v for k, v in result.items() if k != 'suggested_options'})

        # Extract data
        extracted = result.get("extracted_data", {})
        if extracted:
            for key, val in extracted.items():
                if key in REQUIRED_FIELDS or key in OPTIONAL_FIELDS:
                    state.collected[key] = val
            logger.info("LLM extracted: %s -> collected: %s", extracted, state.collected)

        response_text = result.get("response", "")
        state.messages.append({"role": "assistant", "content": response_text})

        # Advance step to match what the LLM collected
        while state.step < len(TEMPLATE_STEPS):
            field = TEMPLATE_STEPS[state.step].get("field")
            if field and field in state.collected:
                state.step += 1
            elif not field:
                # Skip non-field steps (freeform) if LLM already passed them
                state.step += 1
            else:
                break

        all_done = state.all_collected or result.get("all_collected", False)
        if all_done:
            # Fill defaults for any still-missing required fields
            defaults = {
                "fitness_level": "beginner",
                "goals": ["stay_active"],
                "preferred_days": ["mon", "wed", "fri"],
                "session_duration_minutes": 45,
                "train_location": "gym",
            }
            for key, val in defaults.items():
                if key not in state.collected:
                    state.collected[key] = val

        # If the next step is multi-select, override LLM options with template pills
        suggested = result.get("suggested_options", [])
        if not all_done and state.step < len(TEMPLATE_STEPS):
            next_step = TEMPLATE_STEPS[state.step]
            if next_step.get("multi"):
                suggested = [{"label": o["label"], "value": o["value"], "multi": True} for o in next_step["options"]]

        return {
            "response": response_text,
            "suggested_options": suggested,
            "data_collected": state.collected,
            "onboarding_complete": all_done,
            "conversation_id": state.id,
        }
    except Exception as e:
        logger.warning("LLM turn failed: %s", e)
        return None


def _template_turn(state: ConversationState, user_message: str) -> dict:
    """Process a turn using template sequence (LLM fallback)."""
    if state.step < len(TEMPLATE_STEPS):
        current = TEMPLATE_STEPS[state.step]
        _extract_template_data(state, current, user_message)

    state.step += 1

    if state.step >= len(TEMPLATE_STEPS) or state.all_collected:
        # Fill defaults for any missing required fields
        defaults = {
            "fitness_level": "beginner",
            "goals": ["stay_active"],
            "preferred_days": ["mon", "wed", "fri"],
            "session_duration_minutes": 45,
            "train_location": "gym",
        }
        for key, val in defaults.items():
            if key not in state.collected:
                state.collected[key] = val
        return {
            "response": "Perfect! I've got everything I need. Building your plan now...",
            "suggested_options": [],
            "data_collected": state.collected,
            "onboarding_complete": True,
            "conversation_id": state.id,
        }

    next_step = TEMPLATE_STEPS[state.step]
    state.messages.append({"role": "assistant", "content": next_step["response"]})
    opts = [{"label": o["label"], "value": o["value"]} for o in next_step["options"]]
    if next_step.get("multi"):
        for o in opts:
            o["multi"] = True
    return {
        "response": next_step["response"],
        "suggested_options": opts,
        "data_collected": state.collected,
        "onboarding_complete": False,
        "conversation_id": state.id,
    }


def _extract_template_data(state: ConversationState, step: dict, user_message: str):
    """Extract structured data from user response for a template step."""
    field = step.get("field")
    msg = user_message.strip().lower()

    # Always try to extract optional fields (age/height/weight/injuries)
    # from every message, regardless of which step we're on
    before = dict(state.collected)
    _extract_freeform(state, user_message)
    freeform_extracted = {k: v for k, v in state.collected.items() if k not in before or before[k] != v}
    if freeform_extracted:
        logger.info("Freeform extracted from '%s': %s", user_message[:80], freeform_extracted)

    if not field or msg == "__skip__":
        return

    if field == "fitness_level":
        for opt in step["options"]:
            if opt["value"] in msg or opt["label"].lower() in msg:
                state.collected["fitness_level"] = opt["value"]
                return
        state.collected["fitness_level"] = msg if msg in ("beginner", "intermediate", "advanced") else "beginner"

    elif field == "goals":
        goals = []
        for opt in step["options"]:
            if opt["value"] in msg or opt["label"].lower() in msg:
                goals.append(opt["value"])
        if not goals:
            goals = [v.strip() for v in user_message.split(",") if v.strip()]
        state.collected["goals"] = goals if goals else ["stay_active"]

    elif field == "preferred_days":
        # Parse day names from natural language / abbreviations / comma-separated
        day_map = {
            "monday": "mon", "mon": "mon",
            "tuesday": "tue", "tue": "tue", "tues": "tue",
            "wednesday": "wed", "wed": "wed",
            "thursday": "thu", "thu": "thu", "thurs": "thu",
            "friday": "fri", "fri": "fri",
            "saturday": "sat", "sat": "sat",
            "sunday": "sun", "sun": "sun",
        }
        valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        found_days = []

        # Check for full/short day names in the message
        for name, abbr in day_map.items():
            if name in msg and abbr not in found_days:
                found_days.append(abbr)

        # Also try comma-separated values (e.g., "mon,wed,fri" from multi-select)
        if not found_days:
            parts = [d.strip() for d in msg.split(",") if d.strip()]
            found_days = [p for p in parts if p in valid_days]

        state.collected["preferred_days"] = found_days if found_days else ["mon", "wed", "fri"]

    elif field == "session_duration_minutes":
        if "flexible" in msg or "flex" in msg:
            state.collected["session_duration_minutes"] = 45
            return
        for val in ("20", "30", "45", "60"):
            if val in msg:
                state.collected["session_duration_minutes"] = int(val)
                return
        state.collected["session_duration_minutes"] = 45

    elif field == "train_location":
        state.collected["train_location"] = "home" if "home" in msg else "gym"

    elif field == "available_equipment":
        if msg == "__skip__" or "skip" in msg:
            return
        for opt in step["options"]:
            if opt["value"] == msg or opt["label"].lower() in msg:
                if opt["value"] == "none":
                    state.collected["available_equipment"] = []
                else:
                    state.collected["available_equipment"] = opt["value"].split(",")
                return


def _extract_freeform(state: ConversationState, text: str):
    """Try to extract optional fields from free-form text."""
    lower = text.lower()

    # Age: "25 years old", "I'm 25", "age 25", "25 yo", bare "25" if plausible
    age_match = re.search(r'(?:i\'?m\s+|age\s*:?\s*|i am\s+)(\d{2})\b', lower)
    if not age_match:
        age_match = re.search(r'\b(\d{2})\s*(?:years?\s*old|yo|yrs)\b', lower)
    if age_match:
        age = int(age_match.group(1))
        if 13 <= age <= 100:
            state.collected["age"] = age

    # Height: "175cm", "175 cm", "5'11", "5 feet 11", "height 175"
    height_match = re.search(r'(?:height\s*:?\s*)?(\d{3})\s*(?:cm)?\b', lower)
    if height_match:
        h = int(height_match.group(1))
        if 100 <= h <= 250:
            state.collected["height_cm"] = h
    else:
        # Feet/inches: 5'11 or 5 feet 11
        ft_match = re.search(r"(\d)'?\s*(?:feet|ft|foot)?\s*(\d{1,2})?", lower)
        if ft_match:
            feet = int(ft_match.group(1))
            inches = int(ft_match.group(2)) if ft_match.group(2) else 0
            if 4 <= feet <= 7:
                state.collected["height_cm"] = round(feet * 30.48 + inches * 2.54)

    # Weight: "75kg", "75 kg", "75 kgs", "75 kilos", "weigh 75", "weight 75", bare number near "kg"
    weight_match = re.search(r'(?:weigh[t]?\s*:?\s*|i\'?m\s+)?(\d{2,3})\s*(?:kg|kgs|kilos?)\b', lower)
    if not weight_match:
        weight_match = re.search(r'(?:weigh[t]?\s*:?\s*|weight\s*:?\s*)(\d{2,3})\b', lower)
    if weight_match:
        w = int(weight_match.group(1))
        if 30 <= w <= 300:
            state.collected["weight_kg"] = w

    # Injuries
    injury_keywords = ["back", "knee", "shoulder", "wrist", "ankle", "hip", "neck", "elbow"]
    injuries = [kw for kw in injury_keywords if kw in lower]
    if injuries:
        state.collected["injuries"] = injuries


def remove_conversation(conversation_id: str):
    """Clean up a completed conversation."""
    _conversations.pop(conversation_id, None)
