"""
FinBot RBAC Module
Builds Qdrant filter conditions to enforce role-based access control
at the vector database retrieval level.
"""

from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.config import ACCESS_MATRIX


def build_rbac_filter(user_role: str) -> Filter:
    """
    Build a Qdrant metadata filter that restricts retrieval to only
    the collections the user's role is authorized to access.

    This filter is applied at query time so that chunks from
    unauthorized collections are NEVER surfaced to the LLM context.

    Args:
        user_role: The role of the authenticated user.

    Returns:
        A Qdrant Filter object to pass to the search query.
    """
    accessible = ACCESS_MATRIX.get(user_role, [])
    if not accessible:
        # If role is unknown, return a filter that matches nothing
        accessible = ["__none__"]

    return Filter(
        must=[
            FieldCondition(
                key="access_roles",
                match=MatchAny(any=[user_role]),
            )
        ]
    )


def get_accessible_collections(user_role: str) -> list[str]:
    """Return the list of collections a user role can access."""
    return ACCESS_MATRIX.get(user_role, [])


def can_access_collection(user_role: str, collection: str) -> bool:
    """Check whether a user role can access a specific collection."""
    return collection in ACCESS_MATRIX.get(user_role, [])


def get_route_collection_map() -> dict[str, str]:
    """
    Map semantic router route names to collection names.
    Used to intersect routing decisions with RBAC.
    """
    return {
        "finance_route": "finance",
        "engineering_route": "engineering",
        "marketing_route": "marketing",
        "hr_general_route": "general",
        "cross_department_route": None,  # searches all accessible
    }
