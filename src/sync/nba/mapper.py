"""
NBA Mapper Module

Maps raw data from NBAClient to normalized Raw types for consumption
by the sync infrastructure.

This module exports:
    - NBAMapper: Main mapper class with methods for transforming data

Field Mappings (NBA API V3 -> RawTypes):
    Teams (static):
        - id -> external_id
        - full_name -> name
        - abbreviation -> short_name

    Games (LeagueGameFinder):
        - GAME_ID -> external_id
        - TEAM_ID -> home/away_team_external_id (based on MATCHUP)
        - GAME_DATE -> game_date
        - WL -> status (present = final)
        - PTS -> home_score/away_score

    Player Stats (BoxScoreTraditionalV3):
        - personId -> player_external_id
        - firstName + familyName -> player_name
        - teamId (from parent) -> team_external_id
        - statistics.minutes -> minutes_played (MM:SS -> seconds)
        - statistics.points -> points
        - statistics.fieldGoalsMade -> field_goals_made
        - etc.

    PBP Events (PlayByPlayV3):
        - actionNumber -> event_number
        - period -> period
        - clock -> clock (PT format -> MM:SS)
        - actionType -> event_type
        - playerNameI -> player_name
        - teamId -> team_external_id
        - shotResult (Made/Missed) -> success
        - xLegacy, yLegacy -> coord_x, coord_y

Usage:
    from src.sync.nba.mapper import NBAMapper

    mapper = NBAMapper()
    raw_season = mapper.map_season("2023-24")
    raw_team = mapper.map_team(team_data)
"""

from datetime import date, datetime

from src.sync.season import normalize_season_name
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerStats,
    RawSeason,
    RawTeam,
)


