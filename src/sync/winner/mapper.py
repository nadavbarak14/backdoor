"""
Winner League Mapper Module

Maps raw data from WinnerClient and WinnerScraper to normalized Raw types
for consumption by the sync infrastructure.

This module exports:
    - WinnerMapper: Main mapper class with methods for transforming data

Usage:
    from src.sync.winner.mapper import WinnerMapper

    mapper = WinnerMapper()
    raw_game = mapper.map_game(game_data)
    raw_boxscore = mapper.map_boxscore(boxscore_data)
"""

from dataclasses import dataclass
from datetime import date, datetime

from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawPlayerStats,
    RawSeason,
    RawTeam,
)
from src.sync.winner.scraper import PlayerProfile, RosterPlayer


@dataclass
class PlayerRoster:
    """
    Player roster extracted from PBP response.

    Contains player ID to name mapping for enriching boxscore data.

    Attributes:
        players: Dict mapping player_id to (first_name, last_name) tuple.

    Example:
        >>> roster = mapper.extract_player_roster(pbp_data)
        >>> roster.players["1019"]
        ('ROMAN', 'SORKIN')
    """

    players: dict[str, tuple[str, str]]

    def get_full_name(self, player_id: str) -> str:
        """Get full name for a player ID, or empty string if not found."""
        if player_id in self.players:
            first, last = self.players[player_id]
            return f"{first} {last}".strip()
        return ""


