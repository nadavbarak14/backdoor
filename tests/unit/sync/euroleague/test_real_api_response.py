"""
Real API Response Parsing Tests for Euroleague

Tests that verify the sync correctly parses actual API response structures.
Uses a captured API response fixture to prevent regressions when the API
format changes.

Fixture: tests/fixtures/euroleague/season_games_response.json

These tests address Issue #101: Euroleague sync fails due to duplicate
season prefix in game IDs.
"""

import json
from pathlib import Path

import pytest

from src.schemas.enums import GameStatus
from src.sync.euroleague.mapper import EuroleagueMapper

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "euroleague"


@pytest.fixture
def season_games_fixture():
    """Load the season_games API response fixture."""
    fixture_path = FIXTURES_DIR / "season_games_response.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mapper():
    """Create an EuroleagueMapper instance."""
    return EuroleagueMapper()


class TestApiResponseStructure:
    """Tests verifying the API response structure we need to handle."""

    def test_response_is_list(self, season_games_fixture):
        """API returns a list of games."""
        assert isinstance(season_games_fixture, list)
        assert len(season_games_fixture) > 0

    def test_game_has_both_gamecode_fields(self, season_games_fixture):
        """Each game has both gameCode (int) and gamecode (str) fields."""
        game = season_games_fixture[0]

        # Integer field
        assert "gameCode" in game
        assert isinstance(game["gameCode"], int)

        # String field (already formatted)
        assert "gamecode" in game
        assert isinstance(game["gamecode"], str)

    def test_gamecode_string_is_preformatted(self, season_games_fixture):
        """The gamecode string field is already formatted with season prefix."""
        game = season_games_fixture[0]

        # gamecode string should be like "E2025_1"
        gamecode_str = game["gamecode"]
        assert gamecode_str.startswith("E")
        assert "_" in gamecode_str

    def test_game_has_team_codes(self, season_games_fixture):
        """Games have team codes (e.g., 'IST', 'TEL')."""
        game = season_games_fixture[0]
        assert "homecode" in game or "hometeam" in game
        assert "awaycode" in game or "awayteam" in game


class TestGameIdGeneration:
    """Tests that game IDs are generated correctly without duplication."""

    def test_no_duplicate_season_prefix(self, mapper, season_games_fixture):
        """Game ID should not have duplicated season prefix like E2025_E2025_1."""
        game_data = season_games_fixture[0]
        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        # Should be E2025_1, NOT E2025_E2025_1
        assert raw_game.external_id == "E2025_1"
        assert "E2025_E2025" not in raw_game.external_id

    def test_uses_gameCode_integer(self, mapper):
        """Mapper prefers gameCode (int) over gamecode (str)."""
        game_data = {
            "gameCode": 42,
            "gamecode": "E2025_42",  # Would cause duplication if used
            "hometeam": "TEL",
            "awayteam": "IST",
            "date": "Oct 03, 2025",
            "homescore": 85,
            "awayscore": 78,
        }

        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        assert raw_game.external_id == "E2025_42"

    def test_falls_back_to_gamecode_string_when_no_int(self, mapper):
        """When gameCode (int) is missing, uses gamecode (str) directly."""
        game_data = {
            "gamecode": "E2025_99",  # Already formatted
            "hometeam": "TEL",
            "awayteam": "IST",
            "date": "Oct 03, 2025",
            "homescore": 85,
            "awayscore": 78,
        }

        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        # Should use the string directly since it's already formatted
        assert raw_game.external_id == "E2025_99"
        assert "E2025_E2025" not in raw_game.external_id

    def test_all_fixture_games_have_valid_ids(self, mapper, season_games_fixture):
        """All games in fixture produce valid IDs without duplication."""
        for game_data in season_games_fixture:
            raw_game = mapper.map_game(game_data, season=2025, competition="E")

            # ID should start with E2025_
            assert raw_game.external_id.startswith("E2025_")

            # Should NOT have duplicated prefix
            assert raw_game.external_id.count("E2025") == 1

            # Should have a game number after the underscore
            parts = raw_game.external_id.split("_")
            assert len(parts) == 2
            assert parts[1].isdigit()


class TestMapperParsesRealGames:
    """Tests that EuroleagueMapper correctly parses real game data."""

    def test_map_game_extracts_teams(self, mapper, season_games_fixture):
        """Mapper extracts home and away team codes."""
        game_data = season_games_fixture[0]
        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        # Should have team external IDs
        assert raw_game.home_team_external_id is not None
        assert raw_game.away_team_external_id is not None
        assert len(raw_game.home_team_external_id) > 0
        assert len(raw_game.away_team_external_id) > 0

    def test_map_game_extracts_scores(self, mapper, season_games_fixture):
        """Mapper extracts scores from completed games."""
        game_data = season_games_fixture[0]
        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        # Fixture games should have scores
        assert raw_game.home_score is not None
        assert raw_game.away_score is not None
        assert isinstance(raw_game.home_score, int)
        assert isinstance(raw_game.away_score, int)

    def test_map_game_parses_date(self, mapper, season_games_fixture):
        """Mapper parses date from the date field."""
        game_data = season_games_fixture[0]
        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        assert raw_game.game_date is not None

    def test_map_game_determines_status(self, mapper, season_games_fixture):
        """Mapper determines game status based on scores."""
        game_data = season_games_fixture[0]
        raw_game = mapper.map_game(game_data, season=2025, competition="E")

        # Games with scores should be final
        if game_data.get("homescore") and game_data.get("awayscore"):
            assert raw_game.status == GameStatus.FINAL

    def test_map_all_fixture_games(self, mapper, season_games_fixture):
        """All games in fixture can be mapped without errors."""
        mapped_games = []
        for game_data in season_games_fixture:
            raw_game = mapper.map_game(game_data, season=2025, competition="E")
            mapped_games.append(raw_game)

        assert len(mapped_games) == len(season_games_fixture)
        for game in mapped_games:
            assert game.external_id is not None
            assert game.home_team_external_id is not None
            assert game.away_team_external_id is not None


class TestEuroCupCompetition:
    """Tests for EuroCup (competition='U') game ID generation."""

    def test_eurocup_game_id_format(self, mapper):
        """EuroCup games should have 'U' prefix instead of 'E'."""
        game_data = {
            "gameCode": 5,
            "hometeam": "TEL",
            "awayteam": "IST",
            "date": "Oct 03, 2025",
            "homescore": 85,
            "awayscore": 78,
        }

        raw_game = mapper.map_game(game_data, season=2025, competition="U")

        assert raw_game.external_id == "U2025_5"
        assert raw_game.external_id.startswith("U")
