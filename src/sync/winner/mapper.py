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
from src.sync.winner.scraper import PlayerProfile


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
            is_live = data.get("isLive", 0)
            if (
                is_live
                and home_score is not None
                and away_score is not None
                or home_score is not None
                and away_score is not None
            ):
                status = "final"
            else:
                status = "scheduled"

        return RawGame(
            external_id=str(game_id),
            home_team_external_id=str(home_team_id),
            away_team_external_id=str(away_team_id),
            game_date=self.parse_datetime(date_str),
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

    def map_player_stats(self, data: dict, team_id: str) -> RawPlayerStats:
        """
        Map player statistics from boxscore to RawPlayerStats.

        Args:
            data: Player stats dictionary from boxscore.
            team_id: External team ID for this player.

        Returns:
            RawPlayerStats with mapped data.

        Example:
            >>> mapper = WinnerMapper()
            >>> stats = mapper.map_player_stats({
            ...     "PlayerId": "1001",
            ...     "Name": "John Smith",
            ...     "Minutes": "32:15",
            ...     "Points": 22
            ... }, "100")
            >>> stats.minutes_played
            1935
        """
        # Calculate 2-point field goals from totals and 3-pointers
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

    def map_boxscore(self, data: dict) -> RawBoxScore:
        """
        Map boxscore JSON to RawBoxScore.

        Args:
            data: Boxscore dictionary with HomeTeam and AwayTeam.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = WinnerMapper()
            >>> boxscore = mapper.map_boxscore({
            ...     "GameId": "12345",
            ...     "HomeTeam": {"TeamId": "100", "Players": [...]},
            ...     "AwayTeam": {"TeamId": "101", "Players": [...]}
            ... })
            >>> len(boxscore.home_players)
            3
        """
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

        Args:
            data: Full PBP response with Events list.

        Returns:
            List of RawPBPEvent objects with inferred links.

        Example:
            >>> mapper = WinnerMapper()
            >>> events = mapper.map_pbp_events({"Events": [...]})
            >>> len(events)
            245
        """
        events = []
        for i, event_data in enumerate(data.get("Events", []), start=1):
            event = self.map_pbp_event(event_data, i)
            events.append(event)

        # Infer links between related events
        return self.infer_pbp_links(events)

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
