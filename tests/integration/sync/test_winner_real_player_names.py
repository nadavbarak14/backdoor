"""
Integration tests for REAL Winner League player names.

These tests verify that REAL player names (not fake test data) are
extracted from the PBP response and can enrich boxscore data.

The PBP response contains full player rosters with names in:
result.gameInfo.homeTeam.players and result.gameInfo.awayTeam.players

This is the ONLY source of player names - boxscore API doesn't have them.
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
def pbp_fixture() -> dict:
    """Load real PBP fixture with player names."""
    path = FIXTURES_DIR / "pbp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture() -> dict:
    """Load real boxscore fixture (no player names)."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# PLAYER ROSTER EXTRACTION FROM PBP
# =============================================================================


class TestExtractPlayerRoster:
    """Tests for extracting player roster from PBP response."""

    def test_extracts_roster_from_pbp(
        self, mapper: WinnerMapper, pbp_fixture: dict
    ) -> None:
        """Should extract player roster from PBP data."""
        roster = mapper.extract_player_roster(pbp_fixture)

        assert roster is not None
        assert len(roster.players) > 0

    def test_roster_has_home_and_away_players(
        self, mapper: WinnerMapper, pbp_fixture: dict
    ) -> None:
        """Roster should include players from both teams."""
        roster = mapper.extract_player_roster(pbp_fixture)

        # PBP fixture has 17 home + 17 away = 34 players
        assert len(roster.players) >= 30

    def test_roman_sorkin_in_roster(
        self, mapper: WinnerMapper, pbp_fixture: dict
    ) -> None:
        """ROMAN SORKIN (id 1019) should be in roster."""
        roster = mapper.extract_player_roster(pbp_fixture)

        assert "1019" in roster.players
        first_name, last_name = roster.players["1019"]
        assert first_name == "ROMAN"
        assert last_name == "SORKIN"

    def test_jaylen_hoard_in_roster(
        self, mapper: WinnerMapper, pbp_fixture: dict
    ) -> None:
        """JAYLEN HOARD (id 1000) should be in roster."""
        roster = mapper.extract_player_roster(pbp_fixture)

        assert "1000" in roster.players
        first_name, last_name = roster.players["1000"]
        assert first_name == "JAYLEN"
        assert last_name == "HOARD"


class TestPlayerRosterGetFullName:
    """Tests for PlayerRoster.get_full_name method."""

    def test_get_full_name_for_known_player(
        self, mapper: WinnerMapper, pbp_fixture: dict
    ) -> None:
        """Should return full name for known player ID."""
        roster = mapper.extract_player_roster(pbp_fixture)

        name = roster.get_full_name("1019")
        assert name == "ROMAN SORKIN"

    def test_get_full_name_for_unknown_player(
        self, mapper: WinnerMapper, pbp_fixture: dict
    ) -> None:
        """Should return empty string for unknown player ID."""
        roster = mapper.extract_player_roster(pbp_fixture)

        name = roster.get_full_name("99999")
        assert name == ""


# =============================================================================
# MACCABI TEL AVIV PLAYERS (HOME TEAM)
# =============================================================================


class TestMaccabiTelAvivPlayers:
    """Tests verifying real Maccabi Tel Aviv players are in roster."""

    def test_has_jaylen_hoard(self, mapper: WinnerMapper, pbp_fixture: dict) -> None:
        """JAYLEN HOARD (#1) should be in Maccabi roster."""
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1000") == "JAYLEN HOARD"

    def test_has_jimmy_clark(self, mapper: WinnerMapper, pbp_fixture: dict) -> None:
        """JIMMY CLARK III (#2) should be in Maccabi roster."""
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1014") == "JIMMY CLARK III"

    def test_has_roman_sorkin(self, mapper: WinnerMapper, pbp_fixture: dict) -> None:
        """ROMAN SORKIN (#9) should be in Maccabi roster."""
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1019") == "ROMAN SORKIN"

    def test_has_oshae_brissett(self, mapper: WinnerMapper, pbp_fixture: dict) -> None:
        """OSHAE BRISSETT (#10) should be in Maccabi roster."""
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1020") == "OSHAE BRISSETT"

    def test_has_marcio_santos(self, mapper: WinnerMapper, pbp_fixture: dict) -> None:
        """MARCIO SANTOS (#3) should be in Maccabi roster."""
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1015") == "MARCIO SANTOS"


