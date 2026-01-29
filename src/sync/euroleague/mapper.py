"""
Euroleague Mapper Module

Maps raw data from EuroleagueClient and EuroleagueDirectClient to normalized
Raw types for consumption by the sync infrastructure.

This module exports:
    - EuroleagueMapper: Main mapper class with methods for transforming data

Usage:
    from src.sync.euroleague.mapper import EuroleagueMapper

    mapper = EuroleagueMapper()
    raw_season = mapper.map_season(2024, "E")
    raw_team = mapper.map_team(team_data)
"""

from datetime import date, datetime

from src.schemas.enums import EventType, GameStatus
from src.sync.normalizers import Normalizers
from src.sync.season import normalize_season_name
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawPlayerStats,
    RawSeason,
    RawTeam,
)


class EuroleagueMapper:
    """
    Maps Euroleague data to normalized Raw types.

    Transforms data from EuroleagueClient (euroleague-api package) and
    EuroleagueDirectClient (direct XML/JSON APIs) into RawSeason, RawTeam,
    RawGame, RawBoxScore, RawPBPEvent, and RawPlayerInfo types.

    Example:
        >>> mapper = EuroleagueMapper()
        >>> season = mapper.map_season(2024, "E")
        >>> print(season.external_id)
        'E2024'
    """

    # Event type mappings from Euroleague format to canonical EventType
    # None values indicate events that should be skipped (inferred from links)
    EVENT_TYPE_MAP: dict[str, EventType | None] = {
        "2FGM": EventType.SHOT,
        "2FGA": EventType.SHOT,
        "3FGM": EventType.SHOT,
        "3FGA": EventType.SHOT,
        "FTM": EventType.FREE_THROW,
        "FTA": EventType.FREE_THROW,
        "O": EventType.REBOUND,  # subtype: OFFENSIVE
        "D": EventType.REBOUND,  # subtype: DEFENSIVE
        "AS": EventType.ASSIST,
        "TO": EventType.TURNOVER,
        "ST": EventType.STEAL,
        "BLK": EventType.BLOCK,
        "FV": EventType.BLOCK,  # Block in favor
        "AG": None,  # Skip - blocked player inferred from link
        "CM": EventType.FOUL,  # Committed foul
        "RV": None,  # Skip - fouled player inferred from link
        "BP": EventType.PERIOD_START,
        "EP": EventType.PERIOD_END,
        "TPOFF": EventType.JUMP_BALL,
        "IN": EventType.SUBSTITUTION,
        "OUT": EventType.SUBSTITUTION,
    }

    def parse_minutes_to_seconds(self, minutes_str: str) -> int:
        """
        Parse a minutes string like "24:35" to total seconds.

        Args:
            minutes_str: Time string in "MM:SS" format.

        Returns:
            Total seconds as integer.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> mapper.parse_minutes_to_seconds("24:35")
            1475
        """
        if not minutes_str:
            return 0

        try:
            parts = str(minutes_str).split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            return 0
        except (ValueError, AttributeError):
            return 0

    def parse_euroleague_date(self, date_str: str) -> datetime:
        """
        Parse Euroleague date format like "Oct 03, 2024".

        Args:
            date_str: Date string in Euroleague format.

        Returns:
            Parsed datetime object.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> dt = mapper.parse_euroleague_date("Oct 03, 2024")
            >>> dt.month
            10
        """
        if not date_str:
            return datetime.now()

        try:
            # Try "Oct 03, 2024" format
            return datetime.strptime(date_str, "%b %d, %Y")
        except ValueError:
            try:
                # Try ISO format
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try "03/10/2024" format
                    return datetime.strptime(date_str, "%d/%m/%Y")
                except ValueError:
                    return datetime.now()

    def parse_birthdate(self, date_str: str) -> date | None:
        """
        Parse birthdate in Euroleague format like "12 March, 1998".

        Args:
            date_str: Birthdate string.

        Returns:
            Parsed date object or None if invalid.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> bd = mapper.parse_birthdate("12 March, 1998")
            >>> bd.year
            1998
        """
        if not date_str:
            return None

        try:
            # Try "12 March, 1998" format
            return datetime.strptime(date_str, "%d %B, %Y").date()
        except ValueError:
            try:
                # Try "12/03/1998" format
                return datetime.strptime(date_str, "%d/%m/%Y").date()
            except ValueError:
                try:
                    # Try "1998-03-12" format
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    return None

    def height_meters_to_cm(self, height_str: str) -> int | None:
        """
        Convert height from meters (e.g., "1.8") to centimeters.

        Args:
            height_str: Height in meters as string.

        Returns:
            Height in centimeters or None if invalid.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> mapper.height_meters_to_cm("1.8")
            180
            >>> mapper.height_meters_to_cm("2.05")
            205
        """
        if not height_str:
            return None

        try:
            height_m = float(height_str)
            # Use round to avoid floating point precision issues
            return round(height_m * 100)
        except (ValueError, TypeError):
            return None

    def map_season(self, season: int, competition: str = "E") -> RawSeason:
        """
        Create a RawSeason for a Euroleague season.

        The season name is normalized to YYYY-YY format (e.g., "2024-25").
        The source-specific identifier (e.g., "E2024") is stored in source_id.

        Args:
            season: Season year (e.g., 2024).
            competition: Competition code ("E" for Euroleague, "U" for EuroCup).

        Returns:
            RawSeason with normalized name in YYYY-YY format.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> s = mapper.map_season(2024, "E")
            >>> s.name
            '2024-25'
            >>> s.source_id
            'E2024'
        """
        # Normalize to standard YYYY-YY format
        normalized_name = normalize_season_name(season)
        # Store source-specific ID (e.g., "E2024") for external reference
        source_id = f"{competition}{season}"

        return RawSeason(
            external_id=normalized_name,
            name=normalized_name,
            source_id=source_id,
            start_date=date(season, 10, 1),  # Season typically starts in October
            end_date=date(season + 1, 5, 31),  # Season ends in May
            is_current=False,  # Set by adapter based on configured seasons
        )

    def map_team(self, data: dict) -> RawTeam:
        """
        Map team data from teams XML to RawTeam.

        Args:
            data: Team dictionary from parsed XML.

        Returns:
            RawTeam with team information.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> team = mapper.map_team({"code": "BER", "name": "ALBA Berlin"})
            >>> team.external_id
            'BER'
        """
        return RawTeam(
            external_id=data.get("code", ""),
            name=data.get("name", ""),
            short_name=data.get("tv_code") or data.get("code"),
        )

    def map_game(self, data: dict, season: int, competition: str = "E") -> RawGame:
        """
        Map game data from season_games response to RawGame.

        The API returns two gamecode fields:
        - gameCode (int): Raw game number (e.g., 1)
        - gamecode (str): Already formatted ID (e.g., "E2025_1")

        We prefer gameCode (int) to construct the ID ourselves, avoiding
        duplication like "E2025_E2025_1".

        Args:
            data: Game dictionary from euroleague-api.
            season: Season year.
            competition: Competition code.

        Returns:
            RawGame with game information.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> game = mapper.map_game({
            ...     "gameCode": 1,
            ...     "gamecode": "E2024_1",
            ...     "homecode": "BER",
            ...     "awaycode": "PAN",
            ...     "date": "Oct 03, 2024",
            ...     "homescore": 77,
            ...     "awayscore": 87
            ... }, 2024)
            >>> game.external_id
            'E2024_1'
        """
        # Create unique game ID combining season and gamecode
        # Prefer gameCode (int) over gamecode (str) to avoid duplication
        # The API returns gamecode as "E2025_1" which would become "E2025_E2025_1"
        gamecode = data.get("gameCode") or data.get("gamenumber")

        if gamecode is None:
            # Fall back to gamecode string field
            gamecode_str = data.get("gamecode") or data.get("Gamecode") or ""
            # If it already has the competition prefix, use it directly
            if isinstance(gamecode_str, str) and gamecode_str.startswith(competition):
                external_id = gamecode_str
            else:
                external_id = f"{competition}{season}_{gamecode_str}"
        else:
            external_id = f"{competition}{season}_{gamecode}"

        # Parse date
        date_str = data.get("date") or data.get("Date") or ""
        game_date = self.parse_euroleague_date(date_str)

        # Get scores
        home_score = data.get("homescore") or data.get("homescorets")
        away_score = data.get("awayscore") or data.get("awayscorets")

        # Determine status - normalize to GameStatus enum
        raw_status = "final" if home_score is not None and away_score is not None else "scheduled"
        status = Normalizers.normalize_game_status(raw_status, "euroleague")

        return RawGame(
            external_id=external_id,
            home_team_external_id=str(
                data.get("homecode") or data.get("HomeCode") or ""
            ),
            away_team_external_id=str(
                data.get("awaycode") or data.get("AwayCode") or ""
            ),
            game_date=game_date,
            status=status,
            home_score=int(home_score) if home_score is not None else None,
            away_score=int(away_score) if away_score is not None else None,
        )

    def map_player_stats(self, data: dict) -> RawPlayerStats:
        """
        Map player statistics from boxscore to RawPlayerStats.

        Args:
            data: Player stats dictionary from boxscore API.

        Returns:
            RawPlayerStats with mapped statistics.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> stats = mapper.map_player_stats({
            ...     "Player_ID": "P007025",
            ...     "Player": "MATTISSECK, JONAS",
            ...     "Team": "BER",
            ...     "Minutes": "24:35",
            ...     "Points": 6,
            ...     "IsStarter": 1
            ... })
            >>> stats.points
            6
        """
        # Parse minutes
        minutes_str = str(data.get("Minutes", ""))
        minutes_played = self.parse_minutes_to_seconds(minutes_str)

        # Get 2-point and 3-point field goals
        fg2m = data.get("FieldGoalsMade2", 0) or 0
        fg2a = data.get("FieldGoalsAttempted2", 0) or 0
        fg3m = data.get("FieldGoalsMade3", 0) or 0
        fg3a = data.get("FieldGoalsAttempted3", 0) or 0

        return RawPlayerStats(
            player_external_id=str(data.get("Player_ID", "")).strip(),
            player_name=data.get("Player", ""),
            team_external_id=str(data.get("Team", "")).strip(),
            minutes_played=minutes_played,
            is_starter=bool(data.get("IsStarter", 0)),
            points=data.get("Points", 0) or 0,
            field_goals_made=fg2m + fg3m,
            field_goals_attempted=fg2a + fg3a,
            two_pointers_made=fg2m,
            two_pointers_attempted=fg2a,
            three_pointers_made=fg3m,
            three_pointers_attempted=fg3a,
            free_throws_made=data.get("FreeThrowsMade", 0) or 0,
            free_throws_attempted=data.get("FreeThrowsAttempted", 0) or 0,
            offensive_rebounds=data.get("OffensiveRebounds", 0) or 0,
            defensive_rebounds=data.get("DefensiveRebounds", 0) or 0,
            total_rebounds=data.get("TotalRebounds", 0) or 0,
            assists=data.get("Assistances", 0) or 0,
            turnovers=data.get("Turnovers", 0) or 0,
            steals=data.get("Steals", 0) or 0,
            blocks=data.get("BlocksFavour", 0) or 0,
            personal_fouls=data.get("FoulsCommited", 0) or 0,
            plus_minus=data.get("Plusminus", 0) or 0,
            efficiency=data.get("Valuation", 0) or 0,
        )

    def map_boxscore(
        self,
        game_data: dict,
        boxscore_data: list[dict],
        season: int,
        competition: str = "E",
    ) -> RawBoxScore:
        """
        Map boxscore data to RawBoxScore.

        Args:
            game_data: Game metadata dictionary.
            boxscore_data: List of player stats dictionaries.
            season: Season year.
            competition: Competition code.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> boxscore = mapper.map_boxscore(
            ...     {"gamecode": 1, "hometeam": "BER", ...},
            ...     [{"Player_ID": "P007025", ...}],
            ...     2024
            ... )
            >>> len(boxscore.home_players) > 0
            True
        """
        # Map game
        game = self.map_game(game_data, season, competition)

        # Split players by team
        home_players = []
        away_players = []

        for player_data in boxscore_data:
            stats = self.map_player_stats(player_data)

            if stats.team_external_id == game.home_team_external_id:
                home_players.append(stats)
            else:
                away_players.append(stats)

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_boxscore_from_live(
        self,
        live_data: dict,
        gamecode: int,
        season: int,
        competition: str = "E",
    ) -> RawBoxScore:
        """
        Map live boxscore data to RawBoxScore.

        Args:
            live_data: Live boxscore dictionary from direct client.
            gamecode: Game code.
            season: Season year.
            competition: Competition code.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> boxscore = mapper.map_boxscore_from_live(live_data, 1, 2024)
            >>> boxscore.game.external_id
            'E2024_1'
        """
        stats_list = live_data.get("Stats", [])
        if len(stats_list) < 2:
            raise ValueError("Invalid boxscore data: expected 2 teams")

        home_team_data = stats_list[0]
        away_team_data = stats_list[1]

        # Get team codes from player stats
        home_team_code = ""
        away_team_code = ""

        home_players_data = home_team_data.get("PlayersStats", [])
        away_players_data = away_team_data.get("PlayersStats", [])

        if home_players_data:
            home_team_code = str(home_players_data[0].get("Team", ""))
        if away_players_data:
            away_team_code = str(away_players_data[0].get("Team", ""))

        # Get scores from ByQuarter
        by_quarter = live_data.get("ByQuarter", [])
        home_score = None
        away_score = None

        if by_quarter and len(by_quarter) >= 2:
            home_totals = by_quarter[0]
            away_totals = by_quarter[1]
            home_score = sum(
                home_totals.get(f"Quarter{i}", 0) or 0 for i in range(1, 5)
            )
            away_score = sum(
                away_totals.get(f"Quarter{i}", 0) or 0 for i in range(1, 5)
            )

        # Create game - normalize status to GameStatus enum
        is_live = live_data.get("Live", True)
        raw_status = "live" if is_live else "final"
        status = Normalizers.normalize_game_status(raw_status, "euroleague")

        game = RawGame(
            external_id=f"{competition}{season}_{gamecode}",
            home_team_external_id=home_team_code,
            away_team_external_id=away_team_code,
            game_date=datetime.now(),  # Live data doesn't include date
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

        # Map player stats
        home_players = [self.map_player_stats(p) for p in home_players_data]
        away_players = [self.map_player_stats(p) for p in away_players_data]

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_pbp_event(self, data: dict, event_num: int) -> RawPBPEvent | None:
        """
        Map a play-by-play event to RawPBPEvent.

        Args:
            data: Event dictionary from PBP API.
            event_num: Event number to assign.

        Returns:
            RawPBPEvent with mapped event data, or None if event should be skipped.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> event = mapper.map_pbp_event({
            ...     "PLAYTYPE": "2FGM",
            ...     "PERIOD": 1,
            ...     "MARKERTIME": "09:45",
            ...     "TEAM": "BER"
            ... }, 1)
            >>> event.event_type
            EventType.SHOT
        """
        # Get event type
        play_type = str(data.get("PLAYTYPE", data.get("playtype", "")))
        event_type = self.EVENT_TYPE_MAP.get(play_type)

        # Skip events with None mapping (AG, RV - inferred from links)
        if event_type is None:
            return None

        # Determine success for shot events
        success = None
        if play_type in ("2FGM", "3FGM", "FTM"):
            success = True
        elif play_type in ("2FGA", "3FGA", "FTA"):
            success = False

        # Get period
        period = data.get("PERIOD", data.get("period", 1))
        if isinstance(period, str):
            try:
                period = int(period)
            except ValueError:
                period = 1

        # Get player info
        player_name = data.get("PLAYERNAME", data.get("playername"))
        if not player_name:
            player_name = data.get("PLAYER", data.get("player"))

        player_external_id = data.get("PLAYER_ID", data.get("player_id"))
        if player_external_id:
            player_external_id = str(player_external_id).strip() or None

        # Get coordinates
        coord_x = data.get("COORD_X", data.get("coord_x"))
        coord_y = data.get("COORD_Y", data.get("coord_y"))

        if coord_x is not None:
            try:
                coord_x = float(coord_x)
            except (ValueError, TypeError):
                coord_x = None

        if coord_y is not None:
            try:
                coord_y = float(coord_y)
            except (ValueError, TypeError):
                coord_y = None

        # Determine subtype for rebounds
        event_subtype = None
        if play_type == "O":
            event_subtype = "OFFENSIVE"
        elif play_type == "D":
            event_subtype = "DEFENSIVE"

        return RawPBPEvent(
            event_number=event_num,
            period=period,
            clock=str(data.get("MARKERTIME", data.get("markertime", ""))),
            event_type=event_type,
            event_subtype=event_subtype,
            player_external_id=player_external_id,
            player_name=player_name,
            team_external_id=str(data.get("TEAM", data.get("team", ""))) or None,
            success=success,
            coord_x=coord_x,
            coord_y=coord_y,
            related_event_numbers=None,
        )

    def map_pbp_events(self, pbp_data: list[dict]) -> list[RawPBPEvent]:
        """
        Map all play-by-play events from PBP response.

        Args:
            pbp_data: List of PBP event dictionaries.

        Returns:
            List of RawPBPEvent objects (skipping None-mapped events).

        Example:
            >>> mapper = EuroleagueMapper()
            >>> events = mapper.map_pbp_events([{"PLAYTYPE": "2FGM", ...}])
            >>> len(events)
            1
        """
        events = []
        for i, event_data in enumerate(pbp_data, start=1):
            event = self.map_pbp_event(event_data, i)
            if event is not None:
                events.append(event)
        return events

    def map_pbp_from_live(self, live_pbp: dict) -> list[RawPBPEvent]:
        """
        Map play-by-play data from live API format.

        Live PBP data is organized by quarter (FirstQuarter, SecondQuarter, etc.)

        Args:
            live_pbp: Live PBP dictionary with quarters.

        Returns:
            List of RawPBPEvent objects (skipping None-mapped events).

        Example:
            >>> mapper = EuroleagueMapper()
            >>> events = mapper.map_pbp_from_live({
            ...     "FirstQuarter": [{"PLAYTYPE": "2FGM", ...}]
            ... })
        """
        events = []
        event_num = 1

        # Quarter keys in order
        quarter_keys = [
            "FirstQuarter",
            "SecondQuarter",
            "ThirdQuarter",
            "FourthQuarter",
            "ExtraTime",  # Overtime
        ]

        for i, quarter_key in enumerate(quarter_keys, start=1):
            quarter_events = live_pbp.get(quarter_key, [])
            if not quarter_events:
                continue

            for event_data in quarter_events:
                # Add period if not present
                if "PERIOD" not in event_data and "period" not in event_data:
                    event_data["PERIOD"] = i

                event = self.map_pbp_event(event_data, event_num)
                if event is not None:
                    events.append(event)
                event_num += 1

        return events

    def map_player_info(self, data: dict) -> RawPlayerInfo:
        """
        Map player profile data from player XML to RawPlayerInfo.

        Args:
            data: Player dictionary from parsed XML.

        Returns:
            RawPlayerInfo with biographical data.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> info = mapper.map_player_info({
            ...     "name": "EDWARDS, CARSEN",
            ...     "height": "1.8",
            ...     "birthdate": "12 March, 1998"
            ... })
            >>> info.height_cm
            180
        """
        # Parse name (format: "LASTNAME, FIRSTNAME")
        name = data.get("name", "")
        first_name = ""
        last_name = ""

        if "," in name:
            parts = name.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = name.split()
            if parts:
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Parse height
        height_cm = self.height_meters_to_cm(data.get("height"))

        # Parse birthdate
        birth_date = self.parse_birthdate(data.get("birthdate"))

        # Map position - normalize to list of Position enums
        raw_position = data.get("position")
        positions = Normalizers.try_normalize_positions(raw_position, "euroleague") or []

        # Map nationality (country field from API)
        nationality = data.get("country")

        return RawPlayerInfo(
            external_id=data.get("code", data.get("player_code", "")),
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            height_cm=height_cm,
            positions=positions,
            nationality=nationality,
        )

    def map_player_from_roster(
        self, data: dict, team_code: str  # noqa: ARG002
    ) -> RawPlayerInfo:
        """
        Map player data from team roster to RawPlayerInfo.

        Args:
            data: Player dictionary from team roster.
            team_code: Team code for context.

        Returns:
            RawPlayerInfo with basic player data.

        Example:
            >>> mapper = EuroleagueMapper()
            >>> info = mapper.map_player_from_roster({
            ...     "code": "P007025",
            ...     "name": "MATTISSECK, JONAS"
            ... }, "BER")
            >>> info.external_id
            'P007025'
        """
        # Parse name
        name = data.get("name", "")
        first_name = ""
        last_name = ""

        if "," in name:
            parts = name.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = name.split()
            if parts:
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Add P prefix to code for consistency with boxscore Player_ID format
        code = data.get("code", "")
        external_id = f"P{code}" if code and not code.startswith("P") else code

        # Normalize position to list of Position enums
        raw_position = data.get("position")
        positions = Normalizers.try_normalize_positions(raw_position, "euroleague") or []

        return RawPlayerInfo(
            external_id=external_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=None,
            height_cm=None,
            positions=positions,
            jersey_number=data.get("dorsal"),
        )
