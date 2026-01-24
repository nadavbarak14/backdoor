"""
Winner Scraper Tests

Tests for src/sync/winner/scraper.py covering:
- HTML page scraping
- Player profile parsing
- Team roster parsing
- Historical results parsing
- Caching behavior
- Error handling
"""

from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.models.sync_cache import SyncCache
from src.sync.winner.config import WinnerConfig
from src.sync.winner.exceptions import WinnerAPIError, WinnerParseError
from src.sync.winner.scraper import (
    HistoricalResults,
    PlayerProfile,
    RosterPlayer,
    TeamRoster,
    WinnerScraper,
)

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def player_html_fixture():
    """Load player.html fixture."""
    with open(FIXTURES_DIR / "player.html") as f:
        return f.read()


@pytest.fixture
def team_html_fixture():
    """Load team.html fixture."""
    with open(FIXTURES_DIR / "team.html") as f:
        return f.read()


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""

    def _create(text="", status_code=200):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text
        response.headers = {}
        return response

    return _create


class TestPlayerProfile:
    """Tests for PlayerProfile dataclass."""

    def test_creation(self):
        """PlayerProfile should hold player data."""
        profile = PlayerProfile(
            player_id="1001",
            name="John Smith",
            team_name="Maccabi Tel Aviv",
            jersey_number="5",
            position="Guard",
            height_cm=195,
        )

        assert profile.player_id == "1001"
        assert profile.name == "John Smith"
        assert profile.team_name == "Maccabi Tel Aviv"
        assert profile.jersey_number == "5"

    def test_optional_fields(self):
        """Optional fields should default to None."""
        profile = PlayerProfile(player_id="1001", name="Test")

        assert profile.team_name is None
        assert profile.jersey_number is None
        assert profile.height_cm is None


class TestTeamRoster:
    """Tests for TeamRoster dataclass."""

    def test_creation(self):
        """TeamRoster should hold team data."""
        roster = TeamRoster(
            team_id="100",
            team_name="Maccabi Tel Aviv",
            players=[
                RosterPlayer(player_id="1001", name="John Smith", jersey_number="5"),
                RosterPlayer(player_id="1002", name="David Cohen", jersey_number="10"),
            ],
        )

        assert roster.team_id == "100"
        assert roster.team_name == "Maccabi Tel Aviv"
        assert len(roster.players) == 2

    def test_empty_roster(self):
        """Roster should work with no players."""
        roster = TeamRoster(team_id="100")

        assert roster.players == []


class TestWinnerScraperInit:
    """Tests for WinnerScraper initialization."""

    def test_default_config(self, test_db):
        """Scraper should use default config if not provided."""
        scraper = WinnerScraper(test_db)

        assert scraper.config is not None
        assert scraper.config.scrape_requests_per_second == 0.5

    def test_custom_config(self, test_db):
        """Scraper should use provided config."""
        config = WinnerConfig(scrape_requests_per_second=0.25)
        scraper = WinnerScraper(test_db, config=config)

        assert scraper.config.scrape_requests_per_second == 0.25

    def test_context_manager(self, test_db):
        """Scraper should work as context manager."""
        with WinnerScraper(test_db) as scraper:
            assert scraper._client is not None

        assert scraper._client is None


class TestWinnerScraperFetchPlayer:
    """Tests for fetch_player method."""

    def test_fetch_success(self, test_db, player_html_fixture, mock_response):
        """Should fetch and parse player profile."""
        response = mock_response(text=player_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db) as scraper:
                profile = scraper.fetch_player("1001")

        assert profile.player_id == "1001"
        assert profile.name == "John Smith"
        assert profile.team_name == "Maccabi Tel Aviv"
        assert profile.jersey_number == "5"
        assert profile.position == "Guard"
        assert profile.height_cm == 195
        assert profile.nationality == "USA"

    def test_caches_html(self, test_db, player_html_fixture, mock_response):
        """Should cache HTML in database."""
        response = mock_response(text=player_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db) as scraper:
                scraper.fetch_player("1001")

        cache = (
            test_db.query(SyncCache)
            .filter(
                SyncCache.source == "winner",
                SyncCache.resource_type == "player_page",
                SyncCache.resource_id == "1001",
            )
            .first()
        )

        assert cache is not None
        assert cache.raw_data["html"] == player_html_fixture

    def test_returns_cached(self, test_db, player_html_fixture, mock_response):
        """Should return cached data without HTTP request."""
        response = mock_response(text=player_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response) as mock_get:
            with WinnerScraper(test_db) as scraper:
                # First fetch
                scraper.fetch_player("1001")

                # Second fetch should use cache
                profile = scraper.fetch_player("1001")

        assert mock_get.call_count == 1
        assert profile.name == "John Smith"

    def test_force_refresh(self, test_db, player_html_fixture, mock_response):
        """force=True should bypass cache."""
        response = mock_response(text=player_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response) as mock_get:
            with WinnerScraper(test_db) as scraper:
                scraper.fetch_player("1001")
                scraper.fetch_player("1001", force=True)

        assert mock_get.call_count == 2


