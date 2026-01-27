"""
Analytics Service Module

Provides advanced analytics capabilities for the Basketball Analytics Platform.
This service composes existing services to provide higher-level analysis tools
including clutch time filtering, situational analysis, opponent-based analysis,
and home/away performance splits.

This module exports:
    - AnalyticsService: Orchestration layer for analytics queries

Usage:
    from src.services.analytics import AnalyticsService

    service = AnalyticsService(db_session)

    # Check if a moment qualifies as clutch
    is_clutch = service._is_clutch_moment(game_id, period=4, time_remaining=180, margin=3)

    # Get game score at a specific point in time
    home_score, away_score = service._get_game_score_at_time(game_id, period=4, time_remaining=300)

    # Get games between two teams
    games = service.get_games_vs_opponent(lakers_id, celtics_id, season_id)

    # Get player performance vs specific opponent
    stats = service.get_player_stats_vs_opponent(lebron_id, celtics_id)

    # Get home/away performance split
    split = service.get_player_home_away_split(lebron_id, season_id)

The service wraps existing services and does not query the database directly.
All data access goes through composed services for proper separation of concerns.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.play_by_play import PlayByPlayEvent
from src.models.team import Team
from src.schemas.analytics import (
    ClutchFilter,
    ClutchSeasonStats,
    QuarterStats,
    SituationalFilter,
    TimeFilter,
    TrendAnalysis,
)
from src.schemas.game import EventType
from src.services.game import GameService
from src.services.play_by_play import PlayByPlayService
from src.services.player_stats import PlayerSeasonStatsService
from src.services.stats import PlayerGameStatsService, TeamGameStatsService


class AnalyticsService:
    """
    Orchestration service for advanced basketball analytics.

    Composes existing services to provide higher-level analytics capabilities
    including clutch time analysis, situational filtering, and lineup statistics.
    This service does not query the database directly; all data access goes
    through the composed services.

    Attributes:
        db: SQLAlchemy Session for database operations.
        pbp_service: PlayByPlayService for play-by-play event queries.
        player_stats_service: PlayerGameStatsService for player game statistics.
        team_stats_service: TeamGameStatsService for team game statistics.
        season_stats_service: PlayerSeasonStatsService for aggregated season stats.
        game_service: GameService for game data and box scores.

    Example:
        >>> service = AnalyticsService(db_session)
        >>> home, away = service._get_game_score_at_time(game_id, period=4, time_remaining=300)
        >>> print(f"Score at 5:00 in Q4: {home}-{away}")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the analytics service with composed services.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = AnalyticsService(db_session)
        """
        self.db = db
        self.pbp_service = PlayByPlayService(db)
        self.player_stats_service = PlayerGameStatsService(db)
        self.team_stats_service = TeamGameStatsService(db)
        self.season_stats_service = PlayerSeasonStatsService(db)
        self.game_service = GameService(db)

    def _parse_clock_to_seconds(self, clock: str) -> int:
        """
        Parse a clock string to seconds remaining.

        Handles formats like "5:30", "10:00", "0:45".

        Args:
            clock: Clock string in "MM:SS" format.

        Returns:
            Total seconds remaining as an integer.

        Raises:
            ValueError: If clock format is invalid.

        Example:
            >>> service._parse_clock_to_seconds("5:30")
            330
            >>> service._parse_clock_to_seconds("0:45")
            45
        """
        try:
            parts = clock.split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            else:
                # Try parsing as just seconds
                return int(clock)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid clock format: {clock}") from e

    def _get_points_for_event(self, event: PlayByPlayEvent) -> int:
        """
        Calculate points scored for a successful scoring event.

        Args:
            event: A play-by-play event.

        Returns:
            Points scored (0, 1, 2, or 3).

        Example:
            >>> points = service._get_points_for_event(shot_event)
            >>> print(f"Points: {points}")
        """
        if not event.success:
            return 0

        if event.event_type == "FREE_THROW":
            return 1
        elif event.event_type == "SHOT":
            if event.event_subtype == "3PT":
                return 3
            else:
                return 2
        return 0

    def _get_game_score_at_time(
        self,
        game_id: UUID,
        period: int,
        time_remaining: int,
    ) -> tuple[int, int]:
        """
        Calculate the game score at a specific point in time.

        Sums all scoring events (made shots and free throws) up to the
        specified time to determine the running score.

        Args:
            game_id: UUID of the game.
            period: The period number (1-4 for regulation, 5+ for OT).
            time_remaining: Seconds remaining in the period.

        Returns:
            Tuple of (home_score, away_score) at the specified time.

        Example:
            >>> home, away = service._get_game_score_at_time(
            ...     game_id, period=4, time_remaining=300
            ... )
            >>> print(f"Score at 5:00 Q4: {home}-{away}")
            Score at 5:00 Q4: 98-95
        """
        # Get the game to know home/away teams
        game = self.game_service.get_by_id(game_id)
        if game is None:
            return (0, 0)

        # Get all events for the game
        events = self.pbp_service.get_by_game(game_id)

        home_score = 0
        away_score = 0

        for event in events:
            # Check if this event is before or at the specified time
            event_seconds = self._parse_clock_to_seconds(event.clock)

            # Event is "before" if it's in an earlier period, or same period with more time
            event_is_before = (event.period < period) or (
                event.period == period and event_seconds > time_remaining
            )

            # Include events at exactly the specified time
            event_is_at = event.period == period and event_seconds == time_remaining

            if event_is_before or event_is_at:
                points = self._get_points_for_event(event)
                if points > 0:
                    if event.team_id == game.home_team_id:
                        home_score += points
                    elif event.team_id == game.away_team_id:
                        away_score += points

        return (home_score, away_score)

    def _is_clutch_moment(
        self,
        game_id: UUID,
        period: int,
        time_remaining: int,
        score_margin_threshold: int = 5,
        min_period: int = 4,
    ) -> bool:
        """
        Determine if a specific moment in the game qualifies as "clutch".

        A moment is clutch if:
        - It's in the 4th quarter or overtime (period >= min_period)
        - The score margin at that moment is within the threshold

        This implements the common NBA clutch definition: last 5 minutes of
        4th quarter or overtime, with the score within 5 points.

        Args:
            game_id: UUID of the game.
            period: The period number (4 for Q4, 5+ for OT).
            time_remaining: Seconds remaining in the period.
            score_margin_threshold: Maximum point difference to qualify as clutch.
                Defaults to 5 (NBA standard).
            min_period: Minimum period for clutch time. Defaults to 4 (4th quarter).

        Returns:
            True if the moment qualifies as clutch, False otherwise.

        Example:
            >>> # NBA standard clutch: Q4 or OT, within 5 points
            >>> is_clutch = service._is_clutch_moment(
            ...     game_id, period=4, time_remaining=180, score_margin_threshold=5
            ... )
            >>> print(f"Is clutch: {is_clutch}")

            >>> # Stricter "super clutch": last 2 min, within 3 points
            >>> is_super_clutch = service._is_clutch_moment(
            ...     game_id, period=4, time_remaining=60, score_margin_threshold=3
            ... )
        """
        # Must be in 4th quarter or overtime
        if period < min_period:
            return False

        # Get score at this moment
        home_score, away_score = self._get_game_score_at_time(
            game_id, period, time_remaining
        )

        # Check if margin is within threshold
        margin = abs(home_score - away_score)
        return margin <= score_margin_threshold

    def get_game(self, game_id: UUID) -> Game | None:
        """
        Get a game by ID.

        Wrapper around GameService.get_by_id for convenience.

        Args:
            game_id: UUID of the game.

        Returns:
            Game if found, None otherwise.

        Example:
            >>> game = service.get_game(game_id)
            >>> if game:
            ...     print(f"{game.home_team.name} vs {game.away_team.name}")
        """
        return self.game_service.get_by_id(game_id)

    def get_clutch_events(
        self,
        game_id: UUID,
        clutch_filter: ClutchFilter | None = None,
    ) -> list[PlayByPlayEvent]:
        """
        Get all play-by-play events that occurred during clutch time.

        Clutch time is defined by the filter parameters:
        - Time remaining in period <= threshold
        - Score margin <= threshold
        - Period >= minimum (typically 4th quarter or OT)

        Args:
            game_id: UUID of the game.
            clutch_filter: ClutchFilter with criteria. Uses NBA defaults if None.

        Returns:
            List of PlayByPlayEvent that occurred during clutch moments.
            Empty list if game not found or no clutch moments.

        Example:
            >>> # Get clutch events with NBA standard definition
            >>> events = service.get_clutch_events(game_id)
            >>>
            >>> # Get "super clutch" events (last 2 min, within 3 pts)
            >>> filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)
            >>> events = service.get_clutch_events(game_id, filter)
        """
        if clutch_filter is None:
            clutch_filter = ClutchFilter()

        game = self.game_service.get_by_id(game_id)
        if game is None:
            return []

        # Get all events for the game
        all_events = self.pbp_service.get_by_game(game_id)

        clutch_events: list[PlayByPlayEvent] = []

        for event in all_events:
            # Check period constraint
            if event.period < clutch_filter.min_period:
                continue

            # Check overtime inclusion
            if event.period > 4 and not clutch_filter.include_overtime:
                continue

            # Check time remaining
            try:
                event_seconds = self._parse_clock_to_seconds(event.clock)
            except ValueError:
                continue

            if event_seconds > clutch_filter.time_remaining_seconds:
                continue

            # Check score margin BEFORE this event (add 1 second to exclude this event)
            # This determines if the moment was clutch when the event occurred
            home_score, away_score = self._get_game_score_at_time(
                game_id, event.period, event_seconds + 1
            )
            margin = abs(home_score - away_score)

            if margin <= clutch_filter.score_margin:
                clutch_events.append(event)

        return clutch_events

    def _event_matches_situational_filter(
        self,
        event: PlayByPlayEvent,
        filter: SituationalFilter,
    ) -> bool:
        """
        Check if an event matches the situational filter criteria.

        Compares the event's attributes JSON against the filter fields.
        Only non-None filter fields are checked.

        Args:
            event: The play-by-play event to check.
            filter: SituationalFilter with criteria to match.

        Returns:
            True if the event matches all non-None filter criteria.

        Example:
            >>> filter = SituationalFilter(fast_break=True)
            >>> matches = service._event_matches_situational_filter(event, filter)
        """
        attrs = event.attributes or {}

        if (
            filter.fast_break is not None
            and attrs.get("fast_break") != filter.fast_break
        ):
            return False

        if (
            filter.second_chance is not None
            and attrs.get("second_chance") != filter.second_chance
        ):
            return False

        if filter.contested is not None and attrs.get("contested") != filter.contested:
            return False

        return not (
            filter.shot_type is not None and attrs.get("shot_type") != filter.shot_type
        )

    def get_situational_shots(
        self,
        game_id: UUID,
        player_id: UUID | None = None,
        team_id: UUID | None = None,
        filter: SituationalFilter | None = None,
    ) -> list[PlayByPlayEvent]:
        """
        Get shot events filtered by situational attributes.

        Retrieves SHOT events from a game that match the specified situational
        criteria (fast break, second chance, contested, shot type). Optionally
        filter by player or team.

        Args:
            game_id: UUID of the game.
            player_id: Optional UUID to filter by specific player.
            team_id: Optional UUID to filter by specific team.
            filter: SituationalFilter with criteria. If None, returns all shots.

        Returns:
            List of PlayByPlayEvent (shots) matching the filter criteria.
            Empty list if game not found or no matching events.

        Example:
            >>> # Get all fast break shots in a game
            >>> filter = SituationalFilter(fast_break=True)
            >>> shots = service.get_situational_shots(game_id, filter=filter)

            >>> # Get contested shots by a specific player
            >>> filter = SituationalFilter(contested=True)
            >>> shots = service.get_situational_shots(
            ...     game_id, player_id=player.id, filter=filter
            ... )
        """
        if filter is None:
            filter = SituationalFilter()

        # Get all events for the game
        all_events = self.pbp_service.get_by_game(game_id)

        matching_shots: list[PlayByPlayEvent] = []

        for event in all_events:
            # Only consider SHOT events
            if event.event_type != "SHOT":
                continue

            # Filter by player if specified
            if player_id is not None and event.player_id != player_id:
                continue

            # Filter by team if specified
            if team_id is not None and event.team_id != team_id:
                continue

            # Check situational filter
            if self._event_matches_situational_filter(event, filter):
                matching_shots.append(event)

        return matching_shots

    def get_situational_stats(
        self,
        game_ids: list[UUID],
        player_id: UUID,
        filter: SituationalFilter | None = None,
    ) -> dict:
        """
        Calculate shooting statistics for situational shots across multiple games.

        Aggregates made/attempted counts and calculates field goal percentage
        for shots matching the situational filter criteria.

        Args:
            game_ids: List of game UUIDs to aggregate across.
            player_id: UUID of the player to get stats for.
            filter: SituationalFilter with criteria. If None, returns all shot stats.

        Returns:
            Dictionary with shooting statistics:
            - made: Number of successful shots
            - attempted: Number of shot attempts
            - pct: Field goal percentage (0.0-1.0), 0.0 if no attempts

        Example:
            >>> filter = SituationalFilter(fast_break=True)
            >>> stats = service.get_situational_stats(
            ...     game_ids=[game1.id, game2.id],
            ...     player_id=player.id,
            ...     filter=filter
            ... )
            >>> print(f"Fast break FG%: {stats['pct']:.1%}")
            Fast break FG%: 65.0%
        """
        if filter is None:
            filter = SituationalFilter()

        made = 0
        attempted = 0

        for game_id in game_ids:
            shots = self.get_situational_shots(
                game_id=game_id,
                player_id=player_id,
                filter=filter,
            )

            for shot in shots:
                attempted += 1
                if shot.success:
                    made += 1

        pct = made / attempted if attempted > 0 else 0.0

        return {
            "made": made,
            "attempted": attempted,
            "pct": pct,
        }

    def get_games_vs_opponent(
        self,
        team_id: UUID,
        opponent_id: UUID,
        season_id: UUID | None = None,
    ) -> list[Game]:
        """
        Get all games between two teams.

        Returns games where the specified team played against the opponent,
        regardless of home/away status. Optionally filtered by season.

        Args:
            team_id: UUID of the team.
            opponent_id: UUID of the opponent team.
            season_id: Optional UUID of the season to filter by.

        Returns:
            List of Game objects where these teams played each other.
            Empty list if no games found.

        Example:
            >>> games = service.get_games_vs_opponent(
            ...     team_id=lakers_id,
            ...     opponent_id=celtics_id,
            ...     season_id=season_2024_id
            ... )
            >>> print(f"Lakers vs Celtics: {len(games)} games this season")
        """
        from sqlalchemy import and_, or_, select

        # Get games where team_id vs opponent_id (either home or away)
        stmt = select(Game).where(
            or_(
                and_(Game.home_team_id == team_id, Game.away_team_id == opponent_id),
                and_(Game.home_team_id == opponent_id, Game.away_team_id == team_id),
            )
        )

        if season_id is not None:
            stmt = stmt.where(Game.season_id == season_id)

        stmt = stmt.order_by(Game.game_date.desc())

        return list(self.db.scalars(stmt).all())

    def get_player_stats_vs_opponent(
        self,
        player_id: UUID,
        opponent_id: UUID,
        season_id: UUID | None = None,
    ) -> list[PlayerGameStats]:
        """
        Get player's game stats against a specific opponent.

        Returns all PlayerGameStats for games where the player's team
        played against the specified opponent.

        Args:
            player_id: UUID of the player.
            opponent_id: UUID of the opponent team.
            season_id: Optional UUID of the season to filter by.

        Returns:
            List of PlayerGameStats for games against the opponent.
            Empty list if no games found.

        Example:
            >>> stats = service.get_player_stats_vs_opponent(
            ...     player_id=lebron_id,
            ...     opponent_id=celtics_id,
            ...     season_id=season_2024_id
            ... )
            >>> avg_pts = sum(s.points for s in stats) / len(stats) if stats else 0
            >>> print(f"LeBron vs Celtics: {avg_pts:.1f} PPG")
        """
        from sqlalchemy import or_, select
        from sqlalchemy.orm import joinedload

        # Get games where opponent is either home or away team
        stmt = (
            select(PlayerGameStats)
            .options(
                joinedload(PlayerGameStats.game),
                joinedload(PlayerGameStats.player),
                joinedload(PlayerGameStats.team),
            )
            .join(Game)
            .where(PlayerGameStats.player_id == player_id)
            .where(
                or_(
                    Game.home_team_id == opponent_id,
                    Game.away_team_id == opponent_id,
                )
            )
            # Exclude games where player is ON the opponent team
            .where(PlayerGameStats.team_id != opponent_id)
        )

        if season_id is not None:
            stmt = stmt.where(Game.season_id == season_id)

        stmt = stmt.order_by(Game.game_date.desc())

        return list(self.db.scalars(stmt).unique().all())

    def get_player_home_away_split(
        self,
        player_id: UUID,
        season_id: UUID,
    ) -> dict:
        """
        Get player's home vs away performance split.

        Calculates aggregated statistics for home games and away games
        separately, allowing comparison of home court advantage.

        Args:
            player_id: UUID of the player.
            season_id: UUID of the season.

        Returns:
            Dictionary with 'home' and 'away' keys, each containing:
            - games: Number of games played
            - points: Total points
            - rebounds: Total rebounds
            - assists: Total assists
            - avg_points: Points per game
            - avg_rebounds: Rebounds per game
            - avg_assists: Assists per game

        Example:
            >>> split = service.get_player_home_away_split(
            ...     player_id=lebron_id,
            ...     season_id=season_2024_id
            ... )
            >>> print(f"Home PPG: {split['home']['avg_points']:.1f}")
            >>> print(f"Away PPG: {split['away']['avg_points']:.1f}")
        """
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        # Get all player stats for the season with game info
        stmt = (
            select(PlayerGameStats)
            .options(
                joinedload(PlayerGameStats.game),
                joinedload(PlayerGameStats.team),
            )
            .join(Game)
            .where(PlayerGameStats.player_id == player_id)
            .where(Game.season_id == season_id)
        )

        all_stats = list(self.db.scalars(stmt).unique().all())

        home_stats: list[PlayerGameStats] = []
        away_stats: list[PlayerGameStats] = []

        for stat in all_stats:
            # Player is home if their team is the home team
            if stat.team_id == stat.game.home_team_id:
                home_stats.append(stat)
            else:
                away_stats.append(stat)

        def aggregate_stats(stats_list: list[PlayerGameStats]) -> dict:
            """Aggregate a list of stats into totals and averages."""
            if not stats_list:
                return {
                    "games": 0,
                    "points": 0,
                    "rebounds": 0,
                    "assists": 0,
                    "avg_points": 0.0,
                    "avg_rebounds": 0.0,
                    "avg_assists": 0.0,
                }

            games = len(stats_list)
            points = sum(s.points for s in stats_list)
            rebounds = sum(s.total_rebounds for s in stats_list)
            assists = sum(s.assists for s in stats_list)

            return {
                "games": games,
                "points": points,
                "rebounds": rebounds,
                "assists": assists,
                "avg_points": points / games,
                "avg_rebounds": rebounds / games,
                "avg_assists": assists / games,
            }

        return {
            "home": aggregate_stats(home_stats),
            "away": aggregate_stats(away_stats),
        }

    def _get_starters_for_game(self, game_id: UUID, team_id: UUID) -> set[UUID]:
        """Get starting player IDs for a team in a game."""
        from sqlalchemy import select

        stmt = (
            select(PlayerGameStats)
            .where(PlayerGameStats.game_id == game_id)
            .where(PlayerGameStats.team_id == team_id)
            .where(PlayerGameStats.is_starter == True)  # noqa: E712
        )
        starters = list(self.db.scalars(stmt).all())
        if len(starters) >= 5:
            return {s.player_id for s in starters[:5]}

        # Fallback: first 5 players with events
        events = self.pbp_service.get_by_game(game_id)
        seen: set[UUID] = set()
        for event in events:
            if (
                event.team_id == team_id
                and event.player_id
                and event.player_id not in seen
            ):
                seen.add(event.player_id)
                if len(seen) >= 5:
                    break
        return seen

    def _build_on_court_timeline(
        self,
        game_id: UUID,
        player_id: UUID,
        team_id: UUID,
        events: list[PlayByPlayEvent],
    ) -> list[tuple[int, int, int, int, bool]]:
        """Build timeline of (period, start_sec, end_sec, duration, is_on) tuples."""
        is_on = player_id in self._get_starters_for_game(game_id, team_id)
        stints: list[tuple[int, int, int, int, bool]] = []
        REG_SECS, OT_SECS = 720, 300

        current_period = 1
        start_time = REG_SECS

        for event in events:
            if event.event_type != "SUBSTITUTION" or event.player_id != player_id:
                continue
            try:
                event_secs = self._parse_clock_to_seconds(event.clock)
            except ValueError:
                continue

            if event.period != current_period:
                if start_time > 0:
                    stints.append((current_period, start_time, 0, start_time, is_on))
                current_period = event.period
                start_time = REG_SECS if current_period <= 4 else OT_SECS

            if event.event_subtype == "IN" and not is_on:
                if start_time - event_secs > 0:
                    stints.append(
                        (
                            current_period,
                            start_time,
                            event_secs,
                            start_time - event_secs,
                            False,
                        )
                    )
                start_time, is_on = event_secs, True
            elif event.event_subtype == "OUT" and is_on:
                if start_time - event_secs > 0:
                    stints.append(
                        (
                            current_period,
                            start_time,
                            event_secs,
                            start_time - event_secs,
                            True,
                        )
                    )
                start_time, is_on = event_secs, False

        max_period = max((e.period for e in events), default=current_period)
        if start_time > 0:
            stints.append((current_period, start_time, 0, start_time, is_on))
        for period in range(current_period + 1, max_period + 1):
            length = REG_SECS if period <= 4 else OT_SECS
            stints.append((period, length, 0, length, is_on))
        return stints

    def _is_player_on_at_time(
        self,
        stints: list[tuple[int, int, int, int, bool]],
        period: int,
        time_remaining: int,
    ) -> bool:
        """Check if player was on court at a specific time."""
        for p, start, end, _, is_on in stints:
            if p == period and (
                start >= time_remaining > end or time_remaining == start
            ):
                return is_on
        return False

    def get_player_on_off_stats(self, player_id: UUID, game_id: UUID) -> dict:
        """
        Calculate player on/off court stats for a game.

        Returns dict with 'on' and 'off' keys containing team_pts, opp_pts,
        plus_minus, and minutes.
        """
        empty = {
            "on": {"team_pts": 0, "opp_pts": 0, "plus_minus": 0, "minutes": 0.0},
            "off": {"team_pts": 0, "opp_pts": 0, "plus_minus": 0, "minutes": 0.0},
        }

        game = self.game_service.get_by_id(game_id)
        if not game:
            return empty

        player_stats = self.player_stats_service.get_by_player_and_game(
            player_id=player_id, game_id=game_id
        )
        if not player_stats:
            return empty

        team_id = player_stats.team_id
        opp_id = (
            game.away_team_id if team_id == game.home_team_id else game.home_team_id
        )
        events = self.pbp_service.get_by_game(game_id)
        stints = self._build_on_court_timeline(game_id, player_id, team_id, events)

        on_team, on_opp, on_secs = 0, 0, 0
        off_team, off_opp, off_secs = 0, 0, 0

        for _, _, _, dur, is_on in stints:
            if is_on:
                on_secs += dur
            else:
                off_secs += dur

        for event in events:
            if event.event_type not in ("SHOT", "FREE_THROW") or not event.success:
                continue
            pts = self._get_points_for_event(event)
            if pts == 0:
                continue
            try:
                secs = self._parse_clock_to_seconds(event.clock)
            except ValueError:
                continue

            is_on = self._is_player_on_at_time(stints, event.period, secs)
            if event.team_id == team_id:
                on_team += pts if is_on else 0
                off_team += pts if not is_on else 0
            elif event.team_id == opp_id:
                on_opp += pts if is_on else 0
                off_opp += pts if not is_on else 0

        return {
            "on": {
                "team_pts": on_team,
                "opp_pts": on_opp,
                "plus_minus": on_team - on_opp,
                "minutes": round(on_secs / 60, 1),
            },
            "off": {
                "team_pts": off_team,
                "opp_pts": off_opp,
                "plus_minus": off_team - off_opp,
                "minutes": round(off_secs / 60, 1),
            },
        }

    def get_player_on_off_for_season(self, player_id: UUID, season_id: UUID) -> dict:
        """
        Aggregate player on/off stats across a season.

        Returns dict with 'on' and 'off' keys containing team_pts, opp_pts,
        plus_minus, minutes, and games count.
        """
        from sqlalchemy import select

        stmt = (
            select(PlayerGameStats)
            .join(Game)
            .where(PlayerGameStats.player_id == player_id)
            .where(Game.season_id == season_id)
        )
        stats = list(self.db.scalars(stmt).all())

        totals = {
            "on": {
                "team_pts": 0,
                "opp_pts": 0,
                "plus_minus": 0,
                "minutes": 0.0,
                "games": 0,
            },
            "off": {
                "team_pts": 0,
                "opp_pts": 0,
                "plus_minus": 0,
                "minutes": 0.0,
                "games": 0,
            },
        }
        seen: set[UUID] = set()

        for stat in stats:
            if stat.game_id in seen:
                continue
            seen.add(stat.game_id)
            gs = self.get_player_on_off_stats(player_id, stat.game_id)
            for key in ("on", "off"):
                totals[key]["team_pts"] += gs[key]["team_pts"]
                totals[key]["opp_pts"] += gs[key]["opp_pts"]
                totals[key]["minutes"] += gs[key]["minutes"]

        for key in ("on", "off"):
            totals[key]["plus_minus"] = totals[key]["team_pts"] - totals[key]["opp_pts"]
            totals[key]["games"] = len(seen)
            totals[key]["minutes"] = round(totals[key]["minutes"], 1)

        return totals

    def _get_lineup_on_court_intervals(
        self,
        player_ids: list[UUID],
        game_id: UUID,
        team_id: UUID,
        events: list[PlayByPlayEvent],
    ) -> list[tuple[int, int, int]]:
        """
        Get time intervals when ALL specified players are on court together.

        Computes the intersection of on-court timelines for all players in the lineup.

        Args:
            player_ids: List of player UUIDs that must all be on court.
            game_id: UUID of the game.
            team_id: UUID of the team these players belong to.
            events: List of play-by-play events for the game.

        Returns:
            List of (period, start_seconds, end_seconds) tuples representing
            intervals when all players were on court together.

        Example:
            >>> intervals = service._get_lineup_on_court_intervals(
            ...     [lebron_id, ad_id], game_id, lakers_id, events
            ... )
            >>> print(intervals)
            [(1, 720, 360), (1, 180, 0)]  # Q1: 12:00-6:00, 3:00-0:00
        """
        if not player_ids:
            return []

        # Build timeline for each player
        all_timelines: list[list[tuple[int, int, int, int, bool]]] = []
        for pid in player_ids:
            timeline = self._build_on_court_timeline(game_id, pid, team_id, events)
            all_timelines.append(timeline)

        # Extract "on" intervals for each player
        player_on_intervals: list[list[tuple[int, int, int]]] = []
        for timeline in all_timelines:
            on_intervals = [
                (period, start, end)
                for period, start, end, _, is_on in timeline
                if is_on
            ]
            player_on_intervals.append(on_intervals)

        if not player_on_intervals:
            return []

        # Intersect all player intervals
        # Start with first player's intervals
        result = player_on_intervals[0]

        for player_intervals in player_on_intervals[1:]:
            new_result: list[tuple[int, int, int]] = []
            for p1, s1, e1 in result:
                for p2, s2, e2 in player_intervals:
                    # Must be same period
                    if p1 != p2:
                        continue
                    # Compute intersection (time goes from high to low)
                    start = min(s1, s2)
                    end = max(e1, e2)
                    if start > end:
                        new_result.append((p1, start, end))
            result = new_result

        return result

    def get_lineup_stats(
        self,
        player_ids: list[UUID],
        game_id: UUID,
    ) -> dict:
        """
        Calculate stats when ALL specified players are on court together.

        Tracks scoring plays that occur during intervals when the entire
        specified lineup (2-man, 3-man, etc.) is on the court together.

        Args:
            player_ids: List of player UUIDs (2-5 players typically).
            game_id: UUID of the game.

        Returns:
            Dictionary containing:
            - team_pts: Points scored by the lineup's team
            - opp_pts: Points scored by opponent
            - plus_minus: team_pts - opp_pts
            - minutes: Total minutes the lineup played together

        Raises:
            None - returns empty stats if game/players not found.

        Example:
            >>> stats = service.get_lineup_stats(
            ...     [lebron_id, ad_id], game_id
            ... )
            >>> print(f"LeBron+AD: +{stats['plus_minus']} in {stats['minutes']} min")
        """
        empty = {"team_pts": 0, "opp_pts": 0, "plus_minus": 0, "minutes": 0.0}

        if not player_ids:
            return empty

        game = self.game_service.get_by_id(game_id)
        if not game:
            return empty

        # Get team_id from first player's stats
        first_player_stats = self.player_stats_service.get_by_player_and_game(
            player_id=player_ids[0], game_id=game_id
        )
        if not first_player_stats:
            return empty

        team_id = first_player_stats.team_id
        opp_id = (
            game.away_team_id if team_id == game.home_team_id else game.home_team_id
        )

        # Verify all players are on the same team
        for pid in player_ids[1:]:
            pstats = self.player_stats_service.get_by_player_and_game(
                player_id=pid, game_id=game_id
            )
            if not pstats or pstats.team_id != team_id:
                return empty

        events = self.pbp_service.get_by_game(game_id)
        intervals = self._get_lineup_on_court_intervals(
            player_ids, game_id, team_id, events
        )

        # Calculate total minutes
        total_seconds = sum(start - end for _, start, end in intervals)

        # Count scoring during lineup intervals
        team_pts = 0
        opp_pts = 0

        for event in events:
            if event.event_type not in ("SHOT", "FREE_THROW") or not event.success:
                continue

            pts = self._get_points_for_event(event)
            if pts == 0:
                continue

            try:
                event_secs = self._parse_clock_to_seconds(event.clock)
            except ValueError:
                continue

            # Check if event occurred during a lineup interval
            for period, start, end in intervals:
                if event.period == period and (
                    start >= event_secs > end or event_secs == start
                ):
                    if event.team_id == team_id:
                        team_pts += pts
                    elif event.team_id == opp_id:
                        opp_pts += pts
                    break

        return {
            "team_pts": team_pts,
            "opp_pts": opp_pts,
            "plus_minus": team_pts - opp_pts,
            "minutes": round(total_seconds / 60, 1),
        }

    def get_lineup_stats_for_season(
        self,
        player_ids: list[UUID],
        season_id: UUID,
    ) -> dict:
        """
        Aggregate lineup stats across all games in a season.

        Sums stats for all games where all specified players participated
        for the same team.

        Args:
            player_ids: List of player UUIDs (2-5 players typically).
            season_id: UUID of the season.

        Returns:
            Dictionary containing:
            - team_pts: Total points scored by the lineup's team
            - opp_pts: Total points scored by opponent
            - plus_minus: team_pts - opp_pts
            - minutes: Total minutes the lineup played together
            - games: Number of games where lineup appeared together

        Example:
            >>> stats = service.get_lineup_stats_for_season(
            ...     [lebron_id, ad_id], season_id
            ... )
            >>> print(f"Season: +{stats['plus_minus']} in {stats['games']} games")
        """
        from sqlalchemy import select

        totals = {
            "team_pts": 0,
            "opp_pts": 0,
            "plus_minus": 0,
            "minutes": 0.0,
            "games": 0,
        }

        if not player_ids:
            return totals

        # Get all games for first player in the season
        stmt = (
            select(PlayerGameStats)
            .join(Game)
            .where(PlayerGameStats.player_id == player_ids[0])
            .where(Game.season_id == season_id)
        )
        first_player_games = list(self.db.scalars(stmt).all())

        seen_games: set[UUID] = set()

        for pgs in first_player_games:
            if pgs.game_id in seen_games:
                continue
            seen_games.add(pgs.game_id)

            game_stats = self.get_lineup_stats(player_ids, pgs.game_id)
            if game_stats["minutes"] > 0:
                totals["team_pts"] += game_stats["team_pts"]
                totals["opp_pts"] += game_stats["opp_pts"]
                totals["minutes"] += game_stats["minutes"]
                totals["games"] += 1

        totals["plus_minus"] = totals["team_pts"] - totals["opp_pts"]
        totals["minutes"] = round(totals["minutes"], 1)

        return totals

    def get_best_lineups(
        self,
        team_id: UUID,
        game_id: UUID,
        lineup_size: int = 5,
        min_minutes: float = 2.0,
    ) -> list[dict]:
        """
        Get best performing lineups for a team in a game, sorted by plus_minus.

        Discovers all unique lineup combinations of the specified size that
        played together, then ranks them by plus/minus differential.

        Args:
            team_id: UUID of the team.
            game_id: UUID of the game.
            lineup_size: Number of players in lineup (2-5). Defaults to 5.
            min_minutes: Minimum minutes threshold to include lineup.
                Defaults to 2.0 minutes.

        Returns:
            List of dicts sorted by plus_minus (descending), each containing:
            - player_ids: List of player UUIDs in the lineup
            - team_pts: Points scored by team
            - opp_pts: Points scored by opponent
            - plus_minus: team_pts - opp_pts
            - minutes: Minutes played together

        Example:
            >>> lineups = service.get_best_lineups(
            ...     team_id=lakers_id, game_id=game_id, lineup_size=5, min_minutes=2.0
            ... )
            >>> best = lineups[0]
            >>> print(f"Best 5-man: +{best['plus_minus']} in {best['minutes']} min")
        """
        from itertools import combinations

        game = self.game_service.get_by_id(game_id)
        if not game:
            return []

        # Get all players who played for this team in the game
        player_stats_list = self.player_stats_service.get_by_game_and_team(
            game_id=game_id, team_id=team_id
        )
        player_ids = [ps.player_id for ps in player_stats_list]

        if len(player_ids) < lineup_size:
            return []

        lineups: list[dict] = []

        # Generate all combinations of the specified size
        for combo in combinations(player_ids, lineup_size):
            stats = self.get_lineup_stats(list(combo), game_id)
            if stats["minutes"] >= min_minutes:
                lineups.append(
                    {
                        "player_ids": list(combo),
                        "team_pts": stats["team_pts"],
                        "opp_pts": stats["opp_pts"],
                        "plus_minus": stats["plus_minus"],
                        "minutes": stats["minutes"],
                    }
                )

        # Sort by plus_minus descending
        lineups.sort(key=lambda x: x["plus_minus"], reverse=True)

        return lineups

    def get_events_by_time(
        self,
        game_id: UUID,
        time_filter: TimeFilter,
        event_type: EventType | None = None,
    ) -> list[PlayByPlayEvent]:
        """Get play-by-play events filtered by time/period criteria."""
        game = self.game_service.get_by_id(game_id)
        if game is None:
            return []

        all_events = self.pbp_service.get_by_game(game_id)
        valid_periods: set[int] | None = None
        if time_filter.period is not None:
            valid_periods = {time_filter.period}
        elif time_filter.periods is not None:
            valid_periods = set(time_filter.periods)

        matching: list[PlayByPlayEvent] = []
        for event in all_events:
            if event_type is not None and event.event_type != event_type.value:
                continue
            if valid_periods is not None and event.period not in valid_periods:
                continue
            try:
                secs = self._parse_clock_to_seconds(event.clock)
            except ValueError:
                continue
            if (
                time_filter.min_time_remaining is not None
                and secs < time_filter.min_time_remaining
            ):
                continue
            if (
                time_filter.max_time_remaining is not None
                and secs > time_filter.max_time_remaining
            ):
                continue
            if time_filter.exclude_garbage_time:
                home, away = self._get_game_score_at_time(game_id, event.period, secs)
                if abs(home - away) > 20:
                    continue
            matching.append(event)
        return matching

    def get_player_stats_by_quarter(self, player_id: UUID, game_id: UUID) -> dict:
        """Get player stats broken down by quarter (1-4) and OT."""
        game = self.game_service.get_by_id(game_id)
        if game is None:
            return {}

        events = self.pbp_service.get_by_game(game_id)

        def empty() -> dict:
            return {
                "points": 0,
                "fgm": 0,
                "fga": 0,
                "fg3m": 0,
                "fg3a": 0,
                "ftm": 0,
                "fta": 0,
                "rebounds": 0,
                "assists": 0,
                "steals": 0,
                "blocks": 0,
                "turnovers": 0,
            }

        result: dict = {1: empty(), 2: empty(), 3: empty(), 4: empty()}
        ot_stats = empty()
        has_ot = False

        for event in events:
            if event.player_id != player_id:
                continue
            stats = result[event.period] if event.period <= 4 else ot_stats
            if event.period > 4:
                has_ot = True

            if event.event_type == EventType.SHOT.value:
                stats["fga"] += 1
                is_3pt = event.event_subtype == "3PT"
                if is_3pt:
                    stats["fg3a"] += 1
                if event.success:
                    stats["fgm"] += 1
                    stats["points"] += 3 if is_3pt else 2
                    if is_3pt:
                        stats["fg3m"] += 1
            elif event.event_type == EventType.FREE_THROW.value:
                stats["fta"] += 1
                if event.success:
                    stats["ftm"] += 1
                    stats["points"] += 1
            elif event.event_type == EventType.REBOUND.value:
                stats["rebounds"] += 1
            elif event.event_type == EventType.ASSIST.value:
                stats["assists"] += 1
            elif event.event_type == EventType.STEAL.value:
                stats["steals"] += 1
            elif event.event_type == EventType.BLOCK.value:
                stats["blocks"] += 1
            elif event.event_type == EventType.TURNOVER.value:
                stats["turnovers"] += 1

        if has_ot:
            result["OT"] = ot_stats
        return result

    def get_clutch_stats_for_season(
        self,
        season_id: UUID,
        team_id: UUID | None = None,
        player_id: UUID | None = None,
        clutch_filter: ClutchFilter | None = None,
    ) -> ClutchSeasonStats:
        """
        Aggregate clutch performance across all games in a season.

        Calculates shooting splits, win/loss record, and efficiency metrics
        during clutch time for a team or player over an entire season.

        Args:
            season_id: UUID of the season to analyze.
            team_id: Optional UUID of the team to filter for.
            player_id: Optional UUID of the player to filter for.
            clutch_filter: ClutchFilter with criteria. Uses NBA defaults if None.

        Returns:
            ClutchSeasonStats with aggregated clutch performance metrics.

        Raises:
            None - returns zero-filled stats if no data found.

        Example:
            >>> stats = service.get_clutch_stats_for_season(
            ...     season_id, team_id=lakers_id
            ... )
            >>> print(f"Clutch FG%: {stats.fg_pct_clutch:.1%}")
            >>> print(f"Record: {stats.wins}-{stats.losses}")
        """
        from sqlalchemy import select

        if clutch_filter is None:
            clutch_filter = ClutchFilter()

        # Get all games in the season
        stmt = select(Game).where(Game.season_id == season_id)
        if team_id:
            stmt = stmt.where(
                (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
            )
        games = list(self.db.scalars(stmt).all())

        # Initialize accumulators
        games_in_clutch = 0
        wins = 0
        losses = 0

        # Clutch shooting stats
        clutch_fgm, clutch_fga = 0, 0
        clutch_fg3m, clutch_fg3a = 0, 0
        clutch_ftm, clutch_fta = 0, 0
        clutch_points = 0
        clutch_turnovers = 0

        # Overall stats for comparison
        overall_fgm, overall_fga = 0, 0
        overall_fg3m, overall_fg3a = 0, 0
        overall_ftm, overall_fta = 0, 0

        for game in games:
            clutch_events = self.get_clutch_events(game.id, clutch_filter)
            if not clutch_events:
                continue

            games_in_clutch += 1

            # Determine if team won this game
            if team_id:
                is_home = game.home_team_id == team_id
                team_score = game.home_score if is_home else game.away_score
                opp_score = game.away_score if is_home else game.home_score
                if team_score is not None and opp_score is not None:
                    if team_score > opp_score:
                        wins += 1
                    else:
                        losses += 1

            # Get overall stats for this game for comparison
            if player_id:
                player_stats = self.player_stats_service.get_by_player_and_game(
                    player_id=player_id, game_id=game.id
                )
                if player_stats:
                    overall_fgm += player_stats.field_goals_made or 0
                    overall_fga += player_stats.field_goals_attempted or 0
                    overall_fg3m += player_stats.three_pointers_made or 0
                    overall_fg3a += player_stats.three_pointers_attempted or 0
                    overall_ftm += player_stats.free_throws_made or 0
                    overall_fta += player_stats.free_throws_attempted or 0
            elif team_id:
                team_stats = self.team_stats_service.get_by_team_and_game(
                    team_id=team_id, game_id=game.id
                )
                if team_stats:
                    overall_fgm += team_stats.field_goals_made or 0
                    overall_fga += team_stats.field_goals_attempted or 0
                    overall_fg3m += team_stats.three_pointers_made or 0
                    overall_fg3a += team_stats.three_pointers_attempted or 0
                    overall_ftm += team_stats.free_throws_made or 0
                    overall_fta += team_stats.free_throws_attempted or 0

            # Process clutch events
            for event in clutch_events:
                # Filter by player or team if specified
                if player_id and event.player_id != player_id:
                    continue
                if team_id and event.team_id != team_id:
                    continue

                if event.event_type == EventType.SHOT.value:
                    clutch_fga += 1
                    is_3pt = event.event_subtype == "3PT"
                    if is_3pt:
                        clutch_fg3a += 1
                    if event.success:
                        clutch_fgm += 1
                        clutch_points += 3 if is_3pt else 2
                        if is_3pt:
                            clutch_fg3m += 1
                elif event.event_type == EventType.FREE_THROW.value:
                    clutch_fta += 1
                    if event.success:
                        clutch_ftm += 1
                        clutch_points += 1
                elif event.event_type == EventType.TURNOVER.value:
                    clutch_turnovers += 1

        # Calculate percentages
        fg_pct_clutch = clutch_fgm / clutch_fga if clutch_fga > 0 else 0.0
        fg_pct_overall = overall_fgm / overall_fga if overall_fga > 0 else 0.0
        three_pct_clutch = clutch_fg3m / clutch_fg3a if clutch_fg3a > 0 else 0.0
        three_pct_overall = overall_fg3m / overall_fg3a if overall_fg3a > 0 else 0.0
        ft_pct_clutch = clutch_ftm / clutch_fta if clutch_fta > 0 else 0.0
        ft_pct_overall = overall_ftm / overall_fta if overall_fta > 0 else 0.0

        points_per_game = (
            clutch_points / games_in_clutch if games_in_clutch > 0 else 0.0
        )
        to_per_game = clutch_turnovers / games_in_clutch if games_in_clutch > 0 else 0.0

        return ClutchSeasonStats(
            games_in_clutch=games_in_clutch,
            wins=wins,
            losses=losses,
            fg_pct_clutch=round(fg_pct_clutch, 3),
            fg_pct_overall=round(fg_pct_overall, 3),
            three_pct_clutch=round(three_pct_clutch, 3),
            three_pct_overall=round(three_pct_overall, 3),
            ft_pct_clutch=round(ft_pct_clutch, 3),
            ft_pct_overall=round(ft_pct_overall, 3),
            points_per_clutch_game=round(points_per_game, 1),
            turnovers_per_clutch_game=round(to_per_game, 1),
        )

    def get_quarter_splits_for_season(
        self,
        season_id: UUID,
        team_id: UUID | None = None,
        player_id: UUID | None = None,
    ) -> dict[str, QuarterStats]:
        """
        Aggregate Q1/Q2/Q3/Q4/OT stats across all season games.

        Provides quarter-by-quarter performance breakdown to identify
        patterns like strong/weak quarters or 4th quarter struggles.

        Args:
            season_id: UUID of the season to analyze.
            team_id: Optional UUID of the team to filter for.
            player_id: Optional UUID of the player to filter for.

        Returns:
            Dictionary with keys "Q1", "Q2", "Q3", "Q4", and optionally "OT"
            containing QuarterStats for each period.

        Raises:
            None - returns empty dict if no data found.

        Example:
            >>> splits = service.get_quarter_splits_for_season(
            ...     season_id, team_id=lakers_id
            ... )
            >>> print(f"Q4 points: {splits['Q4'].points:.1f}")
            >>> print(f"Q4 FG%: {splits['Q4'].fg_pct:.1%}")
        """
        from sqlalchemy import select

        # Get all games in the season
        stmt = select(Game).where(Game.season_id == season_id)
        if team_id:
            stmt = stmt.where(
                (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
            )
        games = list(self.db.scalars(stmt).all())

        # Initialize accumulators for each quarter
        quarters = {
            "Q1": {"points": 0, "allowed": 0, "fgm": 0, "fga": 0, "pm": 0, "games": 0},
            "Q2": {"points": 0, "allowed": 0, "fgm": 0, "fga": 0, "pm": 0, "games": 0},
            "Q3": {"points": 0, "allowed": 0, "fgm": 0, "fga": 0, "pm": 0, "games": 0},
            "Q4": {"points": 0, "allowed": 0, "fgm": 0, "fga": 0, "pm": 0, "games": 0},
        }
        ot_stats = {"points": 0, "allowed": 0, "fgm": 0, "fga": 0, "pm": 0, "games": 0}
        has_ot = False

        for game in games:
            events = self.pbp_service.get_by_game(game.id)
            if not events:
                continue

            # Determine team context
            if team_id:
                is_home = game.home_team_id == team_id
                opp_id = game.away_team_id if is_home else game.home_team_id
            else:
                opp_id = None

            # Track which quarters had events
            quarters_seen: set[int] = set()

            for event in events:
                # Filter by player if specified
                if player_id and event.player_id != player_id:
                    # Still track opponent scoring for team stats
                    if team_id and event.team_id == opp_id:
                        pass  # Allow opponent events through for allowed calculation
                    else:
                        continue

                # Filter by team if specified (for player's team)
                if player_id:
                    player_stats = self.player_stats_service.get_by_player_and_game(
                        player_id=player_id, game_id=game.id
                    )
                    if player_stats and event.team_id != player_stats.team_id:
                        continue

                period = event.period
                if period <= 4:
                    quarter_key = f"Q{period}"
                    stats = quarters[quarter_key]
                    quarters_seen.add(period)
                else:
                    stats = ot_stats
                    has_ot = True

                if event.event_type == EventType.SHOT.value:
                    # Check if this is the entity's shot or opponent's
                    is_own_shot = True
                    if team_id:
                        is_own_shot = event.team_id == team_id
                    elif player_id:
                        is_own_shot = event.player_id == player_id

                    if is_own_shot:
                        stats["fga"] += 1
                        if event.success:
                            stats["fgm"] += 1
                            pts = 3 if event.event_subtype == "3PT" else 2
                            stats["points"] += pts
                            stats["pm"] += pts
                    elif team_id:
                        # Opponent shot - track for points allowed
                        if event.success:
                            pts = 3 if event.event_subtype == "3PT" else 2
                            stats["allowed"] += pts
                            stats["pm"] -= pts

                elif event.event_type == EventType.FREE_THROW.value:
                    is_own_ft = True
                    if team_id:
                        is_own_ft = event.team_id == team_id
                    elif player_id:
                        is_own_ft = event.player_id == player_id

                    if is_own_ft and event.success:
                        stats["points"] += 1
                        stats["pm"] += 1
                    elif team_id and not is_own_ft and event.success:
                        stats["allowed"] += 1
                        stats["pm"] -= 1

            # Count games per quarter
            for q in quarters_seen:
                quarters[f"Q{q}"]["games"] += 1

        # Build result
        result: dict[str, QuarterStats] = {}
        for key, stats in quarters.items():
            games_count = stats["games"] if stats["games"] > 0 else 1
            fg_pct = stats["fgm"] / stats["fga"] if stats["fga"] > 0 else 0.0

            result[key] = QuarterStats(
                points=round(stats["points"] / games_count, 1),
                points_allowed=(
                    round(stats["allowed"] / games_count, 1) if team_id else None
                ),
                fg_pct=round(fg_pct, 3),
                plus_minus=round(stats["pm"] / games_count, 1) if team_id else None,
            )

        if has_ot:
            games_count = ot_stats["games"] if ot_stats["games"] > 0 else 1
            fg_pct = ot_stats["fgm"] / ot_stats["fga"] if ot_stats["fga"] > 0 else 0.0
            result["OT"] = QuarterStats(
                points=round(ot_stats["points"] / games_count, 1),
                points_allowed=(
                    round(ot_stats["allowed"] / games_count, 1) if team_id else None
                ),
                fg_pct=round(fg_pct, 3),
                plus_minus=round(ot_stats["pm"] / games_count, 1) if team_id else None,
            )

        return result

    def get_performance_trend(
        self,
        stat: str,
        last_n_games: int = 10,
        player_id: UUID | None = None,
        team_id: UUID | None = None,
        season_id: UUID | None = None,
    ) -> TrendAnalysis:
        """
        Analyze performance trend over recent games.

        Compares recent performance to season average to determine
        if the player or team is improving, declining, or stable.

        Args:
            stat: Statistic to track. For players: "points", "rebounds",
                "assists", "steals", "blocks", "fg_pct", "three_pct".
                For teams: "points", "points_allowed", "fg_pct".
            last_n_games: Number of recent games to analyze (default 10).
            player_id: UUID of the player to analyze.
            team_id: UUID of the team to analyze.
            season_id: Optional season UUID. If None, uses most recent games.

        Returns:
            TrendAnalysis with trend direction and statistics.

        Raises:
            ValueError: If neither player_id nor team_id is provided.

        Example:
            >>> trend = service.get_performance_trend(
            ...     "points", last_n_games=10, player_id=lebron_id
            ... )
            >>> print(f"Recent avg: {trend.average:.1f}")
            >>> print(f"Direction: {trend.direction}")
        """
        from sqlalchemy import select

        if not player_id and not team_id:
            raise ValueError("Either player_id or team_id must be provided")

        # Stat mapping for player stats
        player_stat_map = {
            "points": "points",
            "rebounds": "total_rebounds",
            "assists": "assists",
            "steals": "steals",
            "blocks": "blocks",
            "turnovers": "turnovers",
            "fg_pct": None,  # Calculated
            "three_pct": None,  # Calculated
        }

        values: list[float] = []
        game_labels: list[str] = []
        season_total = 0.0
        season_count = 0

        if player_id:
            # Get player's game stats ordered by game date
            stmt = (
                select(PlayerGameStats)
                .join(Game, PlayerGameStats.game_id == Game.id)
                .where(PlayerGameStats.player_id == player_id)
            )
            if season_id:
                stmt = stmt.where(Game.season_id == season_id)
            stmt = stmt.order_by(Game.game_date.desc())

            all_stats = list(self.db.scalars(stmt).all())

            for pgs in all_stats:
                game = self.game_service.get_by_id(pgs.game_id)
                if not game:
                    continue

                # Calculate the stat value
                if stat == "fg_pct":
                    fga = pgs.field_goals_attempted or 0
                    fgm = pgs.field_goals_made or 0
                    value = fgm / fga if fga > 0 else 0.0
                elif stat == "three_pct":
                    tpa = pgs.three_pointers_attempted or 0
                    tpm = pgs.three_pointers_made or 0
                    value = tpm / tpa if tpa > 0 else 0.0
                else:
                    attr = player_stat_map.get(stat, stat)
                    value = float(getattr(pgs, attr, 0) or 0)

                # Track season totals
                season_total += value
                season_count += 1

                # Track recent games
                if len(values) < last_n_games:
                    values.append(value)
                    # Create game label
                    opp_id = (
                        game.away_team_id
                        if pgs.team_id == game.home_team_id
                        else game.home_team_id
                    )
                    is_home = pgs.team_id == game.home_team_id
                    prefix = "vs" if is_home else "@"
                    opp = self.db.get(Team, opp_id) if opp_id else None
                    opp_name = opp.short_name if opp else "???"
                    game_labels.append(f"{prefix} {opp_name}")

        elif team_id:
            # Get team's game stats ordered by game date
            from src.models.game import TeamGameStats

            stmt = (
                select(TeamGameStats)
                .join(Game, TeamGameStats.game_id == Game.id)
                .where(TeamGameStats.team_id == team_id)
            )
            if season_id:
                stmt = stmt.where(Game.season_id == season_id)
            stmt = stmt.order_by(Game.game_date.desc())

            all_stats = list(self.db.scalars(stmt).all())

            for tgs in all_stats:
                game = self.game_service.get_by_id(tgs.game_id)
                if not game:
                    continue

                # Calculate the stat value
                if stat == "points":
                    value = float(tgs.points or 0)
                elif stat == "points_allowed":
                    # Get opponent's points
                    opp_id = (
                        game.away_team_id
                        if tgs.team_id == game.home_team_id
                        else game.home_team_id
                    )
                    opp_stats = self.team_stats_service.get_by_team_and_game(
                        team_id=opp_id, game_id=game.id
                    )
                    value = float(opp_stats.points or 0) if opp_stats else 0.0
                elif stat == "fg_pct":
                    fga = tgs.field_goals_attempted or 0
                    fgm = tgs.field_goals_made or 0
                    value = fgm / fga if fga > 0 else 0.0
                else:
                    value = float(getattr(tgs, stat, 0) or 0)

                season_total += value
                season_count += 1

                if len(values) < last_n_games:
                    values.append(value)
                    opp_id = (
                        game.away_team_id
                        if tgs.team_id == game.home_team_id
                        else game.home_team_id
                    )
                    is_home = tgs.team_id == game.home_team_id
                    prefix = "vs" if is_home else "@"
                    opp = self.db.get(Team, opp_id) if opp_id else None
                    opp_name = opp.short_name if opp else "???"
                    game_labels.append(f"{prefix} {opp_name}")

        # Calculate averages and trend
        recent_avg = sum(values) / len(values) if values else 0.0
        season_avg = season_total / season_count if season_count > 0 else 0.0

        # Determine direction (5% threshold for significance)
        if season_avg > 0:
            change_pct = ((recent_avg - season_avg) / season_avg) * 100
        else:
            change_pct = 0.0

        if change_pct > 5:
            direction = "improving"
        elif change_pct < -5:
            direction = "declining"
        else:
            direction = "stable"

        return TrendAnalysis(
            stat_name=stat,
            values=values,
            games=game_labels,
            average=round(recent_avg, 2),
            season_average=round(season_avg, 2),
            direction=direction,
            change_pct=round(change_pct, 1),
        )
