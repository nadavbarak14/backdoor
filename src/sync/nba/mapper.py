"""
NBA Mapper Module

Maps raw data from NBAClient to normalized Raw types for consumption
by the sync infrastructure.

This module exports:
    - NBAMapper: Main mapper class with methods for transforming data

Field Mappings (NBA API -> RawTypes):
    Teams:
        - id -> external_id
        - full_name -> name
        - abbreviation -> short_name

    Games:
        - GAME_ID -> external_id
        - HOME_TEAM_ID -> home_team_external_id
        - VISITOR_TEAM_ID -> away_team_external_id
        - GAME_DATE -> game_date
        - WL (home) -> status (W/L = final, else scheduled)
        - PTS (home) -> home_score
        - PTS (away) -> away_score

    Player Stats (BoxScoreTraditionalV3):
        - playerId -> player_external_id
        - playerName -> player_name
        - teamId -> team_external_id
        - minutes -> minutes_played (converted to seconds)
        - points -> points
        - fieldGoalsMade -> field_goals_made
        - fieldGoalsAttempted -> field_goals_attempted
        - threePointersMade -> three_pointers_made
        - threePointersAttempted -> three_pointers_attempted
        - freeThrowsMade -> free_throws_made
        - freeThrowsAttempted -> free_throws_attempted
        - reboundsOffensive -> offensive_rebounds
        - reboundsDefensive -> defensive_rebounds
        - reboundsTotal -> total_rebounds
        - assists -> assists
        - turnovers -> turnovers
        - steals -> steals
        - blocks -> blocks
        - foulsPersonal -> personal_fouls
        - plusMinusPoints -> plus_minus

    PBP Events (PlayByPlayV3):
        - actionNumber -> event_number
        - period -> period
        - clock -> clock
        - actionType -> event_type
        - playerNameI -> player_name
        - teamId -> team_external_id
        - shotResult (MADE/MISSED) -> success
        - xLegacy -> coord_x
        - yLegacy -> coord_y

Usage:
    from src.sync.nba.mapper import NBAMapper

    mapper = NBAMapper()
    raw_season = mapper.map_season("2023-24")
    raw_team = mapper.map_team(team_data)
"""

