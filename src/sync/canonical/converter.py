"""
Base League Converter Module

Provides the abstract base class that all league converters must implement.

This module exports:
    - BaseLeagueConverter: Abstract base class for league converters

Usage:
    from src.sync.canonical.converter import BaseLeagueConverter
    from src.sync.canonical.entities import CanonicalPlayer, CanonicalTeam

    class EuroleagueConverter(BaseLeagueConverter):
        source = "euroleague"

        def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
            # Implementation
            ...
"""

from abc import ABC, abstractmethod
from typing import Any

from src.sync.canonical.entities import (
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayer,
    CanonicalPlayerStats,
    CanonicalSeason,
    CanonicalTeam,
)
from src.sync.canonical.types import EventType, Position


class BaseLeagueConverter(ABC):
    """
    Abstract base class for converting league-specific data to canonical format.

    Each league adapter MUST implement this interface. The converter handles
    the translation from raw API responses to validated canonical entities.

    Class Attributes:
        source: Source system name (must be overridden in subclass)

    Example:
        >>> class NBAConverter(BaseLeagueConverter):
        ...     source = "nba"
        ...
        ...     def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
        ...         return CanonicalPlayer(
        ...             external_id=str(raw["personId"]),
        ...             source=self.source,
        ...             first_name=raw["firstName"],
        ...             last_name=raw["lastName"],
        ...             positions=self.map_position(raw.get("position")),
        ...             height=parse_height(raw.get("height")),
        ...             ...
        ...         )
    """

    source: str = ""  # Override in subclass: "euroleague", "nba", etc.

    # === Player Conversion ===

    @abstractmethod
    def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
        """
        Convert raw player data to CanonicalPlayer.

        Args:
            raw: Dictionary from league API containing player data.

        Returns:
            CanonicalPlayer with validated data.

        Raises:
            ConversionError: If required fields missing or invalid.

        Example:
            >>> converter = EuroleagueConverter()
            >>> player = converter.convert_player({"code": "P123", "name": "John Doe"})
        """
        ...

    @abstractmethod
    def map_position(self, raw: str | None) -> list[Position]:
        """
        Convert league-specific position format to canonical positions.

        Different leagues use different position formats:
        - Euroleague: "Guard", "Forward", "Center"
        - NBA: "G", "F", "C", "G-F"
        - iBasketball: Hebrew position names

        Args:
            raw: Raw position string from the league API.

        Returns:
            List of Position enums. Empty list if position unknown.

        Example:
            >>> converter.map_position("Guard")
            [Position.POINT_GUARD, Position.SHOOTING_GUARD]
            >>> converter.map_position("G-F")
            [Position.GUARD, Position.FORWARD]
        """
        ...

    # === Team Conversion ===

    @abstractmethod
    def convert_team(self, raw: dict[str, Any]) -> CanonicalTeam:
        """
        Convert raw team data to CanonicalTeam.

        Args:
            raw: Dictionary from league API containing team data.

        Returns:
            CanonicalTeam with validated data.

        Raises:
            ConversionError: If required fields missing or invalid.
        """
        ...

    # === Game Conversion ===

    @abstractmethod
    def convert_game(self, raw: dict[str, Any]) -> CanonicalGame:
        """
        Convert raw game data to CanonicalGame.

        Args:
            raw: Dictionary from league API containing game data.

        Returns:
            CanonicalGame with validated data.

        Raises:
            ConversionError: If required fields missing or invalid.
        """
        ...

    # === Stats Conversion ===

    @abstractmethod
    def convert_player_stats(self, raw: dict[str, Any]) -> CanonicalPlayerStats:
        """
        Convert raw boxscore stats to CanonicalPlayerStats.

        IMPORTANT: minutes_seconds must be in SECONDS, not minutes.
        Use parse_minutes_to_seconds() to convert from league format.

        Args:
            raw: Dictionary from league API containing player stats.

        Returns:
            CanonicalPlayerStats with validated data.

        Raises:
            ConversionError: If required fields missing or invalid.
        """
        ...

    @abstractmethod
    def parse_minutes_to_seconds(self, raw: str | int | None) -> int:
        """
        Convert minutes from league format to seconds.

        Different leagues use different minute formats:
        - "25:30" → 1530 seconds
        - "PT25M30.00S" → 1530 seconds (ISO 8601)
        - 25 → 1500 seconds (integer minutes)
        - 25.5 → 1530 seconds (decimal minutes)

        Args:
            raw: Raw minutes value in league-specific format.

        Returns:
            Minutes converted to seconds. Returns 0 if input is None/invalid.

        Example:
            >>> converter.parse_minutes_to_seconds("25:30")
            1530
            >>> converter.parse_minutes_to_seconds(25)
            1500
        """
        ...

    # === PBP Conversion ===

    @abstractmethod
    def convert_pbp_event(self, raw: dict[str, Any]) -> CanonicalPBPEvent | None:
        """
        Convert raw PBP event to CanonicalPBPEvent.

        Args:
            raw: Dictionary from league API containing PBP event data.

        Returns:
            CanonicalPBPEvent with validated data, or None for events
            we don't track (game start, etc.).

        Raises:
            ConversionError: If required fields missing or invalid.
        """
        ...

    @abstractmethod
    def map_event_type(self, raw: str) -> tuple[EventType, dict[str, Any]]:
        """
        Map league event code to EventType and subtype attributes.

        Args:
            raw: Raw event type string from the league API.

        Returns:
            Tuple of (EventType, dict with subtype attributes).
            The dict may contain keys like "shot_type", "foul_type", "success".

        Example:
            >>> converter.map_event_type("2FGM")
            (EventType.SHOT, {"shot_type": ShotType.TWO_POINT, "success": True})
            >>> converter.map_event_type("TO")
            (EventType.TURNOVER, {"turnover_type": TurnoverType.OTHER})
        """
        ...

    # === Season Conversion ===

    @abstractmethod
    def convert_season(self, raw: dict[str, Any]) -> CanonicalSeason:
        """
        Convert raw season data to CanonicalSeason.

        Args:
            raw: Dictionary from league API containing season data.

        Returns:
            CanonicalSeason with validated data.

        Raises:
            ConversionError: If required fields missing or invalid.
        """
        ...
