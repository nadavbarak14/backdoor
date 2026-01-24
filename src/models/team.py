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

    team_season = TeamSeason(team_id=team.id, season_id=season.id)
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

    def __repr__(self) -> str:
        """Return string representation of Team."""
        return f"<Team(name='{self.name}', short_name='{self.short_name}')>"


class TeamSeason(TimestampMixin, Base):
    """
    Association model linking teams to seasons.

    This model represents a team's participation in a specific season.
    Uses a composite primary key of (team_id, season_id) rather than UUID.

    Attributes:
        team_id: UUID foreign key to Team (part of composite PK)
        season_id: UUID foreign key to Season (part of composite PK)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)

    Relationships:
        team: The Team participating in the season
        season: The Season the team is participating in

    Example:
        >>> team_season = TeamSeason(team_id=team.id, season_id=season.id)
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

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="team_seasons")
    season: Mapped["Season"] = relationship("Season", back_populates="team_seasons")

    def __repr__(self) -> str:
        """Return string representation of TeamSeason."""
        return f"<TeamSeason(team_id='{self.team_id}', season_id='{self.season_id}')>"


if TYPE_CHECKING:
    from src.models.league import Season
    from src.models.player import PlayerTeamHistory
