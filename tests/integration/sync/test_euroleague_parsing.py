"""
Integration tests for Euroleague data parsing.

These tests verify the Euroleague fixtures have the expected structure
and can be used for sync operations.
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "euroleague"


@pytest.fixture
def schedule_fixture() -> list[dict]:
    """Load schedule fixture."""
    path = FIXTURES_DIR / "schedule.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture() -> list[dict]:
    """Load boxscore fixture."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pbp_fixture() -> list[dict]:
    """Load PBP fixture."""
    path = FIXTURES_DIR / "pbp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestEuroleagueFixtureStructure:
    """Tests for Euroleague fixture structure validation."""

    def test_schedule_fixture_has_required_fields(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule fixture has expected structure."""
        assert len(schedule_fixture) > 0

        for game in schedule_fixture:
            # Each game should have game code and team info
            assert "gamecode" in game or "gameCode" in game or "game" in game
            assert "hometeam" in game or "homeTeam" in game or "homecode" in game

    def test_schedule_fixture_has_team_codes(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule has team codes."""
        for game in schedule_fixture:
            # Should have home and away team identifiers
            home_key = "homecode" if "homecode" in game else "homeTeam"
            away_key = "awaycode" if "awaycode" in game else "awayTeam"
            assert game.get(home_key) or game.get("hometeam")
            assert game.get(away_key) or game.get("awayteam")

    def test_schedule_fixture_has_played_status(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule has played status."""
        for game in schedule_fixture:
            # Should indicate if game was played
            assert "played" in game

    def test_boxscore_fixture_has_player_stats(
        self, boxscore_fixture: list[dict]
    ) -> None:
        """Test boxscore fixture contains player data."""
        assert len(boxscore_fixture) > 0

        # Boxscore should have player stats
        for player in boxscore_fixture:
            # Should have player identifier
            assert "Player" in player or "player" in player or "Player_ID" in player

    def test_pbp_fixture_has_events(
        self, pbp_fixture: list[dict]
    ) -> None:
        """Test PBP fixture has events."""
        assert len(pbp_fixture) > 0

        for event in pbp_fixture:
            # Should have event type or action info
            assert any(
                key in event
                for key in ["PLAYTYPE", "playType", "ACTION", "action", "type"]
            )
