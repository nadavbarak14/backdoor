"""Unit tests for Euroleague direct client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import xmltodict

from src.sync.euroleague.config import EuroleagueConfig
from src.sync.euroleague.direct_client import EuroleagueDirectClient

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "euroleague"


class TestEuroleagueDirectClient:
    """Tests for EuroleagueDirectClient."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    @pytest.fixture
    def teams_xml(self):
        """Load teams XML fixture."""
        with open(FIXTURES_DIR / "teams.xml") as f:
            return f.read()

    @pytest.fixture
    def player_xml(self):
        """Load player XML fixture."""
        with open(FIXTURES_DIR / "player.xml") as f:
            return f.read()

    def test_init_default_config(self, mock_db):
        """Test client initialization with default config."""
        client = EuroleagueDirectClient(mock_db)

        assert client.db == mock_db
        assert client.config.competition == "E"
        assert client._client is None

    def test_init_custom_config(self, mock_db):
        """Test client initialization with custom config."""
        config = EuroleagueConfig(competition="U", requests_per_second=1.0)
        client = EuroleagueDirectClient(mock_db, config=config)

        assert client.config.competition == "U"
        assert client.config.requests_per_second == 1.0

    def test_context_manager(self, mock_db):
        """Test context manager creates and closes client."""
        with EuroleagueDirectClient(mock_db) as client:
            assert client._client is not None

        assert client._client is None

    def test_parse_teams(self, mock_db, teams_xml):
        """Test parsing teams XML."""
        client = EuroleagueDirectClient(mock_db)
        xml_data = xmltodict.parse(teams_xml)

        teams = client._parse_teams(xml_data)

        assert len(teams) == 2

        # Check first team
        berlin = teams[0]
        assert berlin["code"] == "BER"
        assert berlin["name"] == "ALBA Berlin"
        assert berlin["country_code"] == "GER"
        assert berlin["arena_name"] == "UBER ARENA"
        assert len(berlin["players"]) == 3

        # Check player
        edwards = berlin["players"][0]
        assert edwards["code"] == "011987"
        assert edwards["name"] == "EDWARDS, CARSEN"
        assert edwards["position"] == "Guard"
        assert edwards["country_code"] == "USA"

        # Check second team
        pan = teams[1]
        assert pan["code"] == "PAN"
        assert pan["tv_code"] == "PAO"
        assert len(pan["players"]) == 2

    def test_parse_player(self, mock_db, player_xml):
        """Test parsing player XML."""
        client = EuroleagueDirectClient(mock_db)
        xml_data = xmltodict.parse(player_xml)

        player = client._parse_player(xml_data)

        assert player["name"] == "EDWARDS, CARSEN"
        assert player["height"] == "1.8"
        assert player["birthdate"] == "12 March, 1998"
        assert player["country"] == "United States of America"
        assert player["club_code"] == "MUN"
        assert player["club_name"] == "FC Bayern Munich"
        assert player["position"] == "Guard"
        assert "stats" in player

    def test_compute_hash(self, mock_db):
        """Test hash computation for change detection."""
        client = EuroleagueDirectClient(mock_db)

        data1 = {"key": "value"}
        data2 = {"key": "value"}
        data3 = {"key": "different"}

        hash1 = client._compute_hash(data1)
        hash2 = client._compute_hash(data2)
        hash3 = client._compute_hash(data3)

        # Same data produces same hash
        assert hash1 == hash2
        # Different data produces different hash
        assert hash1 != hash3

    def test_get_cache_miss(self, mock_db):
        """Test cache miss returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        client = EuroleagueDirectClient(mock_db)

        result = client._get_cache("teams", "E2024")

        assert result is None

    def test_get_cache_hit(self, mock_db):
        """Test cache hit returns cached entry."""
        cache_entry = MagicMock()
        cache_entry.raw_data = {"test": "data"}
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry

        client = EuroleagueDirectClient(mock_db)
        result = client._get_cache("teams", "E2024")

        assert result == cache_entry

    @patch.object(EuroleagueDirectClient, "_fetch_xml")
    def test_fetch_teams_from_cache(self, mock_fetch, mock_db):
        """Test fetch_teams returns cached data."""
        from datetime import UTC, datetime

        cache_entry = MagicMock()
        cache_entry.raw_data = [{"code": "BER", "name": "ALBA Berlin", "players": []}]
        cache_entry.fetched_at = datetime.now(UTC)
        cache_entry.id = "test-id"
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry

        client = EuroleagueDirectClient(mock_db)
        result = client.fetch_teams(2024)

        assert result.from_cache is True
        assert result.changed is False
        assert result.data == cache_entry.raw_data
        mock_fetch.assert_not_called()

    @patch.object(EuroleagueDirectClient, "_fetch_xml")
    def test_fetch_teams_force_refresh(self, mock_fetch, mock_db, teams_xml):
        """Test fetch_teams with force=True bypasses cache."""
        mock_fetch.return_value = xmltodict.parse(teams_xml)

        client = EuroleagueDirectClient(mock_db)
        result = client.fetch_teams(2024, force=True)

        assert result.from_cache is False
        mock_fetch.assert_called_once()

    @patch.object(EuroleagueDirectClient, "_fetch_xml")
    def test_fetch_player_from_api(self, mock_fetch, mock_db, player_xml):
        """Test fetch_player fetches from API."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_fetch.return_value = xmltodict.parse(player_xml)

        client = EuroleagueDirectClient(mock_db)
        result = client.fetch_player("011987", 2024)

        assert result.from_cache is False
        assert result.data["name"] == "EDWARDS, CARSEN"
        mock_fetch.assert_called_once()


class TestEuroleagueDirectClientLiveAPI:
    """Tests for live API methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    @pytest.fixture
    def boxscore_json(self):
        """Load boxscore JSON fixture."""
        import json

        with open(FIXTURES_DIR / "boxscore.json") as f:
            return json.load(f)

    @patch.object(EuroleagueDirectClient, "_fetch_json")
    def test_fetch_live_boxscore(self, mock_fetch, mock_db, boxscore_json):
        """Test fetch_live_boxscore fetches from API."""
        mock_fetch.return_value = boxscore_json

        client = EuroleagueDirectClient(mock_db)
        result = client.fetch_live_boxscore(2024, 1)

        assert result.from_cache is False
        assert result.data["Attendance"] == "11856"
        assert len(result.data["Stats"]) == 2

    @patch.object(EuroleagueDirectClient, "_fetch_json")
    def test_fetch_live_header(self, mock_fetch, mock_db):
        """Test fetch_live_header fetches from API."""
        mock_fetch.return_value = {
            "Stadium": "UBER ARENA",
            "TeamA": "ALBA BERLIN",
            "TeamB": "PANATHINAIKOS",
            "ScoreA": "77",
            "ScoreB": "87",
        }

        client = EuroleagueDirectClient(mock_db)
        result = client.fetch_live_header(2024, 1)

        assert result.data["Stadium"] == "UBER ARENA"

    @patch.object(EuroleagueDirectClient, "_fetch_json")
    def test_fetch_live_comparison(self, mock_fetch, mock_db):
        """Test fetch_live_comparison fetches from API."""
        mock_fetch.return_value = {
            "maxLeadA": 0,
            "maxLeadB": 14,
            "DefensiveReboundsA": 28,
            "DefensiveReboundsB": 24,
        }

        client = EuroleagueDirectClient(mock_db)
        result = client.fetch_live_comparison(2024, 1)

        assert result.data["maxLeadB"] == 14