class WinnerMapper:
    """
    Maps Winner League data to normalized Raw types.

    Transforms data from WinnerClient (JSON) and WinnerScraper (HTML) into
    RawSeason, RawTeam, RawGame, RawBoxScore, RawPBPEvent, and RawPlayerInfo
    types for processing by the sync infrastructure.

    Example:
        >>> mapper = WinnerMapper()
        >>> game_data = {"GameId": "12345", "HomeTeamId": "100", ...}
        >>> raw_game = mapper.map_game(game_data)
        >>> print(raw_game.external_id)
        '12345'
    """

    # Event type mappings from Winner format to normalized format
    EVENT_TYPE_MAP = {
        "MADE_2PT": "shot",
        "MADE_3PT": "shot",
        "MISS_2PT": "shot",
        "MISS_3PT": "shot",
        "MADE_FT": "free_throw",
        "MISS_FT": "free_throw",
        "REBOUND": "rebound",
        "ASSIST": "assist",
        "TURNOVER": "turnover",
        "STEAL": "steal",
        "BLOCK": "block",
        "FOUL": "foul",
        "JUMP_BALL": "jump_ball",
        "TIMEOUT": "timeout",
        "SUBSTITUTION": "substitution",
    }

    # Event type mappings from segevstats format to normalized format
    SEGEVSTATS_EVENT_TYPE_MAP = {
        "shot": "shot",
        "freeThrow": "free_throw",
        "rebound": "rebound",
        "assist": "assist",
        "turnover": "turnover",
        "steal": "steal",
        "block": "block",
        "foul": "foul",
        "substitution": "substitution",
        "timeout": "timeout",
        "game": "game",
        "quarter": "quarter",
        "clock": "clock",
    }

    def parse_minutes_to_seconds(self, minutes_str: str) -> int:
        """
        Parse a minutes string like "32:15" to total seconds.

        Args:
            minutes_str: Time string in "MM:SS" format.

        Returns:
            Total seconds as integer.

        Raises:
            ValueError: If the format is invalid.

        Example:
            >>> mapper = WinnerMapper()
            >>> mapper.parse_minutes_to_seconds("32:15")
            1935
            >>> mapper.parse_minutes_to_seconds("5:30")
            330
        """
        if not minutes_str:
            return 0

        try:
            parts = minutes_str.split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            return 0
        except (ValueError, AttributeError):
            return 0

    def parse_datetime(self, date_str: str) -> datetime:
        """
        Parse a datetime string from Winner API format.

        Args:
            date_str: Date string in various formats:
                - ISO format: "2024-01-15T19:30:00"
                - DD/MM/YYYY format: "21/09/2025"
                - Basic format: "2024-01-15"

        Returns:
            Parsed datetime object.

        Raises:
            ValueError: If the format is invalid.

        Example:
            >>> mapper = WinnerMapper()
            >>> dt = mapper.parse_datetime("2024-01-15T19:30:00")
            >>> dt.year
            2024
            >>> dt = mapper.parse_datetime("21/09/2025")
            >>> dt.year
            2025
        """
        if not date_str:
            return datetime.now()

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try DD/MM/YYYY format (used by real API in game_date_txt)
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            pass

        # Fall back to basic formats
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return datetime.now()

    def map_season(self, season_str: str, games_data: dict) -> RawSeason:
        """
        Map season information from games_all response.

        If season_str is empty, infers the season from game data:
        - Uses game_year field if available (real API)
        - Falls back to parsing game dates

        Args:
            season_str: Season string (e.g., "2023-24"), or empty to infer.
            games_data: Full games_all response data.

        Returns:
            RawSeason with extracted information.

        Example:
            >>> mapper = WinnerMapper()
            >>> season = mapper.map_season("2023-24", {"games": []})
            >>> season.external_id
            '2023-24'
            >>> # Or infer from game_year
            >>> season = mapper.map_season("", {"games": [{"game_year": 2026}]})
            >>> season.external_id
            '2025-26'
        """
        # Determine if current season based on games
        is_current = True  # Winner API typically returns current season

        # Extract date range from games if available
        start_date = None
        end_date = None
        games = games_data.get("games", [])

        # Infer season from games if not provided
        if not season_str and games:
            # Try game_year field first (real API uses this)
            first_game = games[0]
            game_year = first_game.get("game_year")
            if game_year:
                # game_year is the end year of the season (e.g., 2026 for 2025-26)
                start_year = game_year - 1
                season_str = f"{start_year}-{str(game_year)[-2:]}"
            else:
                # Fall back to parsing game dates
                game_date_str = first_game.get("game_date_txt") or first_game.get(
                    "GameDate"
                )
                if game_date_str:
                    try:
                        game_date = self.parse_datetime(game_date_str)
                        year = game_date.year
                        month = game_date.month
                        if month >= 9:  # Season starts in September
                            season_str = f"{year}-{str(year + 1)[-2:]}"
                        else:
                            season_str = f"{year - 1}-{str(year)[-2:]}"
                    except ValueError:
                        pass

        if games:
            dates = []
            for game in games:
                game_date_str = game.get("game_date_txt") or game.get("GameDate")
                if game_date_str:
                    try:
                        dates.append(self.parse_datetime(game_date_str))
                    except ValueError:
                        continue

            if dates:
                start_date = min(dates).date()
                end_date = max(dates).date()

        return RawSeason(
            external_id=season_str,
            name=f"{season_str} Winner League",
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
        )

    def map_team(self, data: dict) -> RawTeam:
        """
        Map team data to RawTeam.

        Args:
            data: Team dictionary with TeamId, TeamName, etc.

        Returns:
            RawTeam with mapped data.

        Example:
            >>> mapper = WinnerMapper()
            >>> team = mapper.map_team({"TeamId": "100", "TeamName": "Maccabi"})
            >>> team.external_id
            '100'
        """
        return RawTeam(
            external_id=str(data.get("TeamId", data.get("HomeTeamId", ""))),
            name=data.get("TeamName", data.get("HomeTeamName", "")),
            short_name=data.get("ShortName"),
        )

    def extract_teams_from_games(self, games_data: dict) -> list[RawTeam]:
        """
        Extract unique teams from games_all response.

        Handles both legacy and real API field names:
        - HomeTeamId / team1 -> team external_id
        - HomeTeamName / team_name_eng_1 -> team name
        - AwayTeamId / team2 -> team external_id
        - AwayTeamName / team_name_eng_2 -> team name

        Args:
            games_data: Full games_all response with games list.

        Returns:
            List of unique RawTeam objects.

        Example:
            >>> mapper = WinnerMapper()
            >>> teams = mapper.extract_teams_from_games({"games": [...]})
            >>> len(teams)
            12
        """
        teams_dict: dict[str, RawTeam] = {}
        games = games_data.get("games", [])

        for game in games:
            # Extract home team (try real API fields first, then legacy)
            home_id = str(game.get("team1") or game.get("HomeTeamId") or "")
            home_name = (
                game.get("team_name_eng_1")
                or game.get("team_name_1")
                or game.get("HomeTeamName")
                or ""
            )
            if home_id and home_id not in teams_dict:
                teams_dict[home_id] = RawTeam(
                    external_id=home_id,
                    name=home_name,
                    short_name=None,
                )

            # Extract away team (try real API fields first, then legacy)
            away_id = str(game.get("team2") or game.get("AwayTeamId") or "")
            away_name = (
                game.get("team_name_eng_2")
                or game.get("team_name_2")
                or game.get("AwayTeamName")
                or ""
            )
            if away_id and away_id not in teams_dict:
                teams_dict[away_id] = RawTeam(
                    external_id=away_id,
                    name=away_name,
                    short_name=None,
                )

        return list(teams_dict.values())

    def map_game(self, data: dict) -> RawGame:
        """
        Map a game from games_all response to RawGame.

        Handles both legacy field names and real API field names:
        - GameId / ExternalID -> external_id
        - HomeTeamId / team1 -> home_team_external_id
        - AwayTeamId / team2 -> away_team_external_id
        - GameDate / game_date_txt -> game_date
        - HomeScore / score_team1 -> home_score
        - AwayScore / score_team2 -> away_score

        Args:
            data: Single game dictionary from games_all.

        Returns:
            RawGame with mapped data.

        Example:
            >>> mapper = WinnerMapper()
            >>> game = mapper.map_game({
            ...     "ExternalID": "24",
            ...     "team1": 1109,
            ...     "team2": 1112,
            ...     "game_date_txt": "21/09/2025",
            ...     "score_team1": 79,
            ...     "score_team2": 84
            ... })
            >>> game.external_id
            '24'
        """
        # Extract game ID (try real API field first, then legacy)
        game_id = data.get("ExternalID") or data.get("GameId") or ""

        # Extract team IDs (try real API fields first, then legacy)
        home_team_id = data.get("team1") or data.get("HomeTeamId") or ""
        away_team_id = data.get("team2") or data.get("AwayTeamId") or ""

        # Extract scores (try real API fields first, then legacy)
        home_score = data.get("score_team1")
        if home_score is None:
            home_score = data.get("HomeScore")
        away_score = data.get("score_team2")
        if away_score is None:
            away_score = data.get("AwayScore")

        # Extract date (try real API field first, then legacy)
        date_str = data.get("game_date_txt") or data.get("GameDate") or ""

        # Determine status
        status = (data.get("Status") or "").lower()
        if status not in ("scheduled", "live", "final"):
            # Real API uses isLive flag and scores to determine status
            # A game is "final" only if it has non-zero scores
            # 0-0 scores indicate a scheduled/unplayed game
            has_scores = (
                home_score is not None
                and away_score is not None
                and (home_score > 0 or away_score > 0)
            )
            status = "final" if has_scores else "scheduled"

        return RawGame(
            external_id=str(game_id),
            home_team_external_id=str(home_team_id),
            away_team_external_id=str(away_team_id),
            game_date=self.parse_datetime(date_str),
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

    def _parse_int(self, value: str | int | None, default: int = 0) -> int:
        """
        Parse a value to integer, handling strings and None.

        Args:
            value: Value to parse (string, int, or None).
            default: Default value if parsing fails.

        Returns:
            Parsed integer value.

        Example:
            >>> mapper = WinnerMapper()
            >>> mapper._parse_int("22")
            22
            >>> mapper._parse_int(15)
            15
            >>> mapper._parse_int(None)
            0
        """
        if value is None:
            return default
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def map_player_stats(self, data: dict, team_id: str) -> RawPlayerStats:
        """
        Map player statistics from boxscore to RawPlayerStats.

        Handles both legacy format and segevstats JSON-RPC format:
        - Legacy: PlayerId, Name, Minutes, Points, FGM, FGA, etc.
        - Segevstats: playerId, minutes, points, fg_2m, fg_2mis, fg_3m, etc.

        Args:
            data: Player stats dictionary from boxscore.
            team_id: External team ID for this player.

        Returns:
            RawPlayerStats with mapped data.

        Example:
            >>> mapper = WinnerMapper()
            >>> # Legacy format
            >>> stats = mapper.map_player_stats({
            ...     "PlayerId": "1001",
            ...     "Name": "John Smith",
            ...     "Minutes": "32:15",
            ...     "Points": 22
            ... }, "100")
            >>> stats.minutes_played
            1935
            >>> # Segevstats format
            >>> stats = mapper.map_player_stats({
            ...     "playerId": "1001",
            ...     "minutes": "32:15",
            ...     "points": "22",
            ...     "fg_2m": "5",
            ...     "fg_2mis": "3"
            ... }, "100")
            >>> stats.points
            22
        """
        # Check if this is segevstats format (has lowercase playerId)
        if "playerId" in data:
            return self._map_segevstats_player_stats(data, team_id)

        # Legacy format handling
        fgm = data.get("FGM", 0) or 0
        fga = data.get("FGA", 0) or 0
        three_pm = data.get("ThreePM", 0) or 0
        three_pa = data.get("ThreePA", 0) or 0

        two_pm = fgm - three_pm
        two_pa = fga - three_pa

        return RawPlayerStats(
            player_external_id=str(data.get("PlayerId", "")),
            player_name=data.get("Name", ""),
            team_external_id=team_id,
            minutes_played=self.parse_minutes_to_seconds(data.get("Minutes", "")),
            is_starter=data.get("IsStarter", False),
            points=data.get("Points", 0) or 0,
            field_goals_made=fgm,
            field_goals_attempted=fga,
            two_pointers_made=max(0, two_pm),
            two_pointers_attempted=max(0, two_pa),
            three_pointers_made=three_pm,
            three_pointers_attempted=three_pa,
            free_throws_made=data.get("FTM", 0) or 0,
            free_throws_attempted=data.get("FTA", 0) or 0,
            offensive_rebounds=data.get("OffReb", 0) or 0,
            defensive_rebounds=data.get("DefReb", 0) or 0,
            total_rebounds=data.get("Rebounds", 0) or 0,
            assists=data.get("Assists", 0) or 0,
            turnovers=data.get("Turnovers", 0) or 0,
            steals=data.get("Steals", 0) or 0,
            blocks=data.get("Blocks", 0) or 0,
            personal_fouls=data.get("Fouls", 0) or 0,
            plus_minus=data.get("PlusMinus", 0) or 0,
            efficiency=data.get("Efficiency", 0) or 0,
        )

    def _map_segevstats_player_stats(self, data: dict, team_id: str) -> RawPlayerStats:
        """
        Map player stats from segevstats JSON-RPC format.

        Segevstats uses different field names and stores values as strings:
        - playerId: Player ID
        - minutes: Playing time in "MM:SS" format
        - starter: Boolean for starter status
        - points: Total points (string)
        - fg_2m/fg_2mis: 2-point makes/misses
        - fg_3m/fg_3mis: 3-point makes/misses
        - ft_m/ft_mis: Free throw makes/misses
        - reb_d/reb_o: Defensive/offensive rebounds
        - ast: Assists
        - to: Turnovers
        - stl: Steals
        - blk: Blocks
        - f: Personal fouls
        - plusMinus: Plus/minus (string)

        Note: Player names are NOT available in segevstats boxscore.
        Names must be fetched separately via scraper.

        Args:
            data: Player stats dictionary in segevstats format.
            team_id: External team ID for this player.

        Returns:
            RawPlayerStats with mapped data (player_name will be empty).

        Example:
            >>> mapper = WinnerMapper()
            >>> stats = mapper._map_segevstats_player_stats({
            ...     "playerId": "1019",
            ...     "minutes": "27:06",
            ...     "starter": True,
            ...     "points": "22",
            ...     "fg_2m": "6",
            ...     "fg_2mis": "2",
            ...     "fg_3m": "1",
            ...     "fg_3mis": "3"
            ... }, "100")
            >>> stats.points
            22
            >>> stats.two_pointers_made
            6
        """
        # Parse all numeric fields (segevstats returns strings)
        fg_2m = self._parse_int(data.get("fg_2m"))
        fg_2mis = self._parse_int(data.get("fg_2mis"))
        fg_3m = self._parse_int(data.get("fg_3m"))
        fg_3mis = self._parse_int(data.get("fg_3mis"))
        ft_m = self._parse_int(data.get("ft_m"))
        ft_mis = self._parse_int(data.get("ft_mis"))
        reb_d = self._parse_int(data.get("reb_d"))
        reb_o = self._parse_int(data.get("reb_o"))

        # Calculate totals and attempts
        two_pa = fg_2m + fg_2mis
        three_pa = fg_3m + fg_3mis
        fta = ft_m + ft_mis
        fgm = fg_2m + fg_3m
        fga = two_pa + three_pa

        return RawPlayerStats(
            player_external_id=str(data.get("playerId", "")),
            player_name="",  # Not available in segevstats boxscore
            team_external_id=team_id,
            minutes_played=self.parse_minutes_to_seconds(data.get("minutes", "")),
            is_starter=bool(data.get("starter", False)),
            points=self._parse_int(data.get("points")),
            field_goals_made=fgm,
            field_goals_attempted=fga,
            two_pointers_made=fg_2m,
            two_pointers_attempted=two_pa,
            three_pointers_made=fg_3m,
            three_pointers_attempted=three_pa,
            free_throws_made=ft_m,
            free_throws_attempted=fta,
            offensive_rebounds=reb_o,
            defensive_rebounds=reb_d,
            total_rebounds=reb_o + reb_d,
            assists=self._parse_int(data.get("ast")),
            turnovers=self._parse_int(data.get("to")),
            steals=self._parse_int(data.get("stl")),
            blocks=self._parse_int(data.get("blk")),
            personal_fouls=self._parse_int(data.get("f")),
            plus_minus=self._parse_int(data.get("plusMinus")),
            efficiency=self._parse_int(data.get("rate")),
        )

    def map_boxscore(self, data: dict) -> RawBoxScore:
        """
        Map boxscore JSON to RawBoxScore.

        Handles both legacy format and segevstats JSON-RPC format:
        - Legacy: {HomeTeam: {TeamId, Players}, AwayTeam: {...}}
        - JSON-RPC: {result: {boxscore: {gameInfo: {...}, homeTeam: {players}, awayTeam: {...}}}}

        Args:
            data: Boxscore dictionary in either format.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = WinnerMapper()
            >>> # Legacy format
            >>> boxscore = mapper.map_boxscore({
            ...     "GameId": "12345",
            ...     "HomeTeam": {"TeamId": "100", "Players": [...]},
            ...     "AwayTeam": {"TeamId": "101", "Players": [...]}
            ... })
            >>> len(boxscore.home_players)
            3
            >>> # JSON-RPC format
            >>> boxscore = mapper.map_boxscore({
            ...     "result": {"boxscore": {"gameInfo": {...}, "homeTeam": {...}}}
            ... })
        """
        # Check for JSON-RPC format (segevstats)
        if "result" in data and isinstance(data.get("result"), dict):
            return self._map_segevstats_boxscore(data)

        # Legacy format handling
        home_team = data.get("HomeTeam", {})
        away_team = data.get("AwayTeam", {})

        home_team_id = str(home_team.get("TeamId", ""))
        away_team_id = str(away_team.get("TeamId", ""))

        # Determine game status
        status = "final"
        home_score = home_team.get("Score")
        away_score = away_team.get("Score")
        if home_score is None or away_score is None:
            status = "scheduled"

        # Create game object
        game = RawGame(
            external_id=str(data.get("GameId", "")),
            home_team_external_id=home_team_id,
            away_team_external_id=away_team_id,
            game_date=self.parse_datetime(data.get("GameDate", "")),
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

        # Map player stats
        home_players = [
            self.map_player_stats(p, home_team_id) for p in home_team.get("Players", [])
        ]
        away_players = [
            self.map_player_stats(p, away_team_id) for p in away_team.get("Players", [])
        ]

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def _map_segevstats_boxscore(self, data: dict) -> RawBoxScore:
        """
        Map boxscore from segevstats JSON-RPC format.

        Segevstats returns boxscores in JSON-RPC format:
        {
            "jsonrpc": "2.0",
            "result": {
                "boxscore": {
                    "gameInfo": {
                        "gameId": "24",
                        "homeTeamId": "2",
                        "awayTeamId": "4",
                        "homeScore": "79",
                        "awayScore": "84",
                        "gameFinished": true
                    },
                    "homeTeam": {"players": [...]},
                    "awayTeam": {"players": [...]}
                }
            }
        }

        Note: Player names are NOT available in this format.
        Names must be fetched separately via scraper.

        Args:
            data: Full JSON-RPC response from segevstats.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = WinnerMapper()
            >>> boxscore = mapper._map_segevstats_boxscore(jsonrpc_data)
            >>> boxscore.game.external_id
            '24'
        """
        result = data.get("result", {})
        boxscore_data = result.get("boxscore", {})
        game_info = boxscore_data.get("gameInfo", {})
        home_team_data = boxscore_data.get("homeTeam", {})
        away_team_data = boxscore_data.get("awayTeam", {})

        # Extract team IDs from gameInfo
        home_team_id = str(game_info.get("homeTeamId", ""))
        away_team_id = str(game_info.get("awayTeamId", ""))

        # Extract scores (stored as strings in segevstats)
        home_score = self._parse_int(game_info.get("homeScore"))
        away_score = self._parse_int(game_info.get("awayScore"))

        # Determine game status
        game_finished = game_info.get("gameFinished", False)
        status = "final" if game_finished else "live"

        # Create game object
        game = RawGame(
            external_id=str(game_info.get("gameId", "")),
            home_team_external_id=home_team_id,
            away_team_external_id=away_team_id,
            game_date=datetime.now(),  # Not available in boxscore response
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

        # Map player stats
        home_players = [
            self.map_player_stats(p, home_team_id)
            for p in home_team_data.get("players", [])
        ]
        away_players = [
            self.map_player_stats(p, away_team_id)
            for p in away_team_data.get("players", [])
        ]

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_pbp_event(self, data: dict, event_num: int) -> RawPBPEvent:
        """
        Map a play-by-play event to RawPBPEvent.

        Args:
            data: Event dictionary from PBP response.
            event_num: Event number to assign.

        Returns:
            RawPBPEvent with mapped data.

        Example:
            >>> mapper = WinnerMapper()
            >>> event = mapper.map_pbp_event({
            ...     "Quarter": 1,
            ...     "GameClock": "09:45",
            ...     "EventType": "MADE_2PT",
            ...     "TeamId": "100",
            ...     "PlayerId": "1001"
            ... }, 1)
            >>> event.event_type
            'shot'
        """
        # Map event type
        raw_event_type = data.get("EventType", "")
        event_type = self.EVENT_TYPE_MAP.get(raw_event_type, raw_event_type.lower())

        # Determine success for shot events
        success = None
        if raw_event_type.startswith("MADE_"):
            success = True
        elif raw_event_type.startswith("MISS_"):
            success = False

        # Extract player name from description if not provided directly
        player_name = data.get("PlayerName")
        if not player_name:
            desc = data.get("Description", "")
            # Try to extract name from description like "John Smith makes 2-pt shot"
            if desc:
                parts = desc.split(" ")
                if len(parts) >= 2:
                    # First two words might be player name
                    player_name = f"{parts[0]} {parts[1]}"

        return RawPBPEvent(
            event_number=event_num,
            period=data.get("Quarter", 1),
            clock=data.get("GameClock", ""),
            event_type=event_type,
            player_name=player_name,
            team_external_id=(
                str(data.get("TeamId", "")) if data.get("TeamId") else None
            ),
            success=success,
            coord_x=data.get("CoordX"),
            coord_y=data.get("CoordY"),
            related_event_numbers=None,  # Will be filled by infer_pbp_links
        )

    def map_pbp_events(self, data: dict) -> list[RawPBPEvent]:
        """
        Map all play-by-play events from PBP response.

        Handles both formats:
        - Legacy format: {"Events": [...]}
        - Segevstats JSON-RPC format: {"result": {"actions": [...]}}

        Args:
            data: Full PBP response in either format.

        Returns:
            List of RawPBPEvent objects with inferred links.

        Example:
            >>> mapper = WinnerMapper()
            >>> # Legacy format
            >>> events = mapper.map_pbp_events({"Events": [...]})
            >>> # Segevstats format
            >>> events = mapper.map_pbp_events({"result": {"actions": [...]}})
            >>> len(events)
            245
        """
        # Check for segevstats JSON-RPC format
        if "result" in data and isinstance(data.get("result"), dict):
            result = data["result"]
            if "actions" in result:
                return self.map_segevstats_pbp_events(data)

        # Legacy format handling
        events = []
        for i, event_data in enumerate(data.get("Events", []), start=1):
            event = self.map_pbp_event(event_data, i)
            events.append(event)

        # Infer links between related events
        return self.infer_pbp_links(events)

    def extract_player_roster(self, pbp_data: dict) -> PlayerRoster:
        """
        Extract player roster with names from PBP response.

        The PBP response contains full player rosters in:
        result.gameInfo.homeTeam.players and result.gameInfo.awayTeam.players

        Each player has: id, firstName, lastName, jerseyNumber

        Args:
            pbp_data: Full PBP JSON-RPC response.

        Returns:
            PlayerRoster with player_id -> (first_name, last_name) mapping.

        Example:
            >>> mapper = WinnerMapper()
            >>> roster = mapper.extract_player_roster(pbp_data)
            >>> roster.get_full_name("1019")
            'ROMAN SORKIN'
        """
        players: dict[str, tuple[str, str]] = {}

        # Handle JSON-RPC format
        result = pbp_data.get("result", {})
        game_info = result.get("gameInfo", {})

        # Extract home team players
        home_team = game_info.get("homeTeam", {})
        for player in home_team.get("players", []):
            player_id = str(player.get("id", ""))
            first_name = player.get("firstName", "")
            last_name = player.get("lastName", "")
            if player_id:
                players[player_id] = (first_name, last_name)

        # Extract away team players
        away_team = game_info.get("awayTeam", {})
        for player in away_team.get("players", []):
            player_id = str(player.get("id", ""))
            first_name = player.get("firstName", "")
            last_name = player.get("lastName", "")
            if player_id:
                players[player_id] = (first_name, last_name)

        return PlayerRoster(players=players)

    def map_segevstats_pbp_events(self, data: dict) -> list[RawPBPEvent]:
        """
        Map play-by-play events from segevstats JSON-RPC format.

        Parses the segevstats format with result.actions array and extracts
        player names from result.gameInfo roster.

        The segevstats format:
        {
            "result": {
                "gameInfo": {
                    "homeTeam": {"players": [{"id": "1000", "firstName": "JAYLEN", "lastName": "HOARD"}]},
                    "awayTeam": {"players": [...]}
                },
                "actions": [
                    {
                        "type": "shot",
                        "quarter": 1,
                        "quarterTime": "09:45",
                        "playerId": 1000,
                        "teamId": 2,
                        "parameters": {"made": "made", "type": "lay-up", "coordX": 50, "coordY": 30}
                    }
                ]
            }
        }

        Args:
            data: Full JSON-RPC response from segevstats PBP API.

        Returns:
            List of RawPBPEvent objects with inferred links.

        Example:
            >>> mapper = WinnerMapper()
            >>> events = mapper.map_segevstats_pbp_events(pbp_data)
            >>> len(events)
            800
            >>> events[0].event_type
            'shot'
        """
        # Extract player roster for name lookups
        roster = self.extract_player_roster(data)

        # Build team ID mapping (segevstats ID -> "home"/"away")
        result = data.get("result", {})
        game_info = result.get("gameInfo", {})
        team_mapping: dict[str, str] = {}
        home_team = game_info.get("homeTeam", {})
        away_team = game_info.get("awayTeam", {})
        if home_team.get("id"):
            team_mapping[str(home_team["id"])] = "home"
        if away_team.get("id"):
            team_mapping[str(away_team["id"])] = "away"

        # Get actions array
        actions = result.get("actions", [])

        events = []
        for i, action in enumerate(actions, start=1):
            event = self._map_segevstats_pbp_action(action, i, roster, team_mapping)
            if event:
                events.append(event)

        # Infer links between related events
        return self.infer_pbp_links(events)

    def _map_segevstats_pbp_action(
        self,
        action: dict,
        event_num: int,
        roster: PlayerRoster,
        team_mapping: dict[str, str],
    ) -> RawPBPEvent | None:
        """
        Map a single segevstats action to RawPBPEvent.

        Handles all segevstats action types:
        - shot: Field goal attempt (success from parameters.made)
        - freeThrow: Free throw attempt (success from parameters.made)
        - rebound: Rebound (subtype from parameters.type: offensive/defensive)
        - assist: Assist
        - turnover: Turnover
        - steal: Steal
        - block: Block
        - foul: Foul
        - substitution: Player substitution
        - timeout: Timeout

        Args:
            action: Single action dictionary from actions array.
            event_num: Event number to assign.
            roster: PlayerRoster for player name lookups.
            team_mapping: Dict mapping segevstats team ID to "home"/"away".

        Returns:
            RawPBPEvent or None if action should be skipped (clock, game, quarter events).
        """
        action_type = action.get("type", "")

        # Skip non-game-event types (clock updates, game start, quarter start)
        if action_type in ("clock", "game", "quarter"):
            return None

        # Map event type
        event_type = self.SEGEVSTATS_EVENT_TYPE_MAP.get(action_type, action_type)

        # Extract parameters
        params = action.get("parameters", {})

        # Determine success for shot/free throw events
        success = None
        if action_type in ("shot", "freeThrow"):
            made_value = params.get("made", "")
            success = made_value == "made"

        # Extract subtype
        event_subtype = params.get("type")

        # Extract player info
        player_id = action.get("playerId")
        player_external_id = str(player_id) if player_id else None
        player_name = (
            roster.get_full_name(player_external_id) if player_external_id else None
        )

        # Extract team info - map to "home"/"away"
        team_id = action.get("teamId")
        team_external_id = team_mapping.get(str(team_id)) if team_id else None

        # Extract coordinates for shots
        coord_x = params.get("coordX")
        coord_y = params.get("coordY")

        return RawPBPEvent(
            event_number=event_num,
            period=action.get("quarter", 1),
            clock=action.get("quarterTime", ""),
            event_type=event_type,
            event_subtype=event_subtype,
            player_name=player_name,
            player_external_id=player_external_id,
            team_external_id=team_external_id,
            success=success,
            coord_x=coord_x,
            coord_y=coord_y,
            related_event_numbers=None,
        )

    def enrich_boxscore_with_names(
        self, boxscore: RawBoxScore, roster: PlayerRoster
    ) -> RawBoxScore:
        """
        Enrich boxscore player stats with names from roster.

        Since the boxscore API doesn't include player names, we need to
        get them from the PBP response which has full roster info.

        Args:
            boxscore: RawBoxScore with empty player names.
            roster: PlayerRoster extracted from PBP response.

        Returns:
            RawBoxScore with player names filled in.

        Example:
            >>> boxscore = mapper.map_boxscore(boxscore_data)
            >>> roster = mapper.extract_player_roster(pbp_data)
            >>> enriched = mapper.enrich_boxscore_with_names(boxscore, roster)
            >>> enriched.home_players[0].player_name
            'ROMAN SORKIN'
        """
        # Create new player stats with names
        home_players = []
        for player in boxscore.home_players:
            name = roster.get_full_name(player.player_external_id)
            # Create new RawPlayerStats with updated name
            home_players.append(
                RawPlayerStats(
                    player_external_id=player.player_external_id,
                    player_name=name,
                    team_external_id=player.team_external_id,
                    minutes_played=player.minutes_played,
                    is_starter=player.is_starter,
                    points=player.points,
                    field_goals_made=player.field_goals_made,
                    field_goals_attempted=player.field_goals_attempted,
                    two_pointers_made=player.two_pointers_made,
                    two_pointers_attempted=player.two_pointers_attempted,
                    three_pointers_made=player.three_pointers_made,
                    three_pointers_attempted=player.three_pointers_attempted,
                    free_throws_made=player.free_throws_made,
                    free_throws_attempted=player.free_throws_attempted,
                    offensive_rebounds=player.offensive_rebounds,
                    defensive_rebounds=player.defensive_rebounds,
                    total_rebounds=player.total_rebounds,
                    assists=player.assists,
                    turnovers=player.turnovers,
                    steals=player.steals,
                    blocks=player.blocks,
                    personal_fouls=player.personal_fouls,
                    plus_minus=player.plus_minus,
                    efficiency=player.efficiency,
                )
            )

        away_players = []
        for player in boxscore.away_players:
            name = roster.get_full_name(player.player_external_id)
            away_players.append(
                RawPlayerStats(
                    player_external_id=player.player_external_id,
                    player_name=name,
                    team_external_id=player.team_external_id,
                    minutes_played=player.minutes_played,
                    is_starter=player.is_starter,
                    points=player.points,
                    field_goals_made=player.field_goals_made,
                    field_goals_attempted=player.field_goals_attempted,
                    two_pointers_made=player.two_pointers_made,
                    two_pointers_attempted=player.two_pointers_attempted,
                    three_pointers_made=player.three_pointers_made,
                    three_pointers_attempted=player.three_pointers_attempted,
                    free_throws_made=player.free_throws_made,
                    free_throws_attempted=player.free_throws_attempted,
                    offensive_rebounds=player.offensive_rebounds,
                    defensive_rebounds=player.defensive_rebounds,
                    total_rebounds=player.total_rebounds,
                    assists=player.assists,
                    turnovers=player.turnovers,
                    steals=player.steals,
                    blocks=player.blocks,
                    personal_fouls=player.personal_fouls,
                    plus_minus=player.plus_minus,
                    efficiency=player.efficiency,
                )
            )

        return RawBoxScore(
            game=boxscore.game,
            home_players=home_players,
            away_players=away_players,
        )

    def _parse_clock_to_seconds(self, clock: str) -> float:
        """
        Parse game clock string to seconds remaining in period.

        Args:
            clock: Clock string like "09:45" or "9:45".

        Returns:
            Seconds remaining as float.
        """
        if not clock:
            return 0.0

        try:
            parts = clock.split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            return 0.0
        except (ValueError, AttributeError):
            return 0.0

    def infer_pbp_links(self, events: list[RawPBPEvent]) -> list[RawPBPEvent]:
        """
        Infer relationships between play-by-play events.

        Links related events based on timing and type:
        1. ASSIST after made SHOT (same team, <2 sec) -> links to shot
        2. REBOUND after missed SHOT (<3 sec) -> links to shot
        3. STEAL after TURNOVER (diff team, <2 sec) -> links to turnover
        4. BLOCK with missed SHOT (same time) -> links to shot
        5. FREE_THROW after FOUL -> links to foul

        Args:
            events: List of RawPBPEvent objects without links.

        Returns:
            Same events with related_event_numbers populated.

        Example:
            >>> mapper = WinnerMapper()
            >>> events = [shot_event, assist_event]
            >>> linked = mapper.infer_pbp_links(events)
            >>> linked[1].related_event_numbers
            [1]
        """
        # Build index for quick lookup
        for i, event in enumerate(events):

            # Look at previous events in same period for potential links
            for j in range(i - 1, max(0, i - 10) - 1, -1):
                prev_event = events[j]

                # Must be same period
                if prev_event.period != event.period:
                    continue

                prev_time = self._parse_clock_to_seconds(prev_event.clock)
                curr_time = self._parse_clock_to_seconds(event.clock)
                time_diff = prev_time - curr_time  # Clock counts down

                # Rule 1: ASSIST after made SHOT (same team, <2 sec)
                if (
                    event.event_type == "assist"
                    and prev_event.event_type == "shot"
                    and prev_event.success is True
                    and event.team_external_id == prev_event.team_external_id
                    and 0 <= time_diff <= 2
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 2: REBOUND after missed SHOT (<3 sec)
                if (
                    event.event_type == "rebound"
                    and prev_event.event_type == "shot"
                    and prev_event.success is False
                    and 0 <= time_diff <= 3
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 3: STEAL after TURNOVER (diff team, <2 sec)
                if (
                    event.event_type == "steal"
                    and prev_event.event_type == "turnover"
                    and event.team_external_id != prev_event.team_external_id
                    and 0 <= time_diff <= 2
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 4: BLOCK with missed SHOT (same time)
                if (
                    event.event_type == "block"
                    and prev_event.event_type == "shot"
                    and prev_event.success is False
                    and abs(time_diff) <= 1
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 5: FREE_THROW after FOUL
                if (
                    event.event_type == "free_throw"
                    and prev_event.event_type == "foul"
                    and 0 <= time_diff <= 5
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

        return events

    def map_player_info(self, profile: PlayerProfile) -> RawPlayerInfo:
        """
        Map scraped PlayerProfile to RawPlayerInfo.

        Args:
            profile: PlayerProfile from WinnerScraper.

        Returns:
            RawPlayerInfo with biographical data.

        Example:
            >>> mapper = WinnerMapper()
            >>> profile = PlayerProfile(
            ...     player_id="1001",
            ...     name="John Smith",
            ...     height_cm=198,
            ...     birth_date=datetime(1995, 5, 15)
            ... )
            >>> info = mapper.map_player_info(profile)
            >>> info.height_cm
            198
        """
        # Split name into first and last
        first_name = ""
        last_name = ""
        if profile.name:
            parts = profile.name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = " ".join(parts[1:])
            elif len(parts) == 1:
                last_name = parts[0]

        # Convert birth_date datetime to date if needed
        birth_date: date | None = None
        if profile.birth_date:
            if isinstance(profile.birth_date, datetime):
                birth_date = profile.birth_date.date()
            else:
                birth_date = profile.birth_date  # type: ignore

        return RawPlayerInfo(
            external_id=profile.player_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            height_cm=profile.height_cm,
            position=profile.position,
        )

    def map_roster_player_info(self, roster_player: RosterPlayer) -> RawPlayerInfo:
        """
        Map RosterPlayer from team page to RawPlayerInfo.

        This is more efficient than fetching individual player profiles since
        position is available directly from the roster page.

        Args:
            roster_player: RosterPlayer from team roster scrape.

        Returns:
            RawPlayerInfo with available data (position from roster).

        Example:
            >>> mapper = WinnerMapper()
            >>> player = RosterPlayer(
            ...     player_id="1001",
            ...     name="John Smith",
            ...     jersey_number="23",
            ...     position="G"
            ... )
            >>> info = mapper.map_roster_player_info(player)
            >>> info.position
            'G'
        """
        # Split name into first and last
        first_name = ""
        last_name = ""
        if roster_player.name:
            parts = roster_player.name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = " ".join(parts[1:])
            elif len(parts) == 1:
                last_name = parts[0]

        return RawPlayerInfo(
            external_id=roster_player.player_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=None,  # Not available from roster page
            height_cm=None,  # Not available from roster page without profile fetch
            position=roster_player.position,
            jersey_number=roster_player.jersey_number,
        )