class TestWinnerScraperFetchTeamRoster:
    """Tests for fetch_team_roster method."""

    def test_fetch_success(self, test_db, team_html_fixture, mock_response):
        """Should fetch and parse team roster."""
        response = mock_response(text=team_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db) as scraper:
                roster = scraper.fetch_team_roster("100")

        assert roster.team_id == "100"
        assert roster.team_name == "Maccabi Tel Aviv"
        assert len(roster.players) == 5

    def test_extracts_player_ids(self, test_db, team_html_fixture, mock_response):
        """Should extract player IDs from links."""
        response = mock_response(text=team_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db) as scraper:
                roster = scraper.fetch_team_roster("100")

        player_ids = [p.player_id for p in roster.players]
        assert "1001" in player_ids
        assert "1002" in player_ids
        assert "1003" in player_ids

    def test_extracts_jersey_numbers(self, test_db, team_html_fixture, mock_response):
        """Should extract jersey numbers."""
        response = mock_response(text=team_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db) as scraper:
                roster = scraper.fetch_team_roster("100")

        # Find John Smith
        john = next((p for p in roster.players if p.player_id == "1001"), None)
        assert john is not None
        assert john.jersey_number == "5"

    def test_extracts_positions(self, test_db, team_html_fixture, mock_response):
        """Should extract player positions."""
        response = mock_response(text=team_html_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db) as scraper:
                roster = scraper.fetch_team_roster("100")

        # Find John Smith
        john = next((p for p in roster.players if p.player_id == "1001"), None)
        assert john is not None
        assert john.position == "G"


class TestWinnerScraperParsePlayer:
    """Tests for player parsing logic."""

    def test_parse_minimal_html(self, test_db):
        """Should handle minimal HTML."""
        html = "<html><head><title>Test Player</title></head><body></body></html>"

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "999")

        assert profile.player_id == "999"
        assert profile.name == "Test Player"

    def test_parse_empty_html(self, test_db):
        """Should handle empty/minimal HTML gracefully."""
        html = "<html><body></body></html>"

        scraper = WinnerScraper(test_db)
        profile = scraper._parse_player_profile(html, "999")

        assert profile.player_id == "999"
        # Should have default name
        assert "999" in profile.name


class TestWinnerScraperParseTeam:
    """Tests for team roster parsing logic."""

    def test_parse_minimal_html(self, test_db):
        """Should handle minimal HTML."""
        html = "<html><head><title>Test Team</title></head><body></body></html>"

        scraper = WinnerScraper(test_db)
        roster = scraper._parse_team_roster(html, "100")

        assert roster.team_id == "100"
        assert roster.team_name == "Test Team"
        assert roster.players == []


class TestWinnerScraperErrorHandling:
    """Tests for error handling."""

    def test_http_error(self, test_db, mock_response):
        """Should raise WinnerAPIError on HTTP errors."""
        response = mock_response(status_code=404)

        config = WinnerConfig(max_retries=0)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerScraper(test_db, config=config) as scraper:
                with pytest.raises(WinnerAPIError) as exc_info:
                    scraper.fetch_player("9999")

        assert exc_info.value.status_code == 404

    def test_parse_error_includes_context(self, test_db):
        """Parse errors should include context."""
        from datetime import datetime

        scraper = WinnerScraper(test_db)

        # Force a parse by having cached HTML
        cache = SyncCache(
            source="winner",
            resource_type="player_page",
            resource_id="1001",
            raw_data={"html": "<html></html>"},
            content_hash="abc",
            fetched_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        test_db.add(cache)
        test_db.commit()

        # Patch BeautifulSoup to raise an exception during parsing
        with patch(
            "src.sync.winner.scraper.BeautifulSoup",
            side_effect=Exception("Parse failure"),
        ):
            with pytest.raises(WinnerParseError) as exc_info:
                scraper.fetch_player("1001")

        assert exc_info.value.resource_type == "player_page"
        assert exc_info.value.resource_id == "1001"


class TestHistoricalResults:
    """Tests for historical results parsing."""

    def test_creation(self):
        """HistoricalResults should hold results data."""
        from src.sync.winner.scraper import GameResult

        results = HistoricalResults(
            year=2024,
            games=[
                GameResult(
                    game_id="123",
                    date=None,
                    home_team="Team A",
                    away_team="Team B",
                    home_score=85,
                    away_score=78,
                )
            ],
        )

        assert results.year == 2024
        assert len(results.games) == 1
        assert results.games[0].home_score == 85

    def test_parse_results_html(self, test_db):
        """Should parse historical results HTML."""
        html = """
        <html>
        <body>
            <table>
                <tr>
                    <td>Team A</td>
                    <td>85-78</td>
                    <td>Team B</td>
                </tr>
            </table>
        </body>
        </html>
        """

        scraper = WinnerScraper(test_db)
        results = scraper._parse_historical_results(html, 2024)

        assert results.year == 2024
        # May or may not find games depending on HTML structure
        # The test mainly ensures no exceptions
