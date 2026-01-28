"""
Unit tests for LangChain Chat Tools.

Tests the LangChain @tool wrappers around existing services for the chat agent.
Tests verify:
    - Name resolution (team names)
    - Proper service method calls
    - Output formatting (JSON for search tools)
    - Error handling (not found, invalid input)
"""

import json
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.services.chat_tools import (
    _resolve_team_by_name,
    search_players,
    search_teams,
)


class TestNameResolution:
    """Tests for name resolution helper functions."""

    @pytest.fixture
    def sample_team(self, test_db: Session) -> Team:
        """Create a sample team for testing."""
        team = Team(
            id=uuid4(),
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
            external_ids={},
        )
        test_db.add(team)
        test_db.commit()
        return team

    def test_resolve_team_by_name_finds_team(self, test_db: Session, sample_team: Team):
        """Test that team resolution finds a team by name."""
        result = _resolve_team_by_name(test_db, "Warriors")

        assert result is not None
        assert result.id == sample_team.id

    def test_resolve_team_by_name_finds_by_short_name(
        self, test_db: Session, sample_team: Team
    ):
        """Test that team resolution finds a team by short name."""
        result = _resolve_team_by_name(test_db, "GSW")

        assert result is not None
        assert result.short_name == "GSW"

    def test_resolve_team_by_name_returns_none_not_found(self, test_db: Session):
        """Test that team resolution returns None for unknown team."""
        result = _resolve_team_by_name(test_db, "NonExistent")

        assert result is None


class TestSearchTools:
    """Tests for search_players and search_teams tools."""

    @pytest.fixture
    def players(self, test_db: Session) -> list[Player]:
        """Create multiple players for testing."""
        players = [
            Player(
                id=uuid4(),
                first_name="Stephen",
                last_name="Curry",
                position="PG",
                nationality="USA",
                external_ids={},
            ),
            Player(
                id=uuid4(),
                first_name="Seth",
                last_name="Curry",
                position="SG",
                nationality="USA",
                external_ids={},
            ),
            Player(
                id=uuid4(),
                first_name="LeBron",
                last_name="James",
                position="SF",
                nationality="USA",
                external_ids={},
            ),
        ]
        for p in players:
            test_db.add(p)
        test_db.commit()
        return players

    @pytest.fixture
    def teams(self, test_db: Session) -> list[Team]:
        """Create multiple teams for testing."""
        teams = [
            Team(
                id=uuid4(),
                name="Golden State Warriors",
                short_name="GSW",
                city="San Francisco",
                country="USA",
                external_ids={},
            ),
            Team(
                id=uuid4(),
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
                external_ids={},
            ),
        ]
        for t in teams:
            test_db.add(t)
        test_db.commit()
        return teams

    def test_search_players_finds_matches(
        self, test_db: Session, players: list[Player]
    ):
        """Test that search_players finds matching players and returns JSON."""
        result = search_players.invoke({"query": "Curry", "db": test_db})
        data = json.loads(result)

        assert data["total"] == 2
        assert len(data["players"]) == 2
        player_names = [p["name"] for p in data["players"]]
        assert "Stephen Curry" in player_names
        assert "Seth Curry" in player_names

    def test_search_players_returns_empty_when_no_matches(self, test_db: Session):
        """Test that search_players returns empty list when no matches."""
        result = search_players.invoke({"query": "NonExistent", "db": test_db})
        data = json.loads(result)

        assert data["total"] == 0
        assert data["players"] == []

    def test_search_players_filters_by_position(
        self, test_db: Session, players: list[Player]
    ):
        """Test that search_players filters by position."""
        result = search_players.invoke(
            {"query": "Curry", "position": "PG", "db": test_db}
        )
        data = json.loads(result)

        assert data["total"] == 1
        assert data["players"][0]["name"] == "Stephen Curry"

    def test_search_players_returns_error_without_db(self):
        """Test that search_players returns error JSON without database."""
        result = search_players.invoke({"query": "Curry"})
        data = json.loads(result)

        assert "error" in data

    def test_search_teams_finds_matches(self, test_db: Session, teams: list[Team]):
        """Test that search_teams finds matching teams and returns JSON."""
        result = search_teams.invoke({"query": "Lakers", "db": test_db})
        data = json.loads(result)

        assert data["total"] == 1
        assert data["teams"][0]["name"] == "Los Angeles Lakers"

    def test_search_teams_returns_empty_when_no_matches(self, test_db: Session):
        """Test that search_teams returns empty list when no matches."""
        result = search_teams.invoke({"query": "NonExistent", "db": test_db})
        data = json.loads(result)

        assert data["total"] == 0
        assert data["teams"] == []


