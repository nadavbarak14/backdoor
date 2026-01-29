"""
Custom SQLAlchemy Types Module

Provides TypeDecorators for storing domain enums in the database while
maintaining type safety in Python code.

Philosophy:
    - Python side: Always work with proper enum types
    - Database side: Store as strings/JSON for readability and portability
    - Validation: FAIL if invalid values are encountered (no silent corruption)

This module exports:
    - PositionListType: Store list[Position] as JSON array
    - GameStatusType: Store GameStatus as string

Usage:
    from src.models.types import PositionListType, GameStatusType

    class Player(Base):
        positions: Mapped[list[Position]] = mapped_column(
            PositionListType, default=list, nullable=False
        )

    class Game(Base):
        status: Mapped[GameStatus] = mapped_column(
            GameStatusType, default=GameStatus.SCHEDULED, nullable=False
        )
"""

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from src.schemas.enums import GameStatus, Position


class PositionListType(TypeDecorator):
    """
    Store list[Position] as JSON in DB, expose as list[Position] in Python.

    On write:
        - Validates all items are Position enums
        - Stores as JSON array: ["PG", "SG"]
    On read:
        - Converts back to [Position.POINT_GUARD, Position.SHOOTING_GUARD]
        - FAILS if invalid value found (no silent corruption)

    Example:
        >>> # In model definition
        >>> positions: Mapped[list[Position]] = mapped_column(
        ...     PositionListType, default=list
        ... )
        >>> # Usage
        >>> player.positions = [Position.GUARD, Position.FORWARD]
        >>> # Stored in DB as: ["G", "F"]
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: list[Position] | list[str] | None, dialect: Dialect
    ) -> list[str] | None:
        """
        Convert list[Position] or list[str] to JSON-serializable list of strings.

        Accepts both Position enums and string values for backwards compatibility.
        String values are validated to be valid Position values.

        Args:
            value: List of Position enums or valid position strings, or None.
            dialect: Database dialect (unused).

        Returns:
            List of position value strings or empty list.

        Raises:
            ValueError: If value is not a list or contains invalid items.
        """
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"Expected list[Position], got {type(value)}")
        result = []
        for item in value:
            if isinstance(item, Position):
                result.append(item.value)
            elif isinstance(item, str):
                # Validate and convert string to enum, then get value
                try:
                    result.append(Position(item).value)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid Position string: '{item}'. "
                        f"Valid values are: {[p.value for p in Position]}"
                    ) from e
            else:
                raise ValueError(f"Expected Position enum or string, got {type(item)}: {item}")
        return result

    def process_result_value(
        self, value: list[str] | None, dialect: Dialect
    ) -> list[Position]:
        """
        Convert JSON list of strings back to list[Position].

        Args:
            value: List of position value strings from DB.
            dialect: Database dialect (unused).

        Returns:
            List of Position enums.

        Raises:
            ValueError: If any value cannot be converted to Position enum.
        """
        if value is None:
            return []
        result = []
        for v in value:
            try:
                result.append(Position(v))
            except ValueError as e:
                raise ValueError(
                    f"Invalid Position value in database: '{v}'. "
                    f"Valid values are: {[p.value for p in Position]}"
                ) from e
        return result


class GameStatusType(TypeDecorator):
    """
    Store GameStatus enum as string in DB, expose as enum in Python.

    On write:
        - Validates value is GameStatus enum
        - Stores as string: "FINAL"
    On read:
        - Converts back to GameStatus.FINAL
        - FAILS if invalid value found (no silent corruption)

    Example:
        >>> # In model definition
        >>> status: Mapped[GameStatus] = mapped_column(
        ...     GameStatusType, default=GameStatus.SCHEDULED
        ... )
        >>> # Usage
        >>> game.status = GameStatus.FINAL
        >>> # Stored in DB as: "FINAL"
    """

    impl = String(20)
    cache_ok = True

    def process_bind_param(
        self, value: GameStatus | str | None, dialect: Dialect
    ) -> str | None:
        """
        Convert GameStatus enum or string to string for database storage.

        Accepts both GameStatus enum and string values for backwards compatibility.
        String values are validated to be valid GameStatus values.

        Args:
            value: GameStatus enum, valid status string, or None.
            dialect: Database dialect (unused).

        Returns:
            Status value string or None.

        Raises:
            ValueError: If value is not a valid GameStatus.
        """
        if value is None:
            return None
        if isinstance(value, GameStatus):
            return value.value
        if isinstance(value, str):
            # Validate and convert string to enum, then get value
            try:
                return GameStatus(value).value
            except ValueError as e:
                raise ValueError(
                    f"Invalid GameStatus string: '{value}'. "
                    f"Valid values are: {[s.value for s in GameStatus]}"
                ) from e
        raise ValueError(f"Expected GameStatus enum or string, got {type(value)}: {value}")

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> GameStatus | None:
        """
        Convert string back to GameStatus enum.

        Args:
            value: Status value string from DB.
            dialect: Database dialect (unused).

        Returns:
            GameStatus enum or None.

        Raises:
            ValueError: If value cannot be converted to GameStatus enum.
        """
        if value is None:
            return None
        try:
            return GameStatus(value)
        except ValueError as e:
            raise ValueError(
                f"Invalid GameStatus value in database: '{value}'. "
                f"Valid values are: {[s.value for s in GameStatus]}"
            ) from e


class EventTypeType(TypeDecorator):
    """
    Store EventType enum as string in DB, expose as enum in Python.

    On write:
        - Validates value is EventType enum
        - Stores as string: "SHOT"
    On read:
        - Converts back to EventType.SHOT
        - FAILS if invalid value found (no silent corruption)

    Example:
        >>> # In model definition
        >>> event_type: Mapped[EventType] = mapped_column(
        ...     EventTypeType, nullable=False
        ... )
        >>> # Usage
        >>> event.event_type = EventType.SHOT
        >>> # Stored in DB as: "SHOT"
    """

    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        """
        Convert EventType enum or string to string for database storage.

        Accepts both EventType enum and string values for backwards compatibility.
        String values are validated to be valid EventType values.

        Args:
            value: EventType enum, valid event type string, or None.
            dialect: Database dialect (unused).

        Returns:
            Event type value string or None.

        Raises:
            ValueError: If value is not a valid EventType.
        """
        from src.schemas.enums import EventType

        if value is None:
            return None
        if isinstance(value, EventType):
            return value.value
        if isinstance(value, str):
            # Validate and convert string to enum, then get value
            try:
                return EventType(value).value
            except ValueError as e:
                raise ValueError(
                    f"Invalid EventType string: '{value}'. "
                    f"Valid values are: {[e.value for e in EventType]}"
                ) from e
        raise ValueError(f"Expected EventType enum or string, got {type(value)}: {value}")

    def process_result_value(self, value: str | None, dialect: Dialect) -> Any:
        """
        Convert string back to EventType enum.

        Args:
            value: Event type value string from DB.
            dialect: Database dialect (unused).

        Returns:
            EventType enum or None.

        Raises:
            ValueError: If value cannot be converted to EventType enum.
        """
        from src.schemas.enums import EventType

        if value is None:
            return None
        try:
            return EventType(value)
        except ValueError as e:
            raise ValueError(
                f"Invalid EventType value in database: '{value}'. "
                f"Valid values are: {[e.value for e in EventType]}"
            ) from e
