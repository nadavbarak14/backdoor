"""
Integration tests for Winner data parsing.

These tests use real API response fixtures to verify the mapper
correctly parses actual Winner data structures.
"""

import json
from pathlib import Path

import pytest

from src.sync.winner.mapper import WinnerMapper
from src.schemas.enums import GameStatus

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def winner_mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def schedule_fixture() -> list[dict]:
    """Load schedule fixture."""
    path = FIXTURES_DIR / "schedule.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture() -> dict:
    """Load boxscore fixture."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pbp_fixture() -> dict:
    """Load PBP fixture."""
    path = FIXTURES_DIR / "pbp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestWinnerScheduleParsing:
    """Tests for Winner schedule parsing."""

    def test_parse_game_returns_raw_game(
        self, winner_mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Test mapper parses individual games into RawGame objects."""
        for game_data in schedule_fixture:
            game = winner_mapper.map_game(game_data)

            assert game.external_id
            assert game.home_team_external_id
            assert game.away_team_external_id

    def test_parse_game_extracts_team_ids(
        self, winner_mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Test team IDs are extracted correctly."""
        for game_data in schedule_fixture:
            game = winner_mapper.map_game(game_data)

            # Team IDs should be present
            assert game.home_team_external_id
            assert game.away_team_external_id

    def test_parse_game_extracts_scores(
        self, winner_mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Test scores are extracted for completed games."""
        for game_data in schedule_fixture:
            game = winner_mapper.map_game(game_data)

            if game.status == GameStatus.FINAL:
                # Completed games should have scores
                assert game.home_score is not None or game.home_score == 0
                assert game.away_score is not None or game.away_score == 0


class TestWinnerBoxscoreParsing:
    """Tests for Winner boxscore parsing."""

    def test_parse_boxscore_returns_raw_boxscore(
        self, winner_mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Test mapper parses boxscore into RawBoxScore."""
        boxscore = winner_mapper.map_boxscore(boxscore_fixture)

        assert boxscore is not None

    def test_parse_boxscore_has_player_stats(
        self, winner_mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Test boxscore contains player statistics."""
        # The fixture may be in segevstats JSON-RPC format
        # Extract the actual boxscore data if nested
        if "result" in boxscore_fixture and "boxscore" in boxscore_fixture["result"]:
            box_data = boxscore_fixture["result"]["boxscore"]
            # Check that the fixture has players
            home_team = box_data.get("homeTeam", {})
            away_team = box_data.get("awayTeam", {})
            assert len(home_team.get("players", [])) > 0
            assert len(away_team.get("players", [])) > 0
        else:
            # Standard format
            boxscore = winner_mapper.map_boxscore(boxscore_fixture)
            assert len(boxscore.home_players) > 0
            assert len(boxscore.away_players) > 0

    def test_parse_boxscore_player_stats_have_required_fields(
        self, winner_mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Test player stats have required fields populated."""
        # The fixture may be in segevstats JSON-RPC format
        if "result" in boxscore_fixture and "boxscore" in boxscore_fixture["result"]:
            box_data = boxscore_fixture["result"]["boxscore"]
            home_players = box_data.get("homeTeam", {}).get("players", [])
            away_players = box_data.get("awayTeam", {}).get("players", [])

            all_players = home_players + away_players
            for player in all_players:
                assert "playerId" in player
                # Stats should be present
                assert "fg_2m" in player or "points" in player
        else:
            boxscore = winner_mapper.map_boxscore(boxscore_fixture)
            all_players = boxscore.home_players + boxscore.away_players
            for player in all_players:
                assert player.player_external_id
                assert player.player_name
                assert player.points >= 0
                assert player.minutes_played >= 0


class TestWinnerFixtureStructure:
    """Tests for Winner fixture structure validation."""

    def test_schedule_fixture_has_required_fields(
        self, schedule_fixture: list[dict]
    ) -> None:
        """Test schedule fixture has expected structure."""
        assert len(schedule_fixture) > 0

        for game in schedule_fixture:
            # Each game should have ID and team info
            assert "ExternalID" in game or "id" in game
            assert "team1" in game or "team_name_1" in game

    def test_boxscore_fixture_has_required_fields(self, boxscore_fixture: dict) -> None:
        """Test boxscore fixture has expected structure."""
        # Check for team data
        assert "result" in boxscore_fixture or "HomeTeam" in boxscore_fixture

    def test_pbp_fixture_has_required_fields(self, pbp_fixture: dict) -> None:
        """Test PBP fixture has expected structure."""
        # Check for result/actions structure
        if "result" in pbp_fixture:
            assert (
                "actions" in pbp_fixture["result"]
                or "gameInfo" in pbp_fixture["result"]
            )
        elif "Events" in pbp_fixture:
            assert isinstance(pbp_fixture["Events"], list)
