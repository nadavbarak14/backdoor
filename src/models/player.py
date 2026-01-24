"""
Player Models Module

Provides SQLAlchemy ORM models for players and player-team history
in the Basketball Analytics Platform.

This module exports:
    - Player: Represents a basketball player
    - PlayerTeamHistory: Tracks player team affiliations by season

Usage:
    from src.models.player import Player, PlayerTeamHistory
    from datetime import date

    player = Player(
        first_name="LeBron",
        last_name="James",
        birth_date=date(1984, 12, 30),
        nationality="USA",
        height_cm=206,
        position="SF",
        external_ids={"nba": "2544"}
    )

    history = PlayerTeamHistory(
        player_id=player.id,
        team_id=team.id,
        season_id=season.id,
        jersey_number=23,
        position="SF"
    )
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Player(UUIDMixin, TimestampMixin, Base):
    """
    Player entity representing a basketball player.

    Stores biographical information about players including physical
    attributes and identifiers from external data sources.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        first_name: Player's first name
        last_name: Player's last name
        birth_date: Player's date of birth
        nationality: Player's nationality (country code or name)
        height_cm: Player's height in centimeters
        position: Player's primary position (e.g., "PG", "SG", "SF", "PF", "C")
        external_ids: JSON object mapping provider names to external IDs

    Relationships:
        team_histories: PlayerTeamHistory records for this player

    Properties:
        full_name: Returns the player's full name (first_name + last_name)

    Example:
        >>> from datetime import date
        >>> player = Player(
        ...     first_name="Stephen",
        ...     last_name="Curry",
        ...     birth_date=date(1988, 3, 14),
        ...     nationality="USA",
        ...     height_cm=188,
        ...     position="PG",
        ...     external_ids={"nba": "201939"}
        ... )
        >>> session.add(player)
        >>> session.commit()
        >>> print(player.full_name)
        Stephen Curry
    """

    __tablename__ = "players"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[str | None] = mapped_column(String(20), nullable=True)
    external_ids: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    team_histories: Mapped[list["PlayerTeamHistory"]] = relationship(
        "PlayerTeamHistory",
        back_populates="player",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        "PlayerGameStats",
        back_populates="player",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    play_by_play_events: Mapped[list["PlayByPlayEvent"]] = relationship(
        "PlayByPlayEvent",
        back_populates="player",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def full_name(self) -> str:
        """
        Return the player's full name.

        Returns:
            str: First name and last name concatenated with a space.

        Example:
            >>> player = Player(first_name="LeBron", last_name="James")
            >>> player.full_name
            'LeBron James'
        """
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        """Return string representation of Player."""
        return f"<Player(name='{self.full_name}', position='{self.position}')>"


class PlayerTeamHistory(UUIDMixin, TimestampMixin, Base):
    """
    Player-Team-Season association tracking player affiliations.

    Records a player's membership on a team during a specific season,
    including their jersey number and position for that period.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        player_id: UUID foreign key to Player
        team_id: UUID foreign key to Team
        season_id: UUID foreign key to Season
        jersey_number: Player's jersey number for this team/season
        position: Player's position for this team/season

    Relationships:
        player: The Player this history record belongs to
        team: The Team the player was on
        season: The Season this record applies to

    Constraints:
        - Unique constraint on (player_id, team_id, season_id)

    Example:
        >>> history = PlayerTeamHistory(
        ...     player_id=player.id,
        ...     team_id=team.id,
        ...     season_id=season.id,
        ...     jersey_number=23,
        ...     position="SF"
        ... )
        >>> session.add(history)
        >>> session.commit()
    """

    __tablename__ = "player_team_histories"

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
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="team_histories")
    team: Mapped["Team"] = relationship("Team", back_populates="player_team_histories")
    season: Mapped["Season"] = relationship(
        "Season", back_populates="player_team_histories"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_id",
            "season_id",
            name="uq_player_team_season",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of PlayerTeamHistory."""
        return (
            f"<PlayerTeamHistory(player_id='{self.player_id}', "
            f"team_id='{self.team_id}', season_id='{self.season_id}')>"
        )


if TYPE_CHECKING:
    from src.models.game import PlayerGameStats
    from src.models.league import Season
    from src.models.play_by_play import PlayByPlayEvent
    from src.models.team import Team
