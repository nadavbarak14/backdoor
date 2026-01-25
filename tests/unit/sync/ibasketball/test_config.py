"""
Unit tests for IBasketballConfig.

Tests configuration dataclass and URL building methods.
"""

import pytest

from src.sync.ibasketball.config import IBasketballConfig, LeagueConfig


class TestLeagueConfig:
    """Tests for LeagueConfig dataclass."""

    def test_league_config_creation(self):
        """Test creating a LeagueConfig."""
        config = LeagueConfig(
            league_id="123",
            name="Test League",
            short_name="TL",
        )
        assert config.league_id == "123"
        assert config.name == "Test League"
        assert config.short_name == "TL"


class TestIBasketballConfig:
    """Tests for IBasketballConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = IBasketballConfig()

        assert config.base_url == "https://ibasketball.co.il"
        assert config.api_base_url == "https://ibasketball.co.il/wp-json/sportspress/v2"
        assert config.api_requests_per_second == 2.0
        assert config.scrape_requests_per_second == 0.5
        assert config.request_timeout == 30.0
        assert config.max_retries == 3

    def test_default_leagues(self):
        """Test default league configurations."""
        config = IBasketballConfig()

        assert "liga_al" in config.leagues
        assert "liga_leumit" in config.leagues

        liga_leumit = config.leagues["liga_leumit"]
        assert liga_leumit.league_id == "119474"
        assert liga_leumit.name == "Liga Leumit"

        liga_al = config.leagues["liga_al"]
        assert liga_al.league_id == "119473"
        assert liga_al.name == "Liga Alef"

    def test_get_league_config(self):
        """Test getting league configuration by key."""
        config = IBasketballConfig()

        league = config.get_league_config("liga_leumit")
        assert league.league_id == "119474"

        with pytest.raises(KeyError):
            config.get_league_config("invalid_league")

    def test_get_events_url(self):
        """Test events URL generation."""
        config = IBasketballConfig()

        url = config.get_events_url("119474")
        assert url == (
            "https://ibasketball.co.il/wp-json/sportspress/v2/events"
            "?leagues=119474&per_page=100&page=1"
        )

        url_page2 = config.get_events_url("119474", page=2)
        assert "page=2" in url_page2

    def test_get_event_url(self):
        """Test single event URL generation."""
        config = IBasketballConfig()

        url = config.get_event_url("123456")
        assert url == "https://ibasketball.co.il/wp-json/sportspress/v2/events/123456"

    def test_get_standings_url(self):
        """Test standings URL generation."""
        config = IBasketballConfig()

        url = config.get_standings_url("119474")
        assert url == (
            "https://ibasketball.co.il/wp-json/sportspress/v2/tables" "?leagues=119474"
        )

    def test_get_teams_url(self):
        """Test teams URL generation."""
        config = IBasketballConfig()

        url = config.get_teams_url()
        assert "per_page=100" in url
        assert "leagues=" not in url

        url_filtered = config.get_teams_url("119474")
        assert "leagues=119474" in url_filtered

    def test_get_game_page_url(self):
        """Test game page URL generation for scraping."""
        config = IBasketballConfig()

        url = config.get_game_page_url("team-a-vs-team-b")
        assert url == "https://ibasketball.co.il/event/team-a-vs-team-b/"

    def test_get_player_page_url(self):
        """Test player page URL generation for scraping."""
        config = IBasketballConfig()

        url = config.get_player_page_url("john-smith")
        assert url == "https://ibasketball.co.il/player/john-smith/"

    def test_get_available_leagues(self):
        """Test getting list of available leagues."""
        config = IBasketballConfig()

        leagues = config.get_available_leagues()
        assert "liga_al" in leagues
        assert "liga_leumit" in leagues
        assert len(leagues) == 2

    def test_custom_config(self):
        """Test custom configuration values."""
        config = IBasketballConfig(
            api_requests_per_second=1.0,
            request_timeout=60.0,
            max_retries=5,
        )

        assert config.api_requests_per_second == 1.0
        assert config.request_timeout == 60.0
        assert config.max_retries == 5
