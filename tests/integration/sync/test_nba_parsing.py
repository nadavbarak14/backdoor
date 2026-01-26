"""
Integration tests for NBA data parsing.

These tests verify the NBA fixtures have the expected V3 API structure
and can be used for sync operations.
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "nba"


@pytest.fixture
def schedule_fixture() -> list[dict]:
    """Load schedule fixture."""
    path = FIXTURES_DIR / "schedule.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture() -> dict:
    """Load boxscore fixture (V3 format)."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pbp_fixture() -> dict:
    """Load PBP fixture (V3 format)."""
    path = FIXTURES_DIR / "pbp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestNBAFixtureStructure:
    """Tests for NBA fixture structure validation."""

    def test_schedule_fixture_has_required_fields(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule fixture has expected structure."""
        assert len(schedule_fixture) > 0

        for game in schedule_fixture:
            # LeagueGameFinder format
            assert "GAME_ID" in game
            assert "TEAM_ID" in game

    def test_schedule_fixture_has_game_info(self, schedule_fixture: list[dict]) -> None:
        """Test schedule has game info."""
        for game in schedule_fixture:
            # Should have team and game identifiers
            assert game.get("GAME_ID")
            assert game.get("TEAM_ID")
            # Should have points if game was played
            assert "PTS" in game

    def test_boxscore_fixture_has_v3_structure(self, boxscore_fixture: dict) -> None:
        """Test boxscore fixture has V3 nested structure."""
        # V3 format has boxScoreTraditional
        assert "boxScoreTraditional" in boxscore_fixture

        box = boxscore_fixture["boxScoreTraditional"]

        # Should have home and away teams
        assert "homeTeam" in box
        assert "awayTeam" in box

    def test_boxscore_fixture_has_player_stats(self, boxscore_fixture: dict) -> None:
        """Test boxscore has player statistics."""
        box = boxscore_fixture["boxScoreTraditional"]

        home_players = box["homeTeam"].get("players", [])
        away_players = box["awayTeam"].get("players", [])

        assert len(home_players) > 0
        assert len(away_players) > 0

        # Check V3 nested statistics structure
        for player in home_players:
            assert "personId" in player
            assert "statistics" in player

    def test_pbp_fixture_has_v3_structure(self, pbp_fixture: dict) -> None:
        """Test PBP fixture has V3 structure."""
        # V3 format has game.actions
        assert "game" in pbp_fixture

        game = pbp_fixture["game"]
        assert "actions" in game

    def test_pbp_fixture_has_events(self, pbp_fixture: dict) -> None:
        """Test PBP fixture has events."""
        actions = pbp_fixture["game"]["actions"]

        assert len(actions) > 0

        for action in actions:
            # Should have action type
            assert "actionType" in action
            # Should have period
            assert "period" in action