from datetime import date, datetime

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

    # Event type mappings from NBA action types to normalized format
    EVENT_TYPE_MAP = {
        "2pt shot": "shot",
        "3pt shot": "shot",
        "free throw": "free_throw",
        "rebound": "rebound",
        "turnover": "turnover",
        "steal": "steal",
        "block": "block",
        "foul": "foul",
        "violation": "violation",
        "substitution": "substitution",
        "timeout": "timeout",
        "jump ball": "jump_ball",
        "period": "period_event",
        "game": "game_event",
    }

    def parse_minutes_to_seconds(self, minutes_str: str) -> int:
        """
        Parse NBA minutes format (e.g., "PT24M35.00S") to total seconds.

        NBA API returns minutes in ISO 8601 duration format or "MM:SS".

        Args:
            minutes_str: Time string in PT format or MM:SS format.

        Returns:
            Total seconds as integer.

        Example:
            >>> mapper = NBAMapper()
            >>> mapper.parse_minutes_to_seconds("PT24M35.00S")
            1475
            >>> mapper.parse_minutes_to_seconds("24:35")
            1475
        """
        if not minutes_str:
            return 0

        minutes_str = str(minutes_str)

        try:
            # Handle PT format (e.g., "PT24M35.00S")
            if minutes_str.startswith("PT"):
                minutes_str = minutes_str[2:]  # Remove "PT"
                minutes = 0
                seconds = 0

                if "M" in minutes_str:
                    parts = minutes_str.split("M")
                    minutes = int(parts[0])
                    if len(parts) > 1 and parts[1]:
                        # Remove "S" and parse seconds
                        sec_part = parts[1].rstrip("S")
                        if sec_part:
                            seconds = int(float(sec_part))
                elif minutes_str.endswith("S"):
                    seconds = int(float(minutes_str.rstrip("S")))

                return minutes * 60 + seconds

            # Handle MM:SS format
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
        Parse NBA date format (e.g., "2023-10-24T00:00:00").

        Args:
            date_str: Date string from NBA API.

        Returns:
            Parsed datetime object.

        Example:
            >>> mapper = NBAMapper()
            >>> dt = mapper.parse_nba_date("2023-10-24T00:00:00")
            >>> dt.year
            2023
        """
        if not date_str:
            return datetime.now()

        try:
            # Try ISO format
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Try date only format
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # Try MM/DD/YYYY format
                return datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                return datetime.now()

    def parse_clock(self, clock_str: str) -> str:
        """
        Parse NBA clock format (e.g., "PT10M45.00S") to MM:SS.

        Args:
            clock_str: Clock string from NBA API.

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
            # Handle PT format
            if clock_str.startswith("PT"):
                seconds = self.parse_minutes_to_seconds(clock_str)
                minutes = seconds // 60
                secs = seconds % 60
                return f"{minutes:02d}:{secs:02d}"

            # Handle MM:SS format
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

        Args:
            season: Season string (e.g., "2023-24").

        Returns:
            RawSeason with season information.

        Example:
            >>> mapper = NBAMapper()
            >>> season = mapper.map_season("2023-24")
            >>> season.external_id
            'NBA2023-24'
            >>> season.name
            '2023-24 NBA Season'
        """
        # Parse season years
        parts = season.split("-")
        start_year = int(parts[0])
        end_year_short = int(parts[1]) if len(parts) > 1 else (start_year + 1) % 100
        end_year = start_year // 100 * 100 + end_year_short

        return RawSeason(
            external_id=f"NBA{season}",
            name=f"{season} NBA Season",
            start_date=date(start_year, 10, 1),  # Season starts in October
            end_date=date(end_year, 6, 30),  # Season ends in June
            is_current=False,  # Set by adapter based on configured seasons
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
            >>> team.name
            'Atlanta Hawks'
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

        # Note: We only have one team's perspective here.
        # The adapter will need to combine two rows to get both teams.
        return RawGame(
            external_id=game_id,
            home_team_external_id=team_id if is_home else "",
            away_team_external_id=team_id if not is_home else "",
            game_date=self.parse_nba_date(game_date),
            status=status,
            home_score=pts if is_home and pts else None,
            away_score=pts if not is_home and pts else None,
        )

    def map_player_stats(self, data: dict) -> RawPlayerStats:
        """
        Map player statistics from BoxScoreTraditionalV3 to RawPlayerStats.

        Args:
            data: Player stats dictionary from boxscore API.

        Returns:
            RawPlayerStats with mapped statistics.

        Example:
            >>> mapper = NBAMapper()
            >>> stats = mapper.map_player_stats({
            ...     "playerId": 203507,
            ...     "playerName": "Giannis Antetokounmpo",
            ...     "teamId": 1610612749,
            ...     "minutes": "PT34M12.00S",
            ...     "points": 32,
            ...     "starter": "1"
            ... })
            >>> stats.points
            32
        """
        # Parse minutes
        minutes_str = str(data.get("minutes", ""))
        minutes_played = self.parse_minutes_to_seconds(minutes_str)

        # Get 2-point stats (calculated from FG - 3P)
        fgm = data.get("fieldGoalsMade", 0) or 0
        fga = data.get("fieldGoalsAttempted", 0) or 0
        fg3m = data.get("threePointersMade", 0) or 0
        fg3a = data.get("threePointersAttempted", 0) or 0

        fg2m = fgm - fg3m
        fg2a = fga - fg3a

        # Determine if starter
        starter = data.get("starter", data.get("startPosition", ""))
        is_starter = bool(starter and starter not in ("0", "", None))

        return RawPlayerStats(
            player_external_id=str(data.get("playerId", data.get("PLAYER_ID", ""))),
            player_name=data.get("playerName", data.get("PLAYER_NAME", "")),
            team_external_id=str(data.get("teamId", data.get("TEAM_ID", ""))),
            minutes_played=minutes_played,
            is_starter=is_starter,
            points=data.get("points", data.get("PTS", 0)) or 0,
            field_goals_made=fgm,
            field_goals_attempted=fga,
            two_pointers_made=fg2m,
            two_pointers_attempted=fg2a,
            three_pointers_made=fg3m,
            three_pointers_attempted=fg3a,
            free_throws_made=data.get("freeThrowsMade", data.get("FTM", 0)) or 0,
            free_throws_attempted=data.get("freeThrowsAttempted", data.get("FTA", 0))
            or 0,
            offensive_rebounds=data.get("reboundsOffensive", data.get("OREB", 0)) or 0,
            defensive_rebounds=data.get("reboundsDefensive", data.get("DREB", 0)) or 0,
            total_rebounds=data.get("reboundsTotal", data.get("REB", 0)) or 0,
            assists=data.get("assists", data.get("AST", 0)) or 0,
            turnovers=data.get("turnovers", data.get("TO", 0)) or 0,
            steals=data.get("steals", data.get("STL", 0)) or 0,
            blocks=data.get("blocks", data.get("BLK", 0)) or 0,
            personal_fouls=data.get("foulsPersonal", data.get("PF", 0)) or 0,
            plus_minus=data.get("plusMinusPoints", data.get("PLUS_MINUS", 0)) or 0,
            efficiency=0,  # NBA doesn't use PIR, would need to calculate
        )

    def map_boxscore(self, boxscore_data: dict, game_id: str) -> RawBoxScore:
        """
        Map boxscore data to RawBoxScore.

        Args:
            boxscore_data: Boxscore dictionary from BoxScoreTraditionalV3.
            game_id: NBA game ID.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = NBAMapper()
            >>> boxscore = mapper.map_boxscore(boxscore_data, "0022300001")
            >>> len(boxscore.home_players) > 0
            True
        """
        player_stats = boxscore_data.get("PlayerStats", [])
        team_stats = boxscore_data.get("TeamStats", [])

        # Determine home/away teams from team stats
        home_team_id = ""
        away_team_id = ""
        home_score = None
        away_score = None
        game_date = datetime.now()

        if len(team_stats) >= 2:
            # First team is typically home in NBA API
            home_team_id = str(
                team_stats[0].get("teamId", team_stats[0].get("TEAM_ID", ""))
            )
            away_team_id = str(
                team_stats[1].get("teamId", team_stats[1].get("TEAM_ID", ""))
            )
            home_score = team_stats[0].get("points", team_stats[0].get("PTS"))
            away_score = team_stats[1].get("points", team_stats[1].get("PTS"))
            game_date_str = team_stats[0].get(
                "gameDateEst", team_stats[0].get("GAME_DATE_EST", "")
            )
            if game_date_str:
                game_date = self.parse_nba_date(game_date_str)

        # Create game
        game = RawGame(
            external_id=game_id,
            home_team_external_id=home_team_id,
            away_team_external_id=away_team_id,
            game_date=game_date,
            status="final" if home_score is not None else "scheduled",
            home_score=home_score,
            away_score=away_score,
        )

        # Map player stats and split by team
        home_players = []
        away_players = []

        for player_data in player_stats:
            stats = self.map_player_stats(player_data)
            if stats.team_external_id == home_team_id:
                home_players.append(stats)
            else:
                away_players.append(stats)

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_pbp_event(self, data: dict, event_num: int) -> RawPBPEvent:
        """
        Map a play-by-play event to RawPBPEvent.

        Args:
            data: Event dictionary from PlayByPlayV3.
            event_num: Event number to assign (use actionNumber from data).

        Returns:
            RawPBPEvent with mapped event data.

        Example:
            >>> mapper = NBAMapper()
            >>> event = mapper.map_pbp_event({
            ...     "actionNumber": 1,
            ...     "period": 1,
            ...     "clock": "PT12M00.00S",
            ...     "actionType": "jumpball",
            ...     "teamId": 1610612737
            ... }, 1)
            >>> event.event_type
            'jump_ball'
        """
        # Get event type
        action_type = str(data.get("actionType", "")).lower()
        event_type = self.EVENT_TYPE_MAP.get(action_type, action_type)

        # Determine success for shot events
        success = None
        shot_result = data.get("shotResult", "")
        if shot_result:
            success = shot_result.upper() == "MADE"

        # Get period
        period = data.get("period", 1)
        if isinstance(period, str):
            try:
                period = int(period)
            except ValueError:
                period = 1

        # Get player name
        player_name = data.get("playerNameI", data.get("playerName"))

        # Get coordinates
        coord_x = data.get("xLegacy", data.get("x"))
        coord_y = data.get("yLegacy", data.get("y"))

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
        team_id = data.get("teamId", data.get("TEAM_ID"))
        team_external_id = str(team_id) if team_id else None

        return RawPBPEvent(
            event_number=data.get("actionNumber", event_num),
            period=period,
            clock=self.parse_clock(data.get("clock", "")),
            event_type=event_type,
            player_name=player_name,
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
            pbp_data: List of PBP event dictionaries.

        Returns:
            List of RawPBPEvent objects.

        Example:
            >>> mapper = NBAMapper()
            >>> events = mapper.map_pbp_events([{"actionNumber": 1, ...}])
            >>> len(events)
            1
        """
        events = []
        for i, event_data in enumerate(pbp_data, start=1):
            event = self.map_pbp_event(event_data, i)
            events.append(event)
        return events
