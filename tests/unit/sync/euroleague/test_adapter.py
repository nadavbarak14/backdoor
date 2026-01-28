"""
Euroleague Adapter Tests

Tests for the EuroleagueAdapter class that implements BaseLeagueAdapter
and BasePlayerInfoAdapter.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.sync.euroleague.adapter import EuroleagueAdapter
from src.sync.euroleague.direct_client import CacheResult
from src.sync.euroleague.mapper import EuroleagueMapper
from src.sync.types import RawBoxScore, RawGame


@pytest.fixture
def mock_client():
    """Create a mock EuroleagueClient."""
    return MagicMock()


@pytest.fixture
def mock_direct_client():
    """Create a mock EuroleagueDirectClient."""
    return MagicMock()


@pytest.fixture
def mapper():
    """Create a real EuroleagueMapper instance."""
    return EuroleagueMapper()


@pytest.fixture
def adapter(mock_client, mock_direct_client, mapper):
    """Create an EuroleagueAdapter with mocked dependencies."""
    return EuroleagueAdapter(
        mock_client,
        mock_direct_client,
        mapper,
        competition="E",
        configured_seasons=[2024, 2023],
    )


@pytest.fixture
def sample_teams_response():
    """Sample teams API response."""
    return [
        {
            "code": "BER",
            "tv_code": "BER",
            "name": "ALBA Berlin",
            "country_code": "GER",
            "players": [
                {"code": "P007025", "name": "MATTISSECK, JONAS", "position": "Guard"},
                {"code": "P008780", "name": "HERMANNSSON, MARTIN", "position": "Guard"},
            ],
        },
        {
            "code": "PAN",
            "tv_code": "PAO",
            "name": "Panathinaikos AKTOR Athens",
            "country_code": "GRE",
            "players": [
                {"code": "P012774", "name": "NUNN, KENDRICK", "position": "Guard"},
            ],
        },
    ]


@pytest.fixture
def sample_season_games_response():
    """Sample season games API response."""
    return [
        {
            "gamecode": 1,
            "hometeam": "BER",
            "awayteam": "PAN",
            "date": "Oct 03, 2024",
            "homescore": 77,
            "awayscore": 87,
        },
        {
            "gamecode": 2,
            "hometeam": "PAN",
            "awayteam": "BER",
            "date": "Dec 15, 2024",
            "homescore": None,
            "awayscore": None,
        },
    ]


@pytest.fixture
def sample_boxscore_response():
    """Sample live boxscore API response."""
    return {
        "Live": False,
        "ByQuarter": [
            {
                "Team": "ALBA BERLIN",
                "Quarter1": 17,
                "Quarter2": 19,
                "Quarter3": 21,
                "Quarter4": 20,
            },
            {
                "Team": "PANATHINAIKOS",
                "Quarter1": 26,
                "Quarter2": 19,
                "Quarter3": 17,
                "Quarter4": 25,
            },
        ],
        "Stats": [
            {
                "Team": "ALBA BERLIN",
                "PlayersStats": [
                    {
                        "Player_ID": "P007025",
                        "IsStarter": 1,
                        "Team": "BER",
                        "Player": "MATTISSECK, JONAS",
                        "Minutes": "24:35",
                        "Points": 6,
                        "FieldGoalsMade2": 2,
                        "FieldGoalsAttempted2": 4,
                    },
                ],
            },
            {
                "Team": "PANATHINAIKOS",
                "PlayersStats": [
                    {
                        "Player_ID": "P012774",
                        "IsStarter": 1,
                        "Team": "PAN",
                        "Player": "NUNN, KENDRICK",
                        "Minutes": "30:15",
                        "Points": 22,
                        "FieldGoalsMade2": 5,
                        "FieldGoalsAttempted2": 8,
                    },
                ],
            },
        ],
    }


@pytest.fixture
def sample_pbp_response():
    """Sample live PBP API response."""
    return {
        "FirstQuarter": [
            {
                "PLAYTYPE": "2FGM",
                "MARKERTIME": "09:45",
                "TEAM": "BER",
                "PLAYERNAME": "MATTISSECK, JONAS",
            },
            {"PLAYTYPE": "D", "MARKERTIME": "09:30", "TEAM": "PAN"},
        ],
        "SecondQuarter": [
            {"PLAYTYPE": "3FGA", "MARKERTIME": "08:00", "TEAM": "PAN"},
        ],
    }


@pytest.fixture
def sample_player_response():
    """Sample player API response."""
    return {
        "name": "EDWARDS, CARSEN",
        "height": "1.8",
        "birthdate": "12 March, 1998",
        "position": "Guard",
    }


class TestEuroleagueAdapterInit:
    """Tests for EuroleagueAdapter initialization."""

    def test_source_name(self, adapter):
        """Test that source_name is set correctly."""
        assert adapter.source_name == "euroleague"

    def test_has_clients(self, adapter, mock_client, mock_direct_client):
        """Test that clients are accessible."""
        assert adapter.client is mock_client
        assert adapter.direct_client is mock_direct_client

    def test_has_mapper(self, adapter, mapper):
        """Test that mapper is accessible."""
        assert adapter.mapper is mapper

    def test_configured_seasons(self, adapter):
        """Test that configured seasons are set."""
        assert adapter.configured_seasons == [2024, 2023]


class TestParseSeasonId:
    """Tests for _parse_season_id method."""

    def test_euroleague_season(self, adapter):
        """Test parsing Euroleague season ID."""
        comp, year = adapter._parse_season_id("E2024")
        assert comp == "E"
        assert year == 2024

    def test_eurocup_season(self, adapter):
        """Test parsing EuroCup season ID."""
        comp, year = adapter._parse_season_id("U2024")
        assert comp == "U"
        assert year == 2024

    def test_invalid_season_id(self, adapter):
        """Test invalid season ID raises error."""
        with pytest.raises(ValueError):
            adapter._parse_season_id("X")


class TestParseGameId:
    """Tests for _parse_game_id method."""

    def test_valid_game_id(self, adapter):
        """Test parsing valid game ID."""
        comp, season, gamecode = adapter._parse_game_id("E2024_1")
        assert comp == "E"
        assert season == 2024
        assert gamecode == 1

    def test_invalid_game_id(self, adapter):
        """Test invalid game ID raises error."""
        with pytest.raises(ValueError):
            adapter._parse_game_id("invalid")


class TestGetSeasons:
    """Tests for get_seasons method."""

    @pytest.mark.asyncio
    async def test_returns_configured_seasons(self, adapter):
        """Test that configured seasons are returned with normalized names."""
        seasons = await adapter.get_seasons()

        assert len(seasons) == 2
        # external_id is now normalized YYYY-YY format
        assert seasons[0].external_id == "2024-25"
        assert seasons[1].external_id == "2023-24"
        # source_id preserves original Euroleague format
        assert seasons[0].source_id == "E2024"
        assert seasons[1].source_id == "E2023"

    @pytest.mark.asyncio
    async def test_marks_current_season(self, adapter):
        """Test that most recent season is marked current."""
        seasons = await adapter.get_seasons()

        current_seasons = [s for s in seasons if s.is_current]
        assert len(current_seasons) == 1
        assert current_seasons[0].name == "2024-25"


class TestGetTeams:
    """Tests for get_teams method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_teams(
        self, adapter, mock_direct_client, sample_teams_response
    ):
        """Test that teams are fetched and mapped."""
        mock_direct_client.fetch_teams.return_value = CacheResult(
            data=sample_teams_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        teams = await adapter.get_teams("E2024")

        assert len(teams) == 2
        assert teams[0].external_id == "BER"
        assert teams[0].name == "ALBA Berlin"
        assert teams[1].external_id == "PAN"

    @pytest.mark.asyncio
    async def test_caches_teams(
        self, adapter, mock_direct_client, sample_teams_response
    ):
        """Test that teams are cached."""
        mock_direct_client.fetch_teams.return_value = CacheResult(
            data=sample_teams_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        # Call twice
        await adapter.get_teams("E2024")
        await adapter.get_teams("E2024")

        # Should only fetch once
        assert mock_direct_client.fetch_teams.call_count == 1


class TestGetSchedule:
    """Tests for get_schedule method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_games(
        self, adapter, mock_client, sample_season_games_response
    ):
        """Test that games are fetched and mapped."""
        mock_client.fetch_season_games.return_value = CacheResult(
            data=sample_season_games_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        games = await adapter.get_schedule("E2024")

        assert len(games) == 2
        assert games[0].external_id == "E2024_1"
        assert games[0].status == "final"
        assert games[1].status == "scheduled"


class TestGetGameBoxscore:
    """Tests for get_game_boxscore method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_boxscore(
        self, adapter, mock_direct_client, sample_boxscore_response
    ):
        """Test that boxscore is fetched and mapped."""
        mock_direct_client.fetch_live_boxscore.return_value = CacheResult(
            data=sample_boxscore_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        boxscore = await adapter.get_game_boxscore("E2024_1")

        assert isinstance(boxscore, RawBoxScore)
        assert boxscore.game.external_id == "E2024_1"
        assert len(boxscore.home_players) == 1
        assert len(boxscore.away_players) == 1

    @pytest.mark.asyncio
    async def test_calls_correct_api(
        self, adapter, mock_direct_client, sample_boxscore_response
    ):
        """Test that correct API is called with parsed parameters."""
        mock_direct_client.fetch_live_boxscore.return_value = CacheResult(
            data=sample_boxscore_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        await adapter.get_game_boxscore("E2024_5")

        mock_direct_client.fetch_live_boxscore.assert_called_once_with(2024, 5)


class TestGetGamePbp:
    """Tests for get_game_pbp method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_pbp(
        self, adapter, mock_direct_client, sample_pbp_response
    ):
        """Test that PBP is fetched and mapped."""
        mock_direct_client.fetch_live_pbp.return_value = CacheResult(
            data=sample_pbp_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        events = await adapter.get_game_pbp("E2024_1")

        assert len(events) == 3
        assert events[0].event_type == "shot"
        assert events[0].period == 1
        assert events[2].period == 2


class TestIsGameFinal:
    """Tests for is_game_final method."""

    def test_final_game_with_scores(self, adapter):
        """Test that final game with scores returns True."""
        game = RawGame(
            external_id="E2024_1",
            home_team_external_id="BER",
            away_team_external_id="PAN",
            game_date=datetime.now(),
            status="final",
            home_score=77,
            away_score=87,
        )

        assert adapter.is_game_final(game) is True

    def test_scheduled_game(self, adapter):
        """Test that scheduled game returns False."""
        game = RawGame(
            external_id="E2024_1",
            home_team_external_id="BER",
            away_team_external_id="PAN",
            game_date=datetime.now(),
            status="scheduled",
            home_score=None,
            away_score=None,
        )

        assert adapter.is_game_final(game) is False


class TestGetPlayerInfo:
    """Tests for get_player_info method."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_player(
        self, adapter, mock_direct_client, sample_player_response
    ):
        """Test that player info is fetched and mapped."""
        mock_direct_client.fetch_player.return_value = CacheResult(
            data=sample_player_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        player = await adapter.get_player_info("P011987")

        assert player.external_id == "P011987"
        assert player.first_name == "CARSEN"
        assert player.last_name == "EDWARDS"
        assert player.height_cm == 180


class TestSearchPlayer:
    """Tests for search_player method."""

    @pytest.mark.asyncio
    async def test_searches_team_rosters(
        self,
        adapter,
        mock_direct_client,
        sample_teams_response,
    ):
        """Test that search goes through team rosters."""
        mock_direct_client.fetch_teams.return_value = CacheResult(
            data=sample_teams_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        # Mock player fetch to return the player we're searching for
        mattisseck_response = {
            "name": "MATTISSECK, JONAS",
            "height": "1.88",
            "birthdate": "15 October, 2000",
            "position": "Guard",
        }
        mock_direct_client.fetch_player.return_value = CacheResult(
            data=mattisseck_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        results = await adapter.search_player("MATTISSECK")

        assert len(results) >= 1
        # Verify search found the player
        found = any(
            "MATTISSECK" in p.last_name or "MATTISSECK" in p.first_name for p in results
        )
        assert found

    @pytest.mark.asyncio
    async def test_filters_by_team(
        self,
        adapter,
        mock_direct_client,
        sample_teams_response,
        sample_player_response,
    ):
        """Test that search can filter by team."""
        mock_direct_client.fetch_teams.return_value = CacheResult(
            data=sample_teams_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        mock_direct_client.fetch_player.return_value = CacheResult(
            data=sample_player_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        # Search for NUNN only in BER team (should not find)
        results = await adapter.search_player("NUNN", team="BER")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_case_insensitive(
        self,
        adapter,
        mock_direct_client,
        sample_teams_response,
        sample_player_response,
    ):
        """Test that search is case insensitive."""
        mock_direct_client.fetch_teams.return_value = CacheResult(
            data=sample_teams_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        mock_direct_client.fetch_player.return_value = CacheResult(
            data=sample_player_response,
            changed=False,
            fetched_at=datetime.now(),
            cache_id="test",
        )

        results = await adapter.search_player("nunn")

        assert len(results) >= 1
