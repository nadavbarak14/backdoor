"""
Play-by-Play Service Module

Provides business logic for play-by-play events in the Basketball Analytics Platform.

This module exports:
    - PlayByPlayService: CRUD and query operations for play-by-play events

Usage:
    from src.services.play_by_play import PlayByPlayService

    service = PlayByPlayService(db_session)
    events = service.get_by_game(game_id)

    # Get shot chart data
    shots = service.get_shot_chart_data(game_id, team_id=home_team_id)

The service handles all play-by-play related business logic including
event retrieval, filtering, event linking, and bulk operations for sync.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink
from src.schemas.play_by_play import PlayByPlayFilter
from src.services.base import BaseService


class PlayByPlayService(BaseService[PlayByPlayEvent]):
    """
    Service for play-by-play event operations.

    Extends BaseService with play-by-play-specific methods including
    game events retrieval, filtering, event linking, and shot chart data.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The PlayByPlayEvent model class.

    Example:
        >>> service = PlayByPlayService(db_session)
        >>> events = service.get_by_game(game_id)
        >>> for event in events:
        ...     print(f"{event.clock}: {event.description}")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the play-by-play service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = PlayByPlayService(db_session)
        """
        super().__init__(db, PlayByPlayEvent)

    def get_by_game(
        self,
        game_id: UUID,
        filter_params: PlayByPlayFilter | None = None,
    ) -> list[PlayByPlayEvent]:
        """
        Get all events for a game, ordered by event_number.

        Optionally filters by period, event type, player, or team.

        Args:
            game_id: UUID of the game.
            filter_params: Optional PlayByPlayFilter with filter criteria.

        Returns:
            List of PlayByPlayEvent ordered by event_number.

        Example:
            >>> events = service.get_by_game(game_id)
            >>> for event in events:
            ...     print(f"#{event.event_number}: {event.description}")
            >>>
            >>> # With filters
            >>> from src.schemas.play_by_play import PlayByPlayFilter
            >>> filters = PlayByPlayFilter(period=4, event_type="SHOT")
            >>> fourth_quarter_shots = service.get_by_game(game_id, filters)
        """
        stmt = (
            select(PlayByPlayEvent)
            .options(
                joinedload(PlayByPlayEvent.player),
                joinedload(PlayByPlayEvent.team),
            )
            .where(PlayByPlayEvent.game_id == game_id)
        )

        if filter_params:
            if filter_params.period:
                stmt = stmt.where(PlayByPlayEvent.period == filter_params.period)

            if filter_params.event_type:
                stmt = stmt.where(PlayByPlayEvent.event_type == filter_params.event_type)

            if filter_params.player_id:
                stmt = stmt.where(PlayByPlayEvent.player_id == filter_params.player_id)

            if filter_params.team_id:
                stmt = stmt.where(PlayByPlayEvent.team_id == filter_params.team_id)

        stmt = stmt.order_by(PlayByPlayEvent.event_number)
        return list(self.db.scalars(stmt).unique().all())

    def get_with_related(self, event_id: UUID) -> PlayByPlayEvent | None:
        """
        Get event with related events loaded.

        Loads the event with its linked events (e.g., assist linked to shot).

        Args:
            event_id: UUID of the event.

        Returns:
            PlayByPlayEvent with related_events loaded, or None if not found.

        Example:
            >>> event = service.get_with_related(shot_event_id)
            >>> if event:
            ...     for related in event.related_events:
            ...         print(f"Related: {related.event_type}")
        """
        stmt = (
            select(PlayByPlayEvent)
            .options(
                joinedload(PlayByPlayEvent.player),
                joinedload(PlayByPlayEvent.team),
                joinedload(PlayByPlayEvent.related_events),
                joinedload(PlayByPlayEvent.linked_from),
            )
            .where(PlayByPlayEvent.id == event_id)
        )
        return self.db.scalars(stmt).unique().first()

    def create_event(self, data: dict[str, Any]) -> PlayByPlayEvent:
        """
        Create a single play-by-play event.

        Args:
            data: Dictionary containing event fields.

        Returns:
            The newly created PlayByPlayEvent entity.

        Example:
            >>> event = service.create_event({
            ...     "game_id": game_uuid,
            ...     "event_number": 42,
            ...     "period": 2,
            ...     "clock": "5:30",
            ...     "event_type": "SHOT",
            ...     "event_subtype": "3PT",
            ...     "player_id": player_uuid,
            ...     "team_id": team_uuid,
            ...     "success": True,
            ...     "coord_x": 7.5,
            ...     "coord_y": 0.5,
            ...     "description": "Curry makes 3PT from top of key",
            ... })
        """
        if data.get("attributes") is None:
            data["attributes"] = {}
        return self.create(data)

    def update_event(
        self, event_id: UUID, data: dict[str, Any]
    ) -> PlayByPlayEvent | None:
        """
        Update a play-by-play event.

        Args:
            event_id: UUID of the event to update.
            data: Dictionary containing fields to update.

        Returns:
            The updated PlayByPlayEvent if found, None otherwise.

        Example:
            >>> updated = service.update_event(
            ...     event_id=event_uuid,
            ...     data={"description": "Updated description"}
            ... )
        """
        return self.update(event_id, data)

    def link_events(self, event_id: UUID, related_event_ids: list[UUID]) -> None:
        """
        Link an event to multiple related events.

        Creates PlayByPlayEventLink entries connecting the event
        to each related event.

        Args:
            event_id: UUID of the source event.
            related_event_ids: List of UUIDs of events to link to.

        Example:
            >>> # Link assist to shot
            >>> service.link_events(assist_event_id, [shot_event_id])
            >>>
            >>> # Link free throw to both foul and original shot
            >>> service.link_events(
            ...     ft_event_id,
            ...     [foul_event_id, shot_event_id]
            ... )
        """
        for related_id in related_event_ids:
            # Check if link already exists
            existing_stmt = select(PlayByPlayEventLink).where(
                PlayByPlayEventLink.event_id == event_id,
                PlayByPlayEventLink.related_event_id == related_id,
            )
            existing = self.db.scalars(existing_stmt).first()
            if not existing:
                link = PlayByPlayEventLink(
                    event_id=event_id,
                    related_event_id=related_id,
                )
                self.db.add(link)

        self.db.commit()

    def unlink_events(self, event_id: UUID, related_event_ids: list[UUID]) -> None:
        """
        Remove links between events.

        Args:
            event_id: UUID of the source event.
            related_event_ids: List of UUIDs of events to unlink.

        Example:
            >>> service.unlink_events(assist_event_id, [shot_event_id])
        """
        for related_id in related_event_ids:
            stmt = select(PlayByPlayEventLink).where(
                PlayByPlayEventLink.event_id == event_id,
                PlayByPlayEventLink.related_event_id == related_id,
            )
            link = self.db.scalars(stmt).first()
            if link:
                self.db.delete(link)

        self.db.commit()

    def get_related_events(self, event_id: UUID) -> list[PlayByPlayEvent]:
        """
        Get all events related to a specific event.

        Returns events that this event links TO.

        Args:
            event_id: UUID of the event.

        Returns:
            List of related PlayByPlayEvent entities.

        Example:
            >>> # Get the shot that this assist was for
            >>> related = service.get_related_events(assist_event_id)
            >>> for event in related:
            ...     print(f"Related: {event.event_type} - {event.description}")
        """
        event = self.get_with_related(event_id)
        if event is None:
            return []
        return list(event.related_events)

    def get_events_linking_to(self, event_id: UUID) -> list[PlayByPlayEvent]:
        """
        Get all events that link TO this event.

        Returns events where this event is the target (e.g., get assist
        that links to a specific shot).

        Args:
            event_id: UUID of the target event.

        Returns:
            List of PlayByPlayEvent entities that link to this one.

        Example:
            >>> # Get the assist for this shot
            >>> linked = service.get_events_linking_to(shot_event_id)
            >>> for event in linked:
            ...     if event.event_type == "ASSIST":
            ...         print(f"Assisted by: {event.player.first_name}")
        """
        event = self.get_with_related(event_id)
        if event is None:
            return []
        return list(event.linked_from)

    def bulk_create_with_links(
        self,
        events: list[dict[str, Any]],
        links: list[tuple[int, list[int]]],
    ) -> list[PlayByPlayEvent]:
        """
        Bulk create events with their relationships.

        Creates multiple events and links between them in a single
        transaction. Links reference indices in the events list.

        Args:
            events: List of event dictionaries.
            links: List of (event_index, related_indices) tuples
                specifying which events to link.

        Returns:
            List of newly created PlayByPlayEvent entities.

        Example:
            >>> events = [
            ...     {  # index 0: shot
            ...         "game_id": game_id,
            ...         "event_number": 1,
            ...         "event_type": "SHOT",
            ...         "success": True,
            ...         ...
            ...     },
            ...     {  # index 1: assist
            ...         "game_id": game_id,
            ...         "event_number": 2,
            ...         "event_type": "ASSIST",
            ...         ...
            ...     },
            ... ]
            >>> links = [
            ...     (1, [0]),  # assist (index 1) links to shot (index 0)
            ... ]
            >>> created = service.bulk_create_with_links(events, links)
        """
        # Create all events first
        created_events: list[PlayByPlayEvent] = []
        for data in events:
            if data.get("attributes") is None:
                data["attributes"] = {}
            entity = PlayByPlayEvent(**data)
            self.db.add(entity)
            created_events.append(entity)

        # Flush to get IDs without committing
        self.db.flush()

        # Create links using the actual IDs
        for event_index, related_indices in links:
            event = created_events[event_index]
            for related_index in related_indices:
                related_event = created_events[related_index]
                link = PlayByPlayEventLink(
                    event_id=event.id,
                    related_event_id=related_event.id,
                )
                self.db.add(link)

        # Commit everything
        self.db.commit()

        # Refresh all entities
        for entity in created_events:
            self.db.refresh(entity)

        return created_events

    def get_shot_chart_data(
        self,
        game_id: UUID,
        team_id: UUID | None = None,
        player_id: UUID | None = None,
    ) -> list[PlayByPlayEvent]:
        """
        Get shot events with coordinates for shot charts.

        Returns shot events that have coordinate data, optionally
        filtered by team or player.

        Args:
            game_id: UUID of the game.
            team_id: Optional UUID of team to filter by.
            player_id: Optional UUID of player to filter by.

        Returns:
            List of shot PlayByPlayEvent with coordinates.

        Example:
            >>> # All shots in the game
            >>> shots = service.get_shot_chart_data(game_id)
            >>>
            >>> # Only home team shots
            >>> home_shots = service.get_shot_chart_data(
            ...     game_id,
            ...     team_id=home_team_id
            ... )
            >>>
            >>> # Only Curry's shots
            >>> curry_shots = service.get_shot_chart_data(
            ...     game_id,
            ...     player_id=curry_id
            ... )
            >>> for shot in curry_shots:
            ...     result = "Made" if shot.success else "Missed"
            ...     print(f"{shot.event_subtype} at ({shot.coord_x}, {shot.coord_y}): {result}")
        """
        stmt = (
            select(PlayByPlayEvent)
            .options(
                joinedload(PlayByPlayEvent.player),
                joinedload(PlayByPlayEvent.team),
            )
            .where(
                PlayByPlayEvent.game_id == game_id,
                PlayByPlayEvent.event_type == "SHOT",
                PlayByPlayEvent.coord_x.isnot(None),
                PlayByPlayEvent.coord_y.isnot(None),
            )
        )

        if team_id:
            stmt = stmt.where(PlayByPlayEvent.team_id == team_id)

        if player_id:
            stmt = stmt.where(PlayByPlayEvent.player_id == player_id)

        stmt = stmt.order_by(PlayByPlayEvent.event_number)
        return list(self.db.scalars(stmt).unique().all())

    def get_events_by_type(
        self,
        game_id: UUID,
        event_type: str,
        event_subtype: str | None = None,
    ) -> list[PlayByPlayEvent]:
        """
        Get events of a specific type from a game.

        Args:
            game_id: UUID of the game.
            event_type: Type of events to retrieve (SHOT, REBOUND, etc.).
            event_subtype: Optional subtype filter (3PT, OFFENSIVE, etc.).

        Returns:
            List of PlayByPlayEvent matching the criteria.

        Example:
            >>> # All 3-point shots
            >>> threes = service.get_events_by_type(
            ...     game_id,
            ...     event_type="SHOT",
            ...     event_subtype="3PT"
            ... )
            >>> made = [s for s in threes if s.success]
            >>> print(f"3PT: {len(made)}/{len(threes)}")
        """
        stmt = (
            select(PlayByPlayEvent)
            .options(
                joinedload(PlayByPlayEvent.player),
                joinedload(PlayByPlayEvent.team),
            )
            .where(
                PlayByPlayEvent.game_id == game_id,
                PlayByPlayEvent.event_type == event_type,
            )
        )

        if event_subtype:
            stmt = stmt.where(PlayByPlayEvent.event_subtype == event_subtype)

        stmt = stmt.order_by(PlayByPlayEvent.event_number)
        return list(self.db.scalars(stmt).unique().all())

    def count_by_game(self, game_id: UUID) -> int:
        """
        Count total events in a game.

        Args:
            game_id: UUID of the game.

        Returns:
            Total number of events in the game.

        Example:
            >>> total = service.count_by_game(game_id)
            >>> print(f"Game had {total} play-by-play events")
        """
        stmt = (
            select(func.count())
            .select_from(PlayByPlayEvent)
            .where(PlayByPlayEvent.game_id == game_id)
        )
        return self.db.execute(stmt).scalar() or 0

    def delete_by_game(self, game_id: UUID) -> int:
        """
        Delete all events for a game.

        Useful for re-syncing play-by-play data.

        Args:
            game_id: UUID of the game.

        Returns:
            Number of events deleted.

        Example:
            >>> deleted = service.delete_by_game(game_id)
            >>> print(f"Deleted {deleted} events")
        """
        # Get all events to delete
        stmt = select(PlayByPlayEvent).where(PlayByPlayEvent.game_id == game_id)
        events = list(self.db.scalars(stmt).all())
        count = len(events)

        for event in events:
            self.db.delete(event)

        self.db.commit()
        return count
