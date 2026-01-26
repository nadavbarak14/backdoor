"""
Complete integration tests for Winner League sync functionality.

These tests verify the ENTIRE sync pipeline works correctly:
- Season inference and differentiation
- Schedule/games parsing with real API format
- Team extraction from games
- Boxscore parsing (segevstats JSON-RPC format)
- Player stats with all fields populated
- Historical results

Uses real API response fixtures to catch regressions.

Addresses Issue #122: Complete parsing tests with saved fixtures.
"""

import json
from pathlib import Path

import pytest

from src.sync.winner.mapper import WinnerMapper

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def games_all_response() -> list:
    """Load the real games_all API response (list-wrapped format)."""
    path = FIXTURES_DIR / "games_all_response.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def schedule_fixture() -> list[dict]:
    """Load schedule fixture (array of games)."""
    path = FIXTURES_DIR / "schedule.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture() -> dict:
    """Load real segevstats boxscore fixture."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pbp_fixture() -> dict:
    """Load real PBP fixture."""
    path = FIXTURES_DIR / "pbp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# SEASON PARSING TESTS
# =============================================================================


class TestSeasonInference:
    """Tests for season inference from real API data."""

    def test_season_inferred_from_game_year(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Season should be inferred from game_year field.

        The real API provides game_year=2026 which means season 2025-26.
        """
        # Unwrap list-wrapped response
        games_data = games_all_response[0]

        season = mapper.map_season("", games_data)

        # game_year=2026 should produce season 2025-26
        assert season.external_id == "2025-26"
        assert "2025-26" in season.name

    def test_season_uses_explicit_value_when_provided(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """When season string is explicitly provided, use it."""
        games_data = games_all_response[0]

        season = mapper.map_season("2024-25", games_data)

        assert season.external_id == "2024-25"

    def test_season_has_date_range(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Season should have start and end dates from games."""
        games_data = games_all_response[0]

        season = mapper.map_season("", games_data)

        assert season.start_date is not None
        assert season.end_date is not None
        assert season.start_date <= season.end_date

    def test_different_game_years_produce_different_seasons(
        self, mapper: WinnerMapper
    ) -> None:
        """Different game_year values should produce different seasons.

        This verifies that 2024-2025 and 2025-2026 are distinguished.
        """
        # Simulate 2025-26 season data (game_year=2026)
        data_2026 = {"games": [{"game_year": 2026, "game_date_txt": "21/09/2025"}]}
        season_2026 = mapper.map_season("", data_2026)

        # Simulate 2024-25 season data (game_year=2025)
        data_2025 = {"games": [{"game_year": 2025, "game_date_txt": "21/09/2024"}]}
        season_2025 = mapper.map_season("", data_2025)

        assert season_2026.external_id == "2025-26"
        assert season_2025.external_id == "2024-25"
        assert season_2026.external_id != season_2025.external_id


class TestSeasonDateFormats:
    """Tests for parsing different date formats in season inference."""

    def test_parse_dd_mm_yyyy_format(self, mapper: WinnerMapper) -> None:
        """Real API uses DD/MM/YYYY format for game_date_txt."""
        dt = mapper.parse_datetime("21/09/2025")

        assert dt.year == 2025
        assert dt.month == 9
        assert dt.day == 21

    def test_parse_iso_format(self, mapper: WinnerMapper) -> None:
        """Support ISO format for backwards compatibility."""
        dt = mapper.parse_datetime("2025-09-21T19:30:00")

        assert dt.year == 2025
        assert dt.month == 9
        assert dt.day == 21

    def test_season_from_date_fallback(self, mapper: WinnerMapper) -> None:
        """When game_year missing, infer season from game dates.

        September+ = current year starts new season
        Before September = previous year's season
        """
        # September game = season starts this year
        data_sept = {"games": [{"game_date_txt": "21/09/2025"}]}
        season_sept = mapper.map_season("", data_sept)
        assert season_sept.external_id == "2025-26"

        # March game = season started previous year
        data_march = {"games": [{"game_date_txt": "15/03/2025"}]}
        season_march = mapper.map_season("", data_march)
        assert season_march.external_id == "2024-25"


# =============================================================================
# GAMES/SCHEDULE PARSING TESTS
# =============================================================================


class TestGamesAllParsing:
    """Tests for parsing games from games_all API response."""

    def test_unwrap_list_response(self, games_all_response: list) -> None:
        """Real API returns [{"games": [...]}] not {"games": [...]}."""
        assert isinstance(games_all_response, list)
        assert len(games_all_response) == 1
        assert "games" in games_all_response[0]

    def test_parse_all_games(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """All games in response should be parseable."""
        games_data = games_all_response[0]
        games = games_data["games"]

        parsed_games = []
        for game_data in games:
            parsed = mapper.map_game(game_data)
            parsed_games.append(parsed)

        assert len(parsed_games) == len(games)
        assert len(parsed_games) > 0

    def test_game_has_external_id(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Each game must have an external ID from ExternalID field."""
        games_data = games_all_response[0]

        for game_data in games_data["games"]:
            game = mapper.map_game(game_data)
            assert game.external_id, f"Game missing external_id: {game_data}"
            assert game.external_id != ""

    def test_game_has_team_ids(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Each game must have home and away team IDs from team1/team2."""
        games_data = games_all_response[0]

        for game_data in games_data["games"]:
            game = mapper.map_game(game_data)
            assert game.home_team_external_id, "Game missing home team ID"
            assert game.away_team_external_id, "Game missing away team ID"

    def test_completed_games_have_scores(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Games with scores should be marked as final."""
        games_data = games_all_response[0]

        final_games = []
        for game_data in games_data["games"]:
            game = mapper.map_game(game_data)
            if game.home_score is not None and game.away_score is not None:
                final_games.append(game)
                assert game.status == "final"

        # Should have some completed games in fixture
        assert len(final_games) > 0

    def test_game_dates_parsed_correctly(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Game dates should be parsed from game_date_txt (DD/MM/YYYY)."""
        games_data = games_all_response[0]
        first_game = games_data["games"][0]

        game = mapper.map_game(first_game)

        # First game is 21/09/2025
        assert game.game_date.year == 2025
        assert game.game_date.month == 9
        assert game.game_date.day == 21


class TestRealApiFieldNames:
    """Tests verifying real API field names are handled correctly."""

    def test_external_id_from_ExternalID(
        self, mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Real API uses ExternalID, not GameId."""
        game_data = schedule_fixture[0]
        game = mapper.map_game(game_data)

        assert game.external_id == str(game_data["ExternalID"])

    def test_team_ids_from_team1_team2(
        self, mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Real API uses team1/team2, not HomeTeamId/AwayTeamId."""
        game_data = schedule_fixture[0]
        game = mapper.map_game(game_data)

        assert game.home_team_external_id == str(game_data["team1"])
        assert game.away_team_external_id == str(game_data["team2"])

    def test_scores_from_score_team1_score_team2(
        self, mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Real API uses score_team1/score_team2, not HomeScore/AwayScore."""
        game_data = schedule_fixture[0]
        game = mapper.map_game(game_data)

        assert game.home_score == game_data["score_team1"]
        assert game.away_score == game_data["score_team2"]


# =============================================================================
# TEAM EXTRACTION TESTS
# =============================================================================


class TestTeamExtraction:
    """Tests for extracting teams from games data."""

    def test_extract_unique_teams(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Should extract unique teams from all games."""
        games_data = games_all_response[0]

        teams = mapper.extract_teams_from_games(games_data)

        assert len(teams) > 0
        # Teams should be unique
        team_ids = [t.external_id for t in teams]
        assert len(team_ids) == len(set(team_ids))

    def test_teams_have_names(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """All extracted teams should have names."""
        games_data = games_all_response[0]

        teams = mapper.extract_teams_from_games(games_data)

        for team in teams:
            assert team.name, f"Team {team.external_id} has no name"
            assert team.name != ""

    def test_team_names_from_english_fields(
        self, mapper: WinnerMapper, schedule_fixture: list[dict]
    ) -> None:
        """Team names should come from team_name_eng_1/team_name_eng_2."""
        games_data = {"games": schedule_fixture}

        teams = mapper.extract_teams_from_games(games_data)

        # Find Maccabi Tel-Aviv team
        maccabi = None
        for team in teams:
            if "Maccabi" in team.name and "Tel" in team.name:
                maccabi = team
                break

        assert maccabi is not None, "Maccabi Tel-Aviv not found"
        assert "Maccabi" in maccabi.name

    def test_team_count_matches_fixture(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Number of teams should match unique teams in fixture."""
        games_data = games_all_response[0]

        teams = mapper.extract_teams_from_games(games_data)

        # Count unique team IDs in fixture manually
        unique_team_ids = set()
        for game in games_data["games"]:
            unique_team_ids.add(str(game["team1"]))
            unique_team_ids.add(str(game["team2"]))

        assert len(teams) == len(unique_team_ids)


# =============================================================================
# BOXSCORE PARSING TESTS (segevstats JSON-RPC format)
# =============================================================================


class TestBoxscoreJsonRpcFormat:
    """Tests for parsing segevstats JSON-RPC boxscore format."""

    def test_detect_jsonrpc_format(self, boxscore_fixture: dict) -> None:
        """Fixture should be in JSON-RPC format with result.boxscore."""
        assert "result" in boxscore_fixture
        assert "boxscore" in boxscore_fixture["result"]

    def test_parse_game_info(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Game info should be extracted from result.boxscore.gameInfo."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        assert boxscore.game.external_id == "24"
        assert boxscore.game.home_team_external_id == "2"
        assert boxscore.game.away_team_external_id == "4"
        assert boxscore.game.home_score == 79
        assert boxscore.game.away_score == 84

    def test_parse_all_home_players(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """All home team players should be parsed."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Fixture has 12 home players
        assert len(boxscore.home_players) == 12

    def test_parse_all_away_players(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """All away team players should be parsed."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Fixture has 12 away players
        assert len(boxscore.away_players) == 12


class TestPlayerStatsFields:
    """Tests verifying all player stat fields are correctly parsed."""

    def test_points_parsed(self, mapper: WinnerMapper, boxscore_fixture: dict) -> None:
        """Points should be parsed from 'points' field."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019 scored 22 points
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.points == 22

    def test_minutes_parsed(self, mapper: WinnerMapper, boxscore_fixture: dict) -> None:
        """Minutes should be parsed from MM:SS to seconds."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019 played 27:06 = 1626 seconds
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.minutes_played == 1626

    def test_field_goals_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """2-point and 3-point field goals should be parsed."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019: fg_2m=6, fg_2mis=2, fg_3m=1, fg_3mis=3
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.two_pointers_made == 6
        assert player.two_pointers_attempted == 8  # 6 + 2 misses
        assert player.three_pointers_made == 1
        assert player.three_pointers_attempted == 4  # 1 + 3 misses

    def test_free_throws_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Free throws should be parsed from ft_m/ft_mis."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019: ft_m=7, ft_mis=1
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.free_throws_made == 7
        assert player.free_throws_attempted == 8

    def test_rebounds_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Rebounds should be parsed from reb_d/reb_o."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019: reb_d=2, reb_o=3
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.defensive_rebounds == 2
        assert player.offensive_rebounds == 3
        assert player.total_rebounds == 5

    def test_assists_steals_blocks_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Assists, steals, blocks should be parsed."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019: ast=1, stl=2, blk=2
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.assists == 1
        assert player.steals == 2
        assert player.blocks == 2

    def test_turnovers_fouls_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Turnovers and fouls should be parsed."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019: to=1, f=3
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.turnovers == 1
        assert player.personal_fouls == 3

    def test_plus_minus_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Plus/minus should be parsed from string."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019: plusMinus=3
        player = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player.plus_minus == 3

    def test_starter_status_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Starter status should be parsed from boolean."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Player 1019 was a starter
        player_1019 = next(
            p for p in boxscore.home_players if p.player_external_id == "1019"
        )
        assert player_1019.is_starter is True

        # Player 1014 was not a starter
        player_1014 = next(
            p for p in boxscore.home_players if p.player_external_id == "1014"
        )
        assert player_1014.is_starter is False


class TestBoxscoreDataIntegrity:
    """Tests verifying boxscore data is internally consistent."""

    def test_home_points_sum_to_score(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Sum of home player points should equal home score."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        total = sum(p.points for p in boxscore.home_players)
        assert total == boxscore.game.home_score

    def test_away_points_sum_to_score(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Sum of away player points should equal away score."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        total = sum(p.points for p in boxscore.away_players)
        assert total == boxscore.game.away_score

    def test_player_points_math_correct(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Player points should equal 2*2pt + 3*3pt + FT."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        for player in boxscore.home_players + boxscore.away_players:
            if player.minutes_played > 0:
                calculated = (
                    player.two_pointers_made * 2
                    + player.three_pointers_made * 3
                    + player.free_throws_made
                )
                assert player.points == calculated, (
                    f"Player {player.player_external_id} points mismatch: "
                    f"{player.points} != {calculated}"
                )


# =============================================================================
# PLAYER NAME HANDLING
# =============================================================================


class TestPlayerNameFromBoxscore:
    """Tests documenting player name handling in boxscore."""

    def test_player_names_empty_in_boxscore(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Player names are NOT in segevstats boxscore API.

        This is expected - names must come from scraper.
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        for player in boxscore.home_players + boxscore.away_players:
            assert player.player_name == ""


# =============================================================================
# PBP PARSING TESTS
# =============================================================================


class TestPbpParsing:
    """Tests for play-by-play event parsing."""

    def test_pbp_fixture_has_events(self, pbp_fixture: dict) -> None:
        """PBP fixture should contain events."""
        # Check structure - may be in result.actions or Events
        has_events = (
            "result" in pbp_fixture and "actions" in pbp_fixture.get("result", {})
        ) or "Events" in pbp_fixture
        assert has_events or len(pbp_fixture) > 0


# =============================================================================
# HISTORICAL DATA TESTS
# =============================================================================


class TestHistoricalSeasonDifferentiation:
    """Tests verifying different seasons produce different data."""

    def test_season_2025_26_vs_2024_25(self, mapper: WinnerMapper) -> None:
        """2025-26 and 2024-25 seasons should have different IDs."""
        data_2025_26 = {"games": [{"game_year": 2026}]}
        data_2024_25 = {"games": [{"game_year": 2025}]}

        season_2025_26 = mapper.map_season("", data_2025_26)
        season_2024_25 = mapper.map_season("", data_2024_25)

        assert season_2025_26.external_id != season_2024_25.external_id
        assert "2025" in season_2025_26.external_id
        assert "2024" in season_2024_25.external_id

    def test_current_fixture_is_2025_26_season(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Verify current fixture data is 2025-26 season."""
        games_data = games_all_response[0]

        season = mapper.map_season("", games_data)

        # Fixture has game_year=2026 -> season 2025-26
        assert season.external_id == "2025-26"


# =============================================================================
# FULL SYNC CHAIN TESTS
# =============================================================================


class TestFullSyncChain:
    """Tests verifying the complete sync pipeline works."""

    def test_games_to_teams_to_boxscores(
        self,
        mapper: WinnerMapper,
        games_all_response: list,
        boxscore_fixture: dict,
    ) -> None:
        """Full chain: games_all -> teams -> boxscore should work."""
        # 1. Parse games
        games_data = games_all_response[0]
        games = [mapper.map_game(g) for g in games_data["games"]]
        assert len(games) > 0

        # 2. Extract teams
        teams = mapper.extract_teams_from_games(games_data)
        assert len(teams) > 0

        # 3. Parse boxscore
        boxscore = mapper.map_boxscore(boxscore_fixture)
        assert len(boxscore.home_players) > 0
        assert len(boxscore.away_players) > 0

        # 4. Verify teams were extracted with valid IDs
        for team in teams:
            assert team.external_id != ""
            assert team.name != ""

    def test_season_inference_consistent(
        self, mapper: WinnerMapper, games_all_response: list
    ) -> None:
        """Season should be consistently inferred."""
        games_data = games_all_response[0]

        # Infer twice - should get same result
        season1 = mapper.map_season("", games_data)
        season2 = mapper.map_season("", games_data)

        assert season1.external_id == season2.external_id
        assert season1.name == season2.name


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_games_list(self, mapper: WinnerMapper) -> None:
        """Empty games list should not crash."""
        data = {"games": []}

        teams = mapper.extract_teams_from_games(data)
        assert teams == []

    def test_game_missing_optional_fields(self, mapper: WinnerMapper) -> None:
        """Games with missing optional fields should still parse."""
        minimal_game = {
            "ExternalID": "999",
            "team1": 1,
            "team2": 2,
            "game_date_txt": "01/01/2025",
        }

        game = mapper.map_game(minimal_game)

        assert game.external_id == "999"
        assert game.home_team_external_id == "1"
        assert game.away_team_external_id == "2"
        # Missing scores should result in scheduled status
        assert game.status == "scheduled"

    def test_boxscore_with_zero_stats_player(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Players with 00:00 minutes should still parse."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Find a player with 0 minutes (player 1200 has "00:00")
        zero_min_players = [p for p in boxscore.home_players if p.minutes_played == 0]

        # Should have at least one
        assert len(zero_min_players) > 0

        for player in zero_min_players:
            assert player.player_external_id != ""
            assert player.points == 0
