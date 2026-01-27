"""
Stats Calculation Service Module

Provides business logic for calculating aggregated statistics from game-level
data in the Basketball Analytics Platform.

This module exports:
    - StatsCalculationService: Calculate and store aggregated player season stats

Usage:
    from src.services.stats_calculation import StatsCalculationService

    service = StatsCalculationService(db_session)

    # Calculate season stats for a player
    stats = service.calculate_player_season_stats(player_id, team_id, season_id)

    # Recalculate all stats for a season
    count = service.recalculate_all_for_season(season_id)

The service contains static calculation methods that can be tested independently
without database access, plus orchestration methods that aggregate from game data.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.stats import PlayerSeasonStats


class StatsCalculationService:
    """
    Calculates aggregated statistics from game-level data.

    Provides both static calculation methods (for unit testing formulas)
    and database-aware methods (for aggregating and storing stats).

    All formulas are documented with their mathematical definitions.

    Attributes:
        db: SQLAlchemy Session for database operations.

    Example:
        >>> service = StatsCalculationService(db_session)
        >>> stats = service.calculate_player_season_stats(
        ...     player_id=player_uuid,
        ...     team_id=team_uuid,
        ...     season_id=season_uuid
        ... )
        >>> print(f"PPG: {stats.avg_points}")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the stats calculation service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = StatsCalculationService(db_session)
        """
        self.db = db

    def calculate_player_season_stats(
        self,
        player_id: UUID,
        team_id: UUID,
        season_id: UUID,
    ) -> PlayerSeasonStats | None:
        """
        Calculate season stats for a player on a specific team.

        Aggregates from all PlayerGameStats entries for the player/team/season
        combination. Creates or updates the PlayerSeasonStats record.

        Args:
            player_id: UUID of the player.
            team_id: UUID of the team.
            season_id: UUID of the season.

        Returns:
            PlayerSeasonStats with calculated values, or None if no game data exists.

        Example:
            >>> stats = service.calculate_player_season_stats(
            ...     player_id=lebron_id,
            ...     team_id=lakers_id,
            ...     season_id=season_2024_id
            ... )
            >>> if stats:
            ...     print(f"Games: {stats.games_played}, PPG: {stats.avg_points}")
        """
        # Get all game stats for this player/team/season combination
        stmt = (
            select(PlayerGameStats)
            .join(Game)
            .where(
                PlayerGameStats.player_id == player_id,
                PlayerGameStats.team_id == team_id,
                Game.season_id == season_id,
                Game.status == "FINAL",
            )
        )
        game_stats = list(self.db.scalars(stmt).all())

        if not game_stats:
            return None

        # Filter out DNP games (0 minutes played) for games_played count and averages
        games_with_minutes = [gs for gs in game_stats if gs.minutes_played > 0]

        # If no games with actual playing time, don't create stats
        if not games_with_minutes:
            return None

        # Aggregate totals (use all game stats for totals - they'll be 0 anyway for DNP)
        games_played = len(games_with_minutes)
        games_started = sum(1 for gs in games_with_minutes if gs.is_starter)
        total_minutes = sum(gs.minutes_played for gs in game_stats)
        total_points = sum(gs.points for gs in game_stats)
        total_fgm = sum(gs.field_goals_made for gs in game_stats)
        total_fga = sum(gs.field_goals_attempted for gs in game_stats)
        total_2pm = sum(gs.two_pointers_made for gs in game_stats)
        total_2pa = sum(gs.two_pointers_attempted for gs in game_stats)
        total_3pm = sum(gs.three_pointers_made for gs in game_stats)
        total_3pa = sum(gs.three_pointers_attempted for gs in game_stats)
        total_ftm = sum(gs.free_throws_made for gs in game_stats)
        total_fta = sum(gs.free_throws_attempted for gs in game_stats)
        total_oreb = sum(gs.offensive_rebounds for gs in game_stats)
        total_dreb = sum(gs.defensive_rebounds for gs in game_stats)
        total_reb = sum(gs.total_rebounds for gs in game_stats)
        total_ast = sum(gs.assists for gs in game_stats)
        total_tov = sum(gs.turnovers for gs in game_stats)
        total_stl = sum(gs.steals for gs in game_stats)
        total_blk = sum(gs.blocks for gs in game_stats)
        total_pf = sum(gs.personal_fouls for gs in game_stats)
        total_pm = sum(gs.plus_minus for gs in game_stats)

        # Calculate averages
        avg_minutes = self.calculate_average(total_minutes, games_played)
        avg_points = self.calculate_average(total_points, games_played)
        avg_rebounds = self.calculate_average(total_reb, games_played)
        avg_assists = self.calculate_average(total_ast, games_played)
        avg_turnovers = self.calculate_average(total_tov, games_played)
        avg_steals = self.calculate_average(total_stl, games_played)
        avg_blocks = self.calculate_average(total_blk, games_played)

        # Calculate percentages (stored as decimals 0.0-1.0)
        fg_pct = self.calculate_percentage(total_fgm, total_fga) / 100
        two_pct = self.calculate_percentage(total_2pm, total_2pa) / 100
        three_pct = self.calculate_percentage(total_3pm, total_3pa) / 100
        ft_pct = self.calculate_percentage(total_ftm, total_fta) / 100

        # Calculate advanced stats (stored as decimals 0.0-1.0)
        ts_pct = (
            self.calculate_true_shooting_pct(total_points, total_fga, total_fta) / 100
        )
        efg_pct = self.calculate_effective_fg_pct(total_fgm, total_3pm, total_fga) / 100
        ast_tov = self.calculate_assist_turnover_ratio(total_ast, total_tov)

        # Check for existing record
        existing_stmt = select(PlayerSeasonStats).where(
            PlayerSeasonStats.player_id == player_id,
            PlayerSeasonStats.team_id == team_id,
            PlayerSeasonStats.season_id == season_id,
        )
        existing = self.db.scalars(existing_stmt).first()

        if existing:
            # Update existing record
            existing.games_played = games_played
            existing.games_started = games_started
            existing.total_minutes = total_minutes
            existing.total_points = total_points
            existing.total_field_goals_made = total_fgm
            existing.total_field_goals_attempted = total_fga
            existing.total_two_pointers_made = total_2pm
            existing.total_two_pointers_attempted = total_2pa
            existing.total_three_pointers_made = total_3pm
            existing.total_three_pointers_attempted = total_3pa
            existing.total_free_throws_made = total_ftm
            existing.total_free_throws_attempted = total_fta
            existing.total_offensive_rebounds = total_oreb
            existing.total_defensive_rebounds = total_dreb
            existing.total_rebounds = total_reb
            existing.total_assists = total_ast
            existing.total_turnovers = total_tov
            existing.total_steals = total_stl
            existing.total_blocks = total_blk
            existing.total_personal_fouls = total_pf
            existing.total_plus_minus = total_pm
            existing.avg_minutes = avg_minutes
            existing.avg_points = avg_points
            existing.avg_rebounds = avg_rebounds
            existing.avg_assists = avg_assists
            existing.avg_turnovers = avg_turnovers
            existing.avg_steals = avg_steals
            existing.avg_blocks = avg_blocks
            existing.field_goal_pct = fg_pct if total_fga > 0 else None
            existing.two_point_pct = two_pct if total_2pa > 0 else None
            existing.three_point_pct = three_pct if total_3pa > 0 else None
            existing.free_throw_pct = ft_pct if total_fta > 0 else None
            existing.true_shooting_pct = ts_pct if (total_fga + total_fta) > 0 else None
            existing.effective_field_goal_pct = efg_pct if total_fga > 0 else None
            existing.assist_turnover_ratio = ast_tov
            existing.last_calculated = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            # Create new record
            stats = PlayerSeasonStats(
                player_id=player_id,
                team_id=team_id,
                season_id=season_id,
                games_played=games_played,
                games_started=games_started,
                total_minutes=total_minutes,
                total_points=total_points,
                total_field_goals_made=total_fgm,
                total_field_goals_attempted=total_fga,
                total_two_pointers_made=total_2pm,
                total_two_pointers_attempted=total_2pa,
                total_three_pointers_made=total_3pm,
                total_three_pointers_attempted=total_3pa,
                total_free_throws_made=total_ftm,
                total_free_throws_attempted=total_fta,
                total_offensive_rebounds=total_oreb,
                total_defensive_rebounds=total_dreb,
                total_rebounds=total_reb,
                total_assists=total_ast,
                total_turnovers=total_tov,
                total_steals=total_stl,
                total_blocks=total_blk,
                total_personal_fouls=total_pf,
                total_plus_minus=total_pm,
                avg_minutes=avg_minutes,
                avg_points=avg_points,
                avg_rebounds=avg_rebounds,
                avg_assists=avg_assists,
                avg_turnovers=avg_turnovers,
                avg_steals=avg_steals,
                avg_blocks=avg_blocks,
                field_goal_pct=fg_pct if total_fga > 0 else None,
                two_point_pct=two_pct if total_2pa > 0 else None,
                three_point_pct=three_pct if total_3pa > 0 else None,
                free_throw_pct=ft_pct if total_fta > 0 else None,
                true_shooting_pct=ts_pct if (total_fga + total_fta) > 0 else None,
                effective_field_goal_pct=efg_pct if total_fga > 0 else None,
                assist_turnover_ratio=ast_tov,
                last_calculated=datetime.now(UTC),
            )
            self.db.add(stats)
            self.db.commit()
            self.db.refresh(stats)
            return stats

    def recalculate_all_for_season(self, season_id: UUID) -> int:
        """
        Recalculate stats for all players in a season.

        Finds all unique player/team combinations with game data in the season
        and recalculates their aggregated stats.

        Args:
            season_id: UUID of the season.

        Returns:
            Number of PlayerSeasonStats records created/updated.

        Example:
            >>> count = service.recalculate_all_for_season(season_2024_id)
            >>> print(f"Recalculated stats for {count} player-team combos")
        """
        # Find all unique player/team combinations in this season
        stmt = (
            select(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
            )
            .join(Game)
            .where(
                Game.season_id == season_id,
                Game.status == "FINAL",
            )
            .distinct()
        )
        combinations = list(self.db.execute(stmt).all())

        count = 0
        for player_id, team_id in combinations:
            result = self.calculate_player_season_stats(player_id, team_id, season_id)
            if result:
                count += 1

        return count

    def recalculate_for_player(self, player_id: UUID) -> int:
        """
        Recalculate all season stats for a player.

        Finds all unique team/season combinations for the player and
        recalculates their aggregated stats.

        Args:
            player_id: UUID of the player.

        Returns:
            Number of PlayerSeasonStats records created/updated.

        Example:
            >>> count = service.recalculate_for_player(lebron_id)
            >>> print(f"Recalculated {count} season stats for player")
        """
        # Find all unique team/season combinations for this player
        stmt = (
            select(
                PlayerGameStats.team_id,
                Game.season_id,
            )
            .join(Game)
            .where(
                PlayerGameStats.player_id == player_id,
                Game.status == "FINAL",
            )
            .distinct()
        )
        combinations = list(self.db.execute(stmt).all())

        count = 0
        for team_id, season_id in combinations:
            result = self.calculate_player_season_stats(player_id, team_id, season_id)
            if result:
                count += 1

        return count

    # === Static Calculation Methods (independently testable) ===

    @staticmethod
    def calculate_percentage(made: int, attempted: int) -> float:
        """
        Calculate shooting percentage.

        Formula: (made / attempted) * 100

        Args:
            made: Number of shots made.
            attempted: Number of shots attempted.

        Returns:
            Percentage as float (0.0-100.0). Returns 0.0 if no attempts.

        Example:
            >>> StatsCalculationService.calculate_percentage(5, 10)
            50.0
            >>> StatsCalculationService.calculate_percentage(0, 0)
            0.0
            >>> StatsCalculationService.calculate_percentage(1, 3)
            33.3
        """
        if attempted == 0:
            return 0.0
        return round((made / attempted) * 100, 1)

    @staticmethod
    def calculate_true_shooting_pct(points: int, fga: int, fta: int) -> float:
        """
        True Shooting Percentage (TS%).

        Formula: PTS / (2 * (FGA + 0.44 * FTA)) * 100

        Measures scoring efficiency accounting for 3-pointers and free throws.
        The 0.44 coefficient approximates the possession cost of free throws.

        Args:
            points: Total points scored.
            fga: Field goal attempts.
            fta: Free throw attempts.

        Returns:
            TS% as float (0.0-100.0+). Returns 0.0 if no shot attempts.

        Example:
            >>> # 20 pts, 10 FGA, 5 FTA
            >>> # TS% = 20 / (2 * (10 + 0.44 * 5)) * 100
            >>> # TS% = 20 / (2 * 12.2) * 100 = 20 / 24.4 * 100 = 82.0
            >>> StatsCalculationService.calculate_true_shooting_pct(20, 10, 5)
            82.0
        """
        denominator = 2 * (fga + 0.44 * fta)
        if denominator == 0:
            return 0.0
        return round((points / denominator) * 100, 1)

    @staticmethod
    def calculate_effective_fg_pct(fgm: int, three_pm: int, fga: int) -> float:
        """
        Effective Field Goal Percentage (eFG%).

        Formula: (FGM + 0.5 * 3PM) / FGA * 100

        Adjusts FG% to account for 3-pointers being worth more than 2-pointers.
        A made 3-pointer is treated as 1.5 made field goals.

        Args:
            fgm: Field goals made (includes both 2PT and 3PT).
            three_pm: Three-pointers made.
            fga: Field goal attempts.

        Returns:
            eFG% as float (0.0-150.0). Returns 0.0 if no attempts.

        Example:
            >>> # 8 FGM (5 2PT + 3 3PT), 15 FGA
            >>> # eFG% = (8 + 0.5 * 3) / 15 * 100 = 9.5 / 15 * 100 = 63.3
            >>> StatsCalculationService.calculate_effective_fg_pct(8, 3, 15)
            63.3
        """
        if fga == 0:
            return 0.0
        return round(((fgm + 0.5 * three_pm) / fga) * 100, 1)

    @staticmethod
    def calculate_assist_turnover_ratio(assists: int, turnovers: int) -> float:
        """
        Assist-to-Turnover Ratio.

        Formula: AST / TO

        Measures ball security and playmaking efficiency.
        Higher values indicate better ball control.

        Args:
            assists: Number of assists.
            turnovers: Number of turnovers.

        Returns:
            Ratio as float. Returns assists as float if zero turnovers,
            0.0 if both are zero.

        Example:
            >>> StatsCalculationService.calculate_assist_turnover_ratio(10, 5)
            2.0
            >>> StatsCalculationService.calculate_assist_turnover_ratio(5, 0)
            5.0
            >>> StatsCalculationService.calculate_assist_turnover_ratio(0, 0)
            0.0
        """
        if turnovers == 0:
            return float(assists) if assists > 0 else 0.0
        return round(assists / turnovers, 2)

    @staticmethod
    def calculate_average(total: int, games: int) -> float:
        """
        Calculate per-game average.

        Formula: total / games

        Args:
            total: Total value to average.
            games: Number of games.

        Returns:
            Average per game as float. Returns 0.0 if no games.

        Example:
            >>> StatsCalculationService.calculate_average(100, 10)
            10.0
            >>> StatsCalculationService.calculate_average(100, 3)
            33.3
            >>> StatsCalculationService.calculate_average(50, 0)
            0.0
        """
        if games == 0:
            return 0.0
        return round(total / games, 1)
