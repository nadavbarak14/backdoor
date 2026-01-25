"""Unit tests for Euroleague configuration."""

from src.sync.euroleague.config import EuroleagueConfig


class TestEuroleagueConfig:
    """Tests for EuroleagueConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EuroleagueConfig()

        assert config.competition == "E"
        assert config.requests_per_second == 2.0
        assert config.burst_size == 5
        assert config.request_timeout == 30.0
        assert config.max_retries == 3

    def test_eurocup_competition(self):
        """Test EuroCup competition code."""
        config = EuroleagueConfig(competition="U")

        assert config.competition == "U"
        assert config.get_season_code(2024) == "U2024"

    def test_get_season_code(self):
        """Test season code generation."""
        config = EuroleagueConfig()

        assert config.get_season_code(2024) == "E2024"
        assert config.get_season_code(2020) == "E2020"
        assert config.get_season_code(2015) == "E2015"

    def test_get_teams_url(self):
        """Test teams URL generation."""
        config = EuroleagueConfig()

        url = config.get_teams_url(2024)
        assert url == "https://api-live.euroleague.net/v1/teams?seasonCode=E2024"

        # EuroCup
        config_u = EuroleagueConfig(competition="U")
        url_u = config_u.get_teams_url(2024)
        assert url_u == "https://api-live.euroleague.net/v1/teams?seasonCode=U2024"

    def test_get_player_url(self):
        """Test player URL generation."""
        config = EuroleagueConfig()

        url = config.get_player_url("011987", 2024)
        assert (
            url
            == "https://api-live.euroleague.net/v1/players?playerCode=011987&seasonCode=E2024"
        )

    def test_get_schedule_url(self):
        """Test schedule URL generation."""
        config = EuroleagueConfig()

        url = config.get_schedule_url(2024)
        assert url == "https://api-live.euroleague.net/v1/schedules?seasonCode=E2024"

    def test_get_live_url(self):
        """Test live game API URL generation."""
        config = EuroleagueConfig()

        # Boxscore
        url = config.get_live_url("Boxscore", 1, 2024)
        assert (
            url
            == "https://live.euroleague.net/api/Boxscore?gamecode=1&seasoncode=E2024"
        )

        # Header
        url = config.get_live_url("Header", 42, 2024)
        assert (
            url == "https://live.euroleague.net/api/Header?gamecode=42&seasoncode=E2024"
        )

        # PlaybyPlay
        url = config.get_live_url("PlaybyPlay", 100, 2023)
        assert (
            url
            == "https://live.euroleague.net/api/PlaybyPlay?gamecode=100&seasoncode=E2023"
        )

    def test_custom_rate_limits(self):
        """Test custom rate limit configuration."""
        config = EuroleagueConfig(
            requests_per_second=1.0,
            burst_size=3,
            request_timeout=60.0,
        )

        assert config.requests_per_second == 1.0
        assert config.burst_size == 3
        assert config.request_timeout == 60.0

    def test_custom_retry_settings(self):
        """Test custom retry configuration."""
        config = EuroleagueConfig(
            max_retries=5,
            retry_base_delay=2.0,
            retry_max_delay=60.0,
        )

        assert config.max_retries == 5
        assert config.retry_base_delay == 2.0
        assert config.retry_max_delay == 60.0
