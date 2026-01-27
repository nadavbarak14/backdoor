"""
Unit tests for player bio sync functionality.

Tests parsing of English content from basket.co.il with lang=en parameter,
name matching between PBP data and roster data, and bio field extraction.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.sync.winner.config import WinnerConfig
from src.sync.winner.mapper import WinnerMapper
from src.sync.winner.scraper import WinnerScraper

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def winner_config():
    """Create WinnerConfig instance."""
    return WinnerConfig()


@pytest.fixture
def winner_mapper():
    """Create WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def player_html() -> str:
    """Load player HTML fixture."""
    path = FIXTURES_DIR / "player.html"
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def player_with_birthdate_html() -> str:
    """Load player with birthdate HTML fixture."""
    path = FIXTURES_DIR / "player_with_birthdate.html"
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def team_html() -> str:
    """Load team roster HTML fixture."""
    path = FIXTURES_DIR / "team.html"
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestLangEnParameter:
    """Tests for lang=en parameter in URL templates."""

    def test_player_url_includes_lang_en(self, winner_config: WinnerConfig) -> None:
        """Test player URL template includes lang=en parameter."""
        url = winner_config.get_player_url("12345")
        assert "lang=en" in url
        assert "PlayerId=12345" in url

    def test_team_url_includes_lang_en(self, winner_config: WinnerConfig) -> None:
        """Test team URL template includes lang=en parameter."""
        url = winner_config.get_team_url("100")
        assert "lang=en" in url
        assert "TeamId=100" in url

    def test_results_url_includes_lang_en(self, winner_config: WinnerConfig) -> None:
        """Test results URL template includes lang=en parameter."""
        url = winner_config.get_results_url(2024)
        assert "lang=en" in url
        assert "cYear=2024" in url


class TestFetchTeamRosterEnglish:
    """Tests for parsing team roster with English names."""

    def test_parse_team_roster_extracts_players(self, mock_db, team_html: str) -> None:
        """Test roster parsing extracts player IDs and English names."""
        scraper = WinnerScraper(mock_db)
        roster = scraper._parse_team_roster(team_html, "100")

        assert roster.team_id == "100"
        assert roster.team_name == "Maccabi Tel Aviv"
        assert len(roster.players) == 5

    def test_parse_team_roster_english_names(self, mock_db, team_html: str) -> None:
        """Test roster contains English player names."""
        scraper = WinnerScraper(mock_db)
        roster = scraper._parse_team_roster(team_html, "100")

        player_names = [p.name for p in roster.players]
        assert "John Smith" in player_names
        assert "David Cohen" in player_names
        assert "Michael Brown" in player_names

    def test_parse_team_roster_player_ids(self, mock_db, team_html: str) -> None:
        """Test roster extracts correct player IDs."""
        scraper = WinnerScraper(mock_db)
        roster = scraper._parse_team_roster(team_html, "100")

        player_ids = [p.player_id for p in roster.players]
        assert "1001" in player_ids
        assert "1002" in player_ids
        assert "1003" in player_ids

    def test_parse_team_roster_positions(self, mock_db, team_html: str) -> None:
        """Test roster extracts player positions."""
        scraper = WinnerScraper(mock_db)
        roster = scraper._parse_team_roster(team_html, "100")

        positions = {p.name: p.position for p in roster.players}
        assert positions["John Smith"] == "G"
        assert positions["David Cohen"] == "PG"
        assert positions["Michael Brown"] == "C"


class TestFetchPlayerProfileEnglish:
    """Tests for parsing player profile with English content."""

    def test_parse_player_profile_english_name(self, mock_db, player_html: str) -> None:
        """Test player profile parses English name."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_html, "1001")

        assert profile.name == "John Smith"

    def test_parse_player_profile_team_name(self, mock_db, player_html: str) -> None:
        """Test player profile parses English team name."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_html, "1001")

        assert profile.team_name == "Maccabi Tel Aviv"

    def test_parse_player_profile_position(self, mock_db, player_html: str) -> None:
        """Test player profile parses position."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_html, "1001")

        assert profile.position == "Guard"

    def test_parse_player_profile_nationality(self, mock_db, player_html: str) -> None:
        """Test player profile parses nationality."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_html, "1001")

        assert profile.nationality == "USA"


