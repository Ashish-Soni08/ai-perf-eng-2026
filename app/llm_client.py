"""
LLM client for Nebius Token Factory.

Uses the OpenAI-compatible SDK to call the Nebius inference endpoint.
Handles prompt construction, JSON response parsing, and error recovery.
"""

import json
import logging
import re

from openai import AsyncOpenAI, APIError, APITimeoutError, APIConnectionError

from app.config import (
    NEBIUS_API_KEY,
    NEBIUS_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
)

logger = logging.getLogger(__name__)


# ── System Prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a senior software engineer and technical analyst. Your task is to \
analyze a GitHub repository based on the provided metadata, directory structure, \
and source code files, then produce a structured summary.

You MUST return a valid JSON object with exactly these three fields:

{
  "summary": "<string: A clear, human-readable description of what this project does. 2-4 sentences. Focus on the project's purpose, key features, and target audience.>",
  "technologies": ["<string>", "..."],
  "structure": "<string: A brief description of how the project is organized — main directories, where core logic lives, where tests are, etc. 1-3 sentences.>"
}

Guidelines:
- "technologies" should list the primary programming languages, frameworks, \
libraries, and tools used (e.g. "Python", "FastAPI", "PostgreSQL", "Docker"). \
Include only significant dependencies, not every minor utility.
- Be specific and factual — base your analysis only on the provided content.
- Do NOT include markdown fences, comments, or any text outside the JSON object.
- Return ONLY the JSON object, nothing else.
"""

# ── User Prompt Template ──────────────────────────────────────────────

USER_PROMPT_TEMPLATE = """\
Analyze the following GitHub repository and return a JSON summary.

{context}
"""


# ── LLM Error ─────────────────────────────────────────────────────────

class LLMError(Exception):
    """Raised when the LLM call or response parsing fails."""

    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ── Client ────────────────────────────────────────────────────────────

def _get_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client pointed at Nebius Token Factory."""
    if not NEBIUS_API_KEY:
        raise LLMError(
            "NEBIUS_API_KEY environment variable is not set.",
            status_code=500,
        )
    return AsyncOpenAI(
        api_key=NEBIUS_API_KEY,
        base_url=NEBIUS_BASE_URL,
        timeout=LLM_TIMEOUT,
    )


def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from the LLM response text.

    Handles common LLM quirks:
    - Response wrapped in ```json ... ``` markdown fences
    - Leading/trailing whitespace or text outside the JSON
    - Smart quotes or other unicode substitutions
    """
    # Strip markdown code fences if present
    text = text.strip()
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(fence_pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object within the text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    raise LLMError(
        "LLM returned a response that could not be parsed as JSON. "
        "This is usually transient — please try again.",
        status_code=502,
    )


def _validate_response(data: dict) -> dict:
    """
    Validate that the parsed JSON has the required fields and types.

    Returns a cleaned dict with exactly: summary, technologies, structure.
    """
    summary = data.get("summary")
    technologies = data.get("technologies")
    structure = data.get("structure")

    if not isinstance(summary, str) or not summary.strip():
        raise LLMError("LLM response is missing a valid 'summary' field.")
    if not isinstance(technologies, list):
        raise LLMError("LLM response is missing a valid 'technologies' field.")
    if not isinstance(structure, str) or not structure.strip():
        raise LLMError("LLM response is missing a valid 'structure' field.")

    # Ensure all technology entries are strings
    technologies = [str(t) for t in technologies if t]

    return {
        "summary": summary.strip(),
        "technologies": technologies,
        "structure": structure.strip(),
    }


# ── Public API ────────────────────────────────────────────────────────


async def generate_summary(context: str) -> dict:
    """
    Send the repository context to the LLM and return a parsed summary.

    Args:
        context: The formatted repository context string from content_filter.

    Returns:
        A dict with keys: summary, technologies, structure.

    Raises:
        LLMError: If the LLM call fails or the response can't be parsed.
    """
    if not LLM_MODEL:
        raise LLMError(
            "LLM_MODEL is not configured. Please set a model name in app/config.py.",
            status_code=500,
        )

    client = _get_client()
    user_prompt = USER_PROMPT_TEMPLATE.format(context=context)

    logger.info(
        "Calling LLM model=%s, context_chars=%d", LLM_MODEL, len(context)
    )

    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
    except APITimeoutError:
        raise LLMError(
            "LLM request timed out. The repository may be too large, "
            "or the service is temporarily unavailable.",
            status_code=504,
        )
    except APIConnectionError:
        raise LLMError(
            "Could not connect to the Nebius Token Factory API. "
            "Please check your network connection.",
            status_code=502,
        )
    except APIError as exc:
        logger.error("Nebius API error: %s", exc)
        raise LLMError(
            f"Nebius API error: {exc.message}",
            status_code=exc.status_code or 502,
        )

    # Extract the response text — handle reasoning models like Kimi-K2.5
    # where content may be in `content` OR `reasoning_content`
    choice = response.choices[0] if response.choices else None
    if not choice or not choice.message:
        raise LLMError("LLM returned an empty response.")

    raw_text = None
    msg = choice.message

    # Prefer content (the final answer)
    if msg.content and msg.content.strip():
        raw_text = msg.content.strip()
    # Fallback: reasoning models may put everything in reasoning_content
    elif hasattr(msg, "reasoning_content") and msg.reasoning_content:
        logger.warning(
            "LLM content was empty — extracting from reasoning_content"
        )
        raw_text = msg.reasoning_content.strip()
    # Also check the 'reasoning' field (alternative attribute name)
    elif hasattr(msg, "reasoning") and msg.reasoning:
        logger.warning(
            "LLM content was empty — extracting from reasoning field"
        )
        raw_text = msg.reasoning.strip()

    if not raw_text:
        raise LLMError(
            "LLM returned an empty response (no content or reasoning). "
            "This may happen if max_tokens is too low for reasoning models.",
            status_code=502,
        )

    logger.info("LLM response received, length=%d chars", len(raw_text))

    # Parse and validate
    parsed = _extract_json(raw_text)
    validated = _validate_response(parsed)

    return validated

