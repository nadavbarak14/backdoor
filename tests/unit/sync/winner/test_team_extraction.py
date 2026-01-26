"""
Unit tests for Winner League team extraction.

Tests the team extraction logic from games_all response, including:
- Extracting unique teams from games list
- Using English team names (not Hebrew)
- Team deduplication
- External ID handling

Usage:
    pytest tests/unit/sync/winner/test_team_extraction.py -v
"""

import pytest

from src.sync.types import RawTeam
from src.sync.winner.mapper import WinnerMapper


@pytest.fixture
def mapper():
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def games_data_with_english_names():
    """Sample games data with both Hebrew and English team names."""
    return {
        "games": [
            {
                "ExternalID": "24",
                "team1": 1109,
                "team2": 1112,
                "team_name_1": 'מכבי ת"א',
                "team_name_2": "הפועל י-ם",
                "team_name_eng_1": "Maccabi Tel-Aviv",
                "team_name_eng_2": "Hapoel Jerusalem",
                "score_team1": 79,
                "score_team2": 84,
                "game_date_txt": "21/09/2025",
            },
            {
                "ExternalID": "47",
                "team1": 1111,
                "team2": 1123,
                "team_name_1": "מכבי רמת גן",
                "team_name_2": "ראשון לציון",
                "team_name_eng_1": "Maccabi Ramat Gan",
                "team_name_eng_2": "M. Rishon",
                "score_team1": 84,
                "score_team2": 67,
                "game_date_txt": "12/10/2025",
            },
            # Same team (1112) appears again as team1
            {
                "ExternalID": "48",
                "team1": 1112,
                "team2": 1116,
                "team_name_1": "הפועל י-ם",
                "team_name_2": "נס ציונה",
                "team_name_eng_1": "Hapoel Jerusalem",
                "team_name_eng_2": "Ness Ziona",
                "score_team1": 79,
                "score_team2": 65,
                "game_date_txt": "12/10/2025",
            },
        ]
    }


@pytest.fixture
def games_data_legacy_format():
    """Sample games data using legacy field names (without _eng suffix)."""
    return {
        "games": [
            {
                "GameId": "12345",
                "HomeTeamId": "100",
                "AwayTeamId": "101",
                "HomeTeamName": "Maccabi Tel Aviv",
                "AwayTeamName": "Hapoel Jerusalem",
                "HomeScore": 85,
                "AwayScore": 78,
            },
            {
                "GameId": "12346",
                "HomeTeamId": "102",
                "AwayTeamId": "100",
                "HomeTeamName": "Hapoel Tel Aviv",
                "AwayTeamName": "Maccabi Tel Aviv",
                "HomeScore": 92,
                "AwayScore": 88,
            },
        ]
    }


class TestExtractTeamsFromGames:
    """Tests for extracting teams from games_all response."""

    def test_extract_teams_from_games(self, mapper, games_data_with_english_names):
        """Test unique teams are extracted from games list."""
        teams = mapper.extract_teams_from_games(games_data_with_english_names)

        # Should have 6 unique teams: 1109, 1111, 1112, 1116, 1123
        # Note: 1112 appears twice but should only be extracted once
        assert len(teams) == 5

        team_ids = {t.external_id for t in teams}
        assert team_ids == {"1109", "1111", "1112", "1116", "1123"}

    def test_extract_teams_uses_english_names(
        self, mapper, games_data_with_english_names
    ):
        """Test that team_name_eng_X is used instead of Hebrew names."""
        teams = mapper.extract_teams_from_games(games_data_with_english_names)

        team_dict = {t.external_id: t.name for t in teams}

        # Should use English names, not Hebrew
        assert team_dict["1109"] == "Maccabi Tel-Aviv"
        assert team_dict["1112"] == "Hapoel Jerusalem"
        assert team_dict["1111"] == "Maccabi Ramat Gan"
        assert team_dict["1123"] == "M. Rishon"
        assert team_dict["1116"] == "Ness Ziona"

        # Verify no Hebrew characters in any team name
        for team in teams:
            for char in team.name:
                # Hebrew characters are in range 0x0590-0x05FF
                assert not (
                    0x0590 <= ord(char) <= 0x05FF
                ), f"Found Hebrew character in team name: {team.name}"

    def test_team_deduplication(self, mapper, games_data_with_english_names):
        """Test that same team_id only creates one Team record."""
        teams = mapper.extract_teams_from_games(games_data_with_english_names)

        # Count how many times each team_id appears
        team_id_counts = {}
        for team in teams:
            team_id_counts[team.external_id] = (
                team_id_counts.get(team.external_id, 0) + 1
            )

        # All team IDs should appear exactly once
        for team_id, count in team_id_counts.items():
            assert count == 1, f"Team {team_id} appears {count} times, expected 1"

    def test_team_has_external_id(self, mapper, games_data_with_english_names):
        """Test all extracted teams have external_id set."""
        teams = mapper.extract_teams_from_games(games_data_with_english_names)

        for team in teams:
            assert team.external_id, f"Team {team.name} has empty external_id"
            assert isinstance(team.external_id, str)
            # External ID should be a non-empty string
            assert len(team.external_id) > 0

    def test_all_teams_are_raw_team_type(self, mapper, games_data_with_english_names):
        """Test all extracted teams are RawTeam instances."""
        teams = mapper.extract_teams_from_games(games_data_with_english_names)

        for team in teams:
            assert isinstance(team, RawTeam)

    def test_legacy_format_still_works(self, mapper, games_data_legacy_format):
        """Test extraction works with legacy field names."""
        teams = mapper.extract_teams_from_games(games_data_legacy_format)

        # Should have 3 unique teams: 100, 101, 102
        assert len(teams) == 3

        team_dict = {t.external_id: t.name for t in teams}
        assert team_dict["100"] == "Maccabi Tel Aviv"
        assert team_dict["101"] == "Hapoel Jerusalem"
        assert team_dict["102"] == "Hapoel Tel Aviv"

    def test_prefers_english_name_over_hebrew(self, mapper):
        """Test that English name is preferred when both are available."""
        games_data = {
            "games": [
                {
                    "ExternalID": "1",
                    "team1": 1001,
                    "team2": 1002,
                    # Hebrew names
                    "team_name_1": "מכבי",
                    "team_name_2": "הפועל",
                    # English names
                    "team_name_eng_1": "Maccabi",
                    "team_name_eng_2": "Hapoel",
                }
            ]
        }

        teams = mapper.extract_teams_from_games(games_data)
        team_dict = {t.external_id: t.name for t in teams}

        # Should use English, not Hebrew
        assert team_dict["1001"] == "Maccabi"
        assert team_dict["1002"] == "Hapoel"

    def test_falls_back_to_team_name_if_no_eng(self, mapper):
        """Test fallback to team_name_X if team_name_eng_X not available."""
        games_data = {
            "games": [
                {
                    "ExternalID": "1",
                    "team1": 1001,
                    "team2": 1002,
                    # Only non-English names available
                    "team_name_1": "Team One",
                    "team_name_2": "Team Two",
                }
            ]
        }

        teams = mapper.extract_teams_from_games(games_data)
        team_dict = {t.external_id: t.name for t in teams}

        assert team_dict["1001"] == "Team One"
        assert team_dict["1002"] == "Team Two"

    def test_empty_games_returns_empty_list(self, mapper):
        """Test empty games list returns empty teams list."""
        teams = mapper.extract_teams_from_games({"games": []})
        assert teams == []

    def test_handles_missing_games_key(self, mapper):
        """Test handles missing games key gracefully."""
        teams = mapper.extract_teams_from_games({})
        assert teams == []
