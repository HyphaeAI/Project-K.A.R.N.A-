"""
OpenRouter Service for K.A.R.N.A. — Uses Step 3.5 Flash via OpenRouter.

Handles all interactions with the OpenRouter API:
  - Client initialization (uses OPENROUTER_API_KEY)
  - System prompt (unchanged from original design)
  - Question generation
  - Answer evaluation
  - Final summary generation
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt (unchanged)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = (
    "You are K.A.R.N.A. (Knowledge-based Autonomous Reasoning & Neutral Assessment), \n"
    "an unbiased technical interview evaluator.\n"
    "\n"
    "ABSOLUTE RULES:\n"
    "1. You will NEVER receive or consider any visual, demographic, or personal \n"
    "   information about the candidate. You evaluate ONLY the text transcript of \n"
    "their spoken answers.\n"
    "2. You must NEVER reference or infer the candidate's gender, age, race, \n"
    "   ethnicity, accent, educational background, or institutional affiliation.\n"
    "3. You evaluate answers solely on: logical coherence, depth of technical \n"
    "   understanding, problem-solving approach, communication clarity, and \n"
    "adaptability to edge cases.\n"
    "4. You must NEVER produce a final score below 0 or above 100 for any dimension.\n"
    "5. All your outputs must be valid, parseable JSON. No markdown, no prose wrapping.\n"
    "\n"
    "EVALUATION DIMENSIONS (all scores 0-100):\n"
    "- System Design\n"
    "- Problem Solving\n"
    "- Communication Clarity\n"
    "- Depth of Knowledge\n"
    "- Adaptability\n"
    "\n"
    "MEMORIZATION DETECTION:\n"
    "If a candidate's answer exhibits 2 or more of the following signals, flag \n"
    '"memorization_detected": true:\n'
    "- Uses textbook-exact phrasing or definitions verbatim\n"
    "- Lists concepts in a suspiciously ordered, enumerated fashion without \n"
    "  connecting them to the specific question context\n"
    "- Fails to provide concrete examples or personal experience\n"
    '- Uses filler phrases like "as we know" or "it is well known that"\n'
    "- Provides a generic answer that could apply to any similar question\n"
    "\n"
    "PROBE TRIGGERING LOGIC:\n"
    "- If memorization_detected == true -> Generate a specific EDGE-CASE follow-up \n"
    "  that forces the candidate to think beyond the memorized answer.\n"
    '- If answer_quality == "weak" or "vague" -> Generate a CLARIFICATION question \n'
    "  that drills into the specifics of what they said.\n"
    '- If answer_quality == "strong" -> Advance to the next topic area.'
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "stepfun/step-3.5-flash"  # You can change to any OpenRouter model

# ---------------------------------------------------------------------------
# Client singleton (OpenRouter uses stateless HTTP, no client object needed)
# ---------------------------------------------------------------------------

_api_key: Optional[str] = None


def init_openrouter_client() -> str:
    """Initialize OpenRouter configuration and return the API key.

    Sets the OPENROUTER_API_KEY from environment. Raises ValueError if not set.

    Returns:
        The OpenRouter API key string.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    global _api_key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
    _api_key = api_key
    logger.info("OpenRouter client initialized with model %s", MODEL_NAME)
    return api_key


def _get_api_key() -> str:
    """Return the API key, initializing on first call."""
    global _api_key
    if _api_key is None:
        _api_key = init_openrouter_client()
    return _api_key

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences from text."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1)
    return text


_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Return ONLY the raw JSON object, no markdown, no explanation."
)

# Step 3.5 Flash config (OpenRouter)
_GENERATION_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 2000,
}

# Retry backoff parameters
_BASE_DELAY = 1  # seconds
_MAX_DELAY = 16
_MAX_RETRIES = 2


