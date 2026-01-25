"""
Player Info Service Tests

Tests for the PlayerInfoService class.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.sync.player_info.service import PlayerInfoService
from src.sync.types import RawPlayerInfo


@pytest.fixture
def mock_winner_adapter():
    """Create a mock winner adapter."""
    adapter = MagicMock()
    adapter.source_name = "winner"
    adapter.get_player_info = AsyncMock()
    adapter.search_player = AsyncMock()
    return adapter


@pytest.fixture
def mock_euroleague_adapter():
    """Create a mock euroleague adapter."""
    adapter = MagicMock()
    adapter.source_name = "euroleague"
    adapter.get_player_info = AsyncMock()
    adapter.search_player = AsyncMock()
    return adapter


@pytest.fixture
def service(mock_winner_adapter, mock_euroleague_adapter):
    """Create a PlayerInfoService with mocked adapters."""
    return PlayerInfoService([mock_winner_adapter, mock_euroleague_adapter])


@pytest.fixture
def single_adapter_service(mock_winner_adapter):
    """Create a PlayerInfoService with a single adapter."""
    return PlayerInfoService([mock_winner_adapter])


class TestPlayerInfoServiceInit:
    """Tests for PlayerInfoService initialization."""

    def test_stores_adapters(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that adapters are stored."""
        assert service.adapters == [mock_winner_adapter, mock_euroleague_adapter]

    def test_builds_adapter_map(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that adapter map is built correctly."""
        assert service._adapter_map["winner"] is mock_winner_adapter
        assert service._adapter_map["euroleague"] is mock_euroleague_adapter

    def test_source_names_property(self, service):
        """Test source_names property."""
        assert service.source_names == ["winner", "euroleague"]

    def test_get_adapter(self, service, mock_winner_adapter):
        """Test get_adapter method."""
        assert service.get_adapter("winner") is mock_winner_adapter

    def test_get_adapter_not_found(self, service):
        """Test get_adapter returns None for unknown source."""
        assert service.get_adapter("unknown") is None


class TestGetPlayerInfo:
    """Tests for get_player_info method."""

    @pytest.mark.asyncio
    async def test_fetches_from_single_source(
        self, single_adapter_service, mock_winner_adapter
    ):
        """Test fetching from a single source."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )

        merged = await single_adapter_service.get_player_info({"winner": "w123"})

        assert merged is not None
        assert merged.first_name == "John"
        assert merged.last_name == "Smith"
        assert merged.height_cm == 198
        mock_winner_adapter.get_player_info.assert_called_once_with("w123")

    @pytest.mark.asyncio
    async def test_fetches_from_multiple_sources(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test fetching from multiple sources."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )
        mock_euroleague_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="e456",
            first_name="John",
            last_name="Smith",
            position="PG",
        )

        merged = await service.get_player_info(
            {
                "winner": "w123",
                "euroleague": "e456",
            }
        )

        assert merged is not None
        assert merged.first_name == "John"
        assert merged.height_cm == 198  # From winner (first source)
        assert merged.position == "PG"  # From euroleague (not in winner)
        assert merged.sources["height_cm"] == "winner"
        assert merged.sources["position"] == "euroleague"

    @pytest.mark.asyncio
    async def test_respects_adapter_priority(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that adapter priority is respected."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )
        mock_euroleague_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="e456",
            first_name="Johnny",
            last_name="Smith",
            height_cm=200,
        )

        merged = await service.get_player_info(
            {
                "winner": "w123",
                "euroleague": "e456",
            }
        )

        # Winner is first in adapter list, so its values take priority
        assert merged.first_name == "John"
        assert merged.height_cm == 198
        assert merged.sources["first_name"] == "winner"
        assert merged.sources["height_cm"] == "winner"

    @pytest.mark.asyncio
    async def test_skips_sources_not_in_external_ids(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that sources not in external_ids are skipped."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
        )

        merged = await service.get_player_info({"winner": "w123"})

        assert merged is not None
        mock_winner_adapter.get_player_info.assert_called_once()
        mock_euroleague_adapter.get_player_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_external_ids(self, service):
        """Test that empty external_ids returns None."""
        merged = await service.get_player_info({})

        assert merged is None

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_sources(self, service):
        """Test that unknown sources are ignored."""
        merged = await service.get_player_info({"unknown": "123"})

        assert merged is None

    @pytest.mark.asyncio
    async def test_handles_adapter_error(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that adapter errors are handled gracefully."""
        mock_winner_adapter.get_player_info.side_effect = Exception("API Error")
        mock_euroleague_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="e456",
            first_name="John",
            last_name="Smith",
        )

        merged = await service.get_player_info(
            {
                "winner": "w123",
                "euroleague": "e456",
            }
        )

        # Should still return merged data from euroleague
        assert merged is not None
        assert merged.first_name == "John"
        assert merged.sources["first_name"] == "euroleague"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_adapters_fail(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test returns None when all adapters fail."""
        mock_winner_adapter.get_player_info.side_effect = Exception("API Error")
        mock_euroleague_adapter.get_player_info.side_effect = Exception("API Error")

        merged = await service.get_player_info(
            {
                "winner": "w123",
                "euroleague": "e456",
            }
        )

        assert merged is None


class TestGetPlayerInfoFromSource:
    """Tests for get_player_info_from_source method."""

    @pytest.mark.asyncio
    async def test_fetches_from_specified_source(self, service, mock_winner_adapter):
        """Test fetching from a specific source."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
        )

        info = await service.get_player_info_from_source("winner", "w123")

        assert info is not None
        assert info.first_name == "John"
        mock_winner_adapter.get_player_info.assert_called_once_with("w123")

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_source(self, service):
        """Test that unknown source returns None."""
        info = await service.get_player_info_from_source("unknown", "123")

        assert info is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self, service, mock_winner_adapter):
        """Test that errors return None."""
        mock_winner_adapter.get_player_info.side_effect = Exception("API Error")

        info = await service.get_player_info_from_source("winner", "w123")

        assert info is None


class TestSearchPlayer:
    """Tests for search_player method."""

    @pytest.mark.asyncio
    async def test_searches_all_adapters(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that all adapters are searched."""
        mock_winner_adapter.search_player.return_value = [
            RawPlayerInfo(
                external_id="w123",
                first_name="John",
                last_name="Smith",
            ),
        ]
        mock_euroleague_adapter.search_player.return_value = [
            RawPlayerInfo(
                external_id="e456",
                first_name="Johnny",
                last_name="Smith",
            ),
        ]

        results = await service.search_player("Smith")

        assert len(results) == 2
        mock_winner_adapter.search_player.assert_called_once_with("Smith", None)
        mock_euroleague_adapter.search_player.assert_called_once_with("Smith", None)

    @pytest.mark.asyncio
    async def test_passes_team_filter(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that team filter is passed to adapters."""
        mock_winner_adapter.search_player.return_value = []
        mock_euroleague_adapter.search_player.return_value = []

        await service.search_player("Smith", team="100")

        mock_winner_adapter.search_player.assert_called_once_with("Smith", "100")
        mock_euroleague_adapter.search_player.assert_called_once_with("Smith", "100")

    @pytest.mark.asyncio
    async def test_handles_adapter_error(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that adapter errors are handled gracefully."""
        mock_winner_adapter.search_player.side_effect = Exception("API Error")
        mock_euroleague_adapter.search_player.return_value = [
            RawPlayerInfo(
                external_id="e456",
                first_name="John",
                last_name="Smith",
            ),
        ]

        results = await service.search_player("Smith")

        # Should still return results from euroleague
        assert len(results) == 1
        assert results[0].external_id == "e456"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_results(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test returns empty list when no results."""
        mock_winner_adapter.search_player.return_value = []
        mock_euroleague_adapter.search_player.return_value = []

        results = await service.search_player("NonexistentPlayer")

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_all_adapters_fail(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test returns empty list when all adapters fail."""
        mock_winner_adapter.search_player.side_effect = Exception("API Error")
        mock_euroleague_adapter.search_player.side_effect = Exception("API Error")

        results = await service.search_player("Smith")

        assert results == []


class TestUpdatePlayerFromSources:
    """Tests for update_player_from_sources method."""

    @pytest.mark.asyncio
    async def test_returns_updates_dict(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test that updates dict is returned."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )
        mock_euroleague_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="e456",
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 5, 15),
            position="PG",
        )

        player = MagicMock()
        player.external_ids = {"winner": "w123", "euroleague": "e456"}

        updates = await service.update_player_from_sources(player)

        assert updates["first_name"] == "John"
        assert updates["last_name"] == "Smith"
        assert updates["height_cm"] == 198
        assert updates["birth_date"] == date(1995, 5, 15)
        assert updates["position"] == "PG"

    @pytest.mark.asyncio
    async def test_returns_empty_dict_for_no_external_ids(self, service):
        """Test returns empty dict when player has no external_ids."""
        player = MagicMock()
        player.external_ids = {}

        updates = await service.update_player_from_sources(player)

        assert updates == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_data_fetched(
        self, service, mock_winner_adapter, mock_euroleague_adapter
    ):
        """Test returns empty dict when no data is fetched."""
        mock_winner_adapter.get_player_info.side_effect = Exception("API Error")
        mock_euroleague_adapter.get_player_info.side_effect = Exception("API Error")

        player = MagicMock()
        player.external_ids = {"winner": "w123", "euroleague": "e456"}

        updates = await service.update_player_from_sources(player)

        assert updates == {}

    @pytest.mark.asyncio
    async def test_handles_missing_external_ids_attribute(self, service):
        """Test handles player without external_ids attribute."""
        player = MagicMock(spec=[])  # No attributes

        updates = await service.update_player_from_sources(player)

        assert updates == {}

    @pytest.mark.asyncio
    async def test_excludes_none_values(self, service, mock_winner_adapter):
        """Test that None values are excluded from updates."""
        mock_winner_adapter.get_player_info.return_value = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
            # No height_cm, birth_date, or position
        )

        player = MagicMock()
        player.external_ids = {"winner": "w123"}

        updates = await service.update_player_from_sources(player)

        assert "first_name" in updates
        assert "last_name" in updates
        assert "height_cm" not in updates
        assert "birth_date" not in updates
        assert "position" not in updates


class TestEmptyService:
    """Tests for service with no adapters."""

    @pytest.fixture
    def empty_service(self):
        """Create a service with no adapters."""
        return PlayerInfoService([])

    @pytest.mark.asyncio
    async def test_get_player_info_returns_none(self, empty_service):
        """Test get_player_info returns None with no adapters."""
        merged = await empty_service.get_player_info({"winner": "w123"})
        assert merged is None

    @pytest.mark.asyncio
    async def test_search_player_returns_empty(self, empty_service):
        """Test search_player returns empty list with no adapters."""
        results = await empty_service.search_player("Smith")
        assert results == []

    def test_source_names_empty(self, empty_service):
        """Test source_names is empty."""
        assert empty_service.source_names == []
