"""
Play-by-Play Schema Tests

Tests for src/schemas/play_by_play.py covering:
- PlayByPlayEventResponse with related_event_ids
- PlayByPlayResponse structure
- PlayByPlayFilter optional fields
"""

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.game import EventType
from src.schemas.play_by_play import (
    PlayByPlayEventResponse,
    PlayByPlayFilter,
    PlayByPlayResponse,
)


class TestPlayByPlayEventResponse:
    """Tests for PlayByPlayEventResponse schema."""

    def test_complete_event(self):
        """PlayByPlayEventResponse should accept all fields."""
        event_id = uuid.uuid4()
        game_id = uuid.uuid4()
        player_id = uuid.uuid4()
        team_id = uuid.uuid4()
        related_id = uuid.uuid4()

        event = PlayByPlayEventResponse(
            id=event_id,
            game_id=game_id,
            event_number=42,
            period=2,
            clock="5:30",
            event_type="SHOT",
            event_subtype="3PT",
            player_id=player_id,
            player_name="Stephen Curry",
            team_id=team_id,
            team_name="Golden State Warriors",
            success=True,
            coord_x=7.5,
            coord_y=0.5,
            attributes={"shot_distance": 24.5, "fast_break": False},
            description="Curry makes 3PT from top of key",
            related_event_ids=[related_id],
        )

        assert event.id == event_id
        assert event.game_id == game_id
        assert event.event_number == 42
        assert event.period == 2
        assert event.clock == "5:30"
        assert event.event_type == "SHOT"
        assert event.event_subtype == "3PT"
        assert event.player_id == player_id
        assert event.player_name == "Stephen Curry"
        assert event.team_id == team_id
        assert event.team_name == "Golden State Warriors"
        assert event.success is True
        assert event.coord_x == 7.5
        assert event.coord_y == 0.5
        assert event.attributes == {"shot_distance": 24.5, "fast_break": False}
        assert event.description == "Curry makes 3PT from top of key"
        assert len(event.related_event_ids) == 1
        assert event.related_event_ids[0] == related_id

    def test_event_with_multiple_related_events(self):
        """PlayByPlayEventResponse should handle multiple related events."""
        related_id1 = uuid.uuid4()
        related_id2 = uuid.uuid4()

        event = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            event_number=45,
            period=2,
            clock="5:30",
            event_type="FREE_THROW",
            event_subtype=None,
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            team_name="Los Angeles Lakers",
            success=True,
            coord_x=None,
            coord_y=None,
            attributes={},
            description="LeBron makes free throw 1 of 2",
            related_event_ids=[related_id1, related_id2],
        )

        assert len(event.related_event_ids) == 2
        assert related_id1 in event.related_event_ids
        assert related_id2 in event.related_event_ids

    def test_event_with_no_related_events(self):
        """PlayByPlayEventResponse should handle empty related events."""
        event = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            event_number=1,
            period=1,
            clock="12:00",
            event_type="PERIOD_START",
            event_subtype=None,
            player_id=None,
            player_name=None,
            team_id=uuid.uuid4(),
            team_name="Golden State Warriors",
            success=None,
            coord_x=None,
            coord_y=None,
            attributes={},
            description="Period 1 starts",
            related_event_ids=[],
        )

        assert event.related_event_ids == []

    def test_team_event_nullable_player(self):
        """PlayByPlayEventResponse should allow null player for team events."""
        event = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            event_number=50,
            period=2,
            clock="3:30",
            event_type="TIMEOUT",
            event_subtype=None,
            player_id=None,
            player_name=None,
            team_id=uuid.uuid4(),
            team_name="Boston Celtics",
            success=None,
            coord_x=None,
            coord_y=None,
            attributes={"timeout_type": "full"},
            description="Boston Celtics full timeout",
            related_event_ids=[],
        )

        assert event.player_id is None
        assert event.player_name is None
        assert event.event_type == "TIMEOUT"

    def test_missed_shot(self):
        """PlayByPlayEventResponse should handle missed shots."""
        event = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            event_number=30,
            period=1,
            clock="8:45",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=uuid.uuid4(),
            player_name="Anthony Davis",
            team_id=uuid.uuid4(),
            team_name="Los Angeles Lakers",
            success=False,
            coord_x=4.0,
            coord_y=5.0,
            attributes={"shot_type": "jump shot"},
            description="Davis misses 2PT jump shot",
            related_event_ids=[],
        )

        assert event.success is False
        assert event.event_subtype == "2PT"