def _call_openrouter(messages: list[dict[str, str]]) -> str:
    """Call OpenRouter ChatCompletion API and return the assistant's content.

    Retries on rate-limit errors (429) with exponential backoff.

    Args:
        messages: List of chat messages (role + content)

    Returns:
        The assistant's response text.

    Raises:
        ValueError: If response is not valid after all retries.
    """
    api_key = _get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional: Identify your app
        "X-Title": "K.A.R.N.A. Interview Evaluator",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": _GENERATION_CONFIG["temperature"],
        "max_tokens": _GENERATION_CONFIG["max_tokens"],
    }

    delay = _BASE_DELAY
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                # OpenAI format: choices[0].message.content
                content = data["choices"][0]["message"]["content"]
                return content
            elif response.status_code == 429:
                # Rate limited – retry after delay
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "OpenRouter rate limited (429), retrying in %.1fs...",
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, _MAX_DELAY)
                    continue
                else:
                    raise ValueError("OpenRouter rate limit exceeded after retries")
            else:
                logger.error(
                    "OpenRouter API error: %d %s",
                    response.status_code,
                    response.text[:200],
                )
                raise ValueError(f"OpenRouter API error {response.status_code}")

        except requests.RequestException as exc:
            logger.error("OpenRouter request failed: %s", exc)
            if attempt < _MAX_RETRIES:
                time.sleep(delay)
                delay = min(delay * 2, _MAX_DELAY)
                continue
            raise ValueError(f"OpenRouter request failed: {exc}") from exc

    raise ValueError("All retries exhausted")


def _call_with_retry(prompt: str, system_prompt: str = SYSTEM_PROMPT, max_retries: int = 2) -> dict[str, Any]:
    """Send prompt to OpenRouter and parse the JSON response, retrying on failure.

    Args:
        prompt: The full user prompt string.
        system_prompt: System instruction (defaults to SYSTEM_PROMPT).
        max_retries: Maximum number of additional attempts after the first.

    Returns:
        Parsed JSON response as a Python dict.

    Raises:
        ValueError: If all attempts are exhausted without valid JSON.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    current_prompt = prompt  # for suffix appending if needed

    for attempt in range(max_retries + 1):
        try:
            raw = _call_openrouter(messages)
            cleaned = _strip_json_fences(raw)
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "OpenRouter returned invalid JSON on attempt %d/%d: %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
            if attempt < max_retries:
                current_prompt = prompt + _RETRY_SUFFIX
                messages[1]["content"] = current_prompt
            else:
                raise ValueError("OpenRouter returned invalid JSON after retries") from exc
        except ValueError:
            # Propagate errors from _call_openrouter
            if attempt < max_retries:
                current_prompt = prompt + _RETRY_SUFFIX
                messages[1]["content"] = current_prompt
            else:
                raise

# ---------------------------------------------------------------------------
# Question generation (design §6.2)
# ---------------------------------------------------------------------------

def generate_initial_question(
    job_role: str,
    current_round: int,
    total_rounds: int,
    covered_topics: list[str],
    transcript_history: list[Any],
) -> dict[str, Any]:
    """Generate the next interview question for the given round.

    Builds the question-generation prompt, calls OpenRouter, and returns
    the parsed JSON response.

    Args:
        job_role: The role the candidate is being interviewed for.
        current_round: The current round number (1-indexed).
        total_rounds: Total number of rounds in the interview.
        covered_topics: List of topic areas already covered.
        transcript_history: List of previous Q&A records.

    Returns:
        A dict with keys: ``question_text``, ``topic_area``, ``question_type``,
        ``difficulty``.

    Raises:
        ValueError: If OpenRouter returns invalid JSON after all retries.
    """
    history_serialisable = [
        dataclasses.asdict(r) if dataclasses.is_dataclass(r) else r
        for r in transcript_history
    ]
    transcript_history_json = json.dumps(history_serialisable, indent=2)

    prompt = (
        "CONTEXT:\n"
        f"- Job Role: {job_role}\n"
        f"- Round: {current_round} of {total_rounds}\n"
        f"- Topics already covered: {covered_topics}\n"
        f"- Previous Q&A history: {transcript_history_json}\n"
        "\n"
        "TASK:\n"
        "Generate the next interview question. Choose a topic area from the EVALUATION \n"
        "DIMENSIONS list that has NOT been the primary focus of previous rounds (unless \n"
        "probing a weak area).\n"
        "\n"
        "OUTPUT FORMAT (strict JSON, no wrapping):\n"
        "{\n"
        '  "question_text": "...",\n'
        '  "topic_area": "...",\n'
        '  "question_type": "initial",\n'
        '  "difficulty": "medium" | "hard"\n'
        "}"
    )

    result = _call_with_retry(prompt)

    required = {"question_text", "topic_area", "question_type"}
    missing = required - result.keys()
    if missing:
        raise ValueError(
            f"OpenRouter question response missing required keys: {missing}"
        )

    logger.info(
        "Generated question for round %d/%d — topic: %s",
        current_round,
        total_rounds,
        result.get("topic_area"),
    )
    return result

# ---------------------------------------------------------------------------
# Answer evaluation (design §6.3)
# ---------------------------------------------------------------------------

_VALID_ANSWER_QUALITIES = {"strong", "moderate", "weak", "memorized", "vague"}
_SCORE_DIMENSIONS = [
    "System Design",
    "Problem Solving",
    "Communication Clarity",
    "Depth of Knowledge",
    "Adaptability",
]

_EVAL_FALLBACK: dict[str, Any] = {
    "scores": {
        "System Design": 50,
        "Problem Solving": 50,
        "Communication Clarity": 50,
        "Depth of Knowledge": 50,
        "Adaptability": 50,
    },
    "flags": {
        "memorization_detected": False,
        "answer_quality": "moderate",
    },
    "evaluator_notes": "Evaluation unavailable.",
    "probe_needed": False,
    "probe_question": None,
}


def _validate_evaluation(result: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize an evaluation response dict in-place.

    - Clamps all score values to [0, 100].
    - Defaults ``answer_quality`` to ``"moderate"`` if unrecognised.
    - Sets ``probe_needed=False`` when probe_question is missing or lacks
      ``question_text``.
    """
    scores = result.get("scores", {})
    for dim in _SCORE_DIMENSIONS:
        if dim in scores:
            try:
                scores[dim] = max(0, min(100, int(scores[dim])))
            except (TypeError, ValueError):
                scores[dim] = 50

    flags = result.get("flags", {})
    if flags.get("answer_quality") not in _VALID_ANSWER_QUALITIES:
        logger.warning(
            "Unexpected answer_quality %r — defaulting to 'moderate'.",
            flags.get("answer_quality"),
        )
        flags["answer_quality"] = "moderate"

    if result.get("probe_needed"):
        pq = result.get("probe_question")
        if not pq or not pq.get("question_text"):
            logger.warning(
                "probe_needed=True but probe_question is missing/incomplete — "
                "setting probe_needed=False."
            )
            result["probe_needed"] = False

    return result


