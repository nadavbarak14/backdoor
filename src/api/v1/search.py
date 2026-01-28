"""
Search API Endpoints Module

Provides the autocomplete endpoint for the @-mention feature.
Enables fast typeahead search across players, teams, seasons, and leagues.

Endpoints:
    GET /search/autocomplete - Search across all entity types

Usage:
    GET /api/v1/search/autocomplete?q=mac&limit=10

    Response:
    {
        "results": [
            {"id": "...", "type": "player", "name": "Mac McClung", "context": "Maccabi Tel Aviv"},
            {"id": "...", "type": "team", "name": "Maccabi Tel Aviv", "context": "Israeli League"}
        ]
    }
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.schemas.search import AutocompleteResponse
from src.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "/autocomplete",
    response_model=AutocompleteResponse,
    summary="Search entities for @-mention autocomplete",
    description="""
    Search across players, teams, seasons, and leagues for the @-mention feature.

    The search is case-insensitive and matches:
    - Players: first name, last name, or full name
    - Teams: name or short name
    - Seasons: name (e.g., "2024-25")
    - Leagues: name or code

    Results are ordered by relevance, with prefix matches prioritized.
    """,
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "type": "player",
                                "name": "Mac McClung",
                                "context": "Maccabi Tel Aviv",
                            },
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440001",
                                "type": "team",
                                "name": "Maccabi Tel Aviv",
                                "context": "Israeli Basketball League",
                            },
                        ]
                    }
                }
            },
        }
    },
)
def autocomplete(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search query (minimum 1 character)",
        examples=["mac", "curry", "2024"],
    ),
    limit: int = Query(
        10,
        ge=1,
        le=20,
        description="Maximum number of results (1-20)",
    ),
    db: Session = Depends(get_db),
) -> AutocompleteResponse:
    """
    Search across all entity types for autocomplete suggestions.

    Args:
        q: Search query string (1-100 characters)
        limit: Maximum results to return (1-20, default 10)
        db: Database session (injected)

    Returns:
        AutocompleteResponse with matching entities sorted by relevance

    Example:
        >>> # GET /api/v1/search/autocomplete?q=mac&limit=5
        >>> response.results[0].name
        "Mac McClung"
    """
    service = SearchService(db)
    return service.autocomplete(q, limit)
