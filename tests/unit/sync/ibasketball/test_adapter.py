"""
Unit tests for IBasketballAdapter.

Tests adapter with mocked dependencies.
"""

from unittest.mock import MagicMock

import pytest

from src.sync.ibasketball.adapter import IBasketballAdapter
from src.sync.ibasketball.api_client import CacheResult
from src.sync.ibasketball.config import IBasketballConfig
from src.sync.ibasketball.exceptions import IBasketballLeagueNotFoundError
from src.sync.ibasketball.mapper import IBasketballMapper
from src.sync.types import RawGame


class TestIBasketballAdapter:
    """Tests for IBasketballAdapter class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        return MagicMock()

    @pytest.fixture
    def mock_scraper(self):
        """Create mock scraper."""
        return MagicMock()

    @pytest.fixture
    def mapper(self):
        """Create real mapper instance."""
        return IBasketballMapper()

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return IBasketballConfig()

    @pytest.fixture
    def adapter(self, mock_client, mapper, mock_scraper, config):
        """Create adapter instance."""
        return IBasketballAdapter(
            client=mock_client,
            mapper=mapper,
            scraper=mock_scraper,
            config=config,
        )

    class TestSourceName:
        """Tests for source name attribute."""

        def test_source_name(self, adapter):
            """Test source name is correct."""
            assert adapter.source_name == "ibasketball"

    class TestSetLeague:
        """Tests for league switching."""

        def test_set_league_valid(self, adapter):
            """Test setting valid league."""
            adapter.set_league("liga_al")
            assert adapter._active_league_key == "liga_al"

        def test_set_league_invalid(self, adapter):
            """Test setting invalid league raises error."""
            with pytest.raises(IBasketballLeagueNotFoundError) as exc_info:
                adapter.set_league("invalid_league")

            assert exc_info.value.league_key == "invalid_league"
            assert "liga_leumit" in exc_info.value.available_leagues

        def test_set_league_clears_cache(self, adapter):
            """Test switching leagues clears events cache."""
            adapter._events_cache["119474"] = [{"id": 1}]

            adapter.set_league("liga_al")

            assert adapter._events_cache == {}

    class TestGetAvailableLeagues:
        """Tests for getting available leagues."""

        def test_get_available_leagues(self, adapter):
            """Test getting list of available leagues."""
            leagues = adapter.get_available_leagues()

            assert "liga_al" in leagues
            assert "liga_leumit" in leagues

    class TestGetSeasons:
        """Tests for getting seasons."""

        @pytest.mark.asyncio
        async def test_get_seasons(self, adapter, mock_client):
            """Test getting seasons with normalized name format."""
            mock_client.fetch_all_events.return_value = CacheResult(
                data=[
                    {"date": "2024-10-15T19:30:00"},
                    {"date": "2025-01-15T19:30:00"},
                ],
                changed=True,
                fetched_at=MagicMock(),
                cache_id="test",
            )

            seasons = await adapter.get_seasons()

            assert len(seasons) == 1
            # Name and external_id are normalized YYYY-YY format
            assert seasons[0].name == "2024-25"
            assert seasons[0].external_id == "2024-25"
            # Source-specific ID includes league key
            assert "liga_leumit" in seasons[0].source_id
            assert seasons[0].is_current is True

    class TestGetTeams:
        """Tests for getting teams."""

        @pytest.mark.asyncio
        async def test_get_teams(self, adapter, mock_client):
            """Test getting teams from events."""
            mock_client.fetch_all_events.return_value = CacheResult(
                data=[
                    {
                        "teams": [100, 101],
                        "team_names": {"100": "Team A", "101": "Team B"},
                    },
                ],
                changed=True,
                fetched_at=MagicMock(),
                cache_id="test",
            )

            teams = await adapter.get_teams("2024-25")

            assert len(teams) == 2
            team_names = [t.name for t in teams]
            assert "Team A" in team_names
            assert "Team B" in team_names

    class TestGetSchedule:
        """Tests for getting schedule."""

        @pytest.mark.asyncio
        async def test_get_schedule(self, adapter, mock_client):
            """Test getting game schedule."""
            mock_client.fetch_all_events.return_value = CacheResult(
                data=[
                    {
                        "id": 123,
                        "teams": [100, 101],
                        "date": "2024-01-15T19:30:00",
                        "results": {"100": {"pts": 85}, "101": {"pts": 78}},
                    },
                ],
                changed=True,
                fetched_at=MagicMock(),
                cache_id="test",
            )

            games = await adapter.get_schedule("2024-25")

            assert len(games) == 1
            assert games[0].external_id == "123"
            assert games[0].home_score == 85

    class TestGetGameBoxscore:
        """Tests for getting boxscore."""

        @pytest.mark.asyncio
        async def test_get_game_boxscore(self, adapter, mock_client):
            """Test getting game boxscore."""
            mock_client.fetch_event.return_value = CacheResult(
                data={
                    "id": 123,
                    "teams": [100, 101],
                    "date": "2024-01-15T19:30:00",
                    "results": {"100": {"pts": 85}, "101": {"pts": 78}},
                    "performance": {
                        "100": {"1001": {"pts": 22}},
                        "101": {"2001": {"pts": 20}},
                    },
                    "player_names": {"1001": "Player A", "2001": "Player B"},
                },
                changed=True,
                fetched_at=MagicMock(),
                cache_id="test",
            )

            boxscore = await adapter.get_game_boxscore("123")

            assert boxscore.game.external_id == "123"
            assert len(boxscore.home_players) == 1
            assert len(boxscore.away_players) == 1

    class TestGetGamePBP:
        """Tests for getting play-by-play."""

        @pytest.mark.asyncio
        async def test_get_game_pbp_no_scraper(self, adapter):
            """Test getting PBP without scraper returns empty."""
            adapter.scraper = None

            events = await adapter.get_game_pbp("123")

            assert events == []

        @pytest.mark.asyncio
        async def test_get_game_pbp_with_scraper(
            self, adapter, mock_client, mock_scraper
        ):
            """Test getting PBP with scraper."""
            mock_client.fetch_event.return_value = CacheResult(
                data={"id": 123, "slug": "team-a-vs-team-b"},
                changed=True,
                fetched_at=MagicMock(),
                cache_id="test",
            )

            mock_pbp = MagicMock()
            mock_pbp.events = [
                MagicMock(
                    period=1,
                    clock="09:45",
                    type="קליעה",
                    player="Player A",
                    team_id="100",
                    team_name="Team A",
                    success=True,
                ),
            ]
            mock_scraper.fetch_game_pbp.return_value = mock_pbp

            events = await adapter.get_game_pbp("123")

            assert len(events) == 1
            assert events[0].event_type == "shot"
            mock_scraper.fetch_game_pbp.assert_called_once_with("team-a-vs-team-b")

    class TestIsGameFinal:
        """Tests for checking game final status."""

        def test_is_game_final_true(self, adapter):
            """Test game with final status and scores."""
            game = RawGame(
                external_id="123",
                home_team_external_id="100",
                away_team_external_id="101",
                game_date=MagicMock(),
                status="final",
                home_score=85,
                away_score=78,
            )

            assert adapter.is_game_final(game) is True

        def test_is_game_final_no_scores(self, adapter):
            """Test game with final status but no scores."""
            game = RawGame(
                external_id="123",
                home_team_external_id="100",
                away_team_external_id="101",
                game_date=MagicMock(),
                status="final",
                home_score=None,
                away_score=None,
            )

            assert adapter.is_game_final(game) is False

        def test_is_game_final_scheduled(self, adapter):
            """Test scheduled game."""
            game = RawGame(
                external_id="123",
                home_team_external_id="100",
                away_team_external_id="101",
                game_date=MagicMock(),
                status="scheduled",
                home_score=None,
                away_score=None,
            )

            assert adapter.is_game_final(game) is False

    class TestGetPlayerInfo:
        """Tests for getting player info."""

        @pytest.mark.asyncio
        async def test_get_player_info_no_scraper(self, adapter):
            """Test getting player info without scraper."""
            adapter.scraper = None

            info = await adapter.get_player_info("john-smith")

            assert info.external_id == "john-smith"
            assert (
                "John Smith" in info.last_name or "john smith" in info.last_name.lower()
            )

        @pytest.mark.asyncio
        async def test_get_player_info_with_scraper(self, adapter, mock_scraper):
            """Test getting player info with scraper."""
            mock_profile = MagicMock()
            mock_profile.name = "John Smith"
            mock_profile.team_name = "Team A"
            mock_profile.position = "SF"
            mock_profile.height_cm = 198
            mock_profile.birth_date = None
            mock_profile.nationality = "USA"

            mock_scraper.fetch_player.return_value = mock_profile

            info = await adapter.get_player_info("john-smith")

            assert info.first_name == "John"
            assert info.last_name == "Smith"
            assert info.height_cm == 198

    class TestSearchPlayer:
        """Tests for player search."""

        @pytest.mark.asyncio
        async def test_search_player_not_implemented(self, adapter):
            """Test player search returns empty list (not implemented)."""
            results = await adapter.search_player("Smith")

            assert results == []
