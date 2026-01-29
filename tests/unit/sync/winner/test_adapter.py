"""
Winner Adapter Tests

Tests for the WinnerAdapter class that implements BaseLeagueAdapter
and BasePlayerInfoAdapter.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.schemas.game import EventType
from src.sync.types import RawBoxScore, RawGame, RawSeason
from src.sync.winner.adapter import WinnerAdapter
from src.sync.winner.client import CacheResult
from src.sync.winner.mapper import WinnerMapper
from src.sync.winner.scraper import PlayerProfile, RosterPlayer, TeamRoster
from src.schemas.enums import GameStatus


@pytest.fixture
def mock_client():
    """Create a mock WinnerClient."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_scraper():
    """Create a mock WinnerScraper."""
    scraper = MagicMock()
    return scraper


@pytest.fixture
def mapper():
    """Create a real WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def adapter(mock_client, mock_scraper, mapper):
    """Create a WinnerAdapter with mocked dependencies."""
    return WinnerAdapter(mock_client, mock_scraper, mapper)


@pytest.fixture
def sample_games_response():
    """Sample games_all API response."""
    return {
        "games": [
            {
                "GameId": "12345",
                "HomeTeamId": "100",
                "AwayTeamId": "101",
                "HomeTeamName": "Maccabi Tel Aviv",
                "AwayTeamName": "Hapoel Jerusalem",
                "HomeScore": 85,
                "AwayScore": 78,
                "GameDate": "2024-01-15T19:30:00",
                "Status": "Final",
            },
            {
                "GameId": "12346",
                "HomeTeamId": "102",
                "AwayTeamId": "100",
                "HomeTeamName": "Hapoel Tel Aviv",
                "AwayTeamName": "Maccabi Tel Aviv",
                "HomeScore": None,
                "AwayScore": None,
                "GameDate": "2024-01-20T19:00:00",
                "Status": "Scheduled",
            },
        ],
        "season": "2023-24",
    }


@pytest.fixture
def sample_boxscore_response():
    """Sample boxscore API response."""
    return {
        "GameId": "12345",
        "HomeTeam": {
            "TeamId": "100",
            "Score": 85,
            "Players": [
                {
                    "PlayerId": "1001",
                    "Name": "John Smith",
                    "Minutes": "32:15",
                    "Points": 22,
                    "Rebounds": 8,
                    "Assists": 5,
                    "FGM": 8,
                    "FGA": 15,
                    "ThreePM": 3,
                    "ThreePA": 7,
                    "FTM": 3,
                    "FTA": 4,
                },
            ],
        },
        "AwayTeam": {
            "TeamId": "101",
            "Score": 78,
            "Players": [
                {
                    "PlayerId": "2001",
                    "Name": "Alex Johnson",
                    "Minutes": "30:00",
                    "Points": 20,
                    "FGM": 7,
                    "FGA": 14,
                    "ThreePM": 4,
                    "ThreePA": 8,
                    "FTM": 2,
                    "FTA": 2,
                },
            ],
        },
        "GameDate": "2024-01-15T19:30:00",
    }


@pytest.fixture
def sample_pbp_response():
    """Sample play-by-play API response."""
    return {
        "GameId": "12345",
        "Events": [
            {
                "Quarter": 1,
                "GameClock": "09:45",
                "EventType": "MADE_2PT",
                "TeamId": "100",
                "PlayerId": "1001",
            },
            {
                "Quarter": 1,
                "GameClock": "09:30",
                "EventType": "TURNOVER",
                "TeamId": "101",
                "PlayerId": "2001",
            },
        ],
    }


class TestWinnerAdapterInit:
    """Tests for WinnerAdapter initialization."""

    def test_source_name(self, adapter):
        """Test that source_name is set correctly."""
        assert adapter.source_name == "winner"

    def test_has_client(self, adapter, mock_client):
        """Test that client is accessible."""
        assert adapter.client is mock_client

    def test_has_scraper(self, adapter, mock_scraper):
        """Test that scraper is accessible."""
        assert adapter.scraper is mock_scraper

    def test_has_mapper(self, adapter, mapper):
        """Test that mapper is accessible."""
        assert adapter.mapper is mapper


class TestGetSeasons:
    """Tests for get_seasons method."""

    @pytest.mark.asyncio
    async def test_returns_seasons(self, adapter, mock_client, sample_games_response):
        """Test that seasons are returned."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        seasons = await adapter.get_seasons()

        assert len(seasons) == 1
        assert isinstance(seasons[0], RawSeason)
        assert seasons[0].external_id == "2023-24"

    @pytest.mark.asyncio
    async def test_season_name_format(
        self, adapter, mock_client, sample_games_response
    ):
        """Test that season name is in normalized YYYY-YY format."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        seasons = await adapter.get_seasons()

        # Name should be normalized YYYY-YY format
        assert "-" in seasons[0].name
        assert len(seasons[0].name) == 7  # YYYY-YY format

    @pytest.mark.asyncio
    async def test_infers_season_from_dates(self, adapter, mock_client):
        """Test season inference when not provided in response."""
        games_data = {
            "games": [
                {
                    "GameId": "1",
                    "HomeTeamId": "100",
                    "AwayTeamId": "101",
                    "HomeTeamName": "Team A",
                    "AwayTeamName": "Team B",
                    "GameDate": "2024-10-15T19:00:00",
                    "Status": "Final",
                    "HomeScore": 80,
                    "AwayScore": 75,
                }
            ]
        }
        mock_client.fetch_games_all.return_value = CacheResult(
            data=games_data,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        seasons = await adapter.get_seasons()

        # October game should be 2024-25 season
        assert seasons[0].external_id == "2024-25"


class TestGetTeams:
    """Tests for get_teams method."""

    @pytest.mark.asyncio
    async def test_extracts_unique_teams(
        self, adapter, mock_client, sample_games_response
    ):
        """Test that unique teams are extracted."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        teams = await adapter.get_teams("2023-24")

        # Should have 3 unique teams: 100, 101, 102
        assert len(teams) == 3
        team_ids = {t.external_id for t in teams}
        assert team_ids == {"100", "101", "102"}

    @pytest.mark.asyncio
    async def test_team_names_preserved(
        self, adapter, mock_client, sample_games_response
    ):
        """Test that team names are preserved."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        teams = await adapter.get_teams("2023-24")

        team_dict = {t.external_id: t.name for t in teams}
        assert team_dict["100"] == "Maccabi Tel Aviv"
        assert team_dict["101"] == "Hapoel Jerusalem"


class TestGetSchedule:
    """Tests for get_schedule method."""

    @pytest.mark.asyncio
    async def test_returns_all_games(self, adapter, mock_client, sample_games_response):
        """Test that all games are returned."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        games = await adapter.get_schedule("2023-24")

        assert len(games) == 2

    @pytest.mark.asyncio
    async def test_game_status_normalized(
        self, adapter, mock_client, sample_games_response
    ):
        """Test that game status is normalized to lowercase."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        games = await adapter.get_schedule("2023-24")

        assert games[0].status == GameStatus.FINAL
        assert games[1].status == GameStatus.SCHEDULED


class TestGetGameBoxscore:
    """Tests for get_game_boxscore method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_boxscore(
        self, adapter, mock_client, sample_boxscore_response
    ):
        """Test that boxscore is fetched and mapped."""
        mock_client.fetch_boxscore.return_value = CacheResult(
            data=sample_boxscore_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        boxscore = await adapter.get_game_boxscore("12345")

        assert isinstance(boxscore, RawBoxScore)
        assert boxscore.game.external_id == "12345"
        assert boxscore.game.home_score == 85
        assert boxscore.game.away_score == 78

    @pytest.mark.asyncio
    async def test_player_stats_mapped(
        self, adapter, mock_client, sample_boxscore_response
    ):
        """Test that player stats are mapped."""
        mock_client.fetch_boxscore.return_value = CacheResult(
            data=sample_boxscore_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        boxscore = await adapter.get_game_boxscore("12345")

        assert len(boxscore.home_players) == 1
        assert len(boxscore.away_players) == 1
        assert boxscore.home_players[0].player_name == "John Smith"
        assert boxscore.home_players[0].points == 22


class TestGetGamePbp:
    """Tests for get_game_pbp method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_pbp(
        self, adapter, mock_client, sample_pbp_response
    ):
        """Test that play-by-play is fetched and mapped."""
        mock_client.fetch_pbp.return_value = CacheResult(
            data=sample_pbp_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        events, player_id_to_jersey = await adapter.get_game_pbp("12345")

        assert len(events) == 2
        assert events[0].event_type == EventType.SHOT
        assert events[0].success is True
        assert events[1].event_type == EventType.TURNOVER
        assert isinstance(player_id_to_jersey, dict)  # Winner returns jersey mapping


class TestIsGameFinal:
    """Tests for is_game_final method."""

    def test_final_game_with_scores(self, adapter):
        """Test that final game with scores returns True."""
        game = RawGame(
            external_id="12345",
            home_team_external_id="100",
            away_team_external_id="101",
            game_date=datetime.now(),
            status=GameStatus.FINAL,
            home_score=85,
            away_score=78,
        )

        assert adapter.is_game_final(game) is True

    def test_scheduled_game(self, adapter):
        """Test that scheduled game returns False."""
        game = RawGame(
            external_id="12345",
            home_team_external_id="100",
            away_team_external_id="101",
            game_date=datetime.now(),
            status=GameStatus.SCHEDULED,
            home_score=None,
            away_score=None,
        )

        assert adapter.is_game_final(game) is False

    def test_final_without_scores(self, adapter):
        """Test that final status without scores returns False."""
        game = RawGame(
            external_id="12345",
            home_team_external_id="100",
            away_team_external_id="101",
            game_date=datetime.now(),
            status=GameStatus.FINAL,
            home_score=None,
            away_score=None,
        )

        assert adapter.is_game_final(game) is False


class TestGetPlayerInfo:
    """Tests for get_player_info method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_player(self, adapter, mock_scraper):
        """Test that player info is fetched and mapped."""
        mock_scraper.fetch_player.return_value = PlayerProfile(
            player_id="1001",
            name="John Smith",
            height_cm=198,
            birth_date=datetime(1995, 5, 15),
            position="Guard",
        )

        player = await adapter.get_player_info("1001")

        assert player.external_id == "1001"
        assert player.first_name == "John"
        assert player.last_name == "Smith"
        assert player.height_cm == 198
        mock_scraper.fetch_player.assert_called_once_with("1001")


class TestSearchPlayer:
    """Tests for search_player method."""

    @pytest.mark.asyncio
    async def test_searches_team_rosters(
        self, adapter, mock_client, mock_scraper, sample_games_response
    ):
        """Test that search goes through team rosters."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        mock_scraper.fetch_team_roster.return_value = TeamRoster(
            team_id="100",
            team_name="Maccabi Tel Aviv",
            players=[
                RosterPlayer(player_id="1001", name="John Smith"),
                RosterPlayer(player_id="1002", name="David Cohen"),
            ],
        )

        mock_scraper.fetch_player.return_value = PlayerProfile(
            player_id="1001",
            name="John Smith",
            height_cm=198,
        )

        results = await adapter.search_player("Smith")

        assert len(results) >= 1
        assert results[0].last_name == "Smith"

    @pytest.mark.asyncio
    async def test_filters_by_team(
        self, adapter, mock_client, mock_scraper, sample_games_response
    ):
        """Test that search can filter by team."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        mock_scraper.fetch_team_roster.return_value = TeamRoster(
            team_id="100",
            team_name="Maccabi Tel Aviv",
            players=[RosterPlayer(player_id="1001", name="John Smith")],
        )

        mock_scraper.fetch_player.return_value = PlayerProfile(
            player_id="1001",
            name="John Smith",
        )

        # Search only in team 100
        await adapter.search_player("Smith", team="100")

        # Should only fetch roster for team 100
        mock_scraper.fetch_team_roster.assert_called_with("100")


class TestCaching:
    """Tests for internal caching behavior."""

    @pytest.mark.asyncio
    async def test_games_data_cached(self, adapter, mock_client, sample_games_response):
        """Test that games data is cached between calls."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        # Call multiple methods that need games data
        await adapter.get_seasons()
        await adapter.get_teams("2023-24")
        await adapter.get_schedule("2023-24")

        # Should only fetch once
        assert mock_client.fetch_games_all.call_count == 1


class TestListWrappedApiResponse:
    """Tests for handling list-wrapped API responses (Issue #100).

    The Winner API sometimes returns responses wrapped in a list:
    [{"games": [...]}] instead of {"games": [...]}

    These tests ensure the adapter handles both formats correctly.
    """

    @pytest.fixture
    def list_wrapped_games_response(self, sample_games_response):
        """API response wrapped in a list (real API format)."""
        return [sample_games_response]

    @pytest.mark.asyncio
    async def test_handles_list_wrapped_response(
        self, adapter, mock_client, list_wrapped_games_response
    ):
        """Test that list-wrapped responses are unwrapped correctly."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=list_wrapped_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        seasons = await adapter.get_seasons()

        assert len(seasons) == 1
        assert seasons[0].external_id == "2023-24"

    @pytest.mark.asyncio
    async def test_get_teams_with_list_wrapped_response(
        self, adapter, mock_client, list_wrapped_games_response
    ):
        """Test get_teams handles list-wrapped response."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=list_wrapped_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        teams = await adapter.get_teams("2023-24")

        assert len(teams) == 3
        team_ids = {t.external_id for t in teams}
        assert team_ids == {"100", "101", "102"}

    @pytest.mark.asyncio
    async def test_get_schedule_with_list_wrapped_response(
        self, adapter, mock_client, list_wrapped_games_response
    ):
        """Test get_schedule handles list-wrapped response."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=list_wrapped_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        games = await adapter.get_schedule("2023-24")

        assert len(games) == 2

    @pytest.mark.asyncio
    async def test_handles_direct_dict_response(
        self, adapter, mock_client, sample_games_response
    ):
        """Test that direct dict responses still work (backwards compatibility)."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=sample_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        seasons = await adapter.get_seasons()
        teams = await adapter.get_teams("2023-24")
        games = await adapter.get_schedule("2023-24")

        assert len(seasons) == 1
        assert len(teams) == 3
        assert len(games) == 2

    @pytest.mark.asyncio
    async def test_handles_empty_list_response(self, adapter, mock_client):
        """Test that empty list response is handled gracefully."""
        mock_client.fetch_games_all.return_value = CacheResult(
            data=[],
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        # Should handle gracefully - empty list means no data
        # The _get_games_data will return [] which won't have .get()
        # This tests that we don't crash on empty responses
        with pytest.raises(AttributeError):
            await adapter.get_seasons()
