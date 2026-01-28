"""
PBP Link Inference Tests

Tests for the centralized play-by-play event link inference logic.
Tests various scenarios where events should be linked:
1. ASSIST after made SHOT (same team, <2 sec)
2. REBOUND after missed SHOT (<3 sec)
3. STEAL after TURNOVER (diff team, <2 sec)
4. BLOCK with missed SHOT (same time)
5. FREE_THROW after FOUL
"""

from src.schemas.game import EventType
from src.sync.pbp import infer_pbp_links
from src.sync.types import RawPBPEvent


def create_event(
    event_num: int,
    period: int,
    clock: str,
    event_type: EventType,
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

    def test_assist_links_to_made_shot_same_team(self):
        """Assist should link to made shot from same team within 2 seconds."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=True),
            create_event(2, 1, "09:44", EventType.ASSIST, "100"),
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_assist_no_link_to_missed_shot(self):
        """Assist should not link to missed shot."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=False),
            create_event(2, 1, "09:44", EventType.ASSIST, "100"),
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_assist_no_link_to_different_team_shot(self):
        """Assist should not link to shot from different team."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=True),
            create_event(2, 1, "09:44", EventType.ASSIST, "101"),  # Different team
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_assist_no_link_if_too_much_time(self):
        """Assist should not link if more than 2 seconds apart."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=True),
            create_event(2, 1, "09:42", EventType.ASSIST, "100"),  # 3 seconds later
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestReboundToShotLink:
    """Tests for rebound to missed shot linking."""

    def test_rebound_links_to_missed_shot(self):
        """Rebound should link to missed shot within 3 seconds."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=False),
            create_event(2, 1, "09:43", EventType.REBOUND, "100"),  # 2 seconds later
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_defensive_rebound_links_to_missed_shot(self):
        """Defensive rebound should also link to missed shot."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=False),
            create_event(
                2, 1, "09:43", EventType.REBOUND, "101"
            ),  # Different team (defensive)
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_rebound_no_link_to_made_shot(self):
        """Rebound should not link to made shot."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=True),
            create_event(2, 1, "09:43", EventType.REBOUND, "100"),
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_rebound_no_link_if_too_much_time(self):
        """Rebound should not link if more than 3 seconds apart."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=False),
            create_event(2, 1, "09:41", EventType.REBOUND, "100"),  # 4 seconds later
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestStealToTurnoverLink:
    """Tests for steal to turnover linking."""

    def test_steal_links_to_turnover_different_team(self):
        """Steal should link to turnover from different team within 2 seconds."""
        events = [
            create_event(1, 1, "09:45", EventType.TURNOVER, "100"),
            create_event(2, 1, "09:44", EventType.STEAL, "101"),  # Different team
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_steal_no_link_to_same_team_turnover(self):
        """Steal should not link to turnover from same team."""
        events = [
            create_event(1, 1, "09:45", EventType.TURNOVER, "100"),
            create_event(2, 1, "09:44", EventType.STEAL, "100"),  # Same team
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None

    def test_steal_no_link_if_too_much_time(self):
        """Steal should not link if more than 2 seconds apart."""
        events = [
            create_event(1, 1, "09:45", EventType.TURNOVER, "100"),
            create_event(2, 1, "09:42", EventType.STEAL, "101"),  # 3 seconds later
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestBlockToShotLink:
    """Tests for block to missed shot linking."""

    def test_block_links_to_missed_shot_same_time(self):
        """Block should link to missed shot at same time."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=False),
            create_event(2, 1, "09:45", EventType.BLOCK, "101"),  # Same time
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_block_links_to_missed_shot_within_1_second(self):
        """Block should link to missed shot within 1 second."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=False),
            create_event(2, 1, "09:44", EventType.BLOCK, "101"),  # 1 second difference
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_block_no_link_to_made_shot(self):
        """Block should not link to made shot."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, "100", success=True),
            create_event(2, 1, "09:45", EventType.BLOCK, "101"),
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestFreeThrowToFoulLink:
    """Tests for free throw to foul linking."""

    def test_free_throw_links_to_foul(self):
        """Free throw should link to preceding foul."""
        events = [
            create_event(1, 1, "09:45", EventType.FOUL, "100"),
            create_event(2, 1, "09:45", EventType.FREE_THROW, "101"),  # Same time
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]

    def test_multiple_free_throws_link_to_same_foul(self):
        """Multiple free throws should link to same foul."""
        events = [
            create_event(1, 1, "09:45", EventType.FOUL, "100"),
            create_event(2, 1, "09:45", EventType.FREE_THROW, "101"),
            create_event(3, 1, "09:45", EventType.FREE_THROW, "101"),
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers == [1]
        assert linked[2].related_event_numbers == [1]

    def test_free_throw_no_link_if_too_much_time(self):
        """Free throw should not link to foul if too much time passed."""
        events = [
            create_event(1, 1, "09:45", EventType.FOUL, "100"),
            create_event(2, 1, "09:38", EventType.FREE_THROW, "101"),  # 7 seconds later
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestCrossPeriodLinking:
    """Tests for events across different periods."""

    def test_no_link_across_periods(self):
        """Events in different periods should not link."""
        events = [
            create_event(
                1, 1, "00:01", EventType.SHOT, "100", success=False
            ),  # End of Q1
            create_event(2, 2, "10:00", EventType.REBOUND, "100"),  # Start of Q2
        ]

        linked = infer_pbp_links(events)

        assert linked[1].related_event_numbers is None


class TestComplexScenarios:
    """Tests for complex multi-event scenarios."""

    def test_shot_assist_rebound_sequence(self):
        """Test a realistic shot-assist-rebound sequence."""
        events = [
            create_event(
                1, 1, "09:45", EventType.SHOT, "100", success=True
            ),  # Made shot
            create_event(2, 1, "09:44", EventType.ASSIST, "100"),  # Assist to shot
            # New possession
            create_event(
                3, 1, "09:30", EventType.SHOT, "101", success=False
            ),  # Missed shot
            create_event(4, 1, "09:28", EventType.REBOUND, "100"),  # Defensive rebound
        ]

        linked = infer_pbp_links(events)

        # Assist links to made shot
        assert linked[1].related_event_numbers == [1]
        # Rebound links to missed shot
        assert linked[3].related_event_numbers == [3]

    def test_turnover_steal_fastbreak(self):
        """Test turnover leading to steal and fastbreak."""
        events = [
            create_event(1, 1, "05:30", EventType.TURNOVER, "100"),
            create_event(2, 1, "05:29", EventType.STEAL, "101"),  # Steal by other team
            create_event(
                3, 1, "05:25", EventType.SHOT, "101", success=True
            ),  # Fastbreak
        ]

        linked = infer_pbp_links(events)

        # Steal links to turnover
        assert linked[1].related_event_numbers == [1]
        # Shot has no related events
        assert linked[2].related_event_numbers is None

    def test_foul_and_free_throws(self):
        """Test foul with multiple free throws."""
        events = [
            create_event(1, 1, "03:15", EventType.FOUL, "100"),
            create_event(2, 1, "03:15", EventType.FREE_THROW, "101", success=True),
            create_event(3, 1, "03:15", EventType.FREE_THROW, "101", success=False),
            create_event(4, 1, "03:13", EventType.REBOUND, "100"),  # Offensive rebound
        ]

        linked = infer_pbp_links(events)

        # Both FTs link to foul
        assert linked[1].related_event_numbers == [1]
        assert linked[2].related_event_numbers == [1]
        # Rebound after missed FT (no link - FT not a shot in our system)
        # This depends on implementation - might need adjustment


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_events_list(self):
        """Test with empty events list."""
        linked = infer_pbp_links([])
        assert linked == []

    def test_single_event(self):
        """Test with single event."""
        events = [create_event(1, 1, "10:00", EventType.SHOT, "100", success=True)]
        linked = infer_pbp_links(events)

        assert len(linked) == 1
        assert linked[0].related_event_numbers is None

    def test_no_team_id(self):
        """Test events without team ID."""
        events = [
            create_event(1, 1, "09:45", EventType.SHOT, None, success=True),
            create_event(2, 1, "09:44", EventType.ASSIST, None),
        ]

        # Should not crash, but shouldn't link
        linked = infer_pbp_links(events)
        assert len(linked) == 2

    def test_first_event_never_has_links(self):
        """First event should never have links."""
        events = [
            create_event(
                1, 1, "10:00", EventType.ASSIST, "100"
            ),  # Assist first - shouldn't link
        ]

        linked = infer_pbp_links(events)

        assert linked[0].related_event_numbers is None
