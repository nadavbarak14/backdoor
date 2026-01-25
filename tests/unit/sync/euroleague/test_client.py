"""Unit tests for Euroleague client."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.sync.euroleague.client import CacheResult, EuroleagueClient
from src.sync.euroleague.config import EuroleagueConfig


class TestCacheResult:
    """Tests for CacheResult dataclass."""

    def test_cache_result_creation(self):
        """Test CacheResult creation with all fields."""
        now = datetime.now(UTC)
        result = CacheResult(
            data=[{"id": 1}],
            changed=True,
            fetched_at=now,
            cache_id="test-123",
            from_cache=False,
        )

        assert result.data == [{"id": 1}]
        assert result.changed is True
        assert result.fetched_at == now
        assert result.cache_id == "test-123"
        assert result.from_cache is False

    def test_cache_result_default_from_cache(self):
        """Test CacheResult defaults from_cache to False."""
        result = CacheResult(
            data={},
            changed=False,
            fetched_at=datetime.now(UTC),
            cache_id="test",
        )

        assert result.from_cache is False


class TestEuroleagueClient:
    """Tests for EuroleagueClient."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    def test_init_default_config(self, mock_db):
        """Test client initialization with default config."""
        client = EuroleagueClient(mock_db)

        assert client.db == mock_db
        assert client.config.competition == "E"
        assert client._game_metadata is None

    def test_init_custom_config(self, mock_db):
        """Test client initialization with custom config."""
        config = EuroleagueConfig(competition="U")
        client = EuroleagueClient(mock_db, config=config)

        assert client.config.competition == "U"

    def test_context_manager_initializes_clients(self, mock_db):
        """Test context manager initializes API clients."""
        with EuroleagueClient(mock_db) as client:
            assert client._game_metadata is not None
            assert client._boxscore is not None
            assert client._pbp is not None
            assert client._shot_data is not None
            assert client._standings is not None
            assert client._player_stats is not None

    def test_properties_auto_initialize(self, mock_db):
        """Test properties auto-initialize clients."""
        client = EuroleagueClient(mock_db)

        # Access property - should trigger initialization
        gm = client.game_metadata

        assert gm is not None
        assert client._game_metadata is not None

    def test_compute_hash(self, mock_db):
        """Test hash computation for change detection."""
        client = EuroleagueClient(mock_db)

        data1 = [{"id": 1, "name": "Test"}]
        data2 = [{"id": 1, "name": "Test"}]
        data3 = [{"id": 2, "name": "Different"}]

        hash1 = client._compute_hash(data1)
        hash2 = client._compute_hash(data2)
        hash3 = client._compute_hash(data3)

        assert hash1 == hash2
        assert hash1 != hash3

    def test_dataframe_to_dict(self, mock_db):
        """Test DataFrame conversion to list of dicts."""
        client = EuroleagueClient(mock_db)

        df = pd.DataFrame(
            [
                {"id": 1, "name": "Player A"},
                {"id": 2, "name": "Player B"},
            ]
        )

        result = client._dataframe_to_dict(df)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Player A"

    def test_get_cache_miss(self, mock_db):
        """Test cache miss returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        client = EuroleagueClient(mock_db)

        result = client._get_cache("season_games", "E2024")

        assert result is None

    def test_get_cache_hit(self, mock_db):
        """Test cache hit returns cached entry."""
        cache_entry = MagicMock()
        cache_entry.raw_data = [{"id": 1}]
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry

        client = EuroleagueClient(mock_db)
        result = client._get_cache("season_games", "E2024")

        assert result == cache_entry


class TestEuroleagueClientFetchMethods:
    """Tests for EuroleagueClient fetch methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    @pytest.fixture
    def sample_games_df(self):
        """Sample games DataFrame."""
        return pd.DataFrame(
            [
                {
                    "Phase": "RS",
                    "Round": 1,
                    "date": "Oct 03, 2024",
                    "gamecode": "E2024_1",
                    "hometeam": "ALBA BERLIN",
                    "awayteam": "PANATHINAIKOS",
                    "homescore": 77,
                    "awayscore": 87,
                },
                {
                    "Phase": "RS",
                    "Round": 1,
                    "date": "Oct 03, 2024",
                    "gamecode": "E2024_2",
                    "hometeam": "AS MONACO",
                    "awayteam": "EA7 MILAN",
                    "homescore": 93,
                    "awayscore": 80,
                },
            ]
        )

    @pytest.fixture
    def sample_boxscore_df(self):
        """Sample boxscore DataFrame."""
        return pd.DataFrame(
            [
                {
                    "Season": 2024,
                    "Gamecode": 1,
                    "Player_ID": "P007025",
                    "Player": "MATTISSECK, JONAS",
                    "Team": "BER",
                    "Points": 6,
                    "TotalRebounds": 3,
                    "Assistances": 3,
                },
                {
                    "Season": 2024,
                    "Gamecode": 1,
                    "Player_ID": "P008780",
                    "Player": "HERMANNSSON, MARTIN",
                    "Team": "BER",
                    "Points": 12,
                    "TotalRebounds": 3,
                    "Assistances": 5,
                },
            ]
        )

    def test_fetch_season_games_from_cache(self, mock_db):
        """Test fetch_season_games returns cached data."""
        cache_entry = MagicMock()
        cache_entry.raw_data = [{"gamecode": "E2024_1"}]
        cache_entry.fetched_at = datetime.now(UTC)
        cache_entry.id = "cache-123"
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry

        client = EuroleagueClient(mock_db)
        result = client.fetch_season_games(2024)

        assert result.from_cache is True
        assert result.changed is False
        assert result.data == [{"gamecode": "E2024_1"}]
        assert result.cache_id == "cache-123"

    @patch("src.sync.euroleague.client.GameMetadata")
    def test_fetch_season_games_from_api(
        self, mock_game_metadata_class, mock_db, sample_games_df
    ):
        """Test fetch_season_games fetches from API."""
        # Configure mock
        mock_gm_instance = MagicMock()
        mock_gm_instance.get_gamecodes_season.return_value = sample_games_df
        mock_game_metadata_class.return_value = mock_gm_instance

        client = EuroleagueClient(mock_db)
        client._game_metadata = mock_gm_instance

        result = client.fetch_season_games(2024)

        assert result.from_cache is False
        assert len(result.data) == 2
        assert result.data[0]["hometeam"] == "ALBA BERLIN"

    @patch("src.sync.euroleague.client.BoxScoreData")
    def test_fetch_game_boxscore(
        self, mock_boxscore_class, mock_db, sample_boxscore_df
    ):
        """Test fetch_game_boxscore fetches from API."""
        mock_bs_instance = MagicMock()
        mock_bs_instance.get_player_boxscore_stats_data.return_value = (
            sample_boxscore_df
        )
        mock_boxscore_class.return_value = mock_bs_instance

        client = EuroleagueClient(mock_db)
        client._boxscore = mock_bs_instance

        result = client.fetch_game_boxscore(2024, 1)

        assert result.from_cache is False
        assert len(result.data) == 2
        assert result.data[0]["Player"] == "MATTISSECK, JONAS"
        assert result.data[0]["Points"] == 6

    def test_fetch_season_games_force_refresh(self, mock_db):
        """Test force=True bypasses cache."""
        cache_entry = MagicMock()
        cache_entry.raw_data = [{"gamecode": "E2024_1"}]
        cache_entry.fetched_at = datetime.now(UTC)
        cache_entry.id = "cache-123"
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry

        with patch.object(
            EuroleagueClient, "game_metadata", create=True
        ) as mock_gm_prop:
            mock_gm = MagicMock()
            mock_gm.get_gamecodes_season.return_value = pd.DataFrame(
                [{"gamecode": "E2024_NEW"}]
            )
            mock_gm_prop.__get__ = MagicMock(return_value=mock_gm)

            client = EuroleagueClient(mock_db)
            client._game_metadata = mock_gm

            result = client.fetch_season_games(2024, force=True)

            assert result.from_cache is False
            mock_gm.get_gamecodes_season.assert_called_once_with(2024)

    @patch("src.sync.euroleague.client.BoxScoreData")
    def test_fetch_multiple_boxscores(
        self, mock_boxscore_class, mock_db, sample_boxscore_df
    ):
        """Test fetch_multiple_boxscores fetches multiple games."""
        mock_bs_instance = MagicMock()
        mock_bs_instance.get_player_boxscore_stats_data.return_value = (
            sample_boxscore_df
        )
        mock_boxscore_class.return_value = mock_bs_instance

        client = EuroleagueClient(mock_db)
        client._boxscore = mock_bs_instance

        results = client.fetch_multiple_boxscores(2024, [1, 2, 3])

        assert len(results) == 3
        assert 1 in results
        assert 2 in results
        assert 3 in results
        assert mock_bs_instance.get_player_boxscore_stats_data.call_count == 3


class TestEuroleagueClientResourceIds:
    """Tests for resource ID generation in cache."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    def test_season_games_resource_id(self, mock_db):
        """Test season_games uses correct resource ID format."""
        client = EuroleagueClient(mock_db)

        # Euroleague - verify cache is queried
        client._get_cache("season_games", "E2024")
        mock_db.query.assert_called()

        # EuroCup
        config = EuroleagueConfig(competition="U")
        client = EuroleagueClient(mock_db, config=config)
        client._get_cache("season_games", "U2024")

    def test_boxscore_resource_id(self, mock_db):
        """Test boxscore uses correct resource ID format."""
        client = EuroleagueClient(mock_db)

        # Resource ID should be like "E2024_1"
        client._get_cache("boxscore", "E2024_1")
