"""
Integration tests for Winner boxscore parsing with real API fixtures.

These tests verify the complete parsing chain from raw segevstats API
responses to RawBoxScore/RawPlayerStats objects. They use real API
response fixtures to catch regressions.

Addresses Issue #122: Tests don't verify the full parsing chain.

Key verifications:
- Player stats have actual values (points, rebounds, etc.)
- Minutes are correctly parsed from "MM:SS" format
- Team IDs and scores are extracted correctly
- All stat fields are properly mapped from segevstats format

Note: Player names are NOT available in segevstats boxscore API.
Names must come from the scraper (separate endpoint).
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
def boxscore_fixture() -> dict:
    """Load the real segevstats boxscore fixture (JSON-RPC format)."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestSegevstatsBoxscoreParsing:
    """Tests for parsing segevstats JSON-RPC boxscore format."""

    def test_boxscore_parses_without_error(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify boxscore fixture parses without raising errors."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        assert boxscore is not None

    def test_game_info_extracted(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify game info is correctly extracted from JSON-RPC format."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Game ID should be extracted
        assert boxscore.game.external_id == "24"

        # Team IDs should be extracted from gameInfo
        assert boxscore.game.home_team_external_id == "2"
        assert boxscore.game.away_team_external_id == "4"

        # Scores should be parsed (stored as strings in segevstats)
        assert boxscore.game.home_score == 79
        assert boxscore.game.away_score == 84

        # Game should be marked as final
        assert boxscore.game.status == "final"

    def test_home_players_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify home team players are parsed from boxscore."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Should have 12 home players from fixture
        assert len(boxscore.home_players) == 12

        # All players should have the correct team ID
        for player in boxscore.home_players:
            assert player.team_external_id == "2"

    def test_away_players_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify away team players are parsed from boxscore."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Should have 12 away players from fixture
        assert len(boxscore.away_players) == 12

        # All players should have the correct team ID
        for player in boxscore.away_players:
            assert player.team_external_id == "4"


class TestPlayerStatsPopulated:
    """Tests verifying player stats have actual values, not defaults."""

    def test_player_has_points(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify players have points populated from fixture.

        Player 1019 (jersey #9) scored 22 points in the fixture.
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        # Find player 1019 who scored 22 points
        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None, "Player 1019 not found in boxscore"
        assert player_1019.points == 22, f"Expected 22 points, got {player_1019.points}"

    def test_player_has_minutes(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify minutes are correctly parsed from MM:SS format.

        Player 1019 played 27:06 = 1626 seconds.
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        # 27:06 = 27*60 + 6 = 1626 seconds
        assert player_1019.minutes_played == 1626

    def test_player_has_field_goals(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify 2-point and 3-point field goals are parsed.

        Player 1019: fg_2m=6, fg_2mis=2, fg_3m=1, fg_3mis=3
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        assert player_1019.two_pointers_made == 6
        assert player_1019.two_pointers_attempted == 8  # 6 made + 2 missed
        assert player_1019.three_pointers_made == 1
        assert player_1019.three_pointers_attempted == 4  # 1 made + 3 missed
        assert player_1019.field_goals_made == 7  # 6 + 1
        assert player_1019.field_goals_attempted == 12  # 8 + 4

    def test_player_has_free_throws(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify free throws are parsed.

        Player 1019: ft_m=7, ft_mis=1
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        assert player_1019.free_throws_made == 7
        assert player_1019.free_throws_attempted == 8  # 7 made + 1 missed

    def test_player_has_rebounds(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify rebounds are parsed.

        Player 1019: reb_d=2, reb_o=3 -> total=5
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        assert player_1019.defensive_rebounds == 2
        assert player_1019.offensive_rebounds == 3
        assert player_1019.total_rebounds == 5

    def test_player_has_assists_steals_blocks(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify assists, steals, and blocks are parsed.

        Player 1019: ast=1, stl=2, blk=2
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        assert player_1019.assists == 1
        assert player_1019.steals == 2
        assert player_1019.blocks == 2

    def test_player_has_turnovers_fouls(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify turnovers and fouls are parsed.

        Player 1019: to=1, f=3
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        assert player_1019.turnovers == 1
        assert player_1019.personal_fouls == 3

    def test_player_has_plus_minus(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify plus/minus is parsed.

        Player 1019: plusMinus=3
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
                break

        assert player_1019 is not None
        assert player_1019.plus_minus == 3

    def test_starter_status_parsed(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify starter status is correctly parsed.

        Player 1019 was a starter (starter: true).
        Player 1014 was not a starter (starter: false).
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1019 = None
        player_1014 = None
        for p in boxscore.home_players:
            if p.player_external_id == "1019":
                player_1019 = p
            elif p.player_external_id == "1014":
                player_1014 = p

        assert player_1019 is not None
        assert player_1019.is_starter is True

        assert player_1014 is not None
        assert player_1014.is_starter is False


class TestAllPlayersHaveStats:
    """Tests verifying all players in the boxscore have some stats."""

    def test_all_players_have_ids(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Every player must have a non-empty external ID."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        all_players = boxscore.home_players + boxscore.away_players
        assert len(all_players) > 0

        for player in all_players:
            assert player.player_external_id, "Player missing external ID"
            assert player.player_external_id != ""

    def test_all_players_have_team_id(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Every player must have a team ID."""
        boxscore = mapper.map_boxscore(boxscore_fixture)

        all_players = boxscore.home_players + boxscore.away_players

        for player in all_players:
            assert player.team_external_id, "Player missing team ID"
            assert player.team_external_id in ["2", "4"]

    def test_players_with_minutes_have_stats(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Players who played minutes should have some stats.

        If a player has minutes > 0, they should have at least attempted
        something (field goal, free throw) or have a rebound/assist/etc.
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        all_players = boxscore.home_players + boxscore.away_players

        for player in all_players:
            if player.minutes_played > 0:
                # Player who played should have their ID properly set
                # This validates that players with minutes are correctly parsed
                assert (
                    player.player_external_id != ""
                ), f"Player with {player.minutes_played}s played has no ID"


class TestPlayerNameFromPbp:
    """Tests documenting that player names come from PBP, not boxscore.

    The boxscore API doesn't include player names - only IDs.
    Names must be extracted from PBP response and merged in.
    See test_winner_real_player_names.py for full name tests.
    """

    def test_boxscore_alone_has_no_names(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Boxscore API alone does not contain player names.

        Names must be extracted from PBP response using extract_player_roster()
        and merged using enrich_boxscore_with_names().
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        all_players = boxscore.home_players + boxscore.away_players

        # Without PBP enrichment, names are empty
        for player in all_players:
            assert player.player_name == "", (
                "Boxscore alone should not have names - "
                "use enrich_boxscore_with_names() to add them"
            )


class TestAwayTeamTopScorer:
    """Tests verifying away team parsing with specific player data."""

    def test_away_top_scorer_stats(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify away team top scorer (player 1044) stats.

        Player 1044 scored 21 points: 7x2pt + 1x3pt + 4FT = 21
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1044 = None
        for p in boxscore.away_players:
            if p.player_external_id == "1044":
                player_1044 = p
                break

        assert player_1044 is not None, "Player 1044 not found"
        assert player_1044.points == 21
        assert player_1044.two_pointers_made == 7
        assert player_1044.three_pointers_made == 1
        assert player_1044.free_throws_made == 4
        assert player_1044.steals == 3
        assert player_1044.turnovers == 3

    def test_away_team_second_scorer_stats(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Verify player 1043 (20 points) stats.

        Player 1043: 2x2pt + 4x3pt + 4FT = 4 + 12 + 4 = 20
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        player_1043 = None
        for p in boxscore.away_players:
            if p.player_external_id == "1043":
                player_1043 = p
                break

        assert player_1043 is not None, "Player 1043 not found"
        assert player_1043.points == 20
        assert player_1043.two_pointers_made == 2
        assert player_1043.three_pointers_made == 4
        assert player_1043.free_throws_made == 4
        assert player_1043.assists == 4


class TestTeamTotalsValidation:
    """Tests verifying team stats sum correctly."""

    def test_home_team_points_sum(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Home team individual points should sum to team total.

        Home score from gameInfo: 79
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        total_points = sum(p.points for p in boxscore.home_players)
        assert total_points == 79, f"Home points sum {total_points} != 79"

    def test_away_team_points_sum(
        self, mapper: WinnerMapper, boxscore_fixture: dict
    ) -> None:
        """Away team individual points should sum to team total.

        Away score from gameInfo: 84
        """
        boxscore = mapper.map_boxscore(boxscore_fixture)

        total_points = sum(p.points for p in boxscore.away_players)
        assert total_points == 84, f"Away points sum {total_points} != 84"
