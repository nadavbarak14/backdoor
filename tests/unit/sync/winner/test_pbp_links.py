"""
Winner PBP Link Inference Tests

Tests for the play-by-play event link inference logic in WinnerMapper.
Tests various scenarios where events should be linked:
1. ASSIST after made SHOT (same team, <2 sec)
2. REBOUND after missed SHOT (<3 sec)
3. STEAL after TURNOVER (diff team, <2 sec)
4. BLOCK with missed SHOT (same time)
5. FREE_THROW after FOUL
"""

import pytest

from src.sync.types import RawPBPEvent
from src.sync.winner.mapper import WinnerMapper


@pytest.fixture
def mapper():
    """Create a WinnerMapper instance."""
    return WinnerMapper()


def create_event(
    event_num: int,
    period: int,
    clock: str,
    event_type: str,
    team_id: str | None = None,
    success: bool | None = None,
) -> RawPBPEvent:
    """Helper to create RawPBPEvent for testing."""
    return RawPBPEvent(
        event_number=event_num,
        period=period,
        clock=clock,
        event_type=event_type,
        team_external_id=team_id,
        success=success,
    )


class TestAssistToShotLink:
    """Tests for assist to made shot linking."""

    def test_assist_links_to_made_shot_same_team(self, mapper):
        """Assist should link to made shot from same team within 2 seconds."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=True),
            create_event(2, 1, "09:44", "assist", "100"),
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_assist_no_link_to_missed_shot(self, mapper):
        """Assist should not link to missed shot."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=False),
            create_event(2, 1, "09:44", "assist", "100"),
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_assist_no_link_to_different_team_shot(self, mapper):
        """Assist should not link to shot from different team."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=True),
            create_event(2, 1, "09:44", "assist", "101"),  # Different team
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_assist_no_link_if_too_much_time(self, mapper):
        """Assist should not link if more than 2 seconds apart."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=True),
            create_event(2, 1, "09:42", "assist", "100"),  # 3 seconds later
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestReboundToShotLink:
    """Tests for rebound to missed shot linking."""

    def test_rebound_links_to_missed_shot(self, mapper):
        """Rebound should link to missed shot within 3 seconds."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=False),
            create_event(2, 1, "09:43", "rebound", "100"),  # 2 seconds later
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_defensive_rebound_links_to_missed_shot(self, mapper):
        """Defensive rebound should also link to missed shot."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=False),
            create_event(2, 1, "09:43", "rebound", "101"),  # Different team (defensive)
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_rebound_no_link_to_made_shot(self, mapper):
        """Rebound should not link to made shot."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=True),
            create_event(2, 1, "09:43", "rebound", "100"),
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_rebound_no_link_if_too_much_time(self, mapper):
        """Rebound should not link if more than 3 seconds apart."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=False),
            create_event(2, 1, "09:41", "rebound", "100"),  # 4 seconds later
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestStealToTurnoverLink:
    """Tests for steal to turnover linking."""

    def test_steal_links_to_turnover_different_team(self, mapper):
        """Steal should link to turnover from different team within 2 seconds."""
        events = [
            create_event(1, 1, "09:45", "turnover", "100"),
            create_event(2, 1, "09:44", "steal", "101"),  # Different team
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_steal_no_link_to_same_team_turnover(self, mapper):
        """Steal should not link to turnover from same team."""
        events = [
            create_event(1, 1, "09:45", "turnover", "100"),
            create_event(2, 1, "09:44", "steal", "100"),  # Same team
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_steal_no_link_if_too_much_time(self, mapper):
        """Steal should not link if more than 2 seconds apart."""
        events = [
            create_event(1, 1, "09:45", "turnover", "100"),
            create_event(2, 1, "09:42", "steal", "101"),  # 3 seconds later
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestBlockToShotLink:
    """Tests for block to missed shot linking."""

    def test_block_links_to_missed_shot_same_time(self, mapper):
        """Block should link to missed shot at same time."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=False),
            create_event(2, 1, "09:45", "block", "101"),  # Same time
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_block_links_to_missed_shot_within_1_second(self, mapper):
        """Block should link to missed shot within 1 second."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=False),
            create_event(2, 1, "09:44", "block", "101"),  # 1 second difference
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_block_no_link_to_made_shot(self, mapper):
        """Block should not link to made shot."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=True),
            create_event(2, 1, "09:45", "block", "101"),
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestFreeThrowToFoulLink:
    """Tests for free throw to foul linking."""

    def test_free_throw_links_to_foul(self, mapper):
        """Free throw should link to preceding foul."""
        events = [
            create_event(1, 1, "09:45", "foul", "100"),
            create_event(2, 1, "09:45", "free_throw", "101"),  # Same time
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_multiple_free_throws_link_to_same_foul(self, mapper):
        """Multiple free throws should link to same foul."""
        events = [
            create_event(1, 1, "09:45", "foul", "100"),
            create_event(2, 1, "09:45", "free_throw", "101"),
            create_event(3, 1, "09:45", "free_throw", "101"),
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]
        assert linked[2].related_event_numbers == [1]

    def test_free_throw_no_link_if_too_much_time(self, mapper):
        """Free throw should not link to foul if too much time passed."""
        events = [
            create_event(1, 1, "09:45", "foul", "100"),
            create_event(2, 1, "09:38", "free_throw", "101"),  # 7 seconds later
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestCrossPeriodLinking:
    """Tests for events across different periods."""

    def test_no_link_across_periods(self, mapper):
        """Events in different periods should not link."""
        events = [
            create_event(1, 1, "00:01", "shot", "100", success=False),  # End of Q1
            create_event(2, 2, "10:00", "rebound", "100"),  # Start of Q2
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestComplexScenarios:
    """Tests for complex multi-event scenarios."""

    def test_shot_assist_rebound_sequence(self, mapper):
        """Test a realistic shot-assist-rebound sequence."""
        events = [
            create_event(1, 1, "09:45", "shot", "100", success=True),  # Made shot
            create_event(2, 1, "09:44", "assist", "100"),  # Assist to shot
            # New possession
            create_event(3, 1, "09:30", "shot", "101", success=False),  # Missed shot
            create_event(4, 1, "09:28", "rebound", "100"),  # Defensive rebound
        ]

        linked = mapper.infer_pbp_links(events)

        # Assist links to made shot
        assert linked[1].related_event_numbers == [1]
        # Rebound links to missed shot
        assert linked[3].related_event_numbers == [3]

    def test_turnover_steal_fastbreak(self, mapper):
        """Test turnover leading to steal and fastbreak."""
        events = [
            create_event(1, 1, "05:30", "turnover", "100"),
            create_event(2, 1, "05:29", "steal", "101"),  # Steal by other team
            create_event(3, 1, "05:25", "shot", "101", success=True),  # Fastbreak
        ]

        linked = mapper.infer_pbp_links(events)

        # Steal links to turnover
        assert linked[1].related_event_numbers == [1]
        # Shot has no related events
        assert linked[2].related_event_numbers is None

    def test_foul_and_free_throws(self, mapper):
        """Test foul with multiple free throws."""
        events = [
            create_event(1, 1, "03:15", "foul", "100"),
            create_event(2, 1, "03:15", "free_throw", "101", success=True),
            create_event(3, 1, "03:15", "free_throw", "101", success=False),
            create_event(4, 1, "03:13", "rebound", "100"),  # Offensive rebound
        ]

        linked = mapper.infer_pbp_links(events)

        # Both FTs link to foul
        assert linked[1].related_event_numbers == [1]
        assert linked[2].related_event_numbers == [1]
        # Rebound after missed FT (no link - FT not a shot in our system)
        # This depends on implementation - might need adjustment


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_events_list(self, mapper):
        """Test with empty events list."""
        linked = mapper.infer_pbp_links([])
        assert linked == []

    def test_single_event(self, mapper):
        """Test with single event."""
        events = [create_event(1, 1, "10:00", "shot", "100", success=True)]
        linked = mapper.infer_pbp_links(events)

        assert len(linked) == 1
        assert linked[0].related_event_numbers is None

    def test_no_team_id(self, mapper):
        """Test events without team ID."""
        events = [
            create_event(1, 1, "09:45", "shot", None, success=True),
            create_event(2, 1, "09:44", "assist", None),
        ]

        # Should not crash, but shouldn't link
        linked = mapper.infer_pbp_links(events)
        assert len(linked) == 2

    def test_first_event_never_has_links(self, mapper):
        """First event should never have links."""
        events = [
            create_event(
                1, 1, "10:00", "assist", "100"
            ),  # Assist first - shouldn't link
        ]

        linked = mapper.infer_pbp_links(events)

        assert linked[0].related_event_numbers is None
