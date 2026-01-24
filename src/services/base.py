"""
Base Service Module

Provides a generic base service class with common CRUD operations for all
entity services in the Basketball Analytics Platform.

This module exports:
    - BaseService: Generic base class with CRUD operations

Usage:
    from src.services.base import BaseService
    from src.models.player import Player

    class PlayerService(BaseService[Player]):
        def __init__(self, db: Session):
            super().__init__(db, Player)

        # Add custom methods here

The BaseService provides reusable operations that work with any SQLAlchemy
model that inherits from UUIDMixin. Custom services should extend this base
class and add entity-specific business logic.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseService(Generic[ModelT]):
    """
    Generic base service providing CRUD operations for any model.

    This class provides common database operations that are reusable across
    different entity types. Services for specific entities should inherit
    from this class and add custom business logic methods.

    Type Parameters:
        ModelT: The SQLAlchemy model type this service operates on.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The model class this service operates on.

    Example:
        >>> from src.models.player import Player
        >>> class PlayerService(BaseService[Player]):
        ...     def __init__(self, db: Session):
        ...         super().__init__(db, Player)
        ...
        >>> service = PlayerService(db_session)
        >>> player = service.get_by_id(player_id)
    """

    def __init__(self, db: Session, model: type[ModelT]) -> None:
        """
        Initialize the base service.

        Args:
            db: SQLAlchemy database session.
            model: The SQLAlchemy model class to operate on.

        Example:
            >>> service = BaseService(db_session, Player)
        """
        self.db = db
        self.model = model

    def get_by_id(self, id: UUID) -> ModelT | None:
        """
        Retrieve a single entity by its UUID.

        Args:
            id: The UUID primary key of the entity.

        Returns:
            The entity if found, None otherwise.

        Example:
            >>> player = service.get_by_id(UUID("abc-123"))
            >>> if player:
            ...     print(player.name)
        """
        return self.db.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelT]:
        """
        Retrieve all entities with pagination.

        Args:
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            List of entities within the specified range.

        Example:
            >>> players = service.get_all(skip=0, limit=20)
            >>> print(f"Retrieved {len(players)} players")
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count(self) -> int:
        """
        Count the total number of entities.

        Returns:
            Total count of entities in the table.

        Example:
            >>> total = service.count()
            >>> print(f"Total players: {total}")
        """
        stmt = select(func.count()).select_from(self.model)
        result = self.db.execute(stmt).scalar()
        return result or 0

    def create(self, data: dict[str, Any]) -> ModelT:
        """
        Create a new entity from a dictionary of data.

        Args:
            data: Dictionary containing field values for the new entity.
                Keys should match model column names.

        Returns:
            The newly created entity with generated ID and timestamps.

        Example:
            >>> player = service.create({
            ...     "first_name": "LeBron",
            ...     "last_name": "James",
            ...     "position": "SF"
            ... })
            >>> print(player.id)  # Auto-generated UUID
        """
        entity = self.model(**data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, id: UUID, data: dict[str, Any]) -> ModelT | None:
        """
        Update an existing entity.

        Only fields present in the data dictionary will be updated.
        Fields with None values are skipped (use explicit null handling
        if you need to set a field to None).

        Args:
            id: UUID of the entity to update.
            data: Dictionary containing fields to update. Keys should match
                model column names. None values are ignored.

        Returns:
            The updated entity if found, None if entity doesn't exist.

        Example:
            >>> updated = service.update(
            ...     player_id,
            ...     {"position": "PF", "height_cm": 206}
            ... )
            >>> if updated:
            ...     print(f"Updated: {updated.position}")
        """
        entity = self.get_by_id(id)
        if entity is None:
            return None

        for key, value in data.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)

        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, id: UUID) -> bool:
        """
        Delete an entity by its UUID.

        Args:
            id: UUID of the entity to delete.

        Returns:
            True if entity was deleted, False if entity was not found.

        Example:
            >>> deleted = service.delete(player_id)
            >>> if deleted:
            ...     print("Player removed")
            ... else:
            ...     print("Player not found")
        """
        entity = self.get_by_id(id)
        if entity is None:
            return False

        self.db.delete(entity)
        self.db.commit()
        return True
