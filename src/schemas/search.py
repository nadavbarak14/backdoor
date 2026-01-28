"""
Search Schemas Module

Provides Pydantic schemas for the autocomplete and browse endpoints
used by the @-mention feature in the chat UI.

This module exports:
    - EntityType: Enum of searchable entity types
    - SearchResult: Single autocomplete result item
    - AutocompleteResponse: Response for autocomplete endpoint
    - BrowseItem: Single item in browse hierarchy
    - BrowseResponse: Response for browse endpoints

Usage:
    from src.schemas.search import AutocompleteResponse, SearchResult, EntityType

    result = SearchResult(
        id="uuid-123",
        type=EntityType.PLAYER,
        name="Stephen Curry",
        context="Golden State Warriors"
    )
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """
    Enumeration of entity types that can be mentioned.

    Used to categorize search results and browse items,
    enabling type-specific filtering and display.

    Values:
        PLAYER: A basketball player
        TEAM: A basketball team
        SEASON: A season within a league
        LEAGUE: A basketball league
    """

    PLAYER = "player"
    TEAM = "team"
    SEASON = "season"
    LEAGUE = "league"


class SearchResult(BaseModel):
    """
    Single result item from autocomplete search.

    Represents an entity that matched the search query,
    with enough context for display in the dropdown.

    Attributes:
        id: UUID of the entity
        type: Type of entity (player, team, season, league)
        name: Display name of the entity
        context: Additional context (e.g., team name for player)

    Example:
        >>> result = SearchResult(
        ...     id=UUID("abc-123"),
        ...     type=EntityType.PLAYER,
        ...     name="Mac McClung",
        ...     context="Maccabi Tel Aviv"
        ... )
    """

    id: UUID
    type: EntityType
    name: str
    context: str | None = None


class AutocompleteResponse(BaseModel):
    """
    Response for the autocomplete search endpoint.

    Contains a list of matching entities across all types,
    ordered by relevance.

    Attributes:
        results: List of matching entities (max 10)

    Example:
        >>> response = AutocompleteResponse(
        ...     results=[
        ...         SearchResult(id=..., type=EntityType.PLAYER, name="Mac McClung"),
        ...         SearchResult(id=..., type=EntityType.TEAM, name="Maccabi Tel Aviv"),
        ...     ]
        ... )
    """

    results: list[SearchResult] = Field(default_factory=list)


class BrowseItem(BaseModel):
    """
    Single item in the hierarchical browse view.

    Represents an entity at a specific level of the hierarchy
    (League -> Season -> Team -> Player).

    Attributes:
        id: UUID of the entity
        type: Type of entity
        name: Display name of the entity
        has_children: Whether this item can be expanded

    Example:
        >>> item = BrowseItem(
        ...     id=UUID("abc-123"),
        ...     type=EntityType.LEAGUE,
        ...     name="Israeli Basketball League",
        ...     has_children=True
        ... )
    """

    id: UUID
    type: EntityType
    name: str
    has_children: bool = True


class BrowseParent(BaseModel):
    """
    Parent entity for breadcrumb navigation.

    Provides context about the current location in the
    browse hierarchy, enabling back navigation.

    Attributes:
        id: UUID of the parent entity
        type: Type of parent entity
        name: Display name of the parent

    Example:
        >>> parent = BrowseParent(
        ...     id=UUID("abc-123"),
        ...     type=EntityType.SEASON,
        ...     name="2024-25"
        ... )
    """

    id: UUID
    type: EntityType
    name: str


class BrowseResponse(BaseModel):
    """
    Response for hierarchical browse endpoints.

    Contains items at the current level plus parent info
    for breadcrumb navigation.

    Attributes:
        items: List of entities at this level
        parent: Parent entity info for breadcrumb (None at root)

    Example:
        >>> response = BrowseResponse(
        ...     items=[
        ...         BrowseItem(id=..., type=EntityType.TEAM, name="Maccabi Tel Aviv"),
        ...         BrowseItem(id=..., type=EntityType.TEAM, name="Hapoel Jerusalem"),
        ...     ],
        ...     parent=BrowseParent(id=..., type=EntityType.SEASON, name="2024-25")
        ... )
    """

    items: list[BrowseItem] = Field(default_factory=list)
    parent: BrowseParent | None = None
