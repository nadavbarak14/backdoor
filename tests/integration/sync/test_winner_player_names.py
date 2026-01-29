"""
Integration tests for Winner League player name extraction.

These tests verify that player names are correctly extracted from
scraper fixtures (HTML pages), since the boxscore API only provides IDs.

Player names come from:
1. Team roster pages - lists players with IDs and names
2. Player profile pages - individual player details
"""

from pathlib import Path

from src.sync.winner.scraper import WinnerScraper
from src.schemas.enums import Position

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


class TestPlayerNameExtraction:
    """Tests verifying player names are extracted from HTML fixtures."""

    def test_player_name_from_profile(self, test_db) -> None:
        """Player name should be extracted from profile HTML."""
        with open(FIXTURES_DIR / "player.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "1001")

        # Name should be "John Smith" from fixture
        assert profile.name == "John Smith"
        assert profile.name != ""
        assert profile.name != "1001"  # Not the ID

    def test_player_name_not_empty(self, test_db) -> None:
        """Player name should never be empty string."""
        with open(FIXTURES_DIR / "player.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "1001")

        assert profile.name is not None
        assert len(profile.name) > 0

    def test_player_has_team_info(self, test_db) -> None:
        """Player profile should include team information."""
        with open(FIXTURES_DIR / "player.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "1001")

        assert profile.team_name == "Maccabi Tel Aviv"
        assert profile.jersey_number == "5"
        assert profile.position == "Guard"

    def test_player_has_physical_info(self, test_db) -> None:
        """Player profile should include physical attributes."""
        with open(FIXTURES_DIR / "player.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "1001")

        assert profile.height_cm == 195
        assert profile.nationality == "USA"


class TestRosterNameExtraction:
    """Tests verifying player names are extracted from team roster."""

    def test_roster_has_player_names(self, test_db) -> None:
        """Team roster should contain player names."""
        with open(FIXTURES_DIR / "team.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        roster = scraper._parse_team_roster(html, "100")

        # Should have 5 players from fixture
        assert len(roster.players) == 5

        # All players should have names
        for player in roster.players:
            assert player.name is not None
            assert player.name != ""
            assert player.player_id != player.name  # Name is not the ID

    def test_roster_player_names_correct(self, test_db) -> None:
        """Roster should have correct player names from fixture."""
        with open(FIXTURES_DIR / "team.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        roster = scraper._parse_team_roster(html, "100")

        # Build name lookup
        names_by_id = {p.player_id: p.name for p in roster.players}

        # Verify expected names from fixture
        assert names_by_id["1001"] == "John Smith"
        assert names_by_id["1002"] == "David Cohen"
        assert names_by_id["1003"] == "Michael Brown"
        assert names_by_id["1004"] == "James Wilson"
        assert names_by_id["1005"] == "Robert Taylor"

    def test_roster_player_ids_linked(self, test_db) -> None:
        """Player IDs should be extracted from href links."""
        with open(FIXTURES_DIR / "team.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        roster = scraper._parse_team_roster(html, "100")

        player_ids = [p.player_id for p in roster.players]

        assert "1001" in player_ids
        assert "1002" in player_ids
        assert "1003" in player_ids
        assert "1004" in player_ids
        assert "1005" in player_ids

    def test_roster_has_jersey_numbers(self, test_db) -> None:
        """Roster should include jersey numbers."""
        with open(FIXTURES_DIR / "team.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        roster = scraper._parse_team_roster(html, "100")

        # John Smith wears #5
        john = next(p for p in roster.players if p.player_id == "1001")
        assert john.jersey_number == "5"

        # David Cohen wears #10
        david = next(p for p in roster.players if p.player_id == "1002")
        assert david.jersey_number == "10"

    def test_roster_has_positions(self, test_db) -> None:
        """Roster should include player positions."""
        with open(FIXTURES_DIR / "team.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        roster = scraper._parse_team_roster(html, "100")

        # John Smith is Guard
        john = next(p for p in roster.players if p.player_id == "1001")
        assert john.position == "G"  # Normalized abbreviation

        # Michael Brown is Center
        michael = next(p for p in roster.players if p.player_id == "1003")
        assert michael.position == "C"  # Normalized abbreviation


class TestPlayerNameMapping:
    """Tests verifying player names are mapped to RawPlayerInfo."""

    def test_map_player_info_has_names(self, test_db) -> None:
        """Mapped player info should have first and last name."""
        from src.sync.winner.mapper import WinnerMapper

        with open(FIXTURES_DIR / "player.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "1001")

        mapper = WinnerMapper()
        info = mapper.map_player_info(profile)

        # Should split "John Smith" into first/last
        assert info.first_name == "John"
        assert info.last_name == "Smith"

    def test_map_player_info_preserves_attributes(self, test_db) -> None:
        """Mapped player info should preserve all attributes."""
        from src.sync.winner.mapper import WinnerMapper

        with open(FIXTURES_DIR / "player.html") as f:
            html = f.read()

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "1001")

        mapper = WinnerMapper()
        info = mapper.map_player_info(profile)

        assert info.external_id == "1001"
        assert info.height_cm == 195
        assert info.positions == [Position.GUARD]
