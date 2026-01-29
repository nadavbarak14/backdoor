"""
Euroleague Converter Module

Provides the EuroleagueConverter class for converting Euroleague API data to canonical format.
Implements the BaseLeagueConverter interface for all data transformations.

This module exports:
    - EuroleagueConverter: Converts Euroleague API data to canonical entities

Usage:
    from src.sync.euroleague.converter import EuroleagueConverter

    converter = EuroleagueConverter()
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
    ReboundType,
    ShotType,
    parse_birthdate,
)
from src.sync.season import normalize_season_name


class EuroleagueConverter(BaseLeagueConverter):
    """
    Converter for Euroleague and EuroCup basketball data.

    Transforms raw data from Euroleague APIs (api-live.euroleague.net
    and live.euroleague.net) into canonical entities used throughout
    the basketball analytics platform.

    Class Attributes:
        source: Source identifier ("euroleague")
        POSITION_MAP: Maps Euroleague position names to Position enums
        EVENT_MAP: Maps PBP event codes to EventType and attributes

    Example:
        >>> converter = EuroleagueConverter()
        >>> player = converter.convert_player({
        ...     "code": "P001234",
        ...     "name": "GILGEOUS-ALEXANDER, SHAI",
        ...     "position": "Guard",
        ...     "height": "1.98",
        ... })
        >>> print(player.height_cm)
        198
    """

    source = "euroleague"

    # Position mappings for Euroleague
    # Full position names map to specific or general positions
    POSITION_MAP: dict[str, list[Position]] = {
        "GUARD": [Position.POINT_GUARD, Position.SHOOTING_GUARD],
        "FORWARD": [Position.SMALL_FORWARD, Position.POWER_FORWARD],
        "CENTER": [Position.CENTER],
        "POINT GUARD": [Position.POINT_GUARD],
        "SHOOTING GUARD": [Position.SHOOTING_GUARD],
        "SMALL FORWARD": [Position.SMALL_FORWARD],
        "POWER FORWARD": [Position.POWER_FORWARD],
        "GUARD-FORWARD": [Position.SHOOTING_GUARD, Position.SMALL_FORWARD],
        "FORWARD-CENTER": [Position.POWER_FORWARD, Position.CENTER],
        "FORWARD-GUARD": [Position.SHOOTING_GUARD, Position.SMALL_FORWARD],
        "CENTER-FORWARD": [Position.POWER_FORWARD, Position.CENTER],
        # Single letter abbreviations
        "G": [Position.POINT_GUARD, Position.SHOOTING_GUARD],
        "F": [Position.SMALL_FORWARD, Position.POWER_FORWARD],
        "C": [Position.CENTER],
    }

    # PBP event type mappings
    EVENT_MAP: dict[str, tuple[EventType, dict[str, Any]]] = {
        # Shots
        "2FGM": (EventType.SHOT, {"shot_type": ShotType.TWO_POINT, "success": True}),
        "2FGA": (EventType.SHOT, {"shot_type": ShotType.TWO_POINT, "success": False}),
        "3FGM": (
            EventType.SHOT,
            {"shot_type": ShotType.THREE_POINT, "success": True},
        ),
        "3FGA": (
            EventType.SHOT,
            {"shot_type": ShotType.THREE_POINT, "success": False},
        ),
        # Free throws
        "FTM": (EventType.FREE_THROW, {"success": True}),
        "FTA": (EventType.FREE_THROW, {"success": False}),
        # Rebounds
        "O": (EventType.REBOUND, {"rebound_type": ReboundType.OFFENSIVE}),
        "D": (EventType.REBOUND, {"rebound_type": ReboundType.DEFENSIVE}),
        # Other events
        "AS": (EventType.ASSIST, {}),
        "TO": (EventType.TURNOVER, {}),
        "ST": (EventType.STEAL, {}),
        "BLK": (EventType.BLOCK, {}),
        "FV": (EventType.BLOCK, {}),  # Block in favor
        "CM": (EventType.FOUL, {"foul_type": FoulType.PERSONAL}),
        "CMT": (EventType.FOUL, {"foul_type": FoulType.TECHNICAL}),
        "CMU": (EventType.FOUL, {"foul_type": FoulType.FLAGRANT}),  # Unsportsmanlike
        "CMD": (EventType.FOUL, {"foul_type": FoulType.FLAGRANT}),  # Disqualifying
        # Game flow
        "BP": (EventType.PERIOD_START, {}),
        "EP": (EventType.PERIOD_END, {}),
        "TPOFF": (EventType.JUMP_BALL, {}),
        "JB": (EventType.JUMP_BALL, {}),
        "IN": (EventType.SUBSTITUTION, {}),
        "OUT": (EventType.SUBSTITUTION, {}),
        "TOUT": (EventType.TIMEOUT, {}),
        "TV": (EventType.TIMEOUT, {}),
    }

    # === Player Conversion ===

    def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
        """
        Convert raw Euroleague player data to CanonicalPlayer.

        Handles data from both XML API (teams roster) and JSON API
        (player profiles).

        Args:
            raw: Dictionary containing player data. Expected keys:
                - code or player_id or Player_ID: Player identifier
                - name or Player: Player name (LAST, FIRST format)
                - position: Position name (Guard, Forward, etc.)
                - height: Height in meters ("1.98")
                - birthDate or birthdate: Birthdate string
                - country or countryname: Country name
                - dorsal: Jersey number

        Returns:
            CanonicalPlayer with validated data.

        Raises:
            ConversionError: If external_id is missing or height is invalid.

        Example:
            >>> player = converter.convert_player({
            ...     "code": "P001234",
            ...     "name": "GILGEOUS-ALEXANDER, SHAI",
            ...     "height": "1.98",
            ... })
        """
        # Handle different ID field names
        external_id = str(
            raw.get("code")
            or raw.get("player_id")
            or raw.get("Player_ID", "").strip()
            or ""
        )
        if not external_id:
            raise ConversionError("Player missing external_id")

        # Parse height (meters to cm)
        height = self._parse_height_meters(raw.get("height"))

        # Parse birth date
        birth_date = parse_birthdate(
            raw.get("birthDate") or raw.get("birthdate") or raw.get("birth_date")
        )

        # Parse name (Euroleague uses "LAST, FIRST" format)
        first_name, last_name = self._parse_name(
            raw.get("name") or raw.get("Player") or ""
        )

        # Note: We skip nationality parsing as Euroleague provides country names
        # that may not match ISO codes. Set to None for now.

        return CanonicalPlayer(
            external_id=external_id,
            source=self.source,
            first_name=first_name,
            last_name=last_name,
            positions=self.map_position(raw.get("position")),
            height=height,
            birth_date=birth_date,
            nationality=None,  # Skip for now - would need country mapping
            jersey_number=str(raw.get("dorsal") or raw.get("Dorsal") or "") or None,
        )

    def _parse_height_meters(self, raw: Any) -> Height | None:
        """
        Parse height from meters string to Height object.

        Euroleague provides height in meters (e.g., "1.98").

        Args:
            raw: Height value, typically string like "1.98"

        Returns:
            Height object in cm or None if invalid.

        Raises:
            ConversionError: If height is outside valid range (150-250 cm).
        """
        if raw is None or raw == "":
            return None

        try:
            # Convert meters to centimeters
            meters = float(str(raw))
            cm = int(round(meters * 100))

            # Validate range
            if cm < 150 or cm > 250:
                raise ConversionError(f"Invalid height: {raw} ({cm} cm)")

            return Height(cm=cm)
        except (ValueError, TypeError):
            return None

    def _parse_name(self, raw_name: str) -> tuple[str, str]:
        """
        Parse Euroleague name format to first and last name.

        Euroleague uses "LAST, FIRST" format.

        Args:
            raw_name: Name string in "LAST, FIRST" format

        Returns:
            Tuple of (first_name, last_name)
        """
        if not raw_name:
            return ("", "")

        name = raw_name.strip()

        # Handle "LAST, FIRST" format
        if ", " in name:
            parts = name.split(", ", 1)
            last_name = parts[0].strip().title()
            first_name = parts[1].strip().title() if len(parts) > 1 else ""
            return (first_name, last_name)

        # Handle "FIRST LAST" format (fallback)
        parts = name.split(None, 1)
        if len(parts) == 1:
            return (parts[0].title(), "")
        return (parts[0].title(), parts[1].title())

    def map_position(self, raw: str | None) -> list[Position]:
        """
        Convert Euroleague position name to canonical positions.

        Euroleague uses full position names like "Guard", "Forward", "Center".

        Args:
            raw: Raw position string from Euroleague API.

        Returns:
            List of Position enums. Empty list if position unknown.

        Example:
            >>> converter.map_position("Guard")
            [Position.POINT_GUARD, Position.SHOOTING_GUARD]
            >>> converter.map_position("Center")
            [Position.CENTER]
        """
        if not raw:
            return []

        # Normalize input
        position_key = raw.strip().upper()

        # Handle hyphenated positions
        position_key = position_key.replace(" - ", "-")

        if position_key in self.POSITION_MAP:
            return self.POSITION_MAP[position_key]

        return []

    # === Team Conversion ===

    def convert_team(self, raw: dict[str, Any]) -> CanonicalTeam:
        """
        Convert raw Euroleague team data to CanonicalTeam.

        Args:
            raw: Dictionary containing team data. Expected keys:
                - code or teamCode: Team code (e.g., "BER")
                - name: Full team name
                - countryname: Country name
                - arena_name or arenaname: Arena name

        Returns:
            CanonicalTeam with validated data.

        Raises:
            ConversionError: If team code or name is missing.

        Example:
            >>> team = converter.convert_team({
            ...     "code": "BER",
            ...     "name": "ALBA Berlin",
            ... })
        """
        external_id = str(
            raw.get("code")
            or raw.get("teamCode")
            or raw.get("homecode")
            or raw.get("awaycode")
            or ""
        )
        if not external_id:
            raise ConversionError("Team missing external_id")

        name = (
            raw.get("name")
            or raw.get("hometeam")
            or raw.get("awayteam")
            or raw.get("team_name")
            or ""
        )
        if not name:
            raise ConversionError("Team missing name")

        return CanonicalTeam(
            external_id=external_id,
            source=self.source,
            name=name,
            short_name=external_id,  # Team code is the short name
            city=raw.get("city"),
            country=raw.get("countryname") or raw.get("country_name"),
        )

    # === Game Conversion ===

    def convert_game(self, raw: dict[str, Any]) -> CanonicalGame:
        """
        Convert raw Euroleague game data to CanonicalGame.

        Handles data from season schedule and live boxscore formats.

        Args:
            raw: Dictionary containing game data. Expected keys:
                - gamecode: Game identifier (e.g., "E2024_1")
                - homecode, awaycode: Team codes
                - date: Game date string
                - homescore, awayscore: Team scores
                - played: Whether game is complete

        Returns:
            CanonicalGame with validated data.

        Raises:
            ConversionError: If required fields are missing.
        """
        external_id = str(
            raw.get("gamecode")
            or raw.get("game_code")
            or raw.get("gameCode")
            or raw.get("external_id")
            or ""
        )
        if not external_id:
            raise ConversionError("Game missing external_id")

        # Get team codes
        home_team_id = str(
            raw.get("homecode")
            or raw.get("CodeTeamA")
            or raw.get("home_team_code")
            or ""
        )
        away_team_id = str(
            raw.get("awaycode")
            or raw.get("CodeTeamB")
            or raw.get("away_team_code")
            or ""
        )
        if not home_team_id or not away_team_id:
            raise ConversionError("Game missing team codes")

        # Parse game date
        game_date = self._parse_game_date(raw)

        # Get scores
        home_score = self._safe_int(
            raw.get("homescore") or raw.get("HomeScore") or raw.get("home_score")
        )
        away_score = self._safe_int(
            raw.get("awayscore") or raw.get("AwayScore") or raw.get("away_score")
        )

        # Determine game status
        status = self._determine_game_status(raw, home_score, away_score)

        # Extract season from gamecode (e.g., "E2024_1" → "E2024")
        season_id = self._extract_season_id(external_id, raw)

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
            venue=raw.get("arenaname") or raw.get("arena_name"),
        )

    def _parse_game_date(self, raw: dict[str, Any]) -> datetime:
        """Parse game date from various Euroleague formats."""
        date_str = raw.get("date") or raw.get("game_date")
        time_str = raw.get("startime") or raw.get("start_time") or "20:00"

        if not date_str:
            raise ConversionError("Game missing date")

        # Euroleague format: "Oct 03, 2024"
        date_formats = [
            "%b %d, %Y",  # Oct 03, 2024
            "%d %B, %Y",  # 03 October, 2024
            "%Y-%m-%d",  # 2024-10-03
            "%d/%m/%Y",  # 03/10/2024
        ]

        for fmt in date_formats:
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
        """Determine game status from raw data."""
        if raw.get("played") == "true" or raw.get("played") is True:
            return "FINAL"
        if raw.get("Live") is True:
            return "LIVE"
        if home_score is not None and away_score is not None:
            return "FINAL"
        return "SCHEDULED"

    def _extract_season_id(self, game_id: str, raw: dict[str, Any]) -> str:
        """Extract season ID from game ID or raw data."""
        # Try to extract from gamecode (e.g., "E2024_1" → "E2024")
        if "_" in game_id:
            return game_id.split("_")[0]

        # Fall back to raw data
        season = raw.get("Season") or raw.get("season")
        if season:
            return f"E{season}"

        return ""

    def _safe_int(self, value: Any) -> int | None:
        """Safely convert value to int, returning None on failure."""
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    # === Stats Conversion ===

    def convert_player_stats(self, raw: dict[str, Any]) -> CanonicalPlayerStats:
        """
        Convert raw Euroleague boxscore stats to CanonicalPlayerStats.

        Args:
            raw: Dictionary containing player stats from boxscore API.
                Handles both euroleague-api format and live API format.

        Returns:
            CanonicalPlayerStats with all stats fields populated.

        Example:
            >>> stats = converter.convert_player_stats({
            ...     "Player_ID": "P001234",
            ...     "Minutes": "25:30",
            ...     "Points": 22,
            ... })
        """
        player_id = str(
            raw.get("Player_ID", "").strip()
            or raw.get("PlayerId", "")
            or raw.get("player_id", "")
        )
        player_name = raw.get("Player") or raw.get("PlayerName") or ""
        team_id = str(raw.get("Team") or raw.get("team_id") or "")

        # Parse minutes to seconds
        minutes_seconds = self.parse_minutes_to_seconds(raw.get("Minutes"))

        # Get shooting stats
        fg_2m = self._safe_int(raw.get("FieldGoalsMade2")) or 0
        fg_2a = self._safe_int(raw.get("FieldGoalsAttempted2")) or 0
        fg_3m = self._safe_int(raw.get("FieldGoalsMade3")) or 0
        fg_3a = self._safe_int(raw.get("FieldGoalsAttempted3")) or 0
        ft_m = self._safe_int(raw.get("FreeThrowsMade")) or 0
        ft_a = self._safe_int(raw.get("FreeThrowsAttempted")) or 0

        # Rebounds
        off_reb = self._safe_int(raw.get("OffensiveRebounds")) or 0
        def_reb = self._safe_int(raw.get("DefensiveRebounds")) or 0
        total_reb = self._safe_int(raw.get("TotalRebounds")) or (off_reb + def_reb)

        # Determine starter status
        is_starter = raw.get("IsStarter") == 1 or raw.get("IsStarter") == 1.0

        return CanonicalPlayerStats(
            player_external_id=player_id,
            player_name=player_name,
            team_external_id=team_id,
            minutes_seconds=minutes_seconds,
            is_starter=is_starter,
            points=self._safe_int(raw.get("Points")) or 0,
            field_goals_made=fg_2m + fg_3m,
            field_goals_attempted=fg_2a + fg_3a,
            two_pointers_made=fg_2m,
            two_pointers_attempted=fg_2a,
            three_pointers_made=fg_3m,
            three_pointers_attempted=fg_3a,
            free_throws_made=ft_m,
            free_throws_attempted=ft_a,
            offensive_rebounds=off_reb,
            defensive_rebounds=def_reb,
            total_rebounds=total_reb,
            assists=self._safe_int(raw.get("Assistances") or raw.get("Assists")) or 0,
            steals=self._safe_int(raw.get("Steals")) or 0,
            blocks=self._safe_int(raw.get("BlocksFavour") or raw.get("Blocks")) or 0,
            turnovers=self._safe_int(raw.get("Turnovers")) or 0,
            personal_fouls=self._safe_int(raw.get("FoulsCommited")) or 0,
            plus_minus=self._safe_int(raw.get("Plusminus")),
        )

    def parse_minutes_to_seconds(self, raw: str | int | None) -> int:
        """
        Convert minutes from Euroleague MM:SS format to seconds.

        Args:
            raw: Raw minutes value. Expected formats:
                - "25:30" → 1530 seconds
                - "DNP" → 0 seconds
                - 25 → 1500 seconds (integer minutes)
                - None → 0 seconds

        Returns:
            Minutes converted to seconds.

        Example:
            >>> converter.parse_minutes_to_seconds("25:30")
            1530
            >>> converter.parse_minutes_to_seconds("DNP")
            0
        """
        if raw is None or raw == "" or raw == "DNP":
            return 0

        # Handle integer minutes
        if isinstance(raw, int):
            return raw * 60

        # Handle string format
        raw_str = str(raw).strip()
        if not raw_str or raw_str == "DNP":
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
        Convert raw Euroleague PBP event to CanonicalPBPEvent.

        Args:
            raw: Dictionary containing PBP event data. Expected keys:
                - PLAYTYPE: Event type code (2FGM, 3FGA, D, etc.)
                - PERIOD: Period number
                - MARKERTIME: Clock time (MM:SS)
                - PLAYER_ID: Player identifier
                - CODETEAM or TEAM: Team code
                - NUMBEROFPLAY: Event sequence number

        Returns:
            CanonicalPBPEvent or None for events we don't track.
        """
        event_type_raw = raw.get("PLAYTYPE") or raw.get("playtype") or ""
        if not event_type_raw:
            return None

        # Map event type
        event_type, attributes = self.map_event_type(event_type_raw)

        # Skip unmapped events (AG, RV, etc. are inferred from other events)
        if event_type is None:
            return None

        # Parse clock to seconds
        clock_str = raw.get("MARKERTIME") or raw.get("markertime") or "00:00"
        clock_seconds = self._parse_clock_to_seconds(clock_str)

        # Get period
        period = self._safe_int(raw.get("PERIOD") or raw.get("period")) or 1

        # Get event number
        event_number = self._safe_int(
            raw.get("NUMBEROFPLAY")
            or raw.get("numberofplay")
            or raw.get("TRUE_NUMBEROFPLAY")
        )
        if event_number is None:
            event_number = 0

        # Get player ID (may have trailing spaces)
        player_id = (
            str(raw.get("PLAYER_ID") or raw.get("player_id") or "").strip() or None
        )

        return CanonicalPBPEvent(
            event_number=event_number,
            period=period,
            clock_seconds=clock_seconds,
            event_type=event_type,
            shot_type=attributes.get("shot_type"),
            rebound_type=attributes.get("rebound_type"),
            foul_type=attributes.get("foul_type"),
            success=attributes.get("success"),
            player_external_id=player_id,
            player_name=raw.get("PLAYER") or raw.get("player"),
            team_external_id=str(
                raw.get("CODETEAM") or raw.get("codeteam") or raw.get("TEAM") or ""
            )
            or None,
        )

    def map_event_type(self, raw: str) -> tuple[EventType | None, dict[str, Any]]:
        """
        Map Euroleague event code to EventType and subtype attributes.

        Args:
            raw: Raw event type string from Euroleague PBP API.

        Returns:
            Tuple of (EventType, dict with subtype attributes).
            Returns (None, {}) for unmapped event types.

        Example:
            >>> converter.map_event_type("3FGM")
            (EventType.SHOT, {"shot_type": ShotType.THREE_POINT, "success": True})
            >>> converter.map_event_type("D")
            (EventType.REBOUND, {"rebound_type": ReboundType.DEFENSIVE})
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
        Convert raw Euroleague season data to CanonicalSeason.

        Euroleague seasons run from October to May and use codes like "E2024".

        Args:
            raw: Dictionary containing season data. Expected keys:
                - external_id or season_code: Season code (e.g., "E2024")
                - name: Season name (e.g., "2024-25")
                - year or Season: Season year (e.g., 2024)
                - is_current: Whether this is the active season

        Returns:
            CanonicalSeason with validated data.

        Raises:
            ConversionError: If season_id is missing.
        """
        external_id = str(
            raw.get("external_id")
            or raw.get("season_code")
            or raw.get("seasonCode")
            or ""
        )

        # Try to construct from year if not provided
        if not external_id:
            year = raw.get("year") or raw.get("Season")
            if year:
                external_id = f"E{year}"

        if not external_id:
            raise ConversionError("Season missing external_id")

        # Generate name from code if not provided using centralized normalization
        name = raw.get("name") or raw.get("season_name")
        if not name:
            try:
                # Extract year from code (E2024 → 2024, which is the START year)
                year = int(external_id[1:]) if external_id[0] in ("E", "U") else int(external_id)
                name = normalize_season_name(year)
            except (ValueError, IndexError):
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
