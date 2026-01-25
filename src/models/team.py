"""
Team Models Module

Provides SQLAlchemy ORM models for teams and team-season associations
in the Basketball Analytics Platform.

This module exports:
    - Team: Represents a basketball team
    - TeamSeason: Association model linking teams to seasons

Usage:
    from src.models.team import Team, TeamSeason

    team = Team(
        name="Los Angeles Lakers",
        short_name="LAL",
        city="Los Angeles",
        country="USA",
        external_ids={"winner": "123", "euroleague": "ABC"}
    )

    team_season = TeamSeason(
        team_id=team.id, season_id=season.id, external_id="w-123"
    )
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Team(UUIDMixin, TimestampMixin, Base):
    """
    Team entity representing a basketball team.

    Stores team information including identifiers from external data sources.
    The external_ids JSON field allows storing IDs from multiple data providers.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        name: Full team name (e.g., "Los Angeles Lakers")
        short_name: Abbreviated team name (e.g., "LAL")
        city: City where the team is based
        country: Country where the team is based
        external_ids: JSON object mapping provider names to external IDs

    Relationships:
        team_seasons: TeamSeason associations for seasons this team participated in
        player_team_histories: PlayerTeamHistory records for players on this team

    Example:
        >>> team = Team(
        ...     name="Los Angeles Lakers",
        ...     short_name="LAL",
        ...     city="Los Angeles",
        ...     country="USA",
        ...     external_ids={"winner": "123", "nba": "1610612747"}
        ... )
        >>> session.add(team)
        >>> session.commit()
        >>> print(team.external_ids["winner"])
        123
    """

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    external_ids: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    team_seasons: Mapped[list["TeamSeason"]] = relationship(
        "TeamSeason",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    player_team_histories: Mapped[list["PlayerTeamHistory"]] = relationship(
        "PlayerTeamHistory",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    home_games: Mapped[list["Game"]] = relationship(
        "Game",
        foreign_keys="[Game.home_team_id]",
        back_populates="home_team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    away_games: Mapped[list["Game"]] = relationship(
        "Game",
        foreign_keys="[Game.away_team_id]",
        back_populates="away_team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    player_game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        "PlayerGameStats",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    team_game_stats: Mapped[list["TeamGameStats"]] = relationship(
        "TeamGameStats",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    play_by_play_events: Mapped[list["PlayByPlayEvent"]] = relationship(
        "PlayByPlayEvent",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    player_season_stats: Mapped[list["PlayerSeasonStats"]] = relationship(
        "PlayerSeasonStats",
        back_populates="team",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of Team."""
        return f"<Team(name='{self.name}', short_name='{self.short_name}')>"


class TeamSeason(TimestampMixin, Base):
    """
    Association model linking teams to seasons with competition-specific data.

    This model represents a team's participation in a specific season/competition.
    Uses a composite primary key of (team_id, season_id) rather than UUID.

    The external_id field stores the competition-specific identifier for the team.
    For example, Maccabi Tel Aviv might have external_id="w-123" in a Winner League
    season but external_id="MAT" in a Euroleague season, while both records point
    to the same deduplicated Team entity.

    Attributes:
        team_id: UUID foreign key to Team (part of composite PK)
        season_id: UUID foreign key to Season (part of composite PK)
        external_id: Competition-specific external identifier (nullable for legacy)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)

    Relationships:
        team: The Team participating in the season
        season: The Season the team is participating in

    Example:
        >>> team_season = TeamSeason(
        ...     team_id=team.id,
        ...     season_id=season.id,
        ...     external_id="w-123"
        ... )
        >>> session.add(team_season)
        >>> session.commit()
    """

    __tablename__ = "team_seasons"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="team_seasons")
    season: Mapped["Season"] = relationship("Season", back_populates="team_seasons")

    def __repr__(self) -> str:
        """Return string representation of TeamSeason."""
        return f"<TeamSeason(team_id='{self.team_id}', season_id='{self.season_id}')>"


if TYPE_CHECKING:
    from src.models.game import Game, PlayerGameStats, TeamGameStats
    from src.models.league import Season
    from src.models.play_by_play import PlayByPlayEvent
    from src.models.player import PlayerTeamHistory
    from src.models.stats import PlayerSeasonStats
