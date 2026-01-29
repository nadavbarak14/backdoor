"""
Integration tests for Winner League season handling.

These tests verify that:
1. 2024-25 and 2025-26 seasons produce DIFFERENT data
2. Season inference works correctly from game_year
3. Historical data returns correct season
4. Game IDs are different between seasons
"""

import json
from pathlib import Path

import pytest

from src.sync.winner.mapper import WinnerMapper
from src.schemas.enums import GameStatus

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def season_2025_26_data() -> dict:
    """Load 2025-26 season fixture (game_year=2026)."""
    path = FIXTURES_DIR / "games_all_response.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data[0]  # Unwrap list


@pytest.fixture
def season_2024_25_data() -> dict:
    """Load 2024-25 season fixture (game_year=2025)."""
    path = FIXTURES_DIR / "games_2024_25.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data[0]  # Unwrap list


# =============================================================================
# SEASON DIFFERENTIATION TESTS
# =============================================================================


class TestSeasonDifferentiation:
    """Tests verifying 2024-25 and 2025-26 are properly differentiated."""

    def test_season_ids_are_different(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """2024-25 and 2025-26 should have different external IDs."""
        season_2024_25 = mapper.map_season("", season_2024_25_data)
        season_2025_26 = mapper.map_season("", season_2025_26_data)

        assert season_2024_25.external_id != season_2025_26.external_id
        assert season_2024_25.external_id == "2024-25"
        assert season_2025_26.external_id == "2025-26"

    def test_season_names_are_different(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Season names should reflect the correct year."""
        season_2024_25 = mapper.map_season("", season_2024_25_data)
        season_2025_26 = mapper.map_season("", season_2025_26_data)

        assert "2024-25" in season_2024_25.name
        assert "2025-26" in season_2025_26.name
        assert season_2024_25.name != season_2025_26.name

    def test_game_ids_are_different(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Games from different seasons should have different IDs."""
        games_2024_25 = [mapper.map_game(g) for g in season_2024_25_data["games"]]
        games_2025_26 = [mapper.map_game(g) for g in season_2025_26_data["games"]]

        ids_2024_25 = {g.external_id for g in games_2024_25}
        ids_2025_26 = {g.external_id for g in games_2025_26}

        # No overlap in game IDs
        overlap = ids_2024_25 & ids_2025_26
        assert len(overlap) == 0, f"Overlapping game IDs: {overlap}"

    def test_game_dates_are_different_years(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Games should have dates in different years."""
        games_2024_25 = [mapper.map_game(g) for g in season_2024_25_data["games"]]
        games_2025_26 = [mapper.map_game(g) for g in season_2025_26_data["games"]]

        # 2024-25 season games should be in 2024
        for game in games_2024_25:
            assert (
                game.game_date.year == 2024
            ), f"2024-25 game has wrong year: {game.game_date}"

        # 2025-26 season games should be in 2025
        for game in games_2025_26:
            assert (
                game.game_date.year == 2025
            ), f"2025-26 game has wrong year: {game.game_date}"


class TestGameYearMapping:
    """Tests verifying game_year field is correctly interpreted."""

    def test_game_year_2025_is_season_2024_25(self, mapper: WinnerMapper) -> None:
        """game_year=2025 means the season ending in 2025 (2024-25)."""
        data = {"games": [{"game_year": 2025, "game_date_txt": "15/01/2025"}]}

        season = mapper.map_season("", data)

        assert season.external_id == "2024-25"

    def test_game_year_2026_is_season_2025_26(self, mapper: WinnerMapper) -> None:
        """game_year=2026 means the season ending in 2026 (2025-26)."""
        data = {"games": [{"game_year": 2026, "game_date_txt": "15/01/2026"}]}

        season = mapper.map_season("", data)

        assert season.external_id == "2025-26"

    def test_game_year_takes_precedence(self, mapper: WinnerMapper) -> None:
        """game_year should take precedence over date inference."""
        # Date says January 2025 (would infer 2024-25)
        # But game_year says 2026 (2025-26 season)
        data = {"games": [{"game_year": 2026, "game_date_txt": "15/01/2025"}]}

        season = mapper.map_season("", data)

        # game_year wins
        assert season.external_id == "2025-26"


class TestSeasonDateRanges:
    """Tests verifying season date ranges are correct."""

    def test_2024_25_season_dates(
        self, mapper: WinnerMapper, season_2024_25_data: dict
    ) -> None:
        """2024-25 season should span Sep 2024 to ~May 2025."""
        season = mapper.map_season("", season_2024_25_data)

        # Season should start in September 2024
        assert season.start_date.year == 2024
        assert season.start_date.month >= 9

    def test_2025_26_season_dates(
        self, mapper: WinnerMapper, season_2025_26_data: dict
    ) -> None:
        """2025-26 season should span Sep 2025 to ~May 2026."""
        season = mapper.map_season("", season_2025_26_data)

        # Season should start in September 2025
        assert season.start_date.year == 2025
        assert season.start_date.month >= 9

    def test_seasons_do_not_overlap(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Season date ranges should not overlap."""
        season_2024_25 = mapper.map_season("", season_2024_25_data)
        season_2025_26 = mapper.map_season("", season_2025_26_data)

        # 2024-25 should end before 2025-26 starts
        assert season_2024_25.end_date < season_2025_26.start_date


# =============================================================================
# HISTORICAL DATA TESTS
# =============================================================================


class TestHistoricalSeasonData:
    """Tests verifying historical season data works correctly."""

    def test_can_load_2024_25_fixture(self, season_2024_25_data: dict) -> None:
        """2024-25 fixture should load and have games."""
        assert "games" in season_2024_25_data
        assert len(season_2024_25_data["games"]) > 0

    def test_can_load_2025_26_fixture(self, season_2025_26_data: dict) -> None:
        """2025-26 fixture should load and have games."""
        assert "games" in season_2025_26_data
        assert len(season_2025_26_data["games"]) > 0

    def test_2024_25_games_have_correct_structure(
        self, mapper: WinnerMapper, season_2024_25_data: dict
    ) -> None:
        """2024-25 games should parse with all required fields."""
        for game_data in season_2024_25_data["games"]:
            game = mapper.map_game(game_data)

            assert game.external_id != ""
            assert game.home_team_external_id != ""
            assert game.away_team_external_id != ""
            assert game.game_date is not None
            assert game.home_score is not None
            assert game.away_score is not None

    def test_2025_26_games_have_correct_structure(
        self, mapper: WinnerMapper, season_2025_26_data: dict
    ) -> None:
        """2025-26 games should parse with all required fields."""
        for game_data in season_2025_26_data["games"]:
            game = mapper.map_game(game_data)

            assert game.external_id != ""
            assert game.home_team_external_id != ""
            assert game.away_team_external_id != ""
            assert game.game_date is not None


class TestTeamsAcrossSeasons:
    """Tests verifying team data across seasons."""

    def test_teams_extracted_from_2024_25(
        self, mapper: WinnerMapper, season_2024_25_data: dict
    ) -> None:
        """Should extract teams from 2024-25 season."""
        teams = mapper.extract_teams_from_games(season_2024_25_data)

        assert len(teams) > 0
        for team in teams:
            assert team.external_id != ""
            assert team.name != ""

    def test_teams_extracted_from_2025_26(
        self, mapper: WinnerMapper, season_2025_26_data: dict
    ) -> None:
        """Should extract teams from 2025-26 season."""
        teams = mapper.extract_teams_from_games(season_2025_26_data)

        assert len(teams) > 0
        for team in teams:
            assert team.external_id != ""
            assert team.name != ""

    def test_common_teams_have_same_ids(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Teams appearing in both seasons should have consistent IDs.

        Maccabi Tel-Aviv (1109) should have same ID in both seasons.
        """
        teams_2024_25 = mapper.extract_teams_from_games(season_2024_25_data)
        teams_2025_26 = mapper.extract_teams_from_games(season_2025_26_data)

        teams_by_id_2024_25 = {t.external_id: t.name for t in teams_2024_25}
        teams_by_id_2025_26 = {t.external_id: t.name for t in teams_2025_26}

        # Find common team IDs
        common_ids = set(teams_by_id_2024_25.keys()) & set(teams_by_id_2025_26.keys())

        # Common teams should have same/similar names
        assert len(common_ids) > 0, "Should have some common teams between seasons"

        for team_id in common_ids:
            name_2024_25 = teams_by_id_2024_25[team_id]
            name_2025_26 = teams_by_id_2025_26[team_id]
            # Names should be identical or very similar
            assert name_2024_25 == name_2025_26, (
                f"Team {team_id} has different names: "
                f"'{name_2024_25}' vs '{name_2025_26}'"
            )


# =============================================================================
# SCORE DATA TESTS
# =============================================================================


class TestScoreData:
    """Tests verifying score data is correctly parsed."""

    def test_2024_25_games_have_scores(
        self, mapper: WinnerMapper, season_2024_25_data: dict
    ) -> None:
        """2024-25 games should have valid scores."""
        for game_data in season_2024_25_data["games"]:
            game = mapper.map_game(game_data)

            # Completed games should have scores
            if game.status == GameStatus.FINAL:
                assert game.home_score is not None
                assert game.away_score is not None
                assert game.home_score >= 0
                assert game.away_score >= 0

    def test_scores_are_reasonable(
        self, mapper: WinnerMapper, season_2024_25_data: dict
    ) -> None:
        """Scores should be in reasonable basketball range."""
        for game_data in season_2024_25_data["games"]:
            game = mapper.map_game(game_data)

            if game.home_score is not None:
                # Basketball scores typically 50-150
                assert 40 <= game.home_score <= 200
                assert 40 <= game.away_score <= 200


# =============================================================================
# SYNC WORKFLOW TESTS
# =============================================================================


class TestSyncWorkflow:
    """Tests simulating real sync workflow with multiple seasons."""

    def test_sync_both_seasons_independently(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Syncing both seasons should produce independent data."""
        # Sync 2024-25
        season_1 = mapper.map_season("", season_2024_25_data)
        games_1 = [mapper.map_game(g) for g in season_2024_25_data["games"]]

        # Sync 2025-26
        season_2 = mapper.map_season("", season_2025_26_data)
        games_2 = [mapper.map_game(g) for g in season_2025_26_data["games"]]

        # Verify independence
        assert season_1.external_id != season_2.external_id
        assert len(games_1) > 0
        assert len(games_2) > 0

        # Game IDs should not overlap
        game_ids_1 = {g.external_id for g in games_1}
        game_ids_2 = {g.external_id for g in games_2}
        assert len(game_ids_1 & game_ids_2) == 0

    def test_season_switch_produces_different_results(
        self,
        mapper: WinnerMapper,
        season_2024_25_data: dict,
        season_2025_26_data: dict,
    ) -> None:
        """Switching from 2024-25 to 2025-26 should give different games."""
        # First sync: 2024-25
        games_old = [mapper.map_game(g) for g in season_2024_25_data["games"]]
        old_ids = {g.external_id for g in games_old}

        # Second sync: 2025-26
        games_new = [mapper.map_game(g) for g in season_2025_26_data["games"]]
        new_ids = {g.external_id for g in games_new}

        # Should be completely different games
        assert old_ids != new_ids
        assert len(old_ids & new_ids) == 0