class TestPlayByPlayResponse:
    """Tests for PlayByPlayResponse schema."""

    def test_response_structure(self):
        """PlayByPlayResponse should contain game_id, events, and total_events."""
        game_id = uuid.uuid4()

        event1 = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=game_id,
            event_number=1,
            period=1,
            clock="12:00",
            event_type="PERIOD_START",
            event_subtype=None,
            player_id=None,
            player_name=None,
            team_id=uuid.uuid4(),
            team_name="Home Team",
            success=None,
            coord_x=None,
            coord_y=None,
            attributes={},
            description="Period 1 starts",
            related_event_ids=[],
        )

        event2 = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=game_id,
            event_number=2,
            period=1,
            clock="11:45",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=uuid.uuid4(),
            player_name="Player One",
            team_id=uuid.uuid4(),
            team_name="Home Team",
            success=True,
            coord_x=3.0,
            coord_y=4.0,
            attributes={},
            description="Player One makes 2PT",
            related_event_ids=[],
        )

        response = PlayByPlayResponse(
            game_id=game_id,
            events=[event1, event2],
            total_events=425,
        )

        assert response.game_id == game_id
        assert len(response.events) == 2
        assert response.total_events == 425
        assert response.events[0].event_type == "PERIOD_START"
        assert response.events[1].event_type == "SHOT"

    def test_empty_events(self):
        """PlayByPlayResponse should handle empty events list."""
        response = PlayByPlayResponse(
            game_id=uuid.uuid4(),
            events=[],
            total_events=0,
        )

        assert response.events == []
        assert response.total_events == 0


class TestPlayByPlayFilter:
    """Tests for PlayByPlayFilter schema."""

    def test_all_fields_optional(self):
        """PlayByPlayFilter should allow empty data."""
        data = PlayByPlayFilter()
        assert data.period is None
        assert data.event_type is None
        assert data.player_id is None
        assert data.team_id is None

    def test_filter_by_period(self):
        """PlayByPlayFilter should accept period."""
        data = PlayByPlayFilter(period=4)
        assert data.period == 4

    def test_filter_by_event_type(self):
        """PlayByPlayFilter should accept event_type."""
        data = PlayByPlayFilter(event_type="SHOT")
        assert data.event_type == "SHOT"

    def test_filter_by_player_id(self):
        """PlayByPlayFilter should accept player_id."""
        player_id = uuid.uuid4()
        data = PlayByPlayFilter(player_id=player_id)
        assert data.player_id == player_id

    def test_filter_by_team_id(self):
        """PlayByPlayFilter should accept team_id."""
        team_id = uuid.uuid4()
        data = PlayByPlayFilter(team_id=team_id)
        assert data.team_id == team_id

    def test_combined_filters(self):
        """PlayByPlayFilter should accept multiple filters."""
        player_id = uuid.uuid4()
        team_id = uuid.uuid4()

        data = PlayByPlayFilter(
            period=4,
            event_type="SHOT",
            player_id=player_id,
            team_id=team_id,
        )

        assert data.period == 4
        assert data.event_type == "SHOT"
        assert data.player_id == player_id
        assert data.team_id == team_id

    def test_period_validation_positive(self):
        """PlayByPlayFilter should validate period is positive."""
        with pytest.raises(ValidationError) as exc_info:
            PlayByPlayFilter(period=0)
        assert "period" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            PlayByPlayFilter(period=-1)
        assert "period" in str(exc_info.value)

    def test_overtime_periods(self):
        """PlayByPlayFilter should accept overtime period numbers."""
        data = PlayByPlayFilter(period=5)  # First overtime
        assert data.period == 5

        data = PlayByPlayFilter(period=6)  # Second overtime
        assert data.period == 6


class TestEventTypeUsage:
    """Tests for using EventType enum with PlayByPlay schemas."""

    def test_event_type_enum_value(self):
        """PlayByPlayEventResponse should work with EventType enum values."""
        event = PlayByPlayEventResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            event_number=1,
            period=1,
            clock="12:00",
            event_type=EventType.SHOT.value,
            event_subtype=None,
            player_id=uuid.uuid4(),
            player_name="Player One",
            team_id=uuid.uuid4(),
            team_name="Team One",
            success=True,
            coord_x=5.0,
            coord_y=5.0,
            attributes={},
            description="Shot made",
            related_event_ids=[],
        )

        assert event.event_type == "SHOT"

    def test_filter_with_event_type_enum(self):
        """PlayByPlayFilter should work with EventType enum values."""
        data = PlayByPlayFilter(event_type=EventType.REBOUND.value)
        assert data.event_type == "REBOUND"


class TestImports:
    """Tests for module imports."""

    def test_import_from_play_by_play_module(self):
        """Should be able to import from play_by_play schema module."""
        from src.schemas.play_by_play import (
            PlayByPlayEventResponse,
            PlayByPlayFilter,
            PlayByPlayResponse,
        )

        assert PlayByPlayEventResponse is not None
        assert PlayByPlayResponse is not None
        assert PlayByPlayFilter is not None

    def test_import_from_schemas_package(self):
        """Should be able to import from schemas package."""
        from src.schemas import (
            PlayByPlayEventResponse,
            PlayByPlayFilter,
            PlayByPlayResponse,
        )

        assert PlayByPlayEventResponse is not None
        assert PlayByPlayResponse is not None
        assert PlayByPlayFilter is not None
