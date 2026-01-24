"""
Base Schema Utilities Module

Provides shared utilities and base classes for all Pydantic schemas:
- OrmBase: Base model with ORM compatibility configured
- PaginatedResponse: Generic wrapper for paginated list responses

Usage:
    from src.schemas.base import OrmBase, PaginatedResponse

    class PlayerResponse(OrmBase):
        id: UUID
        name: str

    # For paginated endpoints
    response: PaginatedResponse[PlayerResponse]
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class OrmBase(BaseModel):
    """
    Base Pydantic model with ORM compatibility.

    Configured with `from_attributes=True` to allow automatic conversion
    from SQLAlchemy ORM objects to Pydantic models using `model_validate()`.

    All response schemas should inherit from this class to enable
    seamless ORM-to-Pydantic conversion.

    Example:
        >>> class PlayerResponse(OrmBase):
        ...     id: UUID
        ...     first_name: str
        ...
        >>> player_orm = session.get(Player, player_id)
        >>> response = PlayerResponse.model_validate(player_orm)
    """

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Used to wrap list responses with pagination metadata.
    The generic type T specifies the type of items in the list.

    Attributes:
        items: List of items for the current page.
        total: Total number of items across all pages.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        pages: Total number of pages.

    Example:
        >>> from src.schemas.player import PlayerResponse
        >>> response = PaginatedResponse[PlayerResponse](
        ...     items=[player1, player2],
        ...     total=100,
        ...     page=1,
        ...     page_size=20,
        ...     pages=5
        ... )
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
