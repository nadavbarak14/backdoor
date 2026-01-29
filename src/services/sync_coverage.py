"""
Sync Coverage Service Module

Provides business logic for tracking data synchronization coverage
in the Basketball Analytics Platform.

This module exports:
    - SyncCoverageService: Query sync coverage statistics per season

Usage:
    from src.services.sync_coverage import SyncCoverageService

    service = SyncCoverageService(db_session)

    # Get coverage for all seasons
    coverage = service.get_all_seasons_coverage()

    # Get coverage for a specific season
    season_coverage = service.get_season_coverage(season_id)

    # Get games missing specific data
    missing_boxscore = service.get_games_missing_boxscore(season_id)
    missing_pbp = service.get_games_missing_pbp(season_id)
"""

from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import Season
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player, PlayerTeamHistory


class SeasonCoverage:
    """
    Data class holding sync coverage statistics for a season.

    Attributes:
        season_id: UUID of the season.
        season_name: Name of the season (e.g., "2024-25").
        league_name: Name of the league.
        games_total: Total number of FINAL games in the season.
        games_with_boxscore: Games that have PlayerGameStats records.
        games_with_pbp: Games that have PlayByPlayEvent records.
        players_total: Total unique players in the season (via PlayerTeamHistory).
        players_with_bio: Players that have position or height data.
    """

    def __init__(
        self,
        season_id: UUID,
        season_name: str,
        league_name: str,
        games_total: int,
        games_with_boxscore: int,
        games_with_pbp: int,
        players_total: int,
        players_with_bio: int,
    ) -> None:
        self.season_id = season_id
        self.season_name = season_name
        self.league_name = league_name
        self.games_total = games_total
        self.games_with_boxscore = games_with_boxscore
        self.games_with_pbp = games_with_pbp
        self.players_total = players_total
        self.players_with_bio = players_with_bio

    @property
    def boxscore_pct(self) -> float:
        """Percentage of games with boxscore data."""
        if self.games_total == 0:
            return 0.0
        return round(self.games_with_boxscore / self.games_total * 100, 1)

    @property
    def pbp_pct(self) -> float:
        """Percentage of games with play-by-play data."""
        if self.games_total == 0:
            return 0.0
        return round(self.games_with_pbp / self.games_total * 100, 1)

    @property
    def bio_pct(self) -> float:
        """Percentage of players with bio data."""
        if self.players_total == 0:
            return 0.0
        return round(self.players_with_bio / self.players_total * 100, 1)


