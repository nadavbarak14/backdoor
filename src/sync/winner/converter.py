"""
Winner League Converter Module

Provides the WinnerConverter class for converting Winner League data to canonical format.
Implements the BaseLeagueConverter interface for all data transformations.

This module exports:
    - WinnerConverter: Converts Winner API data to canonical entities

Usage:
    from src.sync.winner.converter import WinnerConverter

    converter = WinnerConverter()
    player = converter.convert_player(raw_player_data)
    game = converter.convert_game(raw_game_data)
"""

from datetime import datetime
from typing import Any

from src.sync.canonical import (
    BaseLeagueConverter,
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayer,
    CanonicalPlayerStats,
    CanonicalSeason,
    CanonicalTeam,
    ConversionError,
    EventType,
    FoulType,
    Height,
    Position,
    ShotType,
    parse_birthdate,
    parse_height,
)


class WinnerConverter(BaseLeagueConverter):
    """
    Converter for Winner League (Israeli Basketball Super League) data.

    Transforms raw data from basket.co.il and segevstats.com APIs into
    canonical entities used throughout the basketball analytics platform.

    Class Attributes:
        source: Source identifier ("winner")
        POSITION_MAP: Maps Winner position codes to Position enums
        EVENT_MAP: Maps PBP event codes to EventType and attributes

    Example:
        >>> converter = WinnerConverter()
        >>> player = converter.convert_player({
        ...     "external_id": "1001",
        ...     "first_name": "John",
        ...     "last_name": "Smith",
        ...     "position": "G",
        ...     "height_cm": 195,
        ... })
        >>> print(player.full_name)
        'John Smith'
    """

    source = "winner"

    # Position mappings for Winner League
    # Single letters map to both guards or both forwards
    POSITION_MAP: dict[str, list[Position]] = {
        "G": [Position.POINT_GUARD, Position.SHOOTING_GUARD],
        "PG": [Position.POINT_GUARD],
        "SG": [Position.SHOOTING_GUARD],
        "F": [Position.SMALL_FORWARD, Position.POWER_FORWARD],
        "SF": [Position.SMALL_FORWARD],
        "PF": [Position.POWER_FORWARD],
        "C": [Position.CENTER],
        "G-F": [Position.SHOOTING_GUARD, Position.SMALL_FORWARD],
        "F-G": [Position.SHOOTING_GUARD, Position.SMALL_FORWARD],
        "F-C": [Position.POWER_FORWARD, Position.CENTER],
        "C-F": [Position.POWER_FORWARD, Position.CENTER],
        "Guard": [Position.POINT_GUARD, Position.SHOOTING_GUARD],
        "Forward": [Position.SMALL_FORWARD, Position.POWER_FORWARD],
        "Center": [Position.CENTER],
    }

    # PBP event type mappings
    EVENT_MAP: dict[str, tuple[EventType, dict[str, Any]]] = {
        "MADE_2PT": (EventType.SHOT, {"shot_type": ShotType.TWO_POINT, "success": True}),
        "MISS_2PT": (EventType.SHOT, {"shot_type": ShotType.TWO_POINT, "success": False}),
        "MADE_3PT": (
            EventType.SHOT,
            {"shot_type": ShotType.THREE_POINT, "success": True},
        ),
        "MISS_3PT": (
            EventType.SHOT,
            {"shot_type": ShotType.THREE_POINT, "success": False},
        ),
        "MADE_FT": (EventType.FREE_THROW, {"success": True}),
        "MISS_FT": (EventType.FREE_THROW, {"success": False}),
        "REBOUND": (EventType.REBOUND, {}),
        "ASSIST": (EventType.ASSIST, {}),
        "TURNOVER": (EventType.TURNOVER, {}),
        "STEAL": (EventType.STEAL, {}),
        "BLOCK": (EventType.BLOCK, {}),
        "FOUL": (EventType.FOUL, {"foul_type": FoulType.PERSONAL}),
        "JUMP_BALL": (EventType.JUMP_BALL, {}),
        "TIMEOUT": (EventType.TIMEOUT, {}),
        "SUBSTITUTION": (EventType.SUBSTITUTION, {}),
    }

    # === Player Conversion ===

    def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
        """
        Convert raw Winner player data to CanonicalPlayer.

        Handles data from both roster scraping (basket.co.il) and boxscore
        player entries (segevstats.com).

        Args:
            raw: Dictionary containing player data. Expected keys:
                - external_id or player_id: Player identifier
                - first_name, last_name: Player name parts
                - position: Position code (G, F, C, etc.)
                - height_cm: Height in centimeters (int)
                - birth_date: Birthdate string
                - jersey_number: Jersey number

        Returns:
            CanonicalPlayer with validated data.

        Raises:
            ConversionError: If height is invalid (outside 150-250 cm).

        Example:
            >>> player = converter.convert_player({
            ...     "external_id": "1001",
            ...     "first_name": "John",
            ...     "last_name": "Smith",
            ...     "height_cm": 195,
            ... })
        """
        # Handle different ID field names
        external_id = str(
            raw.get("external_id") or raw.get("player_id") or raw.get("playerId") or ""
        )
        if not external_id:
            raise ConversionError("Player missing external_id")

        # Parse height with validation
        height: Height | None = None
        height_raw = raw.get("height_cm") or raw.get("height")
        if height_raw is not None:
            height = parse_height(height_raw)
            if height is None:
                raise ConversionError(f"Invalid height: {height_raw}")

        # Parse birth date
        birth_date = parse_birthdate(raw.get("birth_date") or raw.get("birthDate"))

        # Get name parts
        first_name = raw.get("first_name", "") or ""
        last_name = raw.get("last_name", "") or ""

        # Handle full name if first/last not available
        if not first_name and not last_name:
            full_name = raw.get("name", "") or raw.get("playerName", "") or ""
            if full_name:
                parts = full_name.strip().split(None, 1)
                first_name = parts[0] if parts else ""
                last_name = parts[1] if len(parts) > 1 else ""

        return CanonicalPlayer(
            external_id=external_id,
            source=self.source,
            first_name=first_name,
            last_name=last_name,
            positions=self.map_position(raw.get("position")),
            height=height,
            birth_date=birth_date,
            nationality=None,  # Winner doesn't reliably provide nationality
            jersey_number=str(raw.get("jersey_number") or raw.get("jerseyNumber") or "")
            or None,
        )

    def map_position(self, raw: str | None) -> list[Position]:
        """
        Convert Winner position code to canonical positions.

        Winner uses single-letter codes (G, F, C) that map to multiple
        positions, or specific codes (PG, SF, etc.) that map to one.

        Args:
            raw: Raw position string from Winner API.

        Returns:
            List of Position enums. Empty list if position unknown.

        Example:
            >>> converter.map_position("G")
            [Position.POINT_GUARD, Position.SHOOTING_GUARD]
            >>> converter.map_position("C")
            [Position.CENTER]
            >>> converter.map_position(None)
            []
        """
        if not raw:
            return []

        # Normalize input
        position_key = raw.strip().upper()

        # Try direct lookup
        if position_key in self.POSITION_MAP:
            return self.POSITION_MAP[position_key]

        # Try title case for full words
        title_case = raw.strip().title()
        if title_case in self.POSITION_MAP:
            return self.POSITION_MAP[title_case]

        return []

    # === Team Conversion ===

    def convert_team(self, raw: dict[str, Any]) -> CanonicalTeam:
        """
        Convert raw Winner team data to CanonicalTeam.

        Args:
            raw: Dictionary containing team data. Expected keys:
                - external_id or team_id or team1/team2: Team identifier
                - name or team_name_eng_1: Team name
                - short_name: Team abbreviation
                - city: Team city
                - country: Team country (usually Israel)

        Returns:
            CanonicalTeam with validated data.

        Raises:
            ConversionError: If team_id or name is missing.

        Example:
            >>> team = converter.convert_team({
            ...     "team_id": "1109",
            ...     "name": "Maccabi Tel Aviv",
            ... })
        """
        external_id = str(
            raw.get("external_id")
            or raw.get("team_id")
            or raw.get("teamId")
            or raw.get("team1")
            or ""
        )
        if not external_id:
            raise ConversionError("Team missing external_id")

        name = (
            raw.get("name")
            or raw.get("team_name")
            or raw.get("team_name_eng_1")
            or raw.get("team_name_eng_2")
            or ""
        )
        if not name:
            raise ConversionError("Team missing name")

        return CanonicalTeam(
            external_id=external_id,
            source=self.source,
            name=name,
            short_name=raw.get("short_name"),
            city=raw.get("city"),
            country=raw.get("country") or "Israel",
        )

    # === Game Conversion ===

    def convert_game(self, raw: dict[str, Any]) -> CanonicalGame:
        """
        Convert raw Winner game data to CanonicalGame.

        Handles both games_all.json format and boxscore gameInfo format.

        Args:
            raw: Dictionary containing game data. Expected keys:
                - ExternalID or external_id: Game identifier
                - team1 or homeTeamId: Home team ID
                - team2 or awayTeamId: Away team ID
                - game_date_txt or game_date: Game date string
                - score_team1 or homeScore: Home team score
                - score_team2 or awayScore: Away team score
                - game_year or season_id: Season identifier

        Returns:
            CanonicalGame with validated data.

        Raises:
            ConversionError: If required fields are missing.

        Example:
            >>> game = converter.convert_game({
            ...     "ExternalID": "1001",
            ...     "team1": 1109,
            ...     "team2": 1112,
            ...     "game_date_txt": "20/09/2024",
            ... })
        """
        external_id = str(
            raw.get("ExternalID")
            or raw.get("external_id")
            or raw.get("gameId")
            or raw.get("game_id")
            or ""
        )
        if not external_id:
            raise ConversionError("Game missing external_id")

        # Get team IDs
        home_team_id = str(
            raw.get("team1") or raw.get("homeTeamId") or raw.get("home_team_id") or ""
        )
        away_team_id = str(
            raw.get("team2") or raw.get("awayTeamId") or raw.get("away_team_id") or ""
        )
        if not home_team_id or not away_team_id:
            raise ConversionError("Game missing team IDs")

        # Parse game date
        game_date = self._parse_game_date(raw)

        # Get scores (may be None for scheduled games)
        home_score = self._safe_int(
            raw.get("score_team1") or raw.get("homeScore") or raw.get("home_score")
        )
        away_score = self._safe_int(
            raw.get("score_team2") or raw.get("awayScore") or raw.get("away_score")
        )

        # Determine game status
        status = self._determine_game_status(raw, home_score, away_score)

        # Season ID
        season_id = str(
            raw.get("game_year")
            or raw.get("season_id")
            or raw.get("season_external_id")
            or ""
        )

        return CanonicalGame(
            external_id=external_id,
            source=self.source,
            season_external_id=season_id,
            home_team_external_id=home_team_id,
            away_team_external_id=away_team_id,
            game_date=game_date,
            status=status,
            home_score=home_score,
            away_score=away_score,
            venue=raw.get("venue"),
        )

    def _parse_game_date(self, raw: dict[str, Any]) -> datetime:
        """Parse game date from various Winner formats."""
        date_str = raw.get("game_date_txt") or raw.get("game_date") or raw.get("date")
        time_str = raw.get("game_time") or "20:00"

        if not date_str:
            raise ConversionError("Game missing date")

        # Try DD/MM/YYYY format (most common in Winner)
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                date_part = datetime.strptime(str(date_str), fmt)
                # Add time if available
                if time_str:
                    try:
                        time_part = datetime.strptime(str(time_str), "%H:%M")
                        return date_part.replace(
                            hour=time_part.hour, minute=time_part.minute
                        )
                    except ValueError:
                        pass
                return date_part
            except ValueError:
                continue

        raise ConversionError(f"Cannot parse game date: {date_str}")

    def _determine_game_status(
        self, raw: dict[str, Any], home_score: int | None, away_score: int | None
    ) -> str:
        """Determine game status from raw data and scores."""
        if raw.get("gameFinished") or raw.get("game_finished"):
            return "FINAL"
        if raw.get("isLive") == 1 or raw.get("is_live"):
            if home_score is not None and away_score is not None:
                return "FINAL"
            return "LIVE"
        if home_score is not None and away_score is not None:
            return "FINAL"
        return "SCHEDULED"

    def _safe_int(self, value: Any) -> int | None:
        """Safely convert value to int, returning None on failure."""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    # === Stats Conversion ===

    def convert_player_stats(self, raw: dict[str, Any]) -> CanonicalPlayerStats:
        """
        Convert raw Winner boxscore stats to CanonicalPlayerStats.

        Args:
            raw: Dictionary containing player stats from segevstats API.
                Expected keys match segevstats boxscore format:
                - playerId: Player identifier
                - minutes: Time played (MM:SS format)
                - points, fg_2m, fg_2mis, fg_3m, fg_3mis, etc.

        Returns:
            CanonicalPlayerStats with all stats fields populated.

        Example:
            >>> stats = converter.convert_player_stats({
            ...     "playerId": "1001",
            ...     "minutes": "25:30",
            ...     "points": "22",
            ... })
            >>> stats.minutes_seconds
            1530
        """
        player_id = str(raw.get("playerId") or raw.get("player_id") or "")
        player_name = raw.get("playerName") or raw.get("player_name") or ""
        team_id = str(raw.get("teamId") or raw.get("team_id") or "")

        # Parse minutes to seconds
        minutes_seconds = self.parse_minutes_to_seconds(raw.get("minutes"))

        # Calculate shooting stats
        fg_2m = self._safe_int(raw.get("fg_2m")) or 0
        fg_2mis = self._safe_int(raw.get("fg_2mis")) or 0
        fg_3m = self._safe_int(raw.get("fg_3m")) or 0
        fg_3mis = self._safe_int(raw.get("fg_3mis")) or 0
        ft_m = self._safe_int(raw.get("ft_m")) or 0
        ft_mis = self._safe_int(raw.get("ft_mis")) or 0

        # Rebounds
        reb_d = self._safe_int(raw.get("reb_d")) or 0
        reb_o = self._safe_int(raw.get("reb_o")) or 0

        return CanonicalPlayerStats(
            player_external_id=player_id,
            player_name=player_name,
            team_external_id=team_id,
            minutes_seconds=minutes_seconds,
            is_starter=raw.get("starter") is True,
            points=self._safe_int(raw.get("points")) or 0,
            field_goals_made=fg_2m + fg_3m,
            field_goals_attempted=fg_2m + fg_2mis + fg_3m + fg_3mis,
            two_pointers_made=fg_2m,
            two_pointers_attempted=fg_2m + fg_2mis,
            three_pointers_made=fg_3m,
            three_pointers_attempted=fg_3m + fg_3mis,
            free_throws_made=ft_m,
            free_throws_attempted=ft_m + ft_mis,
            offensive_rebounds=reb_o,
            defensive_rebounds=reb_d,
            total_rebounds=reb_o + reb_d,
            assists=self._safe_int(raw.get("ast")) or 0,
            steals=self._safe_int(raw.get("stl")) or 0,
            blocks=self._safe_int(raw.get("blk")) or 0,
            turnovers=self._safe_int(raw.get("to")) or 0,
            personal_fouls=self._safe_int(raw.get("f")) or 0,
            plus_minus=self._safe_int(raw.get("plusMinus")),
        )

    def parse_minutes_to_seconds(self, raw: str | int | None) -> int:
        """
        Convert minutes from Winner MM:SS format to seconds.

        Args:
            raw: Raw minutes value. Expected formats:
                - "25:30" → 1530 seconds
                - "08:45" → 525 seconds
                - 25 → 1500 seconds (integer minutes)
                - None → 0 seconds

        Returns:
            Minutes converted to seconds.

        Example:
            >>> converter.parse_minutes_to_seconds("25:30")
            1530
            >>> converter.parse_minutes_to_seconds("00:00")
            0
            >>> converter.parse_minutes_to_seconds(25)
            1500
        """
        if raw is None or raw == "":
            return 0

        # Handle integer minutes
        if isinstance(raw, int):
            return raw * 60

        # Handle string format
        raw_str = str(raw).strip()
        if not raw_str:
            return 0

        # Try MM:SS format
        if ":" in raw_str:
            try:
                parts = raw_str.split(":")
                minutes = int(parts[0])
                seconds = int(parts[1]) if len(parts) > 1 else 0
                return minutes * 60 + seconds
            except (ValueError, IndexError):
                return 0

        # Try plain integer
        try:
            return int(float(raw_str) * 60)
        except ValueError:
            return 0

    # === PBP Conversion ===

    def convert_pbp_event(self, raw: dict[str, Any]) -> CanonicalPBPEvent | None:
        """
        Convert raw Winner PBP event to CanonicalPBPEvent.

        Args:
            raw: Dictionary containing PBP event data. Expected keys:
                - EventId: Event identifier
                - Quarter: Period number (1-4, 5+ for OT)
                - GameClock: Time remaining (MM:SS format)
                - EventType: Event type code (MADE_2PT, MISS_3PT, etc.)
                - TeamId: Team that generated the event
                - PlayerId: Player involved (if applicable)

        Returns:
            CanonicalPBPEvent or None for events we don't track.

        Example:
            >>> event = converter.convert_pbp_event({
            ...     "EventId": "1",
            ...     "Quarter": 1,
            ...     "GameClock": "09:45",
            ...     "EventType": "MADE_2PT",
            ...     "PlayerId": "1001",
            ... })
        """
        event_type_raw = raw.get("EventType") or raw.get("event_type") or ""
        if not event_type_raw:
            return None

        # Map event type
        event_type, attributes = self.map_event_type(event_type_raw)

        # Skip unmapped events
        if event_type is None:
            return None

        # Parse clock to seconds
        clock_str = raw.get("GameClock") or raw.get("game_clock") or "00:00"
        clock_seconds = self._parse_clock_to_seconds(clock_str)

        # Get period
        period = self._safe_int(raw.get("Quarter") or raw.get("period")) or 1

        # Get event number
        event_number = self._safe_int(
            raw.get("EventId") or raw.get("event_id") or raw.get("event_number")
        )
        if event_number is None:
            event_number = 0

        return CanonicalPBPEvent(
            event_number=event_number,
            period=period,
            clock_seconds=clock_seconds,
            event_type=event_type,
            shot_type=attributes.get("shot_type"),
            success=attributes.get("success"),
            player_external_id=str(raw.get("PlayerId") or raw.get("player_id") or "")
            or None,
            team_external_id=str(raw.get("TeamId") or raw.get("team_id") or "")
            or None,
            foul_type=attributes.get("foul_type"),
        )

    def map_event_type(self, raw: str) -> tuple[EventType | None, dict[str, Any]]:
        """
        Map Winner event code to EventType and subtype attributes.

        Args:
            raw: Raw event type string from Winner PBP API.

        Returns:
            Tuple of (EventType, dict with subtype attributes).
            Returns (None, {}) for unmapped event types.

        Example:
            >>> converter.map_event_type("MADE_2PT")
            (EventType.SHOT, {"shot_type": ShotType.TWO_POINT, "success": True})
            >>> converter.map_event_type("UNKNOWN_EVENT")
            (None, {})
        """
        if not raw:
            return (None, {})

        event_key = raw.strip().upper()
        if event_key in self.EVENT_MAP:
            return self.EVENT_MAP[event_key]

        return (None, {})

    def _parse_clock_to_seconds(self, clock_str: str) -> int:
        """Parse game clock MM:SS to seconds remaining."""
        if not clock_str:
            return 0

        try:
            parts = str(clock_str).split(":")
            minutes = int(parts[0])
            seconds = int(parts[1]) if len(parts) > 1 else 0
            return minutes * 60 + seconds
        except (ValueError, IndexError):
            return 0

    # === Season Conversion ===

    def convert_season(self, raw: dict[str, Any]) -> CanonicalSeason:
        """
        Convert raw Winner season data to CanonicalSeason.

        Winner seasons typically follow Israeli academic year (Sep-May).

        Args:
            raw: Dictionary containing season data. Expected keys:
                - external_id or season_id or game_year: Season identifier
                - name: Season name (e.g., "2024-25")
                - start_date, end_date: Season date range
                - is_current: Whether this is the active season

        Returns:
            CanonicalSeason with validated data.

        Raises:
            ConversionError: If season_id is missing.

        Example:
            >>> season = converter.convert_season({
            ...     "game_year": 2025,
            ...     "name": "2024-25",
            ... })
        """
        external_id = str(
            raw.get("external_id")
            or raw.get("season_id")
            or raw.get("game_year")
            or raw.get("year")
            or ""
        )
        if not external_id:
            raise ConversionError("Season missing external_id")

        # Generate name from year if not provided
        name = raw.get("name") or raw.get("season_name")
        if not name:
            try:
                year = int(external_id)
                name = f"{year - 1}-{str(year)[2:]}"
            except ValueError:
                name = external_id

        # Parse dates if provided
        start_date = None
        end_date = None
        if raw.get("start_date"):
            start_date = parse_birthdate(raw.get("start_date"))
        if raw.get("end_date"):
            end_date = parse_birthdate(raw.get("end_date"))

        return CanonicalSeason(
            external_id=external_id,
            source=self.source,
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_current=raw.get("is_current", False),
        )
