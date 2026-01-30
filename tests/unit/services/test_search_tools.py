"""
Unit tests for search tools.

Tests the search tools that help find entity IDs for use with query_stats.
All search tools return JSON format.
"""

import json
from unittest.mock import MagicMock, patch
from uuid import UUID


class TestSearchPlayers:
    """Tests for search_players tool (returns JSON)."""

    def test_search_players_no_db(self):
        """Test search_players returns JSON error when no db provided."""
        from src.services.search_tools import search_players

        result = search_players.func(query="Clark", db=None)
        data = json.loads(result)
        assert "error" in data

    def test_search_players_empty_query(self):
        """Test search_players returns JSON error for empty query."""
        from src.services.search_tools import search_players

        mock_db = MagicMock()
        result = search_players.func(query="", db=mock_db)
        data = json.loads(result)
        assert "error" in data
        assert "at least 2 characters" in data["error"]

    def test_search_players_short_query(self):
        """Test search_players returns JSON error for too short query."""
        from src.services.search_tools import search_players

        mock_db = MagicMock()
        result = search_players.func(query="A", db=mock_db)
        data = json.loads(result)
        assert "error" in data

    def test_search_players_no_results(self):
        """Test search_players returns empty list when no players found."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_filtered.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_players.func(query="NonExistent", db=mock_db)
            data = json.loads(result)

            assert data["total"] == 0
            assert data["players"] == []

    def test_search_players_with_results(self):
        """Test search_players with matching players."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()

            mock_player = MagicMock()
            mock_player.id = UUID("12345678-1234-5678-1234-567812345678")
            mock_player.first_name = "Jimmy"
            mock_player.last_name = "Clark"
            mock_player.positions = [MagicMock(value="PG")]
            mock_player.current_team = MagicMock()
            mock_player.current_team.short_name = "MAC"
            mock_player.current_team.name = "Maccabi"

            mock_service.get_filtered.return_value = ([mock_player], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_players.func(query="Clark", db=mock_db)
            data = json.loads(result)

            assert data["total"] == 1
            assert len(data["players"]) == 1
            player = data["players"][0]
            assert player["name"] == "Jimmy Clark"
            assert player["id"] == "12345678-1234-5678-1234-567812345678"
            assert player["team"] == "MAC"
            assert player["positions"] == ["PG"]

    def test_search_players_returns_id(self):
        """Test search_players result contains usable ID in JSON."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()

            mock_player = MagicMock()
            mock_player.id = UUID("12345678-1234-5678-1234-567812345678")
            mock_player.first_name = "Test"
            mock_player.last_name = "Player"
            mock_player.positions = []
            mock_player.current_team = None

            mock_service.get_filtered.return_value = ([mock_player], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_players.func(query="Test", db=mock_db)
            data = json.loads(result)

            # ID should be directly accessible
            assert "id" in data["players"][0]
            assert data["players"][0]["id"] == "12345678-1234-5678-1234-567812345678"

    def test_search_players_with_team_filter(self):
        """Test search_players with team_id filter."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_filtered.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            valid_uuid = "12345678-1234-5678-1234-567812345678"
            search_players.func(query="Test", team_id=valid_uuid, db=mock_db)

            # Verify filter was applied
            call_args = mock_service.get_filtered.call_args
            filter_obj = call_args[0][0]
            assert filter_obj.team_id == UUID(valid_uuid)

    def test_search_players_invalid_team_id(self):
        """Test search_players with invalid team_id format."""
        from src.services.search_tools import search_players

        mock_db = MagicMock()
        result = search_players.func(query="Test", team_id="invalid-uuid", db=mock_db)
        data = json.loads(result)

        assert "error" in data
        assert "Invalid team_id" in data["error"]


class TestSearchTeams:
    """Tests for search_teams tool (returns JSON)."""

    def test_search_teams_no_db(self):
        """Test search_teams returns JSON error when no db provided."""
        from src.services.search_tools import search_teams

        result = search_teams.func(query="Maccabi", db=None)
        data = json.loads(result)
        assert "error" in data

    def test_search_teams_empty_query(self):
        """Test search_teams returns JSON error for empty query."""
        from src.services.search_tools import search_teams

        mock_db = MagicMock()
        result = search_teams.func(query="", db=mock_db)
        data = json.loads(result)
        assert "error" in data

    def test_search_teams_no_results(self):
        """Test search_teams returns empty list when no teams found."""
        from src.services.search_tools import search_teams

        with patch("src.services.search_tools.TeamService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_filtered.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_teams.func(query="NonExistent", db=mock_db)
            data = json.loads(result)

            assert data["total"] == 0
            assert data["teams"] == []

    def test_search_teams_with_results(self):
        """Test search_teams with matching teams."""
        from src.services.search_tools import search_teams

        with patch("src.services.search_tools.TeamService") as mock_service_class:
            mock_service = MagicMock()

            mock_team = MagicMock()
            mock_team.id = UUID("12345678-1234-5678-1234-567812345678")
            mock_team.name = "Maccabi Tel-Aviv"
            mock_team.short_name = "MAC"
            mock_team.city = "Tel-Aviv"
            mock_team.country = "ISR"

            mock_service.get_filtered.return_value = ([mock_team], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_teams.func(query="Maccabi", db=mock_db)
            data = json.loads(result)

            assert data["total"] == 1
            team = data["teams"][0]
            assert team["name"] == "Maccabi Tel-Aviv"
            assert team["id"] == "12345678-1234-5678-1234-567812345678"
            assert team["short_name"] == "MAC"
            assert team["city"] == "Tel-Aviv"

    def test_search_teams_returns_id(self):
        """Test search_teams result contains usable ID in JSON."""
        from src.services.search_tools import search_teams

        with patch("src.services.search_tools.TeamService") as mock_service_class:
            mock_service = MagicMock()

            mock_team = MagicMock()
            mock_team.id = UUID("12345678-1234-5678-1234-567812345678")
            mock_team.name = "Test Team"
            mock_team.short_name = None
            mock_team.city = None
            mock_team.country = None

            mock_service.get_filtered.return_value = ([mock_team], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_teams.func(query="Test", db=mock_db)
            data = json.loads(result)

            # ID should be directly accessible
            assert "id" in data["teams"][0]
            assert data["teams"][0]["id"] == "12345678-1234-5678-1234-567812345678"


class TestSearchLeagues:
    """Tests for search_leagues tool (returns JSON)."""

    def test_search_leagues_no_db(self):
        """Test search_leagues returns JSON error when no db provided."""
        from src.services.search_tools import search_leagues

        result = search_leagues.func(db=None)
        data = json.loads(result)
        assert "error" in data

    def test_search_leagues_no_results(self):
        """Test search_leagues returns empty list when no leagues found."""
        from src.services.search_tools import search_leagues

        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = []

        result = search_leagues.func(query="NonExistent", db=mock_db)
        data = json.loads(result)

        assert data["leagues"] == []

    def test_search_leagues_with_results(self):
        """Test search_leagues with matching leagues."""
        from src.services.search_tools import search_leagues

        mock_db = MagicMock()

        mock_league = MagicMock()
        mock_league.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_league.name = "Israeli Winner League"
        mock_league.code = "ISRWL"

        mock_db.scalars.return_value.all.return_value = [mock_league]

        result = search_leagues.func(query="Israeli", db=mock_db)
        data = json.loads(result)

        league = data["leagues"][0]
        assert league["name"] == "Israeli Winner League"
        assert league["id"] == "12345678-1234-5678-1234-567812345678"
        assert league["code"] == "ISRWL"

    def test_search_leagues_list_all(self):
        """Test search_leagues lists all when no query."""
        from src.services.search_tools import search_leagues

        mock_db = MagicMock()

        mock_league = MagicMock()
        mock_league.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_league.name = "Test League"
        mock_league.code = "TST"

        mock_db.scalars.return_value.all.return_value = [mock_league]

        result = search_leagues.func(db=mock_db)
        data = json.loads(result)

        assert len(data["leagues"]) == 1
        assert data["leagues"][0]["name"] == "Test League"

    def test_search_leagues_returns_id(self):
        """Test search_leagues result contains usable ID in JSON."""
        from src.services.search_tools import search_leagues

        mock_db = MagicMock()

        mock_league = MagicMock()
        mock_league.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_league.name = "Test League"
        mock_league.code = None

        mock_db.scalars.return_value.all.return_value = [mock_league]

        result = search_leagues.func(db=mock_db)
        data = json.loads(result)

        # ID should be directly accessible
        assert "id" in data["leagues"][0]
        assert data["leagues"][0]["id"] == "12345678-1234-5678-1234-567812345678"


class TestSearchSeasons:
    """Tests for search_seasons tool (returns JSON)."""

    def test_search_seasons_no_db(self):
        """Test search_seasons returns JSON error when no db provided."""
        from src.services.search_tools import search_seasons

        result = search_seasons.func(db=None)
        data = json.loads(result)
        assert "error" in data

    def test_search_seasons_no_results(self):
        """Test search_seasons returns empty list when no seasons found."""
        from src.services.search_tools import search_seasons

        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = []

        result = search_seasons.func(query="2099", db=mock_db)
        data = json.loads(result)

        assert data["seasons"] == []

    def test_search_seasons_with_results(self):
        """Test search_seasons with matching seasons."""
        from src.services.search_tools import search_seasons

        mock_db = MagicMock()

        mock_league = MagicMock()
        mock_league.name = "Israeli League"

        mock_season = MagicMock()
        mock_season.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_season.name = "2024-25"
        mock_season.is_current = True
        mock_season.league = mock_league

        mock_db.scalars.return_value.all.return_value = [mock_season]

        result = search_seasons.func(query="2024", db=mock_db)
        data = json.loads(result)

        season = data["seasons"][0]
        assert season["name"] == "2024-25"
        assert season["id"] == "12345678-1234-5678-1234-567812345678"
        assert season["league"] == "Israeli League"
        assert season["is_current"] is True

    def test_search_seasons_with_league_filter(self):
        """Test search_seasons with league_id filter."""
        from src.services.search_tools import search_seasons

        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = []

        valid_uuid = "12345678-1234-5678-1234-567812345678"
        search_seasons.func(league_id=valid_uuid, db=mock_db)

        # Just verify it doesn't error with valid UUID
        mock_db.scalars.assert_called_once()

    def test_search_seasons_invalid_league_id(self):
        """Test search_seasons with invalid league_id format."""
        from src.services.search_tools import search_seasons

        mock_db = MagicMock()
        result = search_seasons.func(league_id="invalid-uuid", db=mock_db)
        data = json.loads(result)

        assert "error" in data
        assert "Invalid league_id" in data["error"]

    def test_search_seasons_returns_id(self):
        """Test search_seasons result contains usable ID in JSON."""
        from src.services.search_tools import search_seasons

        mock_db = MagicMock()

        mock_season = MagicMock()
        mock_season.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_season.name = "2024-25"
        mock_season.is_current = False
        mock_season.league = MagicMock()
        mock_season.league.name = "Test"

        mock_db.scalars.return_value.all.return_value = [mock_season]

        result = search_seasons.func(db=mock_db)
        data = json.loads(result)

        # ID should be directly accessible
        assert "id" in data["seasons"][0]
        assert data["seasons"][0]["id"] == "12345678-1234-5678-1234-567812345678"


class TestSearchToolsExport:
    """Tests for SEARCH_TOOLS export."""

    def test_search_tools_list(self):
        """Test SEARCH_TOOLS contains all search tools."""
        from src.services.search_tools import SEARCH_TOOLS

        assert len(SEARCH_TOOLS) == 4

        tool_names = [t.name for t in SEARCH_TOOLS]
        assert "search_players" in tool_names
        assert "search_teams" in tool_names
        assert "search_leagues" in tool_names
        assert "search_seasons" in tool_names
