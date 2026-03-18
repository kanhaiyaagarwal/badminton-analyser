"""Provider-agnostic LLM service layer.

Supports OpenAI, Anthropic, and Ollama backends.
Falls back gracefully if API keys are missing or calls fail.
"""

import json
import logging
import asyncio
from typing import Optional

from ....config import get_settings

logger = logging.getLogger(__name__)

# Maximum retries for API calls
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds


async def chat(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = True,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    messages: Optional[list[dict]] = None,
) -> Optional[dict]:
    """Send a chat request to the configured LLM provider.

    When *messages* is provided (list of {role, content} dicts), they are used
    as the conversation history instead of a single user_prompt.  The last
    entry should be the current user turn.

    Returns parsed JSON dict on success, None on failure (callers fall back to templates).
    """
    settings = get_settings()

    if not settings.llm_enabled:
        logger.debug("LLM disabled via config")
        return None

    provider = settings.llm_provider.lower()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if provider == "openai":
                return await _chat_openai(system_prompt, user_prompt, json_mode, temperature, max_tokens, messages)
            elif provider == "anthropic":
                return await _chat_anthropic(system_prompt, user_prompt, json_mode, temperature, max_tokens, messages)
            elif provider == "ollama":
                return await _chat_ollama(system_prompt, user_prompt, json_mode, temperature, max_tokens, messages)
            else:
                logger.warning(f"Unknown LLM provider: {provider}")
                return None
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(f"LLM call failed (attempt {attempt}/{MAX_RETRIES}): {e}. Retrying in {wait}s")
                await asyncio.sleep(wait)
            else:
                logger.error(f"LLM call failed after {MAX_RETRIES} attempts: {e}")
                return None


def _parse_json_response(text: str) -> Optional[dict]:
    """Extract JSON from LLM response text, handling markdown code blocks."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM JSON response: {text[:200]}")
        return None


async def _chat_openai(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    temperature: float,
    max_tokens: int,
    messages: Optional[list[dict]] = None,
) -> Optional[dict]:
    """Call OpenAI Chat Completions API."""
    settings = get_settings()
    if not settings.openai_api_key:
        logger.debug("OpenAI API key not set")
        return None

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    if messages:
        chat_messages = [{"role": "system", "content": system_prompt}] + messages
    else:
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    kwargs = {
        "model": settings.llm_model,
        "messages": chat_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    logger.info(
        f"OpenAI tokens: prompt={response.usage.prompt_tokens}, "
        f"completion={response.usage.completion_tokens}"
    )

    if json_mode:
        return _parse_json_response(content)
    return {"text": content}


async def _chat_anthropic(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    temperature: float,
    max_tokens: int,
    messages: Optional[list[dict]] = None,
) -> Optional[dict]:
    """Call Anthropic Messages API."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.debug("Anthropic API key not set")
        return None

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    model = settings.llm_model
    # Map generic model names to Anthropic models
    if model.startswith("gpt"):
        model = "claude-sonnet-4-20250514"

    suffix = ""
    if json_mode:
        suffix = "\n\nRespond with valid JSON only, no markdown or explanation."

    chat_messages = messages if messages else [{"role": "user", "content": user_prompt}]

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt + suffix,
        messages=chat_messages,
        temperature=temperature,
    )
    content = response.content[0].text

    logger.info(
        f"Anthropic tokens: input={response.usage.input_tokens}, "
        f"output={response.usage.output_tokens}"
    )

    if json_mode:
        return _parse_json_response(content)
    return {"text": content}


async def _chat_ollama(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    temperature: float,
    max_tokens: int,
    messages: Optional[list[dict]] = None,
) -> Optional[dict]:
    """Call local Ollama API via HTTP."""
    settings = get_settings()
    import httpx

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    if messages:
        chat_messages = [{"role": "system", "content": system_prompt}] + messages
    else:
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    payload = {
        "model": settings.llm_model if not settings.llm_model.startswith("gpt") else "llama3",
        "messages": chat_messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    content = data.get("message", {}).get("content", "")
    logger.info(f"Ollama model={payload['model']}, response_len={len(content)}")

    if json_mode:
        return _parse_json_response(content)
    return {"text": content}