class SyncCoverageService:
    """
    Service for querying sync coverage statistics.

    Provides methods to analyze what data has been synced and what's missing
    for each season, enabling incremental sync operations.

    Attributes:
        db: SQLAlchemy Session for database operations.

    Example:
        >>> service = SyncCoverageService(db_session)
        >>> coverage = service.get_all_seasons_coverage()
        >>> for season in coverage:
        ...     print(f"{season.season_name}: {season.boxscore_pct}% boxscore")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the sync coverage service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def get_season_coverage(self, season_id: UUID) -> SeasonCoverage | None:
        """
        Get sync coverage statistics for a specific season.

        Args:
            season_id: UUID of the season to analyze.

        Returns:
            SeasonCoverage object if season exists, None otherwise.

        Example:
            >>> coverage = service.get_season_coverage(season_uuid)
            >>> if coverage:
            ...     print(f"Games with boxscore: {coverage.games_with_boxscore}")
        """
        # Get season info
        season = self.db.get(Season, season_id)
        if season is None:
            return None

        league_name = season.league.name if season.league else "Unknown"

        # Count total FINAL games
        games_total = self._count_total_games(season_id)

        # Count games with boxscore (have PlayerGameStats)
        games_with_boxscore = self._count_games_with_boxscore(season_id)

        # Count games with PBP (have PlayByPlayEvent)
        games_with_pbp = self._count_games_with_pbp(season_id)

        # Count total players in season (via PlayerTeamHistory)
        players_total = self._count_total_players(season_id)

        # Count players with bio data (position or height)
        players_with_bio = self._count_players_with_bio(season_id)

        return SeasonCoverage(
            season_id=season_id,
            season_name=season.name,
            league_name=league_name,
            games_total=games_total,
            games_with_boxscore=games_with_boxscore,
            games_with_pbp=games_with_pbp,
            players_total=players_total,
            players_with_bio=players_with_bio,
        )

    def get_all_seasons_coverage(self) -> list[SeasonCoverage]:
        """
        Get sync coverage statistics for all seasons.

        Returns:
            List of SeasonCoverage objects ordered by season name descending.

        Example:
            >>> coverage_list = service.get_all_seasons_coverage()
            >>> for c in coverage_list:
            ...     print(f"{c.season_name}: {c.games_total} games")
        """
        stmt = select(Season).order_by(Season.name.desc())
        seasons = list(self.db.scalars(stmt).all())

        results = []
        for season in seasons:
            coverage = self.get_season_coverage(season.id)
            if coverage:
                results.append(coverage)

        return results

    def get_games_missing_boxscore(self, season_id: UUID) -> list[Game]:
        """
        Get FINAL games that don't have boxscore data.

        Args:
            season_id: UUID of the season.

        Returns:
            List of Game objects without PlayerGameStats records.

        Example:
            >>> missing = service.get_games_missing_boxscore(season_uuid)
            >>> print(f"Need to sync {len(missing)} games")
        """
        # Subquery: games that have PlayerGameStats
        has_stats = select(PlayerGameStats.game_id).distinct().subquery()

        stmt = (
            select(Game)
            .where(
                Game.season_id == season_id,
                Game.status == "FINAL",
                ~Game.id.in_(select(has_stats.c.game_id)),
            )
            .order_by(Game.game_date)
        )

        return list(self.db.scalars(stmt).all())

    def get_games_missing_pbp(self, season_id: UUID) -> list[Game]:
        """
        Get FINAL games that don't have play-by-play data.

        Args:
            season_id: UUID of the season.

        Returns:
            List of Game objects without PlayByPlayEvent records.

        Example:
            >>> missing = service.get_games_missing_pbp(season_uuid)
            >>> for game in missing:
            ...     print(f"Missing PBP: {game.game_date}")
        """
        # Subquery: games that have PlayByPlayEvent
        has_pbp = select(PlayByPlayEvent.game_id).distinct().subquery()

        stmt = (
            select(Game)
            .where(
                Game.season_id == season_id,
                Game.status == "FINAL",
                ~Game.id.in_(select(has_pbp.c.game_id)),
            )
            .order_by(Game.game_date)
        )

        return list(self.db.scalars(stmt).all())

    def get_players_missing_bio(self, season_id: UUID) -> list[Player]:
        """
        Get players in a season that don't have bio data (position or height).

        Args:
            season_id: UUID of the season.

        Returns:
            List of Player objects without position and height.

        Example:
            >>> missing = service.get_players_missing_bio(season_uuid)
            >>> print(f"Need bio data for {len(missing)} players")
        """
        # Get player IDs in this season via PlayerTeamHistory
        player_ids_in_season = (
            select(PlayerTeamHistory.player_id)
            .where(PlayerTeamHistory.season_id == season_id)
            .distinct()
            .subquery()
        )

        stmt = (
            select(Player)
            .where(
                Player.id.in_(select(player_ids_in_season.c.player_id)),
                # positions is a JSON array - check if empty
                func.json_array_length(Player.positions) == 0,
                Player.height_cm.is_(None),
            )
            .order_by(Player.last_name, Player.first_name)
        )

        return list(self.db.scalars(stmt).all())

    def _count_total_games(self, season_id: UUID) -> int:
        """Count total FINAL games in a season."""
        stmt = (
            select(func.count())
            .select_from(Game)
            .where(
                Game.season_id == season_id,
                Game.status == "FINAL",
            )
        )
        return self.db.execute(stmt).scalar() or 0

    def _count_games_with_boxscore(self, season_id: UUID) -> int:
        """Count FINAL games that have at least one PlayerGameStats record."""
        # Subquery for game IDs with stats
        games_with_stats = (
            select(distinct(PlayerGameStats.game_id))
            .join(Game, PlayerGameStats.game_id == Game.id)
            .where(
                Game.season_id == season_id,
                Game.status == "FINAL",
            )
        )
        stmt = select(func.count()).select_from(games_with_stats.subquery())
        return self.db.execute(stmt).scalar() or 0

    def _count_games_with_pbp(self, season_id: UUID) -> int:
        """Count FINAL games that have at least one PlayByPlayEvent record."""
        games_with_pbp = (
            select(distinct(PlayByPlayEvent.game_id))
            .join(Game, PlayByPlayEvent.game_id == Game.id)
            .where(
                Game.season_id == season_id,
                Game.status == "FINAL",
            )
        )
        stmt = select(func.count()).select_from(games_with_pbp.subquery())
        return self.db.execute(stmt).scalar() or 0

    def _count_total_players(self, season_id: UUID) -> int:
        """Count unique players in a season via PlayerTeamHistory."""
        stmt = select(func.count(distinct(PlayerTeamHistory.player_id))).where(
            PlayerTeamHistory.season_id == season_id
        )
        return self.db.execute(stmt).scalar() or 0

    def _count_players_with_bio(self, season_id: UUID) -> int:
        """Count players in a season that have position OR height."""
        # Get player IDs in this season
        player_ids = (
            select(PlayerTeamHistory.player_id)
            .where(PlayerTeamHistory.season_id == season_id)
            .distinct()
            .subquery()
        )

        stmt = (
            select(func.count())
            .select_from(Player)
            .where(
                Player.id.in_(select(player_ids.c.player_id)),
                # positions is a JSON array - check if not empty OR height exists
                (func.json_array_length(Player.positions) > 0)
                | (Player.height_cm.isnot(None)),
            )
        )
        return self.db.execute(stmt).scalar() or 0
