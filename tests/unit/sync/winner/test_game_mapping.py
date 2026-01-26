"""
Winner Game Mapping Tests

Tests for mapping game data from Winner League API response format
to normalized RawGame objects.

Tests cover:
- Date parsing from DD/MM/YYYY format
- Team ID extraction from team1/team2 fields
- Score extraction from score_team1/score_team2 fields
- Status determination based on scores
"""

from datetime import datetime

import pytest

from src.sync.types import RawGame
from src.sync.winner.mapper import WinnerMapper


@pytest.fixture
def mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def real_api_game_data() -> dict:
    """Sample game data from real Winner API response."""
    return {
        "id": 26586,
        "ExternalID": "24",
        "game_type": 34,
        "GN": 1,
        "team1": 1109,
        "team2": 1112,
        "team_name_1": 'מכבי ת"א',
        "team_name_2": "הפועל י-ם",
        "team_name_eng_1": "Maccabi Tel-Aviv",
        "team_name_eng_2": "Hapoel Jerusalem",
        "game_date_txt": "21/09/2025",
        "game_year": 2026,
        "score_team1": 79,
        "score_team2": 84,
        "game_time": "21:05",
        "liveChannel": "5PLUS",
        "isLive": 1,
    }


@pytest.fixture
def scheduled_game_data() -> dict:
    """Sample scheduled (not yet played) game data."""
    return {
        "id": 26700,
        "ExternalID": "100",
        "game_type": 5,
        "GN": 15,
        "team1": 1109,
        "team2": 1113,
        "team_name_1": 'מכבי ת"א',
        "team_name_2": "הפועל חולון",
        "team_name_eng_1": "Maccabi Tel-Aviv",
        "team_name_eng_2": "Hapoel Holon",
        "game_date_txt": "15/03/2026",
        "game_year": 2026,
        "score_team1": None,
        "score_team2": None,
        "game_time": "20:00",
        "liveChannel": "5SPORT",
        "isLive": 0,
    }


class TestMapGameParsesDateCorrectly:
    """Tests for date parsing from DD/MM/YYYY format."""

    def test_parses_dd_mm_yyyy_format(self, mapper: WinnerMapper) -> None:
        """Test DD/MM/YYYY format is correctly parsed."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": 79,
            "score_team2": 84,
        }
        game = mapper.map_game(game_data)

        assert game.game_date.year == 2025
        assert game.game_date.month == 9
        assert game.game_date.day == 21

    def test_parses_different_dates(self, mapper: WinnerMapper) -> None:
        """Test various date formats are parsed correctly."""
        test_cases = [
            ("01/01/2026", 2026, 1, 1),
            ("31/12/2025", 2025, 12, 31),
            ("15/06/2025", 2025, 6, 15),
            ("05/11/2025", 2025, 11, 5),
        ]

        for date_str, exp_year, exp_month, exp_day in test_cases:
            game_data = {
                "ExternalID": "1",
                "team1": 100,
                "team2": 101,
                "game_date_txt": date_str,
            }
            game = mapper.map_game(game_data)

            assert game.game_date.year == exp_year, f"Failed for {date_str}"
            assert game.game_date.month == exp_month, f"Failed for {date_str}"
            assert game.game_date.day == exp_day, f"Failed for {date_str}"

    def test_empty_date_returns_fallback(self, mapper: WinnerMapper) -> None:
        """Test empty date string returns fallback (now)."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "",
        }
        game = mapper.map_game(game_data)

        # Should be close to now
        now = datetime.now()
        assert game.game_date.year == now.year

    def test_real_api_data_date_parsing(
        self, mapper: WinnerMapper, real_api_game_data: dict
    ) -> None:
        """Test date parsing with real API response data."""
        game = mapper.map_game(real_api_game_data)

        # "21/09/2025" should parse to September 21, 2025
        assert game.game_date.year == 2025
        assert game.game_date.month == 9
        assert game.game_date.day == 21


