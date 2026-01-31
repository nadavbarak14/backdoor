"""
Integration tests for Winner League player bio sync.

Tests the complete flow from HTML scraping to RawPlayerInfo creation,
ensuring height, birthdate, and position are properly extracted.
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from src.schemas.enums import Position
from src.sync.winner.mapper import WinnerMapper
from src.sync.winner.scraper import PlayerProfile, RosterPlayer, WinnerScraper

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def winner_mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def player_profile_modern_html() -> str:
    """Load modern format player profile fixture."""
    path = FIXTURES_DIR / "player_profile_modern.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def player_profile_hebrew_html() -> str:
    """Load Hebrew player profile fixture."""
    path = FIXTURES_DIR / "player_profile_hebrew.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def player_profile_table_html() -> str:
    """Load table-based player profile fixture."""
    path = FIXTURES_DIR / "player_with_birthdate.html"
    return path.read_text(encoding="utf-8")


class TestScraperPlayerProfileParsing:
    """Tests for scraper player profile HTML parsing."""

    def test_parse_modern_format_extracts_height(
        self, player_profile_modern_html: str
    ) -> None:
        """Test parsing height from modern div.p_info format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_modern_html, "1001")

        # Height "2.08" should be converted to 208 cm
        assert profile.height_cm == 208

    def test_parse_modern_format_extracts_birthdate(
        self, player_profile_modern_html: str
    ) -> None:
        """Test parsing birth date from modern format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_modern_html, "1001")

        assert profile.birth_date is not None
        assert profile.birth_date.year == 1998
        assert profile.birth_date.month == 3
        assert profile.birth_date.day == 15

    def test_parse_modern_format_extracts_position(
        self, player_profile_modern_html: str
    ) -> None:
        """Test parsing position from modern format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_modern_html, "1001")

        assert profile.position == "Center"

    def test_parse_modern_format_extracts_name(
        self, player_profile_modern_html: str
    ) -> None:
        """Test name extraction from title in modern format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_modern_html, "1001")

        assert profile.name == "Roman Sorkin"

    def test_parse_modern_format_extracts_team_name(
        self, player_profile_modern_html: str
    ) -> None:
        """Test team name extraction from link in modern format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_modern_html, "1001")

        assert profile.team_name == "Maccabi Tel Aviv"

    def test_parse_hebrew_format_extracts_height(
        self, player_profile_hebrew_html: str
    ) -> None:
        """Test parsing height from Hebrew format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_hebrew_html, "1002")

        # Height "1.88" should be converted to 188 cm
        assert profile.height_cm == 188

    def test_parse_hebrew_format_extracts_birthdate(
        self, player_profile_hebrew_html: str
    ) -> None:
        """Test parsing birth date from Hebrew format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_hebrew_html, "1002")

        assert profile.birth_date is not None
        assert profile.birth_date.year == 1995
        assert profile.birth_date.month == 8
        assert profile.birth_date.day == 22

    def test_parse_hebrew_format_extracts_position(
        self, player_profile_hebrew_html: str
    ) -> None:
        """Test parsing position from Hebrew labels."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_hebrew_html, "1002")

        # Hebrew "גארד" should be extracted
        assert profile.position == "גארד"

    def test_parse_table_format_extracts_height(
        self, player_profile_table_html: str
    ) -> None:
        """Test parsing height from table format (legacy)."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_table_html, "1003")

        # Height "195 cm" should be converted to 195
        assert profile.height_cm == 195

    def test_parse_table_format_extracts_birthdate(
        self, player_profile_table_html: str
    ) -> None:
        """Test parsing birth date from table format."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_table_html, "1003")

        assert profile.birth_date is not None
        assert profile.birth_date.year == 1995
        assert profile.birth_date.month == 5
        assert profile.birth_date.day == 15


class TestMapperPlayerInfo:
    """Tests for mapper player info conversion."""

    def test_map_player_info_converts_height(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test height is preserved in RawPlayerInfo."""
        profile = PlayerProfile(
            player_id="1001",
            name="Roman Sorkin",
            height_cm=208,
            position="Center",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.height_cm == 208

    def test_map_player_info_converts_birthdate(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test birth date is converted to date type."""
        profile = PlayerProfile(
            player_id="1001",
            name="Roman Sorkin",
            birth_date=datetime(1998, 3, 15),
        )

        info = winner_mapper.map_player_info(profile)

        assert info.birth_date == date(1998, 3, 15)

    def test_map_player_info_normalizes_position(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test position is normalized to Position enum."""
        profile = PlayerProfile(
            player_id="1001",
            name="Roman Sorkin",
            position="Center",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.positions == [Position.CENTER]

    def test_map_player_info_normalizes_guard_position(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test Guard position normalization."""
        profile = PlayerProfile(
            player_id="1001",
            name="Test Player",
            position="Guard",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.positions == [Position.GUARD]

    def test_map_player_info_normalizes_hebrew_position(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test Hebrew position normalization."""
        profile = PlayerProfile(
            player_id="1001",
            name="Test Player",
            position="גארד",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.positions == [Position.GUARD]

    def test_map_player_info_splits_name(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test name is split into first and last name."""
        profile = PlayerProfile(
            player_id="1001",
            name="Roman Sorkin",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.first_name == "Roman"
        assert info.last_name == "Sorkin"

    def test_map_player_info_handles_multi_word_last_name(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test multi-word last names are handled correctly."""
        profile = PlayerProfile(
            player_id="1001",
            name="John De La Cruz",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.first_name == "John"
        assert info.last_name == "De La Cruz"

    def test_map_player_info_handles_empty_position(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test empty position results in empty list."""
        profile = PlayerProfile(
            player_id="1001",
            name="Test Player",
            position=None,
        )

        info = winner_mapper.map_player_info(profile)

        assert info.positions == []


class TestMapperRosterPlayerInfo:
    """Tests for mapper roster player info conversion."""

    def test_map_roster_player_info_basic(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test basic roster player mapping."""
        player = RosterPlayer(
            player_id="1001",
            name="John Smith",
            jersey_number="23",
            position="G",
        )

        info = winner_mapper.map_roster_player_info(player)

        assert info.external_id == "1001"
        assert info.first_name == "John"
        assert info.last_name == "Smith"
        assert info.jersey_number == "23"

    def test_map_roster_player_info_normalizes_position(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test position normalization from abbreviation."""
        player = RosterPlayer(
            player_id="1001",
            name="John Smith",
            position="G",
        )

        info = winner_mapper.map_roster_player_info(player)

        assert info.positions == [Position.GUARD]

    def test_map_roster_player_info_no_bio_data(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test roster player has no height or birthdate."""
        player = RosterPlayer(
            player_id="1001",
            name="John Smith",
            position="C",
        )

        info = winner_mapper.map_roster_player_info(player)

        assert info.height_cm is None
        assert info.birth_date is None


class TestEndToEndBioSync:
    """End-to-end tests for player bio sync flow."""

    def test_scrape_and_map_player_with_full_bio(
        self,
        winner_mapper: WinnerMapper,
        player_profile_modern_html: str,
    ) -> None:
        """Test complete flow: scrape HTML -> parse profile -> map to RawPlayerInfo."""
        # Step 1: Parse HTML (simulating scraper)
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_modern_html, "1001")

        # Step 2: Map to RawPlayerInfo
        info = winner_mapper.map_player_info(profile)

        # Verify complete bio data
        assert info.external_id == "1001"
        assert info.first_name == "Roman"
        assert info.last_name == "Sorkin"
        assert info.height_cm == 208
        assert info.birth_date == date(1998, 3, 15)
        assert info.positions == [Position.CENTER]

    def test_scrape_and_map_hebrew_player(
        self,
        winner_mapper: WinnerMapper,
        player_profile_hebrew_html: str,
    ) -> None:
        """Test complete flow with Hebrew content."""
        scraper = WinnerScraper.__new__(WinnerScraper)
        profile = scraper._parse_player_profile(player_profile_hebrew_html, "1002")

        info = winner_mapper.map_player_info(profile)

        # Verify bio data
        assert info.height_cm == 188
        assert info.birth_date == date(1995, 8, 22)
        assert info.positions == [Position.GUARD]

    def test_bio_sync_fallback_to_roster_data(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test that roster data is used as fallback when profile fetch fails."""
        # Simulate what adapter does when profile fetch fails
        roster_player = RosterPlayer(
            player_id="1001",
            name="Test Player",
            jersey_number="5",
            position="Forward",
        )

        # Use roster mapping as fallback
        info = winner_mapper.map_roster_player_info(roster_player)

        # Should have position but no height/birthdate
        assert info.positions == [Position.FORWARD]
        assert info.height_cm is None
        assert info.birth_date is None
