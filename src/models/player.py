"""
Player Models Module

Provides SQLAlchemy ORM models for players and player-team history
in the Basketball Analytics Platform.

This module exports:
    - Player: Represents a basketball player
    - PlayerTeamHistory: Tracks player team affiliations by season

Usage:
    from src.models.player import Player, PlayerTeamHistory
    from src.schemas.enums import Position
    from datetime import date

    player = Player(
        first_name="LeBron",
        last_name="James",
        birth_date=date(1984, 12, 30),
        nationality="USA",
        height_cm=206,
        positions=[Position.SMALL_FORWARD, Position.POWER_FORWARD],
        external_ids={"nba": "2544"}
    )

    history = PlayerTeamHistory(
        player_id=player.id,
        team_id=team.id,
        season_id=season.id,
        jersey_number=23,
        positions=[Position.SMALL_FORWARD]
    )
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.types import PositionListType
from src.schemas.enums import Position


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
        positions: List of player's positions as Position enums
        external_ids: JSON object mapping provider names to external IDs

    Relationships:
        team_histories: PlayerTeamHistory records for this player

    Properties:
        full_name: Returns the player's full name (first_name + last_name)
        position: Returns primary position string for backwards compatibility

    Example:
        >>> from datetime import date
        >>> from src.schemas.enums import Position
        >>> player = Player(
        ...     first_name="Stephen",
        ...     last_name="Curry",
        ...     birth_date=date(1988, 3, 14),
        ...     nationality="USA",
        ...     height_cm=188,
        ...     positions=[Position.POINT_GUARD],
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
    positions: Mapped[list[Position]] = mapped_column(
        PositionListType, default=list, nullable=False
    )
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
    season_stats: Mapped[list["PlayerSeasonStats"]] = relationship(
        "PlayerSeasonStats",
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

    @property
    def position(self) -> str | None:
        """
        Return the player's primary position as string for backwards compatibility.

        Returns:
            str | None: First position value or None if no positions.

        Example:
            >>> player = Player(positions=[Position.SMALL_FORWARD])
            >>> player.position
            'SF'
        """
        if self.positions:
            return self.positions[0].value
        return None

    @position.setter
    def position(self, value: str | None) -> None:
        """
        Set the player's position for backwards compatibility.

        Converts a single position string to a list with one Position enum.

        Args:
            value: Position string like "SF", "PG", etc.

        Example:
            >>> player = Player(first_name="John", last_name="Doe")
            >>> player.position = "SF"
            >>> player.positions
            [Position.SMALL_FORWARD]
        """
        if value is None:
            self.positions = []
        else:
            try:
                self.positions = [Position(value.upper())]
            except ValueError:
                # Unknown position - store as empty list
                self.positions = []

    def __repr__(self) -> str:
        """Return string representation of Player."""
        pos_str = ",".join(p.value for p in self.positions) if self.positions else None
        return f"<Player(name='{self.full_name}', positions='{pos_str}')>"


class PlayerTeamHistory(UUIDMixin, TimestampMixin, Base):
    """
    Player-Team-Season association tracking player affiliations.

    Records a player's membership on a team during a specific season,
    including their jersey number and positions for that period.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        player_id: UUID foreign key to Player
        team_id: UUID foreign key to Team
        season_id: UUID foreign key to Season
        jersey_number: Player's jersey number for this team/season
        positions: Player's positions for this team/season as list of Position enums

    Relationships:
        player: The Player this history record belongs to
        team: The Team the player was on
        season: The Season this record applies to

    Constraints:
        - Unique constraint on (player_id, team_id, season_id)

    Example:
        >>> from src.schemas.enums import Position
        >>> history = PlayerTeamHistory(
        ...     player_id=player.id,
        ...     team_id=team.id,
        ...     season_id=season.id,
        ...     jersey_number=23,
        ...     positions=[Position.SMALL_FORWARD]
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
    positions: Mapped[list[Position]] = mapped_column(
        PositionListType, default=list, nullable=False
    )

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

    @property
    def position(self) -> str | None:
        """
        Return the primary position as string for backwards compatibility.

        Returns:
            str | None: First position value or None if no positions.

        Example:
            >>> history = PlayerTeamHistory(positions=[Position.SMALL_FORWARD])
            >>> history.position
            'SF'
        """
        if self.positions:
            return self.positions[0].value
        return None

    @position.setter
    def position(self, value: str | None) -> None:
        """
        Set the position for backwards compatibility.

        Converts a single position string to a list with one Position enum.

        Args:
            value: Position string like "SF", "PG", etc.
        """
        if value is None:
            self.positions = []
        else:
            try:
                self.positions = [Position(value.upper())]
            except ValueError:
                # Unknown position - store as empty list
                self.positions = []

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
    from src.models.stats import PlayerSeasonStats
    from src.models.team import Team