class TestOutputFormatting:
    """Tests for output formatting of tools."""

    def test_search_players_returns_valid_json(self, test_db: Session):
        """Test that search_players returns valid JSON with correct structure."""
        # Create a player
        player = Player(
            id=uuid4(),
            first_name="Test",
            last_name="Player",
            position="PG",
            external_ids={},
        )
        test_db.add(player)
        test_db.commit()

        result = search_players.invoke({"query": "Player", "db": test_db})
        data = json.loads(result)

        # Should be valid JSON with expected structure
        assert "total" in data
        assert "players" in data
        assert isinstance(data["players"], list)
        assert data["players"][0]["name"] == "Test Player"
        assert "id" in data["players"][0]
        assert "position" in data["players"][0]
        assert "team" in data["players"][0]

    def test_search_teams_returns_valid_json(self, test_db: Session):
        """Test that search_teams returns valid JSON with correct structure."""
        team = Team(
            id=uuid4(),
            name="Test Team",
            short_name="TST",
            city="Test City",
            country="USA",
            external_ids={},
        )
        test_db.add(team)
        test_db.commit()

        result = search_teams.invoke({"query": "Test", "db": test_db})
        data = json.loads(result)

        # Should be valid JSON with expected structure
        assert "total" in data
        assert "teams" in data
        assert isinstance(data["teams"], list)
        assert data["teams"][0]["name"] == "Test Team"
        assert "id" in data["teams"][0]
        assert "short_name" in data["teams"][0]
        assert "city" in data["teams"][0]
        assert "country" in data["teams"][0]


class TestErrorHandling:
    """Tests for error handling in chat tools."""

    def test_tools_handle_no_db_session(self):
        """Test that tools handle missing database session."""
        # Search tools return JSON errors
        search_tools_params = [
            (search_players, {"query": "test"}),
            (search_teams, {"query": "test"}),
        ]

        for tool, params in search_tools_params:
            result = tool.invoke(params)
            data = json.loads(result)
            assert "error" in data

    def test_tools_handle_invalid_input(self, test_db: Session):
        """Test that tools handle invalid input gracefully."""
        # Test with short query - returns empty list in JSON
        result = search_players.invoke({"query": "X", "db": test_db})
        data = json.loads(result)
        # Should not crash, returns empty players list
        assert isinstance(data, dict)
        assert data["players"] == []
        assert data["total"] == 0


class TestAllToolsExist:
    """Test that all required tools are exported."""

    def test_all_tools_are_langchain_tools(self):
        """Test that all tools are valid LangChain tools."""
        from langchain_core.tools import BaseTool

        from src.services.chat_tools import ALL_TOOLS

        assert len(ALL_TOOLS) == 4  # 3 search tools + 1 universal query tool

        for tool in ALL_TOOLS:
            # LangChain tools are instances of BaseTool
            assert isinstance(tool, BaseTool)
            # They have invoke method
            assert hasattr(tool, "invoke")

    def test_all_tools_have_docstrings(self):
        """Test that all tools have proper docstrings."""
        from src.services.chat_tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            # LangChain tools have description attribute
            assert tool.description is not None
            assert len(tool.description) > 50  # Should have meaningful docs


class TestSearchPlayersWithTeamFilter:
    """Tests for search_players tool with team_name filter."""

    @pytest.fixture
    def players_with_teams(self, test_db: Session) -> dict:
        """Create players with team history for testing."""
        league = League(id=uuid4(), name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            id=uuid4(),
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        test_db.add(season)
        test_db.flush()

        team1 = Team(
            id=uuid4(),
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
            external_ids={},
        )
        team2 = Team(
            id=uuid4(),
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={},
        )
        test_db.add(team1)
        test_db.add(team2)
        test_db.flush()

        player1 = Player(
            id=uuid4(),
            first_name="Stephen",
            last_name="Curry",
            position="PG",
            external_ids={},
        )
        player2 = Player(
            id=uuid4(),
            first_name="LeBron",
            last_name="James",
            position="SF",
            external_ids={},
        )
        test_db.add(player1)
        test_db.add(player2)
        test_db.flush()

        # Create team history
        history1 = PlayerTeamHistory(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            jersey_number=30,
            position="PG",
        )
        history2 = PlayerTeamHistory(
            player_id=player2.id,
            team_id=team2.id,
            season_id=season.id,
            jersey_number=23,
            position="SF",
        )
        test_db.add(history1)
        test_db.add(history2)
        test_db.commit()

        return {
            "team1": team1,
            "team2": team2,
            "player1": player1,
            "player2": player2,
        }

    def test_search_players_filters_by_team_name(
        self, test_db: Session, players_with_teams: dict
    ):
        """Test that search_players can filter by team_name."""
        # Search for Curry on Warriors
        result = search_players.invoke(
            {"query": "Curry", "team_name": "Warriors", "db": test_db}
        )
        data = json.loads(result)

        # Only Stephen Curry should be returned (he's on Warriors)
        player_names = [p["name"] for p in data["players"]]
        assert "Stephen Curry" in player_names
        assert "LeBron James" not in player_names