# =============================================================================
# BOXSCORE ENRICHMENT WITH NAMES
# =============================================================================


class TestEnrichBoxscoreWithNames:
    """Tests for enriching boxscore with player names from PBP."""

    def test_enrich_adds_names_to_boxscore(
        self, mapper: WinnerMapper, boxscore_fixture: dict, pbp_fixture: dict
    ) -> None:
        """Enriched boxscore should have player names."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)

        enriched = mapper.enrich_boxscore_with_names(boxscore, roster)

        # Find ROMAN SORKIN (1019) who scored 22 points
        roman = None
        for player in enriched.home_players:
            if player.player_external_id == "1019":
                roman = player
                break

        assert roman is not None
        assert roman.player_name == "ROMAN SORKIN"
        assert roman.points == 22

    def test_all_home_players_have_names(
        self, mapper: WinnerMapper, boxscore_fixture: dict, pbp_fixture: dict
    ) -> None:
        """All home players should have names after enrichment."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)

        enriched = mapper.enrich_boxscore_with_names(boxscore, roster)

        for player in enriched.home_players:
            assert (
                player.player_name != ""
            ), f"Player {player.player_external_id} has no name"

    def test_all_away_players_have_names(
        self, mapper: WinnerMapper, boxscore_fixture: dict, pbp_fixture: dict
    ) -> None:
        """All away players should have names after enrichment."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)

        enriched = mapper.enrich_boxscore_with_names(boxscore, roster)

        for player in enriched.away_players:
            assert (
                player.player_name != ""
            ), f"Player {player.player_external_id} has no name"

    def test_enrichment_preserves_stats(
        self, mapper: WinnerMapper, boxscore_fixture: dict, pbp_fixture: dict
    ) -> None:
        """Enrichment should preserve all player stats."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)

        enriched = mapper.enrich_boxscore_with_names(boxscore, roster)

        # Find ROMAN SORKIN and verify stats preserved
        roman = None
        for player in enriched.home_players:
            if player.player_external_id == "1019":
                roman = player
                break

        assert roman is not None
        assert roman.points == 22
        assert roman.two_pointers_made == 6
        assert roman.three_pointers_made == 1
        assert roman.free_throws_made == 7
        assert roman.minutes_played == 1626  # 27:06


class TestTopScorersHaveNames:
    """Tests verifying top scorers have correct names."""

    def test_roman_sorkin_22_points(
        self, mapper: WinnerMapper, boxscore_fixture: dict, pbp_fixture: dict
    ) -> None:
        """ROMAN SORKIN scored 22 points (home team top scorer)."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)
        enriched = mapper.enrich_boxscore_with_names(boxscore, roster)

        # Find player with 22 points
        top_scorer = max(enriched.home_players, key=lambda p: p.points)

        assert top_scorer.player_name == "ROMAN SORKIN"
        assert top_scorer.points == 22

    def test_away_team_has_real_names(
        self, mapper: WinnerMapper, boxscore_fixture: dict, pbp_fixture: dict
    ) -> None:
        """Away team top scorer should have a real name."""
        boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)
        enriched = mapper.enrich_boxscore_with_names(boxscore, roster)

        # Find away top scorer (should have 21 points)
        top_scorer = max(enriched.away_players, key=lambda p: p.points)

        assert top_scorer.points == 21
        assert top_scorer.player_name != ""
        # Name should be a real name, not empty or an ID
        assert not top_scorer.player_name.isdigit()
