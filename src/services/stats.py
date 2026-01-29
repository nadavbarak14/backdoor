"""
Stats Service Module

Provides business logic for game statistics in the Basketball Analytics Platform.

This module exports:
    - PlayerGameStatsService: CRUD and query operations for player game stats
    - TeamGameStatsService: CRUD and query operations for team game stats

Usage:
    from src.services.stats import PlayerGameStatsService, TeamGameStatsService

    player_stats_service = PlayerGameStatsService(db_session)
    team_stats_service = TeamGameStatsService(db_session)

    # Get player stats for a game
    stats = player_stats_service.get_by_game(game_id)

    # Get player's game log
    game_log, total = player_stats_service.get_player_game_log(player_id)

The services handle all statistics-related business logic including
per-game stats retrieval, game logs, and bulk operations for sync efficiency.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from src.models.game import Game, PlayerGameStats, TeamGameStats
from src.services.base import BaseService


class PlayerGameStatsService(BaseService[PlayerGameStats]):
    """
    Service for player game statistics operations.

    Extends BaseService with player-stats-specific methods including
    per-game retrieval, game logs, and bulk creation for sync.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The PlayerGameStats model class.

    Example:
        >>> service = PlayerGameStatsService(db_session)
        >>> stats = service.get_by_game(game_id)
        >>> for stat in stats:
        ...     print(f"{stat.player.first_name}: {stat.points} pts")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the player game stats service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = PlayerGameStatsService(db_session)
        """
        super().__init__(db, PlayerGameStats)

    def get_by_game(self, game_id: UUID) -> list[PlayerGameStats]:
        """
        Get all player stats for a game with player info loaded.

        Returns stats for all players who participated in the game,
        with player and team relationships eagerly loaded.

        Args:
            game_id: UUID of the game.

        Returns:
            List of PlayerGameStats with player and team loaded.

        Example:
            >>> stats = service.get_by_game(game_id)
            >>> for stat in stats:
            ...     print(f"{stat.player.first_name}: {stat.points} pts")
        """
        stmt = (
            select(PlayerGameStats)
            .options(
                joinedload(PlayerGameStats.player),
                joinedload(PlayerGameStats.team),
            )
            .where(PlayerGameStats.game_id == game_id)
            .order_by(PlayerGameStats.is_starter.desc(), PlayerGameStats.points.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_by_game_and_team(
        self, game_id: UUID, team_id: UUID
    ) -> list[PlayerGameStats]:
        """
        Get player stats for one team in a game.

        Returns stats for players on a specific team in the game.

        Args:
            game_id: UUID of the game.
            team_id: UUID of the team.

        Returns:
            List of PlayerGameStats for the team's players.

        Example:
            >>> home_stats = service.get_by_game_and_team(game_id, home_team_id)
            >>> print(f"Home team had {len(home_stats)} players")
        """
        stmt = (
            select(PlayerGameStats)
            .options(
                joinedload(PlayerGameStats.player),
                joinedload(PlayerGameStats.team),
            )
            .where(
                PlayerGameStats.game_id == game_id,
                PlayerGameStats.team_id == team_id,
            )
            .order_by(PlayerGameStats.is_starter.desc(), PlayerGameStats.points.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_player_game_log(
        self,
        player_id: UUID,
        season_id: UUID | None = None,
        league_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PlayerGameStats], int]:
        """
        Get player's game log with game context.

        Returns the player's stats for each game they played,
        including opponent information and game result.

        Args:
            player_id: UUID of the player.
            season_id: Optional UUID of season to filter by.
            league_id: Optional UUID of league to filter by.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 50.

        Returns:
            Tuple of (list of PlayerGameStats with game loaded, total count).

        Example:
            >>> game_log, total = service.get_player_game_log(
            ...     player_id=lebron_id,
            ...     season_id=season_2024_id,
            ...     league_id=euroleague_id,
            ...     skip=0,
            ...     limit=10
            ... )
            >>> for stat in game_log:
            ...     print(f"{stat.game.game_date}: {stat.points} pts")
        """
        from src.models.league import Season

        stmt = (
            select(PlayerGameStats)
            .options(
                joinedload(PlayerGameStats.player),
                joinedload(PlayerGameStats.team),
                joinedload(PlayerGameStats.game).joinedload(Game.home_team),
                joinedload(PlayerGameStats.game).joinedload(Game.away_team),
            )
            .join(Game)
            .where(PlayerGameStats.player_id == player_id)
        )

        if season_id:
            stmt = stmt.where(Game.season_id == season_id)

        if league_id:
            stmt = stmt.join(Season, Game.season_id == Season.id).where(
                Season.league_id == league_id
            )

        stmt = stmt.order_by(Game.game_date.desc())

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        stats = list(self.db.scalars(stmt).unique().all())

        return stats, total

    def get_by_player_and_game(
        self, player_id: UUID, game_id: UUID
    ) -> PlayerGameStats | None:
        """
        Get stats for a specific player in a specific game.

        Args:
            player_id: UUID of the player.
            game_id: UUID of the game.

        Returns:
            PlayerGameStats if found, None otherwise.

        Example:
            >>> stats = service.get_by_player_and_game(player_id, game_id)
            >>> if stats:
            ...     print(f"Points: {stats.points}")
        """
        stmt = (
            select(PlayerGameStats)
            .options(
                joinedload(PlayerGameStats.player),
                joinedload(PlayerGameStats.team),
                joinedload(PlayerGameStats.game),
            )
            .where(
                PlayerGameStats.player_id == player_id,
                PlayerGameStats.game_id == game_id,
            )
        )
        return self.db.scalars(stmt).unique().first()

    def create_stats(self, data: dict[str, Any]) -> PlayerGameStats:
        """
        Create player game stats entry.

        Args:
            data: Dictionary containing stats fields.

        Returns:
            The newly created PlayerGameStats entity.

        Example:
            >>> stats = service.create_stats({
            ...     "game_id": game_uuid,
            ...     "player_id": player_uuid,
            ...     "team_id": team_uuid,
            ...     "minutes_played": 2040,
            ...     "points": 25,
            ...     "field_goals_made": 9,
            ...     "field_goals_attempted": 18,
            ... })
        """
        if data.get("extra_stats") is None:
            data["extra_stats"] = {}
        return self.create(data)

    def bulk_create(self, stats_list: list[dict[str, Any]]) -> list[PlayerGameStats]:
        """
        Bulk create stats for efficiency during sync.

        Creates multiple PlayerGameStats entries in a single transaction.

        Args:
            stats_list: List of dictionaries containing stats fields.

        Returns:
            List of newly created PlayerGameStats entities.

        Example:
            >>> stats_data = [
            ...     {"game_id": game_id, "player_id": p1_id, "points": 25, ...},
            ...     {"game_id": game_id, "player_id": p2_id, "points": 18, ...},
            ... ]
            >>> created = service.bulk_create(stats_data)
            >>> print(f"Created {len(created)} stat entries")
        """
        entities = []
        for data in stats_list:
            if data.get("extra_stats") is None:
                data["extra_stats"] = {}
            entity = PlayerGameStats(**data)
            self.db.add(entity)
            entities.append(entity)

        self.db.commit()

        for entity in entities:
            self.db.refresh(entity)

        return entities

    def update_stats(
        self, game_id: UUID, player_id: UUID, data: dict[str, Any]
    ) -> PlayerGameStats | None:
        """
        Update player game stats.

        Args:
            game_id: UUID of the game.
            player_id: UUID of the player.
            data: Dictionary containing fields to update.

        Returns:
            The updated PlayerGameStats if found, None otherwise.

        Example:
            >>> updated = service.update_stats(
            ...     game_id=game_uuid,
            ...     player_id=player_uuid,
            ...     data={"points": 30, "assists": 8}
            ... )
        """
        stats = self.get_by_player_and_game(player_id, game_id)
        if stats is None:
            return None

        for key, value in data.items():
            if value is not None and hasattr(stats, key):
                setattr(stats, key, value)

        self.db.commit()
        self.db.refresh(stats)
        return stats


class TeamGameStatsService:
    """
    Service for team game statistics operations.

    Provides methods for team-level stats retrieval, game history,
    and aggregation from player stats.

    Note: This service does not extend BaseService because TeamGameStats
    uses a composite primary key (game_id, team_id) rather than UUID.

    Attributes:
        db: SQLAlchemy Session for database operations.

    Example:
        >>> service = TeamGameStatsService(db_session)
        >>> stats = service.get_by_game(game_id)
        >>> for stat in stats:
        ...     print(f"{stat.team.name}: {stat.points} pts")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the team game stats service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = TeamGameStatsService(db_session)
        """
        self.db = db

    def get_by_game(self, game_id: UUID) -> list[TeamGameStats]:
        """
        Get both team stats for a game.

        Returns stats for both teams in the game with team
        relationships eagerly loaded.

        Args:
            game_id: UUID of the game.

        Returns:
            List of TeamGameStats for both teams (home team first).

        Example:
            >>> stats = service.get_by_game(game_id)
            >>> for stat in stats:
            ...     location = "Home" if stat.is_home else "Away"
            ...     print(f"{location}: {stat.team.name} - {stat.points} pts")
        """
        stmt = (
            select(TeamGameStats)
            .options(joinedload(TeamGameStats.team))
            .where(TeamGameStats.game_id == game_id)
            .order_by(TeamGameStats.is_home.desc())  # Home team first
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_by_team_and_game(
        self, team_id: UUID, game_id: UUID
    ) -> TeamGameStats | None:
        """
        Get stats for a specific team in a specific game.

        Args:
            team_id: UUID of the team.
            game_id: UUID of the game.

        Returns:
            TeamGameStats if found, None otherwise.

        Example:
            >>> stats = service.get_by_team_and_game(team_id, game_id)
            >>> if stats:
            ...     print(f"Points: {stats.points}")
        """
        stmt = (
            select(TeamGameStats)
            .options(
                joinedload(TeamGameStats.team),
                joinedload(TeamGameStats.game),
            )
            .where(
                TeamGameStats.team_id == team_id,
                TeamGameStats.game_id == game_id,
            )
        )
        return self.db.scalars(stmt).unique().first()

    def get_team_game_history(
        self,
        team_id: UUID,
        season_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TeamGameStats], int]:
        """
        Get team's game history with opponent info.

        Returns the team's stats for each game they played,
        including game context for opponent and result determination.

        Args:
            team_id: UUID of the team.
            season_id: Optional UUID of season to filter by.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 50.

        Returns:
            Tuple of (list of TeamGameStats with game loaded, total count).

        Example:
            >>> history, total = service.get_team_game_history(
            ...     team_id=lakers_id,
            ...     season_id=season_2024_id,
            ...     skip=0,
            ...     limit=10
            ... )
            >>> for stat in history:
            ...     print(f"{stat.game.game_date}: {stat.points} pts")
        """
        stmt = (
            select(TeamGameStats)
            .options(
                joinedload(TeamGameStats.team),
                joinedload(TeamGameStats.game).joinedload(Game.home_team),
                joinedload(TeamGameStats.game).joinedload(Game.away_team),
            )
            .join(Game)
            .where(TeamGameStats.team_id == team_id)
        )

        if season_id:
            stmt = stmt.where(Game.season_id == season_id)

        stmt = stmt.order_by(Game.game_date.desc())

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        stats = list(self.db.scalars(stmt).unique().all())

        return stats, total

    def create_stats(self, data: dict[str, Any]) -> TeamGameStats:
        """
        Create team game stats.

        Args:
            data: Dictionary containing stats fields including
                game_id, team_id, and is_home.

        Returns:
            The newly created TeamGameStats entity.

        Example:
            >>> stats = service.create_stats({
            ...     "game_id": game_uuid,
            ...     "team_id": team_uuid,
            ...     "is_home": True,
            ...     "points": 112,
            ...     "field_goals_made": 42,
            ...     "field_goals_attempted": 88,
            ... })
        """
        if data.get("extra_stats") is None:
            data["extra_stats"] = {}
        entity = TeamGameStats(**data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update_stats(
        self, game_id: UUID, team_id: UUID, data: dict[str, Any]
    ) -> TeamGameStats | None:
        """
        Update team game stats.

        Args:
            game_id: UUID of the game.
            team_id: UUID of the team.
            data: Dictionary containing fields to update.

        Returns:
            The updated TeamGameStats if found, None otherwise.

        Example:
            >>> updated = service.update_stats(
            ...     game_id=game_uuid,
            ...     team_id=team_uuid,
            ...     data={"points": 115, "assists": 28}
            ... )
        """
        stats = self.get_by_team_and_game(team_id, game_id)
        if stats is None:
            return None

        for key, value in data.items():
            if value is not None and hasattr(stats, key):
                setattr(stats, key, value)

        self.db.commit()
        self.db.refresh(stats)
        return stats

    def calculate_from_player_stats(
        self, game_id: UUID, team_id: UUID
    ) -> TeamGameStats | None:
        """
        Calculate and create/update team stats from player stats.

        Aggregates individual player stats to produce team totals.
        Creates new TeamGameStats if not exists, updates if exists.

        Args:
            game_id: UUID of the game.
            team_id: UUID of the team.

        Returns:
            The created/updated TeamGameStats, or None if no player stats found.

        Example:
            >>> team_stats = service.calculate_from_player_stats(game_id, team_id)
            >>> if team_stats:
            ...     print(f"Team totals: {team_stats.points} pts")
        """
        # Get all player stats for the team in this game
        player_stats_stmt = select(PlayerGameStats).where(
            PlayerGameStats.game_id == game_id,
            PlayerGameStats.team_id == team_id,
        )
        player_stats = list(self.db.scalars(player_stats_stmt).all())

        if not player_stats:
            return None

        # Get game to determine if home team
        game_stmt = select(Game).where(Game.id == game_id)
        game = self.db.scalars(game_stmt).first()
        if game is None:
            return None

        is_home = game.home_team_id == team_id

        # Aggregate stats
        aggregated = {
            "game_id": game_id,
            "team_id": team_id,
            "is_home": is_home,
            "points": sum(ps.points for ps in player_stats),
            "field_goals_made": sum(ps.field_goals_made for ps in player_stats),
            "field_goals_attempted": sum(
                ps.field_goals_attempted for ps in player_stats
            ),
            "two_pointers_made": sum(ps.two_pointers_made for ps in player_stats),
            "two_pointers_attempted": sum(
                ps.two_pointers_attempted for ps in player_stats
            ),
            "three_pointers_made": sum(ps.three_pointers_made for ps in player_stats),
            "three_pointers_attempted": sum(
                ps.three_pointers_attempted for ps in player_stats
            ),
            "free_throws_made": sum(ps.free_throws_made for ps in player_stats),
            "free_throws_attempted": sum(
                ps.free_throws_attempted for ps in player_stats
            ),
            "offensive_rebounds": sum(ps.offensive_rebounds for ps in player_stats),
            "defensive_rebounds": sum(ps.defensive_rebounds for ps in player_stats),
            "total_rebounds": sum(ps.total_rebounds for ps in player_stats),
            "assists": sum(ps.assists for ps in player_stats),
            "turnovers": sum(ps.turnovers for ps in player_stats),
            "steals": sum(ps.steals for ps in player_stats),
            "blocks": sum(ps.blocks for ps in player_stats),
            "personal_fouls": sum(ps.personal_fouls for ps in player_stats),
            # Team-only stats default to 0 (need separate source)
            "fast_break_points": 0,
            "points_in_paint": 0,
            "second_chance_points": 0,
            "bench_points": sum(ps.points for ps in player_stats if not ps.is_starter),
            "biggest_lead": 0,
            "time_leading": 0,
            "extra_stats": {},
        }

        # Check if stats already exist
        existing = self.get_by_team_and_game(team_id, game_id)
        if existing:
            # Update existing stats (preserve team-only stats if already set)
            for key, value in aggregated.items():
                if key not in ("game_id", "team_id", "is_home"):
                    # Preserve non-zero team-only stats
                    if key in (
                        "fast_break_points",
                        "points_in_paint",
                        "second_chance_points",
                        "biggest_lead",
                        "time_leading",
                    ):
                        existing_value = getattr(existing, key, 0)
                        if existing_value > 0:
                            continue
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            return self.create_stats(aggregated)