class TestParsePlayerHeight:
    """Tests for parsing player height from profile."""

    def test_parse_height_from_profile(self, mock_db, player_html: str) -> None:
        """Test height is parsed from profile HTML."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_html, "1001")

        assert profile.height_cm == 195

    def test_parse_height_with_cm_suffix(self, mock_db) -> None:
        """Test height parsing handles 'cm' suffix."""
        html = """
        <html>
        <body>
            <h1>Test Player</h1>
            <table>
                <tr><td>Height:</td><td>198cm</td></tr>
            </table>
        </body>
        </html>
        """
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(html, "test")

        assert profile.height_cm == 198

    def test_parse_height_with_spaces(self, mock_db) -> None:
        """Test height parsing handles spaces."""
        html = """
        <html>
        <body>
            <h1>Test Player</h1>
            <table>
                <tr><td>Height:</td><td>   201  cm  </td></tr>
            </table>
        </body>
        </html>
        """
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(html, "test")

        assert profile.height_cm == 201


class TestParsePlayerPosition:
    """Tests for parsing player position from profile."""

    def test_parse_position_guard(self, mock_db, player_html: str) -> None:
        """Test parsing Guard position."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_html, "1001")

        assert profile.position == "Guard"

    def test_parse_position_from_various_labels(self, mock_db) -> None:
        """Test position parsing with different label formats."""
        for label in ["Position:", "position", "POSITION:"]:
            html = f"""
            <html>
            <body>
                <h1>Test Player</h1>
                <table>
                    <tr><td>{label}</td><td>Center</td></tr>
                </table>
            </body>
            </html>
            """
            scraper = WinnerScraper(mock_db)
            profile = scraper._parse_player_profile(html, "test")

            assert profile.position == "Center", f"Failed for label: {label}"


class TestParsePlayerBirthdate:
    """Tests for parsing player birth date from profile."""

    def test_parse_birthdate_iso_format(
        self, mock_db, player_with_birthdate_html: str
    ) -> None:
        """Test birth date parsing with ISO format (YYYY-MM-DD)."""
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(player_with_birthdate_html, "1001")

        assert profile.birth_date is not None
        assert profile.birth_date.year == 1995
        assert profile.birth_date.month == 5
        assert profile.birth_date.day == 15

    def test_parse_birthdate_european_format(self, mock_db) -> None:
        """Test birth date parsing with European format (DD/MM/YYYY)."""
        html = """
        <html>
        <body>
            <h1>Test Player</h1>
            <table>
                <tr><td>Birth Date:</td><td>15/05/1995</td></tr>
            </table>
        </body>
        </html>
        """
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(html, "test")

        assert profile.birth_date is not None
        assert profile.birth_date.year == 1995

    def test_parse_birthdate_dot_format(self, mock_db) -> None:
        """Test birth date parsing with dot format (DD.MM.YYYY)."""
        html = """
        <html>
        <body>
            <h1>Test Player</h1>
            <table>
                <tr><td>Birth Date:</td><td>15.05.1995</td></tr>
            </table>
        </body>
        </html>
        """
        scraper = WinnerScraper(mock_db)
        profile = scraper._parse_player_profile(html, "test")

        assert profile.birth_date is not None
        assert profile.birth_date.year == 1995


class TestMatchPlayerByName:
    """Tests for player name matching between PBP and roster."""

    def test_exact_name_match(self) -> None:
        """Test exact name matching."""
        from src.sync.manager import SyncManager

        manager = SyncManager.__new__(SyncManager)

        # Test normalization
        assert manager._normalize_name("John Smith") == "john smith"
        assert manager._normalize_name("  John   Smith  ") == "john smith"
        assert manager._normalize_name("JOHN SMITH") == "john smith"

    def test_normalize_name_with_extra_spaces(self) -> None:
        """Test name normalization removes extra spaces."""
        from src.sync.manager import SyncManager

        manager = SyncManager.__new__(SyncManager)

        assert manager._normalize_name("John  Smith") == "john smith"
        assert manager._normalize_name(" John Smith ") == "john smith"

    def test_normalize_name_case_insensitive(self) -> None:
        """Test name normalization is case insensitive."""
        from src.sync.manager import SyncManager

        manager = SyncManager.__new__(SyncManager)

        assert manager._normalize_name("john smith") == "john smith"
        assert manager._normalize_name("John Smith") == "john smith"
        assert manager._normalize_name("JOHN SMITH") == "john smith"

    def test_normalize_name_strips_position_patterns(self) -> None:
        """Test normalization strips trailing position patterns from corrupted names."""
        from src.sync.manager import SyncManager

        manager = SyncManager.__new__(SyncManager)

        # Test various position patterns that might be appended to names
        assert manager._normalize_name("John Smith F-") == "john smith"
        assert manager._normalize_name("John Smith G-") == "john smith"
        assert manager._normalize_name("John Smith F-C") == "john smith"
        assert manager._normalize_name("John Smith G-F") == "john smith"
        assert manager._normalize_name("John Smith C") == "john smith"
        assert manager._normalize_name("John Smith F") == "john smith"
        assert manager._normalize_name("John Smith G") == "john smith"
        assert manager._normalize_name("John Smith PG") == "john smith"
        assert manager._normalize_name("John Smith SG") == "john smith"
        assert manager._normalize_name("John Smith SF") == "john smith"
        assert manager._normalize_name("John Smith PF") == "john smith"

    def test_normalize_name_strips_captain_suffix(self) -> None:
        """Test normalization strips Captain suffix from names."""
        from src.sync.manager import SyncManager

        manager = SyncManager.__new__(SyncManager)

        assert manager._normalize_name("John Smith Captain|") == "john smith"
        assert manager._normalize_name("John Smith captain|") == "john smith"
        assert manager._normalize_name("John Smith CAPTAIN|") == "john smith"
        assert manager._normalize_name("John Smith captain") == "john smith"

    def test_normalize_name_compact(self) -> None:
        """Test compact normalization removes spaces and punctuation."""
        from src.sync.manager import SyncManager

        manager = SyncManager.__new__(SyncManager)

        # Test compact form removes spaces
        assert manager._normalize_name_compact("John Smith") == "johnsmith"
        assert manager._normalize_name_compact("DJ Kennedy") == "djkennedy"

        # Test compact form removes punctuation
        assert manager._normalize_name_compact("D.J. Kennedy") == "djkennedy"
        assert manager._normalize_name_compact("O'Brien") == "obrien"
        assert manager._normalize_name_compact("Al-Farouq") == "alfarouq"

        # Test combined normalization
        assert manager._normalize_name_compact("John Smith F-") == "johnsmith"
        assert manager._normalize_name_compact("D.J. Kennedy G-") == "djkennedy"


