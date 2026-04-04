"""
FinBot Output Guardrails
Checks applied to LLM responses AFTER generation.
"""

import re
import logging
from typing import Optional

from app.config import COLLECTION_ACCESS_ROLES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source Citation Enforcement (Mandatory)
# ---------------------------------------------------------------------------

def check_source_citation(response: str) -> Optional[str]:
    """
    Verify that the response cites at least one source document.
    Returns a disclaimer string if citations are missing, else None.
    """
    # Check for common citation patterns
    citation_patterns = [
        r"source[:\s]",
        r"document[:\s]",
        r"page\s*\d+",
        r"according\s+to",
        r"as\s+stated\s+in",
        r"from\s+the\s+\w+\s+(report|handbook|document|doc|guide)",
        r"\.(pdf|docx|md|csv)",  # file extensions
        r"📄",  # document emoji sometimes used
    ]

    for pattern in citation_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            return None

    logger.info("Output guardrail: No source citation found in response")
    return (
        "\n\n⚠️ **Citation Warning**: This response may not include explicit source "
        "citations. Please verify the information against official FinSolve documents."
    )


# ---------------------------------------------------------------------------
# Grounding Check (Optional — financial figures)
# ---------------------------------------------------------------------------

def check_grounding(
    response: str,
    retrieved_chunks: list[dict],
) -> Optional[str]:
    """
    Compare financial figures, dates, and specific claims in the response
    against the retrieved chunks. Flag if ungrounded content is detected.

    Returns a disclaimer string if ungrounded content found, else None.
    """
    # Extract numbers from response (potential financial figures)
    response_numbers = set(re.findall(r"\$[\d,]+(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?", response))
    response_percentages = set(re.findall(r"\d+(?:\.\d+)?%", response))

    if not response_numbers and not response_percentages:
        return None  # No financial figures to verify

    # Extract numbers from retrieved context
    context_text = " ".join(
        chunk.get("text", "") for chunk in retrieved_chunks
    )
    context_numbers = set(re.findall(r"\$[\d,]+(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?", context_text))
    context_percentages = set(re.findall(r"\d+(?:\.\d+)?%", context_text))

    # Check for numbers in response that aren't in context
    ungrounded_numbers = response_numbers - context_numbers
    ungrounded_percentages = response_percentages - context_percentages

    if ungrounded_numbers or ungrounded_percentages:
        all_ungrounded = ungrounded_numbers | ungrounded_percentages
        logger.warning(
            f"Output guardrail: Potentially ungrounded figures: {all_ungrounded}"
        )
        return (
            "\n\n⚠️ **Grounding Warning**: This response contains financial figures "
            "or statistics that could not be directly traced to the retrieved source "
            "documents. Please verify these figures independently."
        )

    return None


# ---------------------------------------------------------------------------
# Cross-Role Leakage Check (Optional)
# ---------------------------------------------------------------------------

# Keywords strongly associated with specific collections
COLLECTION_KEYWORDS: dict[str, list[str]] = {
    "finance": [
        "revenue", "profit", "budget", "earnings", "fiscal",
        "dividend", "shareholder", "investor", "balance sheet",
        "income statement", "cash flow", "EBITDA", "ROI",
    ],
    "engineering": [
        "microservice", "API endpoint", "deployment", "CI/CD",
        "docker", "kubernetes", "sprint", "codebase", "repository",
        "pull request", "incident", "SLA", "uptime",
    ],
    "marketing": [
        "campaign", "brand awareness", "market share",
        "customer acquisition", "conversion rate", "CTR",
        "impressions", "engagement rate", "ad spend",
    ],
}


def check_cross_role_leakage(
    response: str,
    user_role: str,
    accessible_collections: list[str],
) -> Optional[str]:
    """
    Verify that the response doesn't contain terms from collections
    the user is not authorized to access.

    Returns a warning if leakage detected, else None.
    """
    response_lower = response.lower()
    leaked_collections = []

    for collection, keywords in COLLECTION_KEYWORDS.items():
        if collection in accessible_collections:
            continue  # User has access, not a leak

        hit_count = sum(1 for kw in keywords if kw.lower() in response_lower)
        if hit_count >= 2:  # Require multiple hits to reduce false positives
            leaked_collections.append(collection)

    if leaked_collections:
        logger.warning(
            f"Output guardrail: Possible cross-role leakage detected. "
            f"Collections: {leaked_collections}, User role: {user_role}"
        )
        return (
            "\n\n⚠️ **Security Notice**: This response has been flagged for "
            "potential cross-department information leakage and may require review."
        )

    return None


# ---------------------------------------------------------------------------
# Combined Output Guard
# ---------------------------------------------------------------------------

def run_output_guards(
    response: str,
    retrieved_chunks: list[dict],
    user_role: str,
    accessible_collections: list[str],
) -> dict:
    """
    Run all output guardrails on a generated response.

    Returns:
        Dict with:
        - warnings: List of warning strings to append
        - has_warnings: Boolean
    """
    warnings = []

    # 1. Source citation check (mandatory)
    citation_warning = check_source_citation(response)
    if citation_warning:
        warnings.append(citation_warning)

    # 2. Grounding check (optional but implemented)
    grounding_warning = check_grounding(response, retrieved_chunks)
    if grounding_warning:
        warnings.append(grounding_warning)

    # 3. Cross-role leakage check (optional but implemented)
    leakage_warning = check_cross_role_leakage(
        response, user_role, accessible_collections
    )
    if leakage_warning:
        warnings.append(leakage_warning)

    return {
        "warnings": warnings,
        "has_warnings": len(warnings) > 0,
    }
