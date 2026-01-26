"""
Integration tests for iBasketball data parsing.

These tests verify the iBasketball fixtures have the expected SportsPress
structure and can be used for sync operations.
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "ibasketball"


@pytest.fixture
def schedule_fixture() -> list[dict]:
    """Load schedule fixture."""
    path = FIXTURES_DIR / "schedule.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture() -> dict | None:
    """Load boxscore fixture if available."""
    for filename in ["boxscore.json", "event_single.json"]:
        path = FIXTURES_DIR / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return None


class TestIBasketballFixtureStructure:
    """Tests for iBasketball fixture structure validation."""

    def test_schedule_fixture_has_required_fields(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule fixture has expected SportsPress structure."""
        assert len(schedule_fixture) > 0

        for event in schedule_fixture:
            # SportsPress event format
            assert "id" in event
            assert "teams" in event or "home" in event

    def test_schedule_fixture_has_team_info(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule has team info."""
        for event in schedule_fixture:
            # Should have home/away team info
            if "home" in event:
                assert event["home"].get("team") or event.get("teams")
            else:
                assert "teams" in event

    def test_schedule_fixture_has_date(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule has date info."""
        for event in schedule_fixture:
            # Should have date
            assert "date" in event

    def test_schedule_fixture_has_status(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule has status."""
        for event in schedule_fixture:
            # Should have status (future, publish, etc.)
            assert "status" in event

    def test_boxscore_fixture_has_expected_structure(
        self, boxscore_fixture: dict | None
    ) -> None:
        """Test boxscore fixture has expected structure if available."""
        if boxscore_fixture is None:
            pytest.skip("No boxscore fixture available")

        # SportsPress event detail format
        assert "id" in boxscore_fixture
        # Should have results or performance data
        assert "results" in boxscore_fixture or "performance" in boxscore_fixture
