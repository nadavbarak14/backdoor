"""
Unit tests for search tools.

Tests the search tools that help find entity IDs for use with query_stats.
"""

from unittest.mock import MagicMock, patch
from uuid import UUID


class TestSearchPlayers:
    """Tests for search_players tool."""

    def test_search_players_no_db(self):
        """Test search_players returns error when no db provided."""
        from src.services.search_tools import search_players

        result = search_players.func(query="Clark", db=None)
        assert "Error" in result

    def test_search_players_empty_query(self):
        """Test search_players returns error for empty query."""
        from src.services.search_tools import search_players

        mock_db = MagicMock()
        result = search_players.func(query="", db=mock_db)
        assert "Error" in result
        assert "at least 2 characters" in result

    def test_search_players_short_query(self):
        """Test search_players returns error for too short query."""
        from src.services.search_tools import search_players

        mock_db = MagicMock()
        result = search_players.func(query="A", db=mock_db)
        assert "Error" in result

    def test_search_players_no_results(self):
        """Test search_players when no players found."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_filtered.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_players.func(query="NonExistent", db=mock_db)

            assert "No players found" in result

    def test_search_players_with_results(self):
        """Test search_players with matching players."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()

            mock_player = MagicMock()
            mock_player.id = UUID("12345678-1234-5678-1234-567812345678")
            mock_player.first_name = "Jimmy"
            mock_player.last_name = "Clark"
            mock_player.position = "PG"
            mock_player.current_team = MagicMock()
            mock_player.current_team.short_name = "MAC"
            mock_player.current_team.name = "Maccabi"

            mock_service.get_filtered.return_value = ([mock_player], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_players.func(query="Clark", db=mock_db)

            assert "Jimmy Clark" in result
            assert "12345678-1234-5678-1234-567812345678" in result
            assert "MAC" in result
            assert "PG" in result

    def test_search_players_returns_id(self):
        """Test search_players result contains usable ID."""
        from src.services.search_tools import search_players

        with patch("src.services.search_tools.PlayerService") as mock_service_class:
            mock_service = MagicMock()

            mock_player = MagicMock()
            mock_player.id = UUID("12345678-1234-5678-1234-567812345678")
            mock_player.first_name = "Test"
            mock_player.last_name = "Player"
            mock_player.position = None
            mock_player.current_team = None

            mock_service.get_filtered.return_value = ([mock_player], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_players.func(query="Test", db=mock_db)

            # Should include guidance for using the ID
            assert "query_stats" in result
            assert "player_ids" in result

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

        assert "Error" in result
        assert "Invalid team_id" in result


class TestSearchTeams:
    """Tests for search_teams tool."""

    def test_search_teams_no_db(self):
        """Test search_teams returns error when no db provided."""
        from src.services.search_tools import search_teams

        result = search_teams.func(query="Maccabi", db=None)
        assert "Error" in result

    def test_search_teams_empty_query(self):
        """Test search_teams returns error for empty query."""
        from src.services.search_tools import search_teams

        mock_db = MagicMock()
        result = search_teams.func(query="", db=mock_db)
        assert "Error" in result

    def test_search_teams_no_results(self):
        """Test search_teams when no teams found."""
        from src.services.search_tools import search_teams

        with patch("src.services.search_tools.TeamService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_filtered.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = search_teams.func(query="NonExistent", db=mock_db)

            assert "No teams found" in result

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

            assert "Maccabi Tel-Aviv" in result
            assert "12345678-1234-5678-1234-567812345678" in result
            assert "MAC" in result
            assert "Tel-Aviv" in result

    def test_search_teams_returns_id(self):
        """Test search_teams result contains usable ID."""
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

            # Should include guidance for using the ID
            assert "query_stats" in result
            assert "team_id" in result


class TestSearchLeagues:
    """Tests for search_leagues tool."""

    def test_search_leagues_no_db(self):
        """Test search_leagues returns error when no db provided."""
        from src.services.search_tools import search_leagues

        result = search_leagues.func(db=None)
        assert "Error" in result

    def test_search_leagues_no_results(self):
        """Test search_leagues when no leagues found."""
        from src.services.search_tools import search_leagues

        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = []

        result = search_leagues.func(query="NonExistent", db=mock_db)

        assert "No leagues found" in result

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

        assert "Israeli Winner League" in result
        assert "12345678-1234-5678-1234-567812345678" in result
        assert "ISRWL" in result

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

        assert "Available Leagues" in result
        assert "Test League" in result

    def test_search_leagues_returns_id(self):
        """Test search_leagues result contains usable ID."""
        from src.services.search_tools import search_leagues

        mock_db = MagicMock()

        mock_league = MagicMock()
        mock_league.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_league.name = "Test League"
        mock_league.code = None

        mock_db.scalars.return_value.all.return_value = [mock_league]

        result = search_leagues.func(db=mock_db)

        # Should include guidance for using the ID
        assert "query_stats" in result
        assert "league_id" in result


class TestSearchSeasons:
    """Tests for search_seasons tool."""

    def test_search_seasons_no_db(self):
        """Test search_seasons returns error when no db provided."""
        from src.services.search_tools import search_seasons

        result = search_seasons.func(db=None)
        assert "Error" in result

    def test_search_seasons_no_results(self):
        """Test search_seasons when no seasons found."""
        from src.services.search_tools import search_seasons

        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = []

        result = search_seasons.func(query="2099", db=mock_db)

        assert "No seasons found" in result

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

        assert "2024-25" in result
        assert "12345678-1234-5678-1234-567812345678" in result
        assert "Israeli League" in result
        assert "Yes" in result  # is_current

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

        assert "Error" in result
        assert "Invalid league_id" in result

    def test_search_seasons_returns_id(self):
        """Test search_seasons result contains usable ID."""
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

        # Should include guidance for using the ID
        assert "query_stats" in result
        assert "season_id" in result


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
