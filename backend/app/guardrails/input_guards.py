"""
FinBot Input Guardrails
Checks applied to user input BEFORE any LLM or retrieval processing.
"""

import re
import logging
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session Rate Limiter (in-memory)
# ---------------------------------------------------------------------------
_session_counters: dict[str, int] = defaultdict(int)


def check_rate_limit(session_id: str, limit: int = 20) -> Optional[str]:
    """
    Check if a session has exceeded the rate limit.
    Returns a warning message if exceeded, else None.
    """
    _session_counters[session_id] += 1
    count = _session_counters[session_id]

    if count > limit:
        logger.warning(f"Rate limit exceeded for session {session_id}: {count}/{limit}")
        return (
            f"⚠️ You have exceeded the session query limit ({limit} queries). "
            f"Please start a new session or contact your administrator."
        )

    if count == limit:
        logger.info(f"Session {session_id} has reached the rate limit ({limit})")
        return (
            f"⚠️ Warning: You have reached the session query limit ({limit} queries). "
            f"This is your last query in this session."
        )

    return None


def reset_rate_limit(session_id: str) -> None:
    """Reset the rate limit counter for a session."""
    _session_counters[session_id] = 0


# ---------------------------------------------------------------------------
# PII Detection and Scrubbing
# ---------------------------------------------------------------------------

# Patterns for PII detection
PII_PATTERNS = {
    "aadhaar": {
        "pattern": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
        "description": "Aadhaar number",
    },
    "bank_account": {
        "pattern": re.compile(r"\b\d{9,18}\b"),  # typical bank account lengths
        "description": "bank account number",
    },
    "email": {
        "pattern": re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        "description": "email address",
    },
    "credit_card": {
        "pattern": re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        ),
        "description": "credit card number",
    },
    "phone": {
        "pattern": re.compile(
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "description": "phone number",
    },
    "pan": {
        "pattern": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
        "description": "PAN number",
    },
}


def check_pii(text: str) -> Optional[str]:
    """
    Detect PII in the user's query.
    Returns a warning message if PII is found, else None.
    """
    detected = []
    for pii_type, info in PII_PATTERNS.items():
        if info["pattern"].search(text):
            detected.append(info["description"])

    if detected:
        pii_list = ", ".join(detected)
        logger.warning(f"PII detected in query: {pii_list}")
        return (
            f"⚠️ Your query appears to contain personal information ({pii_list}). "
            f"For your security, please do not include personal data in your queries. "
            f"Your query has been blocked."
        )

    return None


# ---------------------------------------------------------------------------
# Prompt Injection Detection (keyword-based supplement to semantic router)
# ---------------------------------------------------------------------------

INJECTION_KEYWORDS = [
    "ignore your instructions",
    "ignore previous instructions",
    "ignore all instructions",
    "disregard your instructions",
    "forget your instructions",
    "override your",
    "bypass",
    "act as a different",
    "you are now",
    "pretend you",
    "no restrictions",
    "show me all documents regardless",
    "show me everything",
    "admin mode",
    "developer mode",
    "jailbreak",
    "DAN mode",
]


def check_prompt_injection(text: str) -> Optional[str]:
    """
    Detect prompt injection attempts using keyword matching.
    This supplements the semantic router's injection detection.
    Returns a warning message if injection detected, else None.
    """
    text_lower = text.lower()
    for keyword in INJECTION_KEYWORDS:
        if keyword.lower() in text_lower:
            logger.warning(f"Prompt injection detected: matched '{keyword}'")
            return (
                "🚫 Prompt injection detected. Your query has been blocked. "
                "Please use the system as intended within your authorized scope."
            )
    return None


# ---------------------------------------------------------------------------
# Combined Input Guard
# ---------------------------------------------------------------------------

def run_input_guards(
    query: str,
    session_id: str,
    rate_limit: int = 20,
) -> Optional[dict]:
    """
    Run all input guardrails on a query.

    Returns:
        None if all checks pass, or a dict with:
        - blocked: True
        - reason: Description of why
        - guardrail_type: Type of guardrail triggered
    """
    # 1. Rate limiting
    rate_msg = check_rate_limit(session_id, rate_limit)
    if rate_msg and _session_counters[session_id] > rate_limit:
        return {
            "blocked": True,
            "reason": rate_msg,
            "guardrail_type": "rate_limit",
        }

    # 2. PII detection
    pii_msg = check_pii(query)
    if pii_msg:
        return {
            "blocked": True,
            "reason": pii_msg,
            "guardrail_type": "pii_detected",
        }

    # 3. Prompt injection (keyword-based)
    injection_msg = check_prompt_injection(query)
    if injection_msg:
        return {
            "blocked": True,
            "reason": injection_msg,
            "guardrail_type": "prompt_injection",
        }

    # Rate limit warning (not blocking)
    if rate_msg:
        return {
            "blocked": False,
            "reason": rate_msg,
            "guardrail_type": "rate_limit_warning",
        }

    return None
