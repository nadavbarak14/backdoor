"""
iBasketball Mapper Module

Maps raw data from IBasketballApiClient and IBasketballScraper to normalized
Raw types for consumption by the sync infrastructure.

This module exports:
    - IBasketballMapper: Main mapper class with methods for transforming data

Usage:
    from src.sync.ibasketball.mapper import IBasketballMapper

    mapper = IBasketballMapper()
    raw_game = mapper.map_game(event_data)
    raw_boxscore = mapper.map_boxscore(event_data)
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


class IBasketballMapper:
    """
    Maps iBasketball data to normalized Raw types.

    Transforms data from IBasketballApiClient (JSON API) and IBasketballScraper
    (HTML) into RawSeason, RawTeam, RawGame, RawBoxScore, RawPBPEvent, and
    RawPlayerInfo types for processing by the sync infrastructure.

    Attributes:
        STAT_MAPPING: Mapping from SportsPress stat keys to normalized names.
        PBP_EVENT_MAP: Mapping from Hebrew PBP event names to normalized types.

    Example:
        >>> mapper = IBasketballMapper()
        >>> event_data = {"id": 12345, "teams": [100, 101], ...}
        >>> raw_game = mapper.map_game(event_data)
        >>> print(raw_game.external_id)
        '12345'
    """

    # SportsPress stat field mapping to normalized names
    STAT_MAPPING = {
        "pts": "points",
        "fgm": "field_goals_made",
        "fga": "field_goals_attempted",
        "threepm": "three_pointers_made",
        "3pm": "three_pointers_made",
        "threepa": "three_pointers_attempted",
        "3pa": "three_pointers_attempted",
        "ftm": "free_throws_made",
        "fta": "free_throws_attempted",
        "off": "offensive_rebounds",
        "oreb": "offensive_rebounds",
        "def": "defensive_rebounds",
        "dreb": "defensive_rebounds",
        "reb": "total_rebounds",
        "ast": "assists",
        "stl": "steals",
        "blk": "blocks",
        "to": "turnovers",
        "tov": "turnovers",
        "pf": "personal_fouls",
        "min": "minutes_played",
        "eff": "efficiency",
        "plusminus": "plus_minus",
    }

    # Hebrew PBP event type mapping to canonical EventType enums
    PBP_EVENT_MAP: dict[str, EventType] = {
        # Shots
        "קליעה": EventType.SHOT,
        "קליעת שתיים": EventType.SHOT,
        "קליעת שלוש": EventType.SHOT,
        "החטאה": EventType.SHOT,
        "החטאת שתיים": EventType.SHOT,
        "החטאת שלוש": EventType.SHOT,
        # Free throws
        "קליעת עונשין": EventType.FREE_THROW,
        "החטאת עונשין": EventType.FREE_THROW,
        # Rebounds
        "ריבאונד": EventType.REBOUND,
        "ריבאונד התקפי": EventType.REBOUND,
        "ריבאונד הגנתי": EventType.REBOUND,
        # Other events
        "אסיסט": EventType.ASSIST,
        "חטיפה": EventType.STEAL,
        "איבוד": EventType.TURNOVER,
        "חסימה": EventType.BLOCK,
        "עבירה": EventType.FOUL,
        "פאול": EventType.FOUL,
        # English fallbacks
        "made": EventType.SHOT,
        "missed": EventType.SHOT,
        "rebound": EventType.REBOUND,
        "assist": EventType.ASSIST,
        "steal": EventType.STEAL,
        "turnover": EventType.TURNOVER,
        "block": EventType.BLOCK,
        "foul": EventType.FOUL,
    }

    def parse_datetime(self, date_str: str) -> datetime:
        """
        Parse a datetime string from SportsPress API format.

        Args:
            date_str: Date string in ISO format or WordPress format.

        Returns:
            Parsed datetime object.

        Raises:
            ValueError: If the format is invalid.

        Example:
            >>> mapper = IBasketballMapper()
            >>> dt = mapper.parse_datetime("2024-01-15T19:30:00")
            >>> dt.year
            2024
        """
        if not date_str:
            return datetime.now()

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Try WordPress date format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        # Try date only
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass

        # Try European format
        try:
            return datetime.strptime(date_str, "%d/%m/%Y %H:%M")
        except ValueError:
            pass

        return datetime.now()

    def parse_minutes_to_seconds(self, minutes_str: str | int) -> int:
        """
        Parse a minutes string like "32:15" or integer to total seconds.

        Args:
            minutes_str: Time string in "MM:SS" format or integer minutes.

        Returns:
            Total seconds as integer.

        Example:
            >>> mapper = IBasketballMapper()
            >>> mapper.parse_minutes_to_seconds("32:15")
            1935
            >>> mapper.parse_minutes_to_seconds(32)
            1920
        """
        if not minutes_str:
            return 0

        if isinstance(minutes_str, int):
            return minutes_str * 60

        if isinstance(minutes_str, float):
            return int(minutes_str * 60)

        try:
            minutes_str = str(minutes_str).strip()
            if ":" in minutes_str:
                parts = minutes_str.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes * 60 + seconds
            # Try parsing as decimal minutes
            return int(float(minutes_str) * 60)
        except (ValueError, AttributeError):
            return 0

    def map_season(
        self,
        league_key: str,
        league_name: str,  # noqa: ARG002
        events_data: list[dict] | None = None,
    ) -> RawSeason:
        """
        Map season information from league configuration and events.

        iBasketball doesn't expose explicit season data, so we infer
        the season from the league and optionally from event dates.
        The season name is normalized to YYYY-YY format.

        Args:
            league_key: League key identifier (e.g., "liga_leumit").
            league_name: Display name of the league.
            events_data: Optional list of events to infer date range.

        Returns:
            RawSeason with normalized name in YYYY-YY format.

        Example:
            >>> mapper = IBasketballMapper()
            >>> s = mapper.map_season("liga_leumit", "Liga Leumit", events)
            >>> s.name
            '2024-25'
            >>> s.source_id
            'ibasketball_liga_leumit_2024-25'
        """
        # Determine season string from current date or event dates
        now = datetime.now()
        season_year = now.year

        start_date = None
        end_date = None

        if events_data:
            dates = []
            for event in events_data:
                date_str = event.get("date") or event.get("date_gmt")
                if date_str:
                    try:
                        dates.append(self.parse_datetime(date_str))
                    except (ValueError, TypeError):
                        continue

            if dates:
                start_date = min(dates).date()
                end_date = max(dates).date()
                # Use first event year for season calculation
                first_date = min(dates)
                if first_date.month >= 9:
                    season_year = first_date.year
                else:
                    season_year = first_date.year - 1

        # Normalize to standard YYYY-YY format
        normalized_name = normalize_season_name(season_year)
        # Store source-specific ID for external reference
        source_id = f"ibasketball_{league_key}_{normalized_name}"

        return RawSeason(
            external_id=normalized_name,
            name=normalized_name,
            source_id=source_id,
            start_date=start_date,
            end_date=end_date,
            is_current=True,
        )

    def map_team(self, data: dict) -> RawTeam:
        """
        Map team data from SportsPress API to RawTeam.

        Args:
            data: Team dictionary from SportsPress API.

        Returns:
            RawTeam with mapped data.

        Example:
            >>> mapper = IBasketballMapper()
            >>> team = mapper.map_team({"id": 100, "title": {"rendered": "Maccabi"}})
            >>> team.external_id
            '100'
        """
        team_id = str(data.get("id", ""))

        # Get title - may be in different formats
        title = data.get("title", {})
        name = title.get("rendered", "") if isinstance(title, dict) else str(title)

        # Clean HTML entities from name
        name = self._clean_html_text(name)

        # Get short name if available
        short_name = data.get("short_name") or data.get("abbreviation")

        return RawTeam(
            external_id=team_id,
            name=name,
            short_name=short_name,
        )

    def extract_teams_from_events(self, events_data: list[dict]) -> list[RawTeam]:
        """
        Extract unique teams from events list.

        Args:
            events_data: List of event dictionaries from SportsPress API.

        Returns:
            List of unique RawTeam objects.

        Example:
            >>> mapper = IBasketballMapper()
            >>> teams = mapper.extract_teams_from_events(events)
            >>> len(teams)
            12
        """
        teams_dict: dict[str, RawTeam] = {}

        for event in events_data:
            teams = event.get("teams", [])
            team_names = event.get("team_names", {})

            for team_id in teams:
                team_id_str = str(team_id)
                if team_id_str not in teams_dict:
                    team_name = team_names.get(str(team_id), f"Team {team_id}")
                    teams_dict[team_id_str] = RawTeam(
                        external_id=team_id_str,
                        name=self._clean_html_text(team_name),
                        short_name=None,
                    )

        return list(teams_dict.values())

    def map_game(self, data: dict) -> RawGame:
        """
        Map an event from SportsPress API to RawGame.

        Args:
            data: Single event dictionary from SportsPress API.

        Returns:
            RawGame with mapped data.

        Example:
            >>> mapper = IBasketballMapper()
            >>> game = mapper.map_game({
            ...     "id": 12345,
            ...     "teams": [100, 101],
            ...     "date": "2024-01-15T19:30:00",
            ...     "results": {"100": {"outcome": "win"}, "101": {"outcome": "loss"}}
            ... })
            >>> game.external_id
            '12345'
        """
        event_id = str(data.get("id", ""))
        teams = data.get("teams", [])

        # Get team IDs (home is first, away is second in SportsPress)
        home_team_id = str(teams[0]) if len(teams) > 0 else ""
        away_team_id = str(teams[1]) if len(teams) > 1 else ""

        # Parse date
        date_str = data.get("date") or data.get("date_gmt", "")
        game_date = self.parse_datetime(date_str)

        # Get results/scores
        results = data.get("results", {}) or {}
        home_result = results.get(str(home_team_id), {}) or {}
        away_result = results.get(str(away_team_id), {}) or {}

        # Extract scores - may be in different fields
        home_score = self._extract_score(home_result)
        away_score = self._extract_score(away_result)

        # Determine status
        status = self._determine_game_status(data, home_score, away_score)

        return RawGame(
            external_id=event_id,
            home_team_external_id=home_team_id,
            away_team_external_id=away_team_id,
            game_date=game_date,
            status=status,
            home_score=home_score,
            away_score=away_score,
        )

    def _extract_score(self, result: dict) -> int | None:
        """Extract score from a result dictionary."""
        # Try different possible score fields
        for key in ["pts", "score", "total", "final"]:
            value = result.get(key)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return None

    def _determine_game_status(
        self,
        data: dict,
        home_score: int | None,
        away_score: int | None,
    ) -> GameStatus:
        """Determine game status from event data, returning GameStatus enum."""
        status = data.get("status", "").lower()

        if status in ("publish", "final", "finished", "completed"):
            return Normalizers.normalize_game_status("final", "ibasketball")

        if status in ("future", "scheduled"):
            return Normalizers.normalize_game_status("scheduled", "ibasketball")

        if status in ("live", "in_progress", "playing"):
            return Normalizers.normalize_game_status("live", "ibasketball")

        # Infer from scores
        if home_score is not None and away_score is not None:
            return Normalizers.normalize_game_status("final", "ibasketball")

        # Check if game date is in the future
        date_str = data.get("date") or data.get("date_gmt", "")
        if date_str:
            try:
                game_date = self.parse_datetime(date_str)
                if game_date > datetime.now():
                    return Normalizers.normalize_game_status("scheduled", "ibasketball")
            except (ValueError, TypeError):
                pass

        raw_status = "final" if home_score is not None else "scheduled"
        return Normalizers.normalize_game_status(raw_status, "ibasketball")

    def map_player_stats(
        self,
        player_id: str,
        player_name: str,
        team_id: str,
        stats: dict,
    ) -> RawPlayerStats:
        """
        Map player statistics from boxscore to RawPlayerStats.

        Args:
            player_id: External player ID.
            player_name: Player display name.
            team_id: External team ID.
            stats: Statistics dictionary from SportsPress.

        Returns:
            RawPlayerStats with mapped data.

        Example:
            >>> mapper = IBasketballMapper()
            >>> stats = mapper.map_player_stats(
            ...     "1001", "John Smith", "100",
            ...     {"pts": 22, "reb": 8, "ast": 5, "min": "32:15"}
            ... )
            >>> stats.points
            22
        """

        # Parse stats using mapping
        def get_stat(key: str, default: int = 0) -> int:
            value = stats.get(key)
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        # Get basic stats
        points = get_stat("pts")
        fgm = get_stat("fgm")
        fga = get_stat("fga")
        three_pm = get_stat("threepm") or get_stat("3pm")
        three_pa = get_stat("threepa") or get_stat("3pa")
        ftm = get_stat("ftm")
        fta = get_stat("fta")
        oreb = get_stat("off") or get_stat("oreb")
        dreb = get_stat("def") or get_stat("dreb")
        total_reb = get_stat("reb")
        assists = get_stat("ast")
        steals = get_stat("stl")
        blocks = get_stat("blk")
        turnovers = get_stat("to") or get_stat("tov")
        fouls = get_stat("pf")
        plus_minus = get_stat("plusminus")
        efficiency = get_stat("eff")

        # Calculate 2-pointers from totals
        two_pm = max(0, fgm - three_pm)
        two_pa = max(0, fga - three_pa)

        # Parse minutes
        minutes_str = stats.get("min", "")
        minutes_played = self.parse_minutes_to_seconds(minutes_str)

        # Check if starter
        is_starter = stats.get("starter", False) or stats.get("is_starter", False)

        return RawPlayerStats(
            player_external_id=player_id,
            player_name=player_name,
            team_external_id=team_id,
            minutes_played=minutes_played,
            is_starter=is_starter,
            points=points,
            field_goals_made=fgm,
            field_goals_attempted=fga,
            two_pointers_made=two_pm,
            two_pointers_attempted=two_pa,
            three_pointers_made=three_pm,
            three_pointers_attempted=three_pa,
            free_throws_made=ftm,
            free_throws_attempted=fta,
            offensive_rebounds=oreb,
            defensive_rebounds=dreb,
            total_rebounds=total_reb if total_reb else oreb + dreb,
            assists=assists,
            turnovers=turnovers,
            steals=steals,
            blocks=blocks,
            personal_fouls=fouls,
            plus_minus=plus_minus,
            efficiency=efficiency,
        )

    def map_boxscore(self, data: dict) -> RawBoxScore:
        """
        Map event data with player performance to RawBoxScore.

        Args:
            data: Event dictionary with performance data from SportsPress API.

        Returns:
            RawBoxScore with game and player stats.

        Example:
            >>> mapper = IBasketballMapper()
            >>> boxscore = mapper.map_boxscore(event_data)
            >>> len(boxscore.home_players)
            12
        """
        # Map the game first
        game = self.map_game(data)

        home_players: list[RawPlayerStats] = []
        away_players: list[RawPlayerStats] = []

        # Get player performance data
        performance = data.get("performance", {}) or {}
        player_names = data.get("player_names", {}) or {}

        for team_id_str, team_performance in performance.items():
            if not isinstance(team_performance, dict):
                continue

            is_home = team_id_str == game.home_team_external_id
            players_list = home_players if is_home else away_players

            for player_id_str, player_stats in team_performance.items():
                if not isinstance(player_stats, dict):
                    continue

                # Get player name
                player_name = player_names.get(player_id_str, f"Player {player_id_str}")
                player_name = self._clean_html_text(player_name)

                stats = self.map_player_stats(
                    player_id=player_id_str,
                    player_name=player_name,
                    team_id=team_id_str,
                    stats=player_stats,
                )
                players_list.append(stats)

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_pbp_event(
        self,
        event_num: int,
        period: int,
        clock: str,
        event_type: str,
        player_name: str | None,
        team_id: str | None,
        success: bool | None,
    ) -> RawPBPEvent | None:
        """
        Map a single play-by-play event to RawPBPEvent.

        Args:
            event_num: Sequential event number.
            period: Period/quarter number.
            clock: Game clock time string.
            event_type: Raw event type string (Hebrew or English).
            player_name: Player name if applicable.
            team_id: Team ID if applicable.
            success: Whether event was successful (for shots).

        Returns:
            RawPBPEvent with mapped data, or None if event type cannot be mapped.

        Example:
            >>> mapper = IBasketballMapper()
            >>> event = mapper.map_pbp_event(
            ...     1, 1, "09:45", "קליעה", "John Smith", "100", True
            ... )
            >>> event.event_type
            <EventType.SHOT: 'SHOT'>
        """
        # Normalize event type to EventType enum
        normalized_type = self._normalize_pbp_event_type(event_type)
        if normalized_type is None:
            return None

        return RawPBPEvent(
            event_number=event_num,
            period=period,
            clock=clock,
            event_type=normalized_type,
            player_name=player_name,
            team_external_id=team_id,
            success=success,
            coord_x=None,
            coord_y=None,
            related_event_numbers=None,
        )

    def _normalize_pbp_event_type(self, raw_type: str) -> EventType | None:
        """Normalize PBP event type from Hebrew or English to EventType enum."""
        if not raw_type:
            return None

        raw_lower = raw_type.lower().strip()

        # Check direct mapping
        if raw_type in self.PBP_EVENT_MAP:
            return self.PBP_EVENT_MAP[raw_type]

        # Check lowercase
        if raw_lower in self.PBP_EVENT_MAP:
            return self.PBP_EVENT_MAP[raw_lower]

        # Check partial matches
        for key, value in self.PBP_EVENT_MAP.items():
            if key in raw_type or key in raw_lower:
                return value

        # Try normalizer for unknown types
        return Normalizers.try_normalize_event_type(raw_type, "ibasketball")

    def map_pbp_events(self, events_data: list[dict]) -> list[RawPBPEvent]:
        """
        Map all play-by-play events from scraped data.

        Args:
            events_data: List of event dictionaries from scraper.

        Returns:
            List of RawPBPEvent objects with inferred links (skipping None-mapped events).

        Example:
            >>> mapper = IBasketballMapper()
            >>> events = mapper.map_pbp_events(pbp_data)
            >>> len(events)
            245
        """
        events: list[RawPBPEvent] = []

        for i, event_data in enumerate(events_data, start=1):
            period = event_data.get("period", 1)
            clock = event_data.get("clock", "")
            event_type = event_data.get("type", "")
            player_name = event_data.get("player")
            team_id = event_data.get("team_id")
            success = event_data.get("success")

            event = self.map_pbp_event(
                event_num=i,
                period=period,
                clock=clock,
                event_type=event_type,
                player_name=player_name,
                team_id=str(team_id) if team_id else None,
                success=success,
            )
            if event is not None:
                events.append(event)

        # Infer links between related events
        return self.infer_pbp_links(events)

    def _parse_clock_to_seconds(self, clock: str) -> float:
        """Parse game clock string to seconds remaining in period."""
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
            >>> mapper = IBasketballMapper()
            >>> events = [shot_event, assist_event]
            >>> linked = mapper.infer_pbp_links(events)
            >>> linked[1].related_event_numbers
            [1]
        """
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
                    event.event_type == EventType.ASSIST
                    and prev_event.event_type == EventType.SHOT
                    and prev_event.success is True
                    and event.team_external_id == prev_event.team_external_id
                    and 0 <= time_diff <= 2
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 2: REBOUND after missed SHOT (<3 sec)
                if (
                    event.event_type == EventType.REBOUND
                    and prev_event.event_type == EventType.SHOT
                    and prev_event.success is False
                    and 0 <= time_diff <= 3
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 3: STEAL after TURNOVER (diff team, <2 sec)
                if (
                    event.event_type == EventType.STEAL
                    and prev_event.event_type == EventType.TURNOVER
                    and event.team_external_id != prev_event.team_external_id
                    and 0 <= time_diff <= 2
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 4: BLOCK with missed SHOT (same time)
                if (
                    event.event_type == EventType.BLOCK
                    and prev_event.event_type == EventType.SHOT
                    and prev_event.success is False
                    and abs(time_diff) <= 1
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

                # Rule 5: FREE_THROW after FOUL
                if (
                    event.event_type == EventType.FREE_THROW
                    and prev_event.event_type == EventType.FOUL
                    and 0 <= time_diff <= 5
                ):
                    event.related_event_numbers = [prev_event.event_number]
                    break

        return events

    def map_player_info(
        self,
        player_id: str,
        data: dict,
    ) -> RawPlayerInfo:
        """
        Map player data from API or scraper to RawPlayerInfo.

        Args:
            player_id: External player ID.
            data: Player data dictionary.

        Returns:
            RawPlayerInfo with biographical data.

        Example:
            >>> mapper = IBasketballMapper()
            >>> info = mapper.map_player_info("1001", {
            ...     "name": "John Smith",
            ...     "height": 198,
            ...     "position": "SF"
            ... })
            >>> info.height_cm
            198
        """
        # Get name - may be in different formats
        name = data.get("name", "")
        if not name:
            title = data.get("title", {})
            name = title.get("rendered", "") if isinstance(title, dict) else str(title)

        name = self._clean_html_text(name)

        # Split name into first and last
        first_name = ""
        last_name = ""
        if name:
            parts = name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = " ".join(parts[1:])
            elif len(parts) == 1:
                last_name = parts[0]

        # Get height
        height_cm = None
        height = data.get("height") or data.get("height_cm")
        if height:
            try:
                # May be string like "198cm" or just number
                height_str = str(height).replace("cm", "").strip()
                height_cm = int(float(height_str))
            except (ValueError, TypeError):
                pass

        # Get birth date
        birth_date = None
        dob = data.get("birth_date") or data.get("dob") or data.get("birthdate")
        if dob:
            try:
                if isinstance(dob, date):
                    birth_date = dob
                elif isinstance(dob, datetime):
                    birth_date = dob.date()
                else:
                    dt = self.parse_datetime(str(dob))
                    birth_date = dt.date()
            except (ValueError, TypeError):
                pass

        # Get position - normalize to list of Position enums
        raw_position = data.get("position") or data.get("positions")
        if isinstance(raw_position, list):
            raw_position = raw_position[0] if raw_position else None
        positions = Normalizers.try_normalize_positions(raw_position, "ibasketball") or []

        return RawPlayerInfo(
            external_id=player_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            height_cm=height_cm,
            positions=positions,
        )

    def _clean_html_text(self, text: str) -> str:
        """Clean HTML entities and tags from text."""
        if not text:
            return ""

        import html

        # Decode HTML entities
        text = html.unescape(text)

        # Remove common HTML tags
        import re

        text = re.sub(r"<[^>]+>", "", text)

        return text.strip()
