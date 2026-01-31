"""
Real API Response Parsing Tests for Winner League

Tests that verify the sync correctly parses actual API response structures.
Uses a captured API response fixture to prevent regressions when the API
format changes.

Fixture: tests/fixtures/winner/games_all_response.json

These tests address Issue #100: Winner League sync fails due to API
response structure changes.
"""

import json
from pathlib import Path

import pytest

from src.schemas.enums import GameStatus
from src.sync.winner.mapper import WinnerMapper

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def games_all_fixture():
    """Load the games_all API response fixture."""
    fixture_path = FIXTURES_DIR / "games_all_response.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mapper():
    """Create a WinnerMapper instance."""
    return WinnerMapper()


class TestApiResponseStructure:
    """Tests verifying the API response structure we need to handle."""

    def test_response_is_list_wrapped(self, games_all_fixture):
        """API returns a list containing a dict, not a direct dict."""
        assert isinstance(games_all_fixture, list)
        assert len(games_all_fixture) == 1
        assert isinstance(games_all_fixture[0], dict)

    def test_inner_dict_has_games_key(self, games_all_fixture):
        """The inner dict contains a 'games' list."""
        inner = games_all_fixture[0]
        assert "games" in inner
        assert isinstance(inner["games"], list)
        assert len(inner["games"]) > 0

    def test_game_object_structure(self, games_all_fixture):
        """Each game has the expected fields."""
        game = games_all_fixture[0]["games"][0]

        # Required fields for mapping
        assert "ExternalID" in game  # Game ID
        assert "team1" in game  # Home team ID
        assert "team2" in game  # Away team ID
        assert "team_name_eng_1" in game  # Home team name
        assert "team_name_eng_2" in game  # Away team name
        assert "game_date_txt" in game  # Game date
        assert "score_team1" in game  # Home score
        assert "score_team2" in game  # Away score


class TestUnwrapListResponse:
    """Tests for unwrapping the list-wrapped response."""

    def test_unwrap_list_to_dict(self, games_all_fixture):
        """Unwrapping list gives us the games dict."""
        # This is what _get_games_data() does
        data = games_all_fixture
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        assert isinstance(data, dict)
        assert "games" in data

    def test_unwrap_handles_direct_dict(self):
        """Unwrap logic handles direct dict (backwards compatibility)."""
        direct_dict = {"games": [{"id": 1}]}

        data = direct_dict
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        assert data == direct_dict


class TestMapperParsesRealGames:
    """Tests that WinnerMapper correctly parses real game data."""

    def test_map_game_extracts_external_id(self, mapper, games_all_fixture):
        """Mapper extracts external_id from ExternalID field."""
        game_data = games_all_fixture[0]["games"][0]
        raw_game = mapper.map_game(game_data)

        assert raw_game.external_id == game_data["ExternalID"]

    def test_map_game_extracts_team_ids(self, mapper, games_all_fixture):
        """Mapper extracts home and away team IDs."""
        game_data = games_all_fixture[0]["games"][0]
        raw_game = mapper.map_game(game_data)

        assert raw_game.home_team_external_id == str(game_data["team1"])
        assert raw_game.away_team_external_id == str(game_data["team2"])

    def test_map_game_extracts_scores(self, mapper, games_all_fixture):
        """Mapper extracts scores from score_team1/score_team2."""
        game_data = games_all_fixture[0]["games"][0]
        raw_game = mapper.map_game(game_data)

        assert raw_game.home_score == game_data["score_team1"]
        assert raw_game.away_score == game_data["score_team2"]

    def test_map_game_parses_date(self, mapper, games_all_fixture):
        """Mapper parses date from game_date_txt field."""
        game_data = games_all_fixture[0]["games"][0]
        raw_game = mapper.map_game(game_data)

        assert raw_game.game_date is not None

    def test_map_game_determines_status(self, mapper, games_all_fixture):
        """Mapper determines game status (final if has scores)."""
        game_data = games_all_fixture[0]["games"][0]
        raw_game = mapper.map_game(game_data)

        # Games with scores should be final
        if game_data["score_team1"] and game_data["score_team2"]:
            assert raw_game.status == GameStatus.FINAL

    def test_map_all_fixture_games(self, mapper, games_all_fixture):
        """All games in fixture can be mapped without errors."""
        inner = games_all_fixture[0]
        games = inner["games"]

        mapped_games = []
        for game_data in games:
            raw_game = mapper.map_game(game_data)
            mapped_games.append(raw_game)

        assert len(mapped_games) == len(games)
        for game in mapped_games:
            assert game.external_id is not None
            assert game.home_team_external_id is not None
            assert game.away_team_external_id is not None


class TestMapperExtractsTeams:
    """Tests that WinnerMapper correctly extracts teams from games."""

    def test_extract_teams_from_games(self, mapper, games_all_fixture):
        """Mapper extracts unique teams from games data."""
        inner = games_all_fixture[0]
        teams = mapper.extract_teams_from_games(inner)

        assert len(teams) > 0

    def test_extracted_teams_have_names(self, mapper, games_all_fixture):
        """Extracted teams have names from team_name_eng fields."""
        inner = games_all_fixture[0]
        teams = mapper.extract_teams_from_games(inner)

        for team in teams:
            assert team.name is not None
            assert len(team.name) > 0

    def test_extracted_teams_have_ids(self, mapper, games_all_fixture):
        """Extracted teams have external IDs from team1/team2 fields."""
        inner = games_all_fixture[0]
        teams = mapper.extract_teams_from_games(inner)

        for team in teams:
            assert team.external_id is not None

    def test_teams_are_unique(self, mapper, games_all_fixture):
        """No duplicate teams are extracted."""
        inner = games_all_fixture[0]
        teams = mapper.extract_teams_from_games(inner)

        team_ids = [t.external_id for t in teams]
        assert len(team_ids) == len(set(team_ids))


class TestMapperExtractsSeason:
    """Tests that WinnerMapper correctly extracts/infers season."""

    def test_infer_season_from_game_year(self, mapper, games_all_fixture):
        """Season can be inferred from game_year field."""
        inner = games_all_fixture[0]
        season = mapper.map_season("", inner)

        # Should produce a valid season ID like "2025-26"
        assert season.external_id is not None
        assert "-" in season.external_id

    def test_season_has_name(self, mapper, games_all_fixture):
        """Season has a display name."""
        inner = games_all_fixture[0]
        season = mapper.map_season("", inner)

        assert season.name is not None
        assert "Winner" in season.name or len(season.name) > 0