class NBAMapper:
    """
    Maps NBA API data to normalized Raw types.

    Transforms data from NBAClient into RawSeason, RawTeam, RawGame,
    RawBoxScore, and RawPBPEvent types.

    Example:
        >>> mapper = NBAMapper()
        >>> season = mapper.map_season("2023-24")
        >>> print(season.external_id)
        'NBA2023-24'
    """

    # Event type mappings from NBA V3 actionType to normalized format
    EVENT_TYPE_MAP = {
        "Made Shot": "shot",
        "Missed Shot": "shot",
        "Free Throw": "free_throw",
        "Rebound": "rebound",
        "Turnover": "turnover",
        "Steal": "steal",
        "Block": "block",
        "Foul": "foul",
        "Violation": "violation",
        "Substitution": "substitution",
        "Timeout": "timeout",
        "Jump Ball": "jump_ball",
        "period": "period_event",
        "game": "game_event",
    }

    def parse_minutes_to_seconds(self, minutes_str: str) -> int:
        """
        Parse NBA minutes format to total seconds.

        Handles both MM:SS format (from boxscore) and PT format (from PBP).

        Args:
            minutes_str: Time string in MM:SS or PT format.

        Returns:
            Total seconds as integer.

        Example:
            >>> mapper = NBAMapper()
            >>> mapper.parse_minutes_to_seconds("24:35")
            1475
            >>> mapper.parse_minutes_to_seconds("PT10M30.00S")
            630
        """
        if not minutes_str:
            return 0

        minutes_str = str(minutes_str)

        try:
            # Handle PT format (e.g., "PT24M35.00S") - used in PBP clock
            if minutes_str.startswith("PT"):
                minutes_str = minutes_str[2:]  # Remove "PT"
                minutes = 0
                seconds = 0

                if "M" in minutes_str:
                    parts = minutes_str.split("M")
                    minutes = int(parts[0])
                    if len(parts) > 1 and parts[1]:
                        sec_part = parts[1].rstrip("S")
                        if sec_part:
                            seconds = int(float(sec_part))
                elif minutes_str.endswith("S"):
                    seconds = int(float(minutes_str.rstrip("S")))

                return minutes * 60 + seconds

            # Handle MM:SS format (from boxscore)
            if ":" in minutes_str:
                parts = minutes_str.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(float(parts[1]))
                    return minutes * 60 + seconds

            # Try as just minutes
            return int(float(minutes_str)) * 60

        except (ValueError, AttributeError):
            return 0

    def parse_nba_date(self, date_str: str) -> datetime:
        """
        Parse NBA date format.

        Args:
            date_str: Date string from NBA API.

        Returns:
            Parsed datetime object.

        Example:
            >>> mapper = NBAMapper()
            >>> dt = mapper.parse_nba_date("2023-10-24")
            >>> dt.year
            2023
        """
        if not date_str:
            return datetime.now()

        try:
            # Try ISO format with time
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Try date only format (YYYY-MM-DD)
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # Try MM/DD/YYYY format
                return datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                return datetime.now()

    def parse_clock(self, clock_str: str) -> str:
        """
        Parse NBA V3 clock format (PT format) to MM:SS.

        Args:
            clock_str: Clock string in PT format (e.g., "PT10M45.00S").

        Returns:
            Clock in MM:SS format.

        Example:
            >>> mapper = NBAMapper()
            >>> mapper.parse_clock("PT10M45.00S")
            '10:45'
        """
        if not clock_str:
            return "00:00"

        clock_str = str(clock_str)

        try:
            if clock_str.startswith("PT"):
                seconds = self.parse_minutes_to_seconds(clock_str)
                minutes = seconds // 60
                secs = seconds % 60
                return f"{minutes:02d}:{secs:02d}"

            if ":" in clock_str:
                parts = clock_str.split(":")
                if len(parts) == 2:
                    return f"{int(parts[0]):02d}:{int(float(parts[1])):02d}"

            return clock_str
        except (ValueError, AttributeError):
            return "00:00"

    def map_season(self, season: str) -> RawSeason:
        """
        Create a RawSeason for an NBA season.

        The season name is normalized to YYYY-YY format (e.g., "2023-24").
        The source-specific identifier (e.g., "NBA2023-24") is stored in source_id.

        Args:
            season: Season string (e.g., "2023-24").

        Returns:
            RawSeason with normalized name in YYYY-YY format.

        Example:
            >>> mapper = NBAMapper()
            >>> s = mapper.map_season("2023-24")
            >>> s.name
            '2023-24'
            >>> s.source_id
            'NBA2023-24'
        """
        parts = season.split("-")
        start_year = int(parts[0])
        end_year_short = int(parts[1]) if len(parts) > 1 else (start_year + 1) % 100
        end_year = start_year // 100 * 100 + end_year_short

        # Normalize to standard YYYY-YY format
        normalized_name = normalize_season_name(start_year)
        # Store source-specific ID for external reference
        source_id = f"NBA{season}"

        return RawSeason(
            external_id=normalized_name,
            name=normalized_name,
            source_id=source_id,
            start_date=date(start_year, 10, 1),
            end_date=date(end_year, 6, 30),
            is_current=False,
        )

    def map_team(self, data: dict) -> RawTeam:
        """
        Map team data from nba_api static teams to RawTeam.

        Args:
            data: Team dictionary from nba_api.

        Returns:
            RawTeam with team information.

        Example:
            >>> mapper = NBAMapper()
            >>> team = mapper.map_team({
            ...     "id": 1610612737,
            ...     "full_name": "Atlanta Hawks",
            ...     "abbreviation": "ATL"
            ... })
            >>> team.external_id
            '1610612737'
        """
        return RawTeam(
            external_id=str(data.get("id", "")),
            name=data.get("full_name", data.get("name", "")),
            short_name=data.get("abbreviation", data.get("nickname", "")),
        )

    def map_game_from_schedule(self, data: dict) -> RawGame:
        """
        Map game data from LeagueGameFinder to RawGame.

        Note: LeagueGameFinder returns one row per team per game,
        so we get duplicates. The adapter handles deduplication.

        Args:
            data: Game dictionary from LeagueGameFinder.

        Returns:
            RawGame with game information.

        Example:
            >>> mapper = NBAMapper()
            >>> game = mapper.map_game_from_schedule({
            ...     "GAME_ID": "0022300001",
            ...     "TEAM_ID": 1610612737,
            ...     "MATCHUP": "ATL vs. CHI",
            ...     "GAME_DATE": "2023-10-24",
            ...     "WL": "W",
            ...     "PTS": 112
            ... })
            >>> game.external_id
            '0022300001'
        """
        game_id = str(data.get("GAME_ID", ""))
        team_id = str(data.get("TEAM_ID", ""))
        matchup = data.get("MATCHUP", "")
        game_date = data.get("GAME_DATE", "")
        wl = data.get("WL")
        pts = data.get("PTS")

        # Parse matchup to determine home/away
        # Matchup format: "ATL vs. CHI" (home) or "ATL @ CHI" (away)
        is_home = " vs. " in matchup

        # Determine status
        status = "final" if wl is not None else "scheduled"

        return RawGame(
            external_id=game_id,
            home_team_external_id=team_id if is_home else "",
            away_team_external_id=team_id if not is_home else "",
            game_date=self.parse_nba_date(game_date),
            status=status,
            home_score=pts if is_home and pts else None,
            away_score=pts if not is_home and pts else None,
        )

    def map_player_stats_v3(self, player: dict, team_id: str) -> RawPlayerStats:
        """
        Map player statistics from BoxScoreTraditionalV3 nested structure.

        V3 format has player info at top level and stats in nested 'statistics'.

        Args:
            player: Player dictionary with nested statistics.
            team_id: Team ID from parent structure.

        Returns:
            RawPlayerStats with mapped statistics.

        Example:
            >>> mapper = NBAMapper()
            >>> stats = mapper.map_player_stats_v3({
            ...     "personId": 1627759,
            ...     "firstName": "Jaylen",
            ...     "familyName": "Brown",
            ...     "position": "F",
            ...     "statistics": {
            ...         "minutes": "35:56",
            ...         "points": 37,
            ...         ...
            ...     }
            ... }, "1610612738")
            >>> stats.points
            37
        """
        stats = player.get("statistics", {})

        # Parse minutes (MM:SS format in V3)
        minutes_str = str(stats.get("minutes", ""))
        minutes_played = self.parse_minutes_to_seconds(minutes_str)

        # Build player name
        first_name = player.get("firstName", "")
        family_name = player.get("familyName", "")
        player_name = f"{first_name} {family_name}".strip()
        if not player_name:
            player_name = player.get("nameI", "")

        # Get field goal stats
        fgm = stats.get("fieldGoalsMade", 0) or 0
        fga = stats.get("fieldGoalsAttempted", 0) or 0
        fg3m = stats.get("threePointersMade", 0) or 0
        fg3a = stats.get("threePointersAttempted", 0) or 0

        # Calculate 2-point stats
        fg2m = fgm - fg3m
        fg2a = fga - fg3a

        # Determine if starter from position field
        position = player.get("position", "")
        is_starter = bool(position and position.strip())

        return RawPlayerStats(
            player_external_id=str(player.get("personId", "")),
            player_name=player_name,
            team_external_id=team_id,
            minutes_played=minutes_played,
            is_starter=is_starter,
            points=stats.get("points", 0) or 0,
            field_goals_made=fgm,
            field_goals_attempted=fga,
            two_pointers_made=fg2m,
            two_pointers_attempted=fg2a,
            three_pointers_made=fg3m,
            three_pointers_attempted=fg3a,
            free_throws_made=stats.get("freeThrowsMade", 0) or 0,
            free_throws_attempted=stats.get("freeThrowsAttempted", 0) or 0,
            offensive_rebounds=stats.get("reboundsOffensive", 0) or 0,
            defensive_rebounds=stats.get("reboundsDefensive", 0) or 0,
            total_rebounds=stats.get("reboundsTotal", 0) or 0,
            assists=stats.get("assists", 0) or 0,
            turnovers=stats.get("turnovers", 0) or 0,
            steals=stats.get("steals", 0) or 0,
            blocks=stats.get("blocks", 0) or 0,
            personal_fouls=stats.get("foulsPersonal", 0) or 0,
            plus_minus=int(stats.get("plusMinusPoints", 0) or 0),
            efficiency=0,  # NBA doesn't use PIR
        )

    def map_boxscore(self, boxscore_data: dict, game_id: str) -> RawBoxScore:
        """
        Map boxscore data from BoxScoreTraditionalV3 to RawBoxScore.

        V3 structure: boxScoreTraditional.homeTeam/awayTeam with nested players.

        Args:
            boxscore_data: Full response from BoxScoreTraditionalV3.get_dict().
            game_id: NBA game ID.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = NBAMapper()
            >>> boxscore = mapper.map_boxscore(boxscore_data, "0022400001")
            >>> len(boxscore.home_players) > 0
            True
        """
        bs = boxscore_data.get("boxScoreTraditional", {})

        home_team = bs.get("homeTeam", {})
        away_team = bs.get("awayTeam", {})

        home_team_id = str(home_team.get("teamId", bs.get("homeTeamId", "")))
        away_team_id = str(away_team.get("teamId", bs.get("awayTeamId", "")))

        # Get team scores from statistics
        home_stats = home_team.get("statistics", {})
        away_stats = away_team.get("statistics", {})
        home_score = home_stats.get("points")
        away_score = away_stats.get("points")

        # Create game record
        game = RawGame(
            external_id=game_id,
            home_team_external_id=home_team_id,
            away_team_external_id=away_team_id,
            game_date=datetime.now(),  # V3 doesn't include date in boxscore
            status="final" if home_score is not None else "scheduled",
            home_score=home_score,
            away_score=away_score,
        )

        # Map player stats
        home_players = []
        for player in home_team.get("players", []):
            stats = self.map_player_stats_v3(player, home_team_id)
            home_players.append(stats)

        away_players = []
        for player in away_team.get("players", []):
            stats = self.map_player_stats_v3(player, away_team_id)
            away_players.append(stats)

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_pbp_event(self, data: dict) -> RawPBPEvent:
        """
        Map a play-by-play event from PlayByPlayV3 to RawPBPEvent.

        V3 uses actionType like "Made Shot", "Missed Shot", "Rebound", etc.

        Args:
            data: Event dictionary from PlayByPlayV3 actions array.

        Returns:
            RawPBPEvent with mapped event data.

        Example:
            >>> mapper = NBAMapper()
            >>> event = mapper.map_pbp_event({
            ...     "actionNumber": 1,
            ...     "period": 1,
            ...     "clock": "PT12M00.00S",
            ...     "actionType": "Jump Ball",
            ...     "teamId": 1610612737
            ... })
            >>> event.event_type
            'jump_ball'
        """
        # Get event type
        action_type = data.get("actionType", "")
        event_type = self.EVENT_TYPE_MAP.get(action_type, action_type.lower())

        # Determine success for shot events
        success = None
        shot_result = data.get("shotResult", "")
        if shot_result:
            success = shot_result.lower() == "made"
        elif action_type == "Made Shot":
            success = True
        elif action_type == "Missed Shot":
            success = False

        # Get period
        period = data.get("period", 1)
        if isinstance(period, str):
            try:
                period = int(period)
            except ValueError:
                period = 1

        # Get player name (V3 uses playerNameI)
        player_name = data.get("playerNameI") or data.get("playerName")

        # Get coordinates
        coord_x = data.get("xLegacy")
        coord_y = data.get("yLegacy")

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

        # Get team ID
        team_id = data.get("teamId")
        team_external_id = str(team_id) if team_id and team_id != 0 else None

        return RawPBPEvent(
            event_number=data.get("actionNumber", 0),
            period=period,
            clock=self.parse_clock(data.get("clock", "")),
            event_type=event_type,
            player_name=player_name if player_name else None,
            team_external_id=team_external_id,
            success=success,
            coord_x=coord_x,
            coord_y=coord_y,
            related_event_numbers=None,
        )

    def map_pbp_events(self, pbp_data: list[dict]) -> list[RawPBPEvent]:
        """
        Map all play-by-play events from PlayByPlayV3 response.

        Args:
            pbp_data: List of action dictionaries from game.actions.

        Returns:
            List of RawPBPEvent objects.

        Example:
            >>> mapper = NBAMapper()
            >>> events = mapper.map_pbp_events([{"actionNumber": 1, ...}])
            >>> len(events)
            1
        """
        events = []
        for event_data in pbp_data:
            event = self.map_pbp_event(event_data)
            events.append(event)
        return events
