"""
Play-by-Play Models Module

Provides SQLAlchemy ORM models for play-by-play events
in the Basketball Analytics Platform.

This module exports:
    - PlayByPlayEvent: Individual play-by-play event in a game
    - PlayByPlayEventLink: Association table linking related events

Usage:
    from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink
    from src.schemas.enums import EventType

    # Create a made shot event
    shot = PlayByPlayEvent(
        game_id=game.id,
        event_number=1,
        period=1,
        clock="10:30",
        event_type=EventType.SHOT,
        event_subtype="2PT",
        player_id=player.id,
        team_id=team.id,
        success=True,
        coord_x=5.5,
        coord_y=8.2,
        description="Lessort makes 2PT driving layup",
    )

    # Create an assist linked to the shot
    assist = PlayByPlayEvent(
        game_id=game.id,
        event_number=2,
        period=1,
        clock="10:30",
        event_type=EventType.ASSIST,
        player_id=passer.id,
        team_id=team.id,
        description="Wilbekin assist",
    )

    # Link the assist to the shot
    link = PlayByPlayEventLink(
        event_id=assist.id,
        related_event_id=shot.id,
    )
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.types import EventTypeType
from src.schemas.enums import EventType


class PlayByPlayEvent(UUIDMixin, TimestampMixin, Base):
    """
    Individual play-by-play event in a game.

    Stores granular event data including shots, rebounds, assists, turnovers,
    fouls, and other basketball actions. Events can be linked to each other
    to represent relationships (e.g., assist linked to made shot).

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        game_id: UUID foreign key to the Game
        event_number: Sequence number within the game
        period: Period/quarter number (1-4 for regulation, 5+ for OT)
        clock: Game clock time (e.g., "10:30" or seconds remaining)
        event_type: Type of event as EventType enum (SHOT, REBOUND, ASSIST,
                    TURNOVER, STEAL, FOUL, BLOCK, SUBSTITUTION, TIMEOUT, etc.)
        event_subtype: Subtype for additional detail (e.g., "3PT", "OFFENSIVE",
                       "PERSONAL", "TECHNICAL")
        player_id: UUID foreign key to the Player (nullable for team events)
        team_id: UUID foreign key to the Team
        success: Whether the action was successful (for shots)
        coord_x: X coordinate on court for shot location
        coord_y: Y coordinate on court for shot location
        attributes: JSON object for extensible event attributes
        description: Human-readable description of the event

    Relationships:
        game: The Game this event belongs to
        player: The Player involved (if applicable)
        team: The Team involved
        related_events: Events linked via PlayByPlayEventLink

    Example:
        >>> from src.schemas.enums import EventType
        >>> event = PlayByPlayEvent(
        ...     game_id=game.id,
        ...     event_number=42,
        ...     period=2,
        ...     clock="5:30",
        ...     event_type=EventType.SHOT,
        ...     event_subtype="3PT",
        ...     player_id=curry.id,
        ...     team_id=warriors.id,
        ...     success=True,
        ...     coord_x=7.5,
        ...     coord_y=0.5,
        ...     attributes={"shot_distance": 24.5, "fast_break": False},
        ...     description="Curry makes 3PT from top of key",
        ... )
    """

    __tablename__ = "play_by_play_events"

    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_number: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    clock: Mapped[str] = mapped_column(String(20), nullable=False)

    event_type: Mapped[EventType] = mapped_column(EventTypeType, nullable=False)
    event_subtype: Mapped[str | None] = mapped_column(String(50), nullable=True)

    player_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True,
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )

    # For shots
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    coord_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    coord_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Extensible attributes
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="play_by_play_events")
    player: Mapped["Player | None"] = relationship(
        "Player", back_populates="play_by_play_events"
    )
    team: Mapped["Team"] = relationship("Team", back_populates="play_by_play_events")

    # Related events via link table (events this event links TO)
    related_events: Mapped[list["PlayByPlayEvent"]] = relationship(
        "PlayByPlayEvent",
        secondary="play_by_play_event_links",
        primaryjoin="PlayByPlayEvent.id == PlayByPlayEventLink.event_id",
        secondaryjoin="PlayByPlayEvent.id == PlayByPlayEventLink.related_event_id",
        viewonly=True,
    )

    # Events that link TO this event (reverse relationship)
    linked_from: Mapped[list["PlayByPlayEvent"]] = relationship(
        "PlayByPlayEvent",
        secondary="play_by_play_event_links",
        primaryjoin="PlayByPlayEvent.id == PlayByPlayEventLink.related_event_id",
        secondaryjoin="PlayByPlayEvent.id == PlayByPlayEventLink.event_id",
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint("game_id", "event_number", name="uq_game_event_number"),
    )

    def __repr__(self) -> str:
        """Return string representation of PlayByPlayEvent."""
        return (
            f"<PlayByPlayEvent(id='{self.id}', event_number={self.event_number}, "
            f"type='{self.event_type}')>"
        )


class PlayByPlayEventLink(Base):
    """
    Association table linking related play-by-play events.

    Creates relationships between events such as:
    - Assist linked to made shot
    - Rebound linked to missed shot
    - Steal linked to turnover
    - Foul linked to shot attempt (and-1)
    - Free throw linked to foul and original shot

    Attributes:
        event_id: UUID foreign key to the source event (part of composite PK)
        related_event_id: UUID foreign key to the related event (part of composite PK)

    Relationships:
        event: The source PlayByPlayEvent
        related_event: The related PlayByPlayEvent

    Example (And-1 Play):
        Event 1: SHOT (2PT, made, player=Lessort)
        Event 2: ASSIST (player=Wilbekin) -> links to [1]
        Event 3: FOUL (shooting, player=Opponent) -> links to [1]
        Event 4: FREE_THROW (made, player=Lessort) -> links to [1, 3]

        >>> link_assist = PlayByPlayEventLink(
        ...     event_id=assist_event.id,
        ...     related_event_id=shot_event.id,
        ... )
        >>> link_foul = PlayByPlayEventLink(
        ...     event_id=foul_event.id,
        ...     related_event_id=shot_event.id,
        ... )
        >>> link_ft_to_shot = PlayByPlayEventLink(
        ...     event_id=free_throw_event.id,
        ...     related_event_id=shot_event.id,
        ... )
        >>> link_ft_to_foul = PlayByPlayEventLink(
        ...     event_id=free_throw_event.id,
        ...     related_event_id=foul_event.id,
        ... )
    """

    __tablename__ = "play_by_play_event_links"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("play_by_play_events.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    related_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("play_by_play_events.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Relationships
    event: Mapped["PlayByPlayEvent"] = relationship(
        "PlayByPlayEvent",
        foreign_keys=[event_id],
        overlaps="related_events,linked_from",
    )
    related_event: Mapped["PlayByPlayEvent"] = relationship(
        "PlayByPlayEvent",
        foreign_keys=[related_event_id],
        overlaps="related_events,linked_from",
    )

    def __repr__(self) -> str:
        """Return string representation of PlayByPlayEventLink."""
        return (
            f"<PlayByPlayEventLink(event_id='{self.event_id}', "
            f"related_event_id='{self.related_event_id}')>"
        )


if TYPE_CHECKING:
    from src.models.game import Game
    from src.models.player import Player
    from src.models.team import Team
