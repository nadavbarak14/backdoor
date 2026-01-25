"""
Analytics Service Module

Provides advanced analytics capabilities for the Basketball Analytics Platform.
This service composes existing services to provide higher-level analysis tools
including clutch time filtering, situational analysis, and lineup statistics.

This module exports:
    - AnalyticsService: Orchestration layer for analytics queries

Usage:
    from src.services.analytics import AnalyticsService

    service = AnalyticsService(db_session)

    # Check if a moment qualifies as clutch
    is_clutch = service._is_clutch_moment(game_id, period=4, time_remaining=180, margin=3)

    # Get game score at a specific point in time
    home_score, away_score = service._get_game_score_at_time(game_id, period=4, time_remaining=300)

The service wraps existing services and does not query the database directly.
All data access goes through composed services for proper separation of concerns.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.play_by_play import PlayByPlayEvent
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