class TestMapperPlayerInfo:
    """Tests for mapping player profile to RawPlayerInfo."""

    def test_map_player_info_splits_name(self, winner_mapper: WinnerMapper) -> None:
        """Test name is split into first and last name."""
        from src.sync.winner.scraper import PlayerProfile

        profile = PlayerProfile(
            player_id="1001",
            name="John Smith",
            height_cm=195,
            position="Guard",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.first_name == "John"
        assert info.last_name == "Smith"

    def test_map_player_info_multiple_last_names(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test handling names with multiple parts."""
        from src.sync.winner.scraper import PlayerProfile

        profile = PlayerProfile(
            player_id="1001",
            name="Juan Carlos Rodriguez",
        )

        info = winner_mapper.map_player_info(profile)

        assert info.first_name == "Juan"
        assert info.last_name == "Carlos Rodriguez"

    def test_map_player_info_preserves_bio_data(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test bio data is preserved in mapping."""
        from datetime import datetime

        from src.sync.winner.scraper import PlayerProfile

        profile = PlayerProfile(
            player_id="1001",
            name="John Smith",
            height_cm=195,
            position="Guard",
            birth_date=datetime(1995, 5, 15),
        )

        info = winner_mapper.map_player_info(profile)

        assert info.height_cm == 195
        assert info.position == "Guard"
        assert info.birth_date is not None
        assert info.birth_date.year == 1995


class TestMapRosterPlayerInfo:
    """Tests for mapping roster player to RawPlayerInfo."""

    def test_map_roster_player_info_basic(self, winner_mapper: WinnerMapper) -> None:
        """Test mapping a roster player to RawPlayerInfo."""
        from src.sync.winner.scraper import RosterPlayer

        roster_player = RosterPlayer(
            player_id="1001",
            name="John Smith",
            position="G",
        )

        info = winner_mapper.map_roster_player_info(roster_player)

        assert info.external_id == "1001"
        assert info.first_name == "John"
        assert info.last_name == "Smith"
        assert info.position == "G"
        assert info.height_cm is None
        assert info.birth_date is None

    def test_map_roster_player_info_multiple_names(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test mapping roster player with multiple name parts."""
        from src.sync.winner.scraper import RosterPlayer

        roster_player = RosterPlayer(
            player_id="1002",
            name="Juan Carlos Rodriguez",
            position="C",
        )

        info = winner_mapper.map_roster_player_info(roster_player)

        assert info.first_name == "Juan"
        assert info.last_name == "Carlos Rodriguez"

    def test_map_roster_player_info_single_name(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test mapping roster player with single name."""
        from src.sync.winner.scraper import RosterPlayer

        roster_player = RosterPlayer(
            player_id="1003",
            name="Madonna",
            position="F",
        )

        info = winner_mapper.map_roster_player_info(roster_player)

        assert info.first_name == ""
        assert info.last_name == "Madonna"

    def test_map_roster_player_info_empty_name(
        self, winner_mapper: WinnerMapper
    ) -> None:
        """Test mapping roster player with empty name."""
        from src.sync.winner.scraper import RosterPlayer

        roster_player = RosterPlayer(
            player_id="1004",
            name="",
            position="",
        )

        info = winner_mapper.map_roster_player_info(roster_player)

        assert info.first_name == ""
        assert info.last_name == ""