def evaluate_answer(
    job_role: str,
    question_text: str,
    topic_area: str,
    transcript: str,
    current_round: int,
    total_rounds: int,
) -> dict[str, Any]:
    """Evaluate a candidate's answer using OpenRouter.

    Builds the evaluation prompt, calls OpenRouter, validates the response,
    and returns the sanitized evaluation dict.

    Args:
        job_role: The role the candidate is being interviewed for.
        question_text: The question that was asked.
        topic_area: The skill dimension being evaluated.
        transcript: The candidate's spoken answer (transcribed text).
        current_round: The current round number (1-indexed).
        total_rounds: Total number of rounds in the interview.

    Returns:
        A dict with keys: ``scores``, ``flags``, ``evaluator_notes``,
        ``probe_needed``, ``probe_question``. Falls back to
        :data:`_EVAL_FALLBACK` on total failure.
    """
    prompt = (
        "CONTEXT:\n"
        f"- Job Role: {job_role}\n"
        f"- Current Question: {question_text}\n"
        f"- Topic Area: {topic_area}\n"
        f'- Candidate\'s Transcript: "{transcript}"\n'
        f"- Round: {current_round} of {total_rounds}\n"
        "\n"
        "TASK:\n"
        "Evaluate the candidate's answer. Score each dimension. Detect memorization.\n"
        "Determine if a follow-up probe is needed.\n"
        "\n"
        "OUTPUT FORMAT (strict JSON, no wrapping):\n"
        "{\n"
        '  "scores": {\n'
        '    "System Design": <int 0-100>,\n'
        '    "Problem Solving": <int 0-100>,\n'
        '    "Communication Clarity": <int 0-100>,\n'
        '    "Depth of Knowledge": <int 0-100>,\n'
        '    "Adaptability": <int 0-100>\n'
        "  },\n"
        '  "flags": {\n'
        '    "memorization_detected": <bool>,\n'
        '    "answer_quality": "strong" | "moderate" | "weak" | "memorized" | "vague"\n'
        "  },\n"
        '  "evaluator_notes": "<1-2 sentence assessment>",\n'
        '  "probe_needed": <bool>,\n'
        '  "probe_question": {\n'
        '    "question_text": "...",\n'
        '    "topic_area": "...",\n'
        '    "question_type": "follow_up_probe" | "clarification"\n'
        "  }\n"
        "}"
    )

    try:
        result = _call_with_retry(prompt)
        return _validate_evaluation(result)
    except Exception as exc:
        logger.error(
            "evaluate_answer failed after retries — returning fallback. Error: %s",
            exc,
        )
        return dict(_EVAL_FALLBACK)

