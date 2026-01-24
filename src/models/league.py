"""
League Models Module

Provides SQLAlchemy ORM models for leagues and seasons in the
Basketball Analytics Platform.

This module exports:
    - League: Represents a basketball league (e.g., NBA, EuroLeague)
    - Season: Represents a season within a league

Usage:
    from src.models.league import League, Season

    league = League(name="NBA", code="NBA", country="USA")
    season = Season(
        league_id=league.id,
        name="2023-24",
        start_date=date(2023, 10, 24),
        end_date=date(2024, 6, 20),
        is_current=True
    )
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.game import Game
    from src.models.player import PlayerTeamHistory
    from src.models.team import TeamSeason


class League(UUIDMixin, TimestampMixin, Base):
    """
    League entity representing a basketball league.

    Stores information about basketball leagues such as NBA, EuroLeague,
    or national leagues. Each league has a unique code used for identification
    in external systems.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        name: Full name of the league (e.g., "National Basketball Association")
        code: Unique short code for the league (e.g., "NBA")
        country: Country where the league is based

    Relationships:
        seasons: List of Season instances for this league

    Example:
        >>> league = League(name="NBA", code="NBA", country="USA")
        >>> session.add(league)
        >>> session.commit()
        >>> print(league.code)
        NBA
    """

    __tablename__ = "leagues"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    seasons: Mapped[list["Season"]] = relationship(
        "Season",
        back_populates="league",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of League."""
        return f"<League(code='{self.code}', name='{self.name}')>"


class Season(UUIDMixin, TimestampMixin, Base):
    """
    Season entity representing a season within a league.

    Stores information about individual seasons including date ranges
    and whether the season is currently active.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        league_id: Foreign key to the parent League
        name: Season name (e.g., "2023-24")
        start_date: Date the season starts
        end_date: Date the season ends
        is_current: Whether this is the current active season

    Relationships:
        league: The League this season belongs to
        team_seasons: TeamSeason associations for teams in this season
        player_team_histories: PlayerTeamHistory records for this season

    Example:
        >>> from datetime import date
        >>> season = Season(
        ...     league_id=league.id,
        ...     name="2023-24",
        ...     start_date=date(2023, 10, 24),
        ...     end_date=date(2024, 6, 20),
        ...     is_current=True
        ... )
        >>> session.add(season)
        >>> session.commit()
    """

    __tablename__ = "seasons"

    league_id: Mapped[str] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    league: Mapped["League"] = relationship("League", back_populates="seasons")
    team_seasons: Mapped[list["TeamSeason"]] = relationship(
        "TeamSeason",
        back_populates="season",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    player_team_histories: Mapped[list["PlayerTeamHistory"]] = relationship(
        "PlayerTeamHistory",
        back_populates="season",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    games: Mapped[list["Game"]] = relationship(
        "Game",
        back_populates="season",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("league_id", "name", name="uq_season_league_name"),
    )

    def __repr__(self) -> str:
        """Return string representation of Season."""
        return f"<Season(name='{self.name}', league_id='{self.league_id}')>"
