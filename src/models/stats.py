"""
Player Season Stats Model Module

Provides the SQLAlchemy ORM model for pre-computed aggregated player
season statistics in the Basketball Analytics Platform.

This module exports:
    - PlayerSeasonStats: Aggregated player statistics for a season per team

Usage:
    from src.models.stats import PlayerSeasonStats

    stats = PlayerSeasonStats(
        player_id=player.id,
        team_id=team.id,
        season_id=season.id,
        games_played=72,
        total_points=1800,
        avg_points=25.0,
        field_goal_pct=0.485,
    )

Note:
    If a player is traded mid-season, they will have multiple rows
    (one per team) in this table for that season.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class PlayerSeasonStats(UUIDMixin, TimestampMixin, Base):
    """
    Aggregated player statistics for a season per team.

    Stores pre-computed totals, averages, and percentages for a player's
    performance during a specific season with a specific team. Minutes are
    stored as seconds for precision.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        player_id: UUID foreign key to the Player
        team_id: UUID foreign key to the Team
        season_id: UUID foreign key to the Season
        games_played: Number of games the player appeared in
        games_started: Number of games the player started
        total_minutes: Total playing time in seconds
        total_points: Total points scored
        total_field_goals_made: Total field goals made
        total_field_goals_attempted: Total field goals attempted
        total_two_pointers_made: Total 2-point field goals made
        total_two_pointers_attempted: Total 2-point field goals attempted
        total_three_pointers_made: Total 3-point field goals made
        total_three_pointers_attempted: Total 3-point field goals attempted
        total_free_throws_made: Total free throws made
        total_free_throws_attempted: Total free throws attempted
        total_offensive_rebounds: Total offensive rebounds
        total_defensive_rebounds: Total defensive rebounds
        total_rebounds: Total rebounds
        total_assists: Total assists
        total_turnovers: Total turnovers
        total_steals: Total steals
        total_blocks: Total blocks
        total_personal_fouls: Total personal fouls
        total_plus_minus: Cumulative plus/minus
        avg_minutes: Average playing time per game (in seconds)
        avg_points: Average points per game
        avg_rebounds: Average rebounds per game
        avg_assists: Average assists per game
        avg_turnovers: Average turnovers per game
        avg_steals: Average steals per game
        avg_blocks: Average blocks per game
        field_goal_pct: Field goal percentage (0.0 - 1.0)
        two_point_pct: Two-point percentage (0.0 - 1.0)
        three_point_pct: Three-point percentage (0.0 - 1.0)
        free_throw_pct: Free throw percentage (0.0 - 1.0)
        true_shooting_pct: True shooting percentage (TS%)
        effective_field_goal_pct: Effective field goal percentage (eFG%)
        assist_turnover_ratio: Assist to turnover ratio
        last_calculated: When stats were last recomputed

    Relationships:
        player: The Player these stats belong to
        team: The Team the player played for
        season: The Season these stats are for

    Constraints:
        - Unique constraint on (player_id, team_id, season_id)

    Example:
        >>> stats = PlayerSeasonStats(
        ...     player_id=player.id,
        ...     team_id=team.id,
        ...     season_id=season.id,
        ...     games_played=72,
        ...     games_started=72,
        ...     total_points=1800,
        ...     total_assists=540,
        ...     avg_points=25.0,
        ...     avg_assists=7.5,
        ...     field_goal_pct=0.485,
        ...     three_point_pct=0.367,
        ... )
        >>> session.add(stats)
        >>> session.commit()
    """

    __tablename__ = "player_season_stats"

    # Foreign keys
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Games
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_started: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Totals
    total_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_field_goals_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_field_goals_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_two_pointers_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_two_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_three_pointers_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_three_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_free_throws_made: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_free_throws_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_offensive_rebounds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_defensive_rebounds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_turnovers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_steals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_blocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_personal_fouls: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_plus_minus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Averages
    avg_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_points: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_rebounds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_assists: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_turnovers: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_steals: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_blocks: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Percentages (stored as decimals 0.0-1.0)
    field_goal_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    two_point_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    three_point_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_throw_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Advanced stats
    true_shooting_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_field_goal_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    assist_turnover_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Tracking
    last_calculated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="season_stats")
    team: Mapped["Team"] = relationship("Team", back_populates="player_season_stats")
    season: Mapped["Season"] = relationship(
        "Season", back_populates="player_season_stats"
    )

    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_id",
            "season_id",
            name="uq_player_team_season_stats",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of PlayerSeasonStats."""
        return (
            f"<PlayerSeasonStats(player_id='{self.player_id}', "
            f"team_id='{self.team_id}', season_id='{self.season_id}', "
            f"games={self.games_played}, ppg={self.avg_points})>"
        )


if TYPE_CHECKING:
    from src.models.league import Season
    from src.models.player import Player
    from src.models.team import Team
