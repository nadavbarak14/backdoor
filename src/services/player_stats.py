"""
Player Season Stats Service Module

Provides business logic for player season statistics in the Basketball
Analytics Platform.

This module exports:
    - PlayerSeasonStatsService: CRUD and query operations for aggregated season stats

Usage:
    from src.services.player_stats import PlayerSeasonStatsService

    service = PlayerSeasonStatsService(db_session)

    # Get player's stats for a season
    stats = service.get_player_season(player_id, season_id)

    # Get league leaders
    leaders = service.get_league_leaders(season_id, "points", limit=10)

The service handles all season stats retrieval including career stats
and league leader queries with minimum games filters.
"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from src.models.stats import PlayerSeasonStats
from src.services.base import BaseService


class PlayerSeasonStatsService(BaseService[PlayerSeasonStats]):
    """
    Service for player season statistics operations.

    Extends BaseService with season-stats-specific methods including
    player career stats, multi-team season handling, and league leaders.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The PlayerSeasonStats model class.

    Example:
        >>> service = PlayerSeasonStatsService(db_session)
        >>> career = service.get_player_career(player_id)
        >>> for season_stats in career:
        ...     print(f"{season_stats.season.name}: {season_stats.avg_points} PPG")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the player season stats service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = PlayerSeasonStatsService(db_session)
        """
        super().__init__(db, PlayerSeasonStats)

    def get_player_season(
        self,
        player_id: UUID,
        season_id: UUID,
    ) -> list[PlayerSeasonStats]:
        """
        Get stats for player in a season (may have multiple teams).

        If a player was traded mid-season, they will have multiple entries
        (one per team). All entries for the player/season are returned.

        Args:
            player_id: UUID of the player.
            season_id: UUID of the season.

        Returns:
            List of PlayerSeasonStats for the player in the season.
            Empty list if no stats found.

        Example:
            >>> stats = service.get_player_season(player_id, season_id)
            >>> for s in stats:
            ...     print(f"{s.team.name}: {s.games_played} games")
        """
        stmt = (
            select(PlayerSeasonStats)
            .options(
                joinedload(PlayerSeasonStats.player),
                joinedload(PlayerSeasonStats.team),
                joinedload(PlayerSeasonStats.season),
            )
            .where(
                PlayerSeasonStats.player_id == player_id,
                PlayerSeasonStats.season_id == season_id,
            )
            .order_by(PlayerSeasonStats.games_played.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_player_career(self, player_id: UUID) -> list[PlayerSeasonStats]:
        """
        Get all season stats for a player's career.

        Returns stats ordered by season (most recent first) and games played.

        Args:
            player_id: UUID of the player.

        Returns:
            List of PlayerSeasonStats for all seasons, ordered by season.

        Example:
            >>> career = service.get_player_career(player_id)
            >>> total_games = sum(s.games_played for s in career)
            >>> print(f"Career games: {total_games}")
        """
        stmt = (
            select(PlayerSeasonStats)
            .options(
                joinedload(PlayerSeasonStats.player),
                joinedload(PlayerSeasonStats.team),
                joinedload(PlayerSeasonStats.season),
            )
            .where(PlayerSeasonStats.player_id == player_id)
            .order_by(
                desc(PlayerSeasonStats.season_id),
                desc(PlayerSeasonStats.games_played),
            )
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_league_leaders(
        self,
        season_id: UUID,
        category: str,
        limit: int = 10,
        min_games: int = 1,
    ) -> list[PlayerSeasonStats]:
        """
        Get league leaders for a stat category.

        Returns players ranked by the specified category, filtered by
        minimum games played requirement.

        Args:
            season_id: UUID of the season.
            category: Stat category to rank by. Valid values:
                - "points" or "avg_points": Points per game
                - "rebounds" or "avg_rebounds": Rebounds per game
                - "assists" or "avg_assists": Assists per game
                - "steals" or "avg_steals": Steals per game
                - "blocks" or "avg_blocks": Blocks per game
                - "field_goal_pct": Field goal percentage
                - "three_point_pct": Three-point percentage
                - "free_throw_pct": Free throw percentage
                - "true_shooting_pct" or "efficiency": True shooting percentage
                - "effective_field_goal_pct": Effective FG%
            limit: Maximum number of results. Defaults to 10.
            min_games: Minimum games played to qualify. Defaults to 1.

        Returns:
            List of PlayerSeasonStats ranked by the category.

        Raises:
            ValueError: If category is not recognized.

        Example:
            >>> leaders = service.get_league_leaders(
            ...     season_id=season_uuid,
            ...     category="points",
            ...     limit=10,
            ...     min_games=20
            ... )
            >>> for i, stats in enumerate(leaders, 1):
            ...     print(f"{i}. {stats.player.first_name}: {stats.avg_points}")
        """
        # Map category names to model attributes
        category_mapping = {
            "points": PlayerSeasonStats.avg_points,
            "avg_points": PlayerSeasonStats.avg_points,
            "rebounds": PlayerSeasonStats.avg_rebounds,
            "avg_rebounds": PlayerSeasonStats.avg_rebounds,
            "assists": PlayerSeasonStats.avg_assists,
            "avg_assists": PlayerSeasonStats.avg_assists,
            "steals": PlayerSeasonStats.avg_steals,
            "avg_steals": PlayerSeasonStats.avg_steals,
            "blocks": PlayerSeasonStats.avg_blocks,
            "avg_blocks": PlayerSeasonStats.avg_blocks,
            "field_goal_pct": PlayerSeasonStats.field_goal_pct,
            "three_point_pct": PlayerSeasonStats.three_point_pct,
            "free_throw_pct": PlayerSeasonStats.free_throw_pct,
            "true_shooting_pct": PlayerSeasonStats.true_shooting_pct,
            "efficiency": PlayerSeasonStats.true_shooting_pct,
            "effective_field_goal_pct": PlayerSeasonStats.effective_field_goal_pct,
        }

        if category not in category_mapping:
            raise ValueError(
                f"Unknown category: {category}. "
                f"Valid categories: {', '.join(sorted(category_mapping.keys()))}"
            )

        order_column = category_mapping[category]

        stmt = (
            select(PlayerSeasonStats)
            .options(
                joinedload(PlayerSeasonStats.player),
                joinedload(PlayerSeasonStats.team),
                joinedload(PlayerSeasonStats.season),
            )
            .where(
                PlayerSeasonStats.season_id == season_id,
                PlayerSeasonStats.games_played >= min_games,
                order_column.isnot(None),
            )
            .order_by(desc(order_column))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_team_season_stats(
        self,
        team_id: UUID,
        season_id: UUID,
    ) -> list[PlayerSeasonStats]:
        """
        Get all player stats for a team in a season.

        Returns stats for all players on the team, ordered by games played.

        Args:
            team_id: UUID of the team.
            season_id: UUID of the season.

        Returns:
            List of PlayerSeasonStats for all players on the team.

        Example:
            >>> roster_stats = service.get_team_season_stats(team_id, season_id)
            >>> for stats in roster_stats:
            ...     print(f"{stats.player.first_name}: {stats.avg_points} PPG")
        """
        stmt = (
            select(PlayerSeasonStats)
            .options(
                joinedload(PlayerSeasonStats.player),
                joinedload(PlayerSeasonStats.team),
                joinedload(PlayerSeasonStats.season),
            )
            .where(
                PlayerSeasonStats.team_id == team_id,
                PlayerSeasonStats.season_id == season_id,
            )
            .order_by(desc(PlayerSeasonStats.games_played))
        )
        return list(self.db.scalars(stmt).unique().all())