class TestMapGameExtractsTeamIds:
    """Tests for team ID extraction from team1/team2 fields."""

    def test_extracts_team1_as_home(self, mapper: WinnerMapper) -> None:
        """Test team1 is extracted as home team."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
        }
        game = mapper.map_game(game_data)

        assert game.home_team_external_id == "1109"

    def test_extracts_team2_as_away(self, mapper: WinnerMapper) -> None:
        """Test team2 is extracted as away team."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
        }
        game = mapper.map_game(game_data)

        assert game.away_team_external_id == "1112"

    def test_converts_int_to_string(self, mapper: WinnerMapper) -> None:
        """Test integer team IDs are converted to strings."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,  # Integer
            "team2": 1112,  # Integer
            "game_date_txt": "21/09/2025",
        }
        game = mapper.map_game(game_data)

        assert isinstance(game.home_team_external_id, str)
        assert isinstance(game.away_team_external_id, str)

    def test_real_api_data_team_extraction(
        self, mapper: WinnerMapper, real_api_game_data: dict
    ) -> None:
        """Test team extraction with real API response data."""
        game = mapper.map_game(real_api_game_data)

        # team1=1109 (Maccabi Tel-Aviv), team2=1112 (Hapoel Jerusalem)
        assert game.home_team_external_id == "1109"
        assert game.away_team_external_id == "1112"

    def test_handles_missing_team_fields(self, mapper: WinnerMapper) -> None:
        """Test graceful handling of missing team fields."""
        game_data = {
            "ExternalID": "24",
            "game_date_txt": "21/09/2025",
            # No team1/team2 fields
        }
        game = mapper.map_game(game_data)

        # Should have empty strings rather than crashing
        assert game.home_team_external_id == ""
        assert game.away_team_external_id == ""


class TestMapGameExtractsScores:
    """Tests for score extraction from score_team1/score_team2 fields."""

    def test_extracts_score_team1_as_home_score(self, mapper: WinnerMapper) -> None:
        """Test score_team1 is extracted as home score."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": 79,
            "score_team2": 84,
        }
        game = mapper.map_game(game_data)

        assert game.home_score == 79

    def test_extracts_score_team2_as_away_score(self, mapper: WinnerMapper) -> None:
        """Test score_team2 is extracted as away score."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": 79,
            "score_team2": 84,
        }
        game = mapper.map_game(game_data)

        assert game.away_score == 84

    def test_handles_null_scores(self, mapper: WinnerMapper) -> None:
        """Test null scores for scheduled games."""
        game_data = {
            "ExternalID": "100",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": None,
            "score_team2": None,
        }
        game = mapper.map_game(game_data)

        assert game.home_score is None
        assert game.away_score is None

    def test_real_api_data_score_extraction(
        self, mapper: WinnerMapper, real_api_game_data: dict
    ) -> None:
        """Test score extraction with real API response data."""
        game = mapper.map_game(real_api_game_data)

        # score_team1=79, score_team2=84
        assert game.home_score == 79
        assert game.away_score == 84

    def test_handles_zero_scores(self, mapper: WinnerMapper) -> None:
        """Test zero scores are preserved (not treated as null)."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": 0,
            "score_team2": 80,
        }
        game = mapper.map_game(game_data)

        # 0 should be preserved, not converted to None
        assert game.home_score == 0
        assert game.away_score == 80


class TestMapGameDeterminesStatus:
    """Tests for status determination based on scores."""

    def test_final_when_scores_present(self, mapper: WinnerMapper) -> None:
        """Test status is 'final' when both scores are present."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": 79,
            "score_team2": 84,
            "isLive": 1,
        }
        game = mapper.map_game(game_data)

        assert game.status == "final"

    def test_scheduled_when_no_scores(self, mapper: WinnerMapper) -> None:
        """Test status is 'scheduled' when scores are null."""
        game_data = {
            "ExternalID": "100",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "15/03/2026",
            "score_team1": None,
            "score_team2": None,
            "isLive": 0,
        }
        game = mapper.map_game(game_data)

        assert game.status == "scheduled"

    def test_scheduled_when_scores_missing(self, mapper: WinnerMapper) -> None:
        """Test status is 'scheduled' when score fields are absent."""
        game_data = {
            "ExternalID": "100",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "15/03/2026",
            # No score fields
        }
        game = mapper.map_game(game_data)

        assert game.status == "scheduled"

    def test_real_api_completed_game_status(
        self, mapper: WinnerMapper, real_api_game_data: dict
    ) -> None:
        """Test completed game status with real API data."""
        game = mapper.map_game(real_api_game_data)

        # Has scores (79-84), so should be final
        assert game.status == "final"

    def test_real_api_scheduled_game_status(
        self, mapper: WinnerMapper, scheduled_game_data: dict
    ) -> None:
        """Test scheduled game status with real API data."""
        game = mapper.map_game(scheduled_game_data)

        # No scores, so should be scheduled
        assert game.status == "scheduled"


class TestMapGameExternalId:
    """Tests for external ID extraction."""

    def test_extracts_external_id(self, mapper: WinnerMapper) -> None:
        """Test ExternalID field is extracted."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
        }
        game = mapper.map_game(game_data)

        assert game.external_id == "24"

    def test_converts_external_id_to_string(self, mapper: WinnerMapper) -> None:
        """Test integer ExternalID is converted to string."""
        game_data = {
            "ExternalID": 24,  # Integer
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
        }
        game = mapper.map_game(game_data)

        assert game.external_id == "24"
        assert isinstance(game.external_id, str)


class TestMapGameReturnsRawGame:
    """Tests that map_game returns proper RawGame objects."""

    def test_returns_raw_game_type(self, mapper: WinnerMapper) -> None:
        """Test that RawGame type is returned."""
        game_data = {
            "ExternalID": "24",
            "team1": 1109,
            "team2": 1112,
            "game_date_txt": "21/09/2025",
            "score_team1": 79,
            "score_team2": 84,
        }
        game = mapper.map_game(game_data)

        assert isinstance(game, RawGame)

    def test_all_fields_populated(
        self, mapper: WinnerMapper, real_api_game_data: dict
    ) -> None:
        """Test all RawGame fields are populated from real API data."""
        game = mapper.map_game(real_api_game_data)

        assert game.external_id == "24"
        assert game.home_team_external_id == "1109"
        assert game.away_team_external_id == "1112"
        assert game.game_date.year == 2025
        assert game.game_date.month == 9
        assert game.game_date.day == 21
        assert game.home_score == 79
        assert game.away_score == 84
        assert game.status == "final"
