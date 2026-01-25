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
from src.schemas.analytics import ClutchFilter, SituationalFilter
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
