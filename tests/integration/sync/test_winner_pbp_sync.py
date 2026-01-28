"""
Integration tests for Winner PBP sync using real fixtures.
"""

import json
from pathlib import Path

import pytest

from src.schemas.game import EventType
from src.sync.winner.mapper import WinnerMapper


@pytest.fixture
def mapper():
    return WinnerMapper()


@pytest.fixture
def real_pbp_fixture():
    """Load real segevstats PBP fixture."""
    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "winner" / "pbp.json"
    )
    with open(fixture_path) as f:
        return json.load(f)


class TestSyncPbpCreatesEvents:
    """Test PlayByPlayEvent records created from real fixture."""

    def test_pbp_events_created(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        assert len(events) > 0


class TestSyncPbpEventCount:
    """Test ~800 events per game."""

    def test_event_count_realistic(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        # Real games have 400-1000+ events
        assert 100 <= len(events) <= 2000


class TestSyncPbpShotsHaveSuccess:
    """Test shot events have success=True/False."""

    def test_all_shots_have_success_value(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        shots = [e for e in events if e.event_type == EventType.SHOT]

        assert len(shots) > 0, "Should have shot events"
        for shot in shots:
            assert (
                shot.success is not None
            ), f"Shot event {shot.event_number} missing success value"
            assert shot.success in (True, False)

    def test_free_throws_have_success_value(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        fts = [e for e in events if e.event_type == EventType.FREE_THROW]

        assert len(fts) > 0, "Should have free throw events"
        for ft in fts:
            assert ft.success is not None


class TestSyncPbpPlayersResolved:
    """Test player_id linked to Player record."""

    def test_events_have_player_external_id(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        # Most events should have player IDs (except timeouts, etc.)
        events_with_player = [e for e in events if e.player_external_id]
        assert len(events_with_player) > len(events) * 0.8

    def test_player_names_resolved(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        events_with_names = [e for e in events if e.player_name]
        # Most events with player IDs should have names
        assert len(events_with_names) > len(events) * 0.7


class TestSyncPbpIdempotent:
    """Test re-sync produces same results."""

    def test_mapping_is_deterministic(self, mapper, real_pbp_fixture):
        events1 = mapper.map_pbp_events(real_pbp_fixture)
        events2 = mapper.map_pbp_events(real_pbp_fixture)

        assert len(events1) == len(events2)
        for e1, e2 in zip(events1, events2, strict=True):
            assert e1.event_number == e2.event_number
            assert e1.event_type == e2.event_type
            assert e1.player_external_id == e2.player_external_id


class TestSyncPbpCoordinates:
    """Test coordinates stored for shot events."""

    def test_some_shots_have_coordinates(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        shots = [e for e in events if e.event_type == EventType.SHOT]
        shots_with_coords = [
            s for s in shots if s.coord_x is not None and s.coord_y is not None
        ]

        # Many (but not all) shots should have coordinates
        assert len(shots_with_coords) > len(shots) * 0.3


class TestSyncPbpEventTypes:
    """Test event types correctly categorized."""

    def test_has_all_major_event_types(self, mapper, real_pbp_fixture):
        events = mapper.map_pbp_events(real_pbp_fixture)
        event_types = {e.event_type for e in events}

        # Should have common basketball event types
        expected_types = {
            EventType.SHOT,
            EventType.FREE_THROW,
            EventType.REBOUND,
            EventType.FOUL,
        }
        for expected in expected_types:
            assert expected in event_types, f"Missing event type: {expected}"
