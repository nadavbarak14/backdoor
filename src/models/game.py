"""
Game Models Module

Provides SQLAlchemy ORM models for games and game statistics
in the Basketball Analytics Platform.

This module exports:
    - Game: Represents a basketball game between two teams
    - PlayerGameStats: Per-player box score statistics for a game
    - TeamGameStats: Team-level aggregated statistics for a game

Usage:
    from src.models.game import Game, PlayerGameStats, TeamGameStats

    game = Game(
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=datetime(2024, 1, 15, 19, 30),
        status="FINAL",
        home_score=112,
        away_score=108,
    )

    player_stats = PlayerGameStats(
        game_id=game.id,
        player_id=player.id,
        team_id=team.id,
        minutes_played=2040,  # 34 minutes in seconds
        points=25,
        field_goals_made=9,
        field_goals_attempted=18,
    )
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Game(UUIDMixin, TimestampMixin, Base):
    """
    Game entity representing a basketball game between two teams.

    Stores game information including participating teams, scores, venue,
    and identifiers from external data sources.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        season_id: UUID foreign key to the Season this game belongs to
        home_team_id: UUID foreign key to the home Team
        away_team_id: UUID foreign key to the away Team
        game_date: Date and time of the game
        status: Game status (SCHEDULED, LIVE, FINAL, POSTPONED)
        home_score: Final score of the home team (None if not finished)
        away_score: Final score of the away team (None if not finished)
        venue: Name of the arena/venue where the game is played
        attendance: Number of spectators attending the game
        external_ids: JSON object mapping provider names to external IDs

    Relationships:
        season: The Season this game belongs to
        home_team: The home Team
        away_team: The away Team
        player_game_stats: PlayerGameStats records for all players in this game
        team_game_stats: TeamGameStats records for both teams in this game
        play_by_play_events: PlayByPlayEvent records for this game

    Example:
        >>> game = Game(
        ...     season_id=season.id,
        ...     home_team_id=lakers.id,
        ...     away_team_id=celtics.id,
        ...     game_date=datetime(2024, 1, 15, 19, 30),
        ...     status="FINAL",
        ...     home_score=112,
        ...     away_score=108,
        ...     venue="Crypto.com Arena",
        ...     attendance=18997,
        ...     external_ids={"winner": "123", "nba": "0022300567"}
        ... )
        >>> session.add(game)
        >>> session.commit()
    """

    __tablename__ = "games"

    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
    )
    home_team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    away_team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    game_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SCHEDULED")
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ids: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="games")
    home_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[home_team_id],
        back_populates="home_games",
    )
    away_team: Mapped["Team"] = relationship(
        "Team",
        foreign_keys=[away_team_id],
        back_populates="away_games",
    )
    player_game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        "PlayerGameStats",
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    team_game_stats: Mapped[list["TeamGameStats"]] = relationship(
        "TeamGameStats",
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    play_by_play_events: Mapped[list["PlayByPlayEvent"]] = relationship(
        "PlayByPlayEvent",
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(
        "SyncLog",
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("ix_games_game_date", "game_date"),)

    def __repr__(self) -> str:
        """Return string representation of Game."""
        return (
            f"<Game(id='{self.id}', date='{self.game_date}', "
            f"status='{self.status}')>"
        )


class PlayerGameStats(UUIDMixin, TimestampMixin, Base):
    """
    Per-player box score statistics for a game.

    Stores all box score data for a single player in a single game.
    Minutes are stored as seconds for precision.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        game_id: UUID foreign key to the Game
        player_id: UUID foreign key to the Player
        team_id: UUID foreign key to the Team (player's team for this game)
        minutes_played: Playing time in seconds for precision
        is_starter: Whether the player was in the starting lineup
        points: Total points scored
        field_goals_made: Number of field goals made
        field_goals_attempted: Number of field goals attempted
        two_pointers_made: Number of 2-point field goals made
        two_pointers_attempted: Number of 2-point field goals attempted
        three_pointers_made: Number of 3-point field goals made
        three_pointers_attempted: Number of 3-point field goals attempted
        free_throws_made: Number of free throws made
        free_throws_attempted: Number of free throws attempted
        offensive_rebounds: Number of offensive rebounds
        defensive_rebounds: Number of defensive rebounds
        total_rebounds: Total number of rebounds
        assists: Number of assists
        turnovers: Number of turnovers
        steals: Number of steals
        blocks: Number of blocks
        personal_fouls: Number of personal fouls
        plus_minus: Plus/minus statistic
        efficiency: Performance index rating (PIR or similar)
        extra_stats: JSON object for league-specific stats

    Relationships:
        game: The Game this stat line belongs to
        player: The Player who recorded these stats
        team: The Team the player played for

    Example:
        >>> stats = PlayerGameStats(
        ...     game_id=game.id,
        ...     player_id=player.id,
        ...     team_id=team.id,
        ...     minutes_played=2040,  # 34 minutes
        ...     is_starter=True,
        ...     points=25,
        ...     field_goals_made=9,
        ...     field_goals_attempted=18,
        ...     three_pointers_made=3,
        ...     three_pointers_attempted=7,
        ... )
    """

    __tablename__ = "player_game_stats"

    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Playing time
    minutes_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Scoring
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    field_goals_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    field_goals_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    two_pointers_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    two_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    three_pointers_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    three_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    free_throws_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    free_throws_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Rebounds
    offensive_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defensive_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Other stats
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turnovers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    personal_fouls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plus_minus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    efficiency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Extensible
    extra_stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="player_game_stats")
    player: Mapped["Player"] = relationship("Player", back_populates="game_stats")
    team: Mapped["Team"] = relationship("Team", back_populates="player_game_stats")

    __table_args__ = (
        UniqueConstraint("game_id", "player_id", name="uq_player_game_stats"),
    )

    def __repr__(self) -> str:
        """Return string representation of PlayerGameStats."""
        return (
            f"<PlayerGameStats(game_id='{self.game_id}', "
            f"player_id='{self.player_id}', points={self.points})>"
        )


class TeamGameStats(TimestampMixin, Base):
    """
    Team-level aggregated statistics for a game.

    Uses a composite primary key of (game_id, team_id) rather than UUID.
    Stores team-level stats including team-only metrics like fast break points.

    Attributes:
        game_id: UUID foreign key to the Game (part of composite PK)
        team_id: UUID foreign key to the Team (part of composite PK)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        is_home: Whether this team is the home team
        points: Total points scored
        field_goals_made: Number of field goals made
        field_goals_attempted: Number of field goals attempted
        two_pointers_made: Number of 2-point field goals made
        two_pointers_attempted: Number of 2-point field goals attempted
        three_pointers_made: Number of 3-point field goals made
        three_pointers_attempted: Number of 3-point field goals attempted
        free_throws_made: Number of free throws made
        free_throws_attempted: Number of free throws attempted
        offensive_rebounds: Number of offensive rebounds
        defensive_rebounds: Number of defensive rebounds
        total_rebounds: Total number of rebounds
        assists: Number of assists
        turnovers: Number of turnovers
        steals: Number of steals
        blocks: Number of blocks
        personal_fouls: Number of personal fouls
        fast_break_points: Points scored on fast breaks
        points_in_paint: Points scored in the paint
        second_chance_points: Points scored on second chance opportunities
        bench_points: Points scored by bench players
        biggest_lead: Largest lead during the game
        time_leading: Time spent leading in seconds
        extra_stats: JSON object for league-specific stats

    Relationships:
        game: The Game this stat line belongs to
        team: The Team these stats belong to

    Example:
        >>> team_stats = TeamGameStats(
        ...     game_id=game.id,
        ...     team_id=team.id,
        ...     is_home=True,
        ...     points=112,
        ...     field_goals_made=42,
        ...     field_goals_attempted=88,
        ...     fast_break_points=18,
        ...     points_in_paint=52,
        ... )
    """

    __tablename__ = "team_game_stats"

    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Standard stats (aggregated from players)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    field_goals_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    field_goals_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    two_pointers_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    two_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    three_pointers_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    three_pointers_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    free_throws_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    free_throws_attempted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    offensive_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defensive_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rebounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turnovers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    personal_fouls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Team-only stats
    fast_break_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_in_paint: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    second_chance_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    bench_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    biggest_lead: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    time_leading: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Extensible
    extra_stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="team_game_stats")
    team: Mapped["Team"] = relationship("Team", back_populates="team_game_stats")

    def __repr__(self) -> str:
        """Return string representation of TeamGameStats."""
        return (
            f"<TeamGameStats(game_id='{self.game_id}', "
            f"team_id='{self.team_id}', points={self.points})>"
        )


if TYPE_CHECKING:
    from src.models.league import Season
    from src.models.play_by_play import PlayByPlayEvent
    from src.models.player import Player
    from src.models.sync import SyncLog
    from src.models.team import Team