# ---------------------------------------------------------------------------
# Final summary (design §6.4)
# ---------------------------------------------------------------------------

def generate_final_summary(
    job_role: str,
    full_transcript_history: list[Any],
    all_round_scores: dict[str, Any],
) -> dict[str, Any]:
    """Generate the final aggregated assessment for a completed interview.

    Builds the summary prompt, calls OpenRouter, validates the response,
    and returns the parsed summary dict.

    Args:
        job_role: The role the candidate was interviewed for.
        full_transcript_history: List of RoundRecord dataclass instances
            (or plain dicts) representing the complete Q&A history.
        all_round_scores: Cumulative per-skill scores dict.

    Returns:
        A dict with keys: ``overall_score``, ``recommendation``,
        ``skill_scores``, ``flags``, ``summary``. Falls back to a minimal
        summary dict derived from *all_round_scores* on total failure.
    """
    history_serialisable = [
        dataclasses.asdict(r) if dataclasses.is_dataclass(r) else r
        for r in full_transcript_history
    ]
    transcript_history_json = json.dumps(history_serialisable, indent=2)
    all_round_scores_json = json.dumps(all_round_scores, indent=2)

    prompt = (
        "CONTEXT:\n"
        f"- Job Role: {job_role}\n"
        f"- Complete Q&A History: {transcript_history_json}\n"
        f"- Per-Round Scores: {all_round_scores_json}\n"
        "\n"
        "TASK:\n"
        "Produce the final aggregated assessment. Average the per-round scores for each \n"
        "dimension (weighted: initial questions = 1.0x, follow-up probes = 1.5x weight \n"
        "since they reveal true understanding). Generate an overall score and a \n"
        "recommendation tier.\n"
        "\n"
        "RECOMMENDATION TIERS:\n"
        '- "Strong": overall_score >= 75\n'
        '- "Moderate": 50 <= overall_score < 75\n'
        '- "Weak": overall_score < 50\n'
        "\n"
        "OUTPUT FORMAT (strict JSON, no wrapping):\n"
        "{\n"
        '  "overall_score": <int 0-100>,\n'
        '  "recommendation": "Strong" | "Moderate" | "Weak",\n'
        '  "skill_scores": {\n'
        '    "System Design": <int>,\n'
        '    "Problem Solving": <int>,\n'
        '    "Communication Clarity": <int>,\n'
        '    "Depth of Knowledge": <int>,\n'
        '    "Adaptability": <int>\n'
        "  },\n"
        '  "flags": {\n'
        '    "memorization_detected": <bool>,\n'
        '    "follow_up_triggered_count": <int>,\n'
        '    "total_questions_asked": <int>,\n'
        '    "total_rounds": <int>\n'
        "  },\n"
        '  "summary": "<2-3 sentence holistic assessment>"\n'
        "}"
    )

    try:
        result = _call_with_retry(prompt)

        valid_tiers = {"Strong", "Moderate", "Weak"}
        if result.get("recommendation") not in valid_tiers:
            overall = result.get("overall_score", 0)
            if overall >= 75:
                result["recommendation"] = "Strong"
            elif overall >= 50:
                result["recommendation"] = "Moderate"
            else:
                result["recommendation"] = "Weak"
            logger.warning(
                "Invalid recommendation tier from OpenRouter — recomputed as %r.",
                result["recommendation"],
            )

        logger.info(
            "Final summary generated — overall_score=%s, recommendation=%s",
            result.get("overall_score"),
            result.get("recommendation"),
        )
        return result

    except Exception as exc:
        logger.error(
            "generate_final_summary failed after retries — returning fallback. Error: %s",
            exc,
        )
        skill_scores = {dim: 50 for dim in _SCORE_DIMENSIONS}
        if isinstance(all_round_scores, dict):
            for dim in _SCORE_DIMENSIONS:
                if dim in all_round_scores:
                    try:
                        skill_scores[dim] = max(0, min(100, int(all_round_scores[dim])))
                    except (TypeError, ValueError):
                        pass

        overall = int(sum(skill_scores.values()) / len(skill_scores))
        if overall >= 75:
            recommendation = "Strong"
        elif overall >= 50:
            recommendation = "Moderate"
        else:
            recommendation = "Weak"

        return {
            "overall_score": overall,
            "recommendation": recommendation,
            "skill_scores": skill_scores,
            "flags": {
                "memorization_detected": False,
                "follow_up_triggered_count": 0,
                "total_questions_asked": 0,
                "total_rounds": 0,
            },
            "summary": "Summary unavailable due to an evaluation error.",
        }
