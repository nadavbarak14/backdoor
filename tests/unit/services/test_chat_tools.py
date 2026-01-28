"""
Unit tests for LangChain Chat Tools.

Tests the LangChain @tool wrappers around existing services for the chat agent.
Tests verify:
    - Name resolution (player names, team names, seasons)
    - Proper service method calls
    - Output formatting (JSON for search tools, markdown for other tools)
    - Error handling (not found, invalid input)
"""

import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.stats import PlayerSeasonStats
from src.models.team import Team, TeamSeason
from src.services.chat_tools import (
    _resolve_player_by_name,
    _resolve_season,
    _resolve_team_by_name,
    get_clutch_stats,
    get_game_details,
    get_home_away_split,
    get_league_leaders,
    get_lineup_stats,
    get_on_off_stats,
    get_player_games,
    get_player_stats,
    get_quarter_splits,
    get_team_roster,
    get_trend,
    get_vs_opponent,
    search_players,
    search_teams,
)


class TestNameResolution:
    """Tests for name resolution helper functions."""

    @pytest.fixture
    def sample_player(self, test_db: Session) -> Player:
        """Create a sample player for testing."""
        player = Player(
            id=uuid4(),
            first_name="Stephen",
            last_name="Curry",
            birth_date=date(1988, 3, 14),
            nationality="USA",
            position="PG",
            external_ids={},
        )
        test_db.add(player)
        test_db.commit()
        return player

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

    @pytest.fixture
    def sample_league_and_season(self, test_db: Session) -> tuple[League, Season]:
        """Create a sample league and season for testing."""
        league = League(
            id=uuid4(),
            name="NBA",
            code="NBA",
            country="USA",
        )
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
        test_db.commit()
        return league, season

    def test_resolve_player_by_name_finds_player(
        self, test_db: Session, sample_player: Player
    ):
        """Test that player resolution finds a player by last name."""
        result = _resolve_player_by_name(test_db, "Curry")

        assert result is not None
        assert result.id == sample_player.id
        assert result.last_name == "Curry"

    def test_resolve_player_by_name_finds_by_first_name(
        self, test_db: Session, sample_player: Player
    ):
        """Test that player resolution finds a player by first name."""
        result = _resolve_player_by_name(test_db, "Stephen")

        assert result is not None
        assert result.first_name == "Stephen"

    def test_resolve_player_by_name_returns_none_not_found(self, test_db: Session):
        """Test that player resolution returns None for unknown player."""
        result = _resolve_player_by_name(test_db, "NonExistent")

        assert result is None

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

    def test_resolve_season_finds_current(
        self, test_db: Session, sample_league_and_season: tuple[League, Season]
    ):
        """Test that season resolution finds current season."""
        _, season = sample_league_and_season
        result = _resolve_season(test_db)

        assert result is not None
        assert result.id == season.id

    def test_resolve_season_by_name(
        self, test_db: Session, sample_league_and_season: tuple[League, Season]
    ):
        """Test that season resolution finds season by name."""
        _, season = sample_league_and_season
        result = _resolve_season(test_db, "2023-24")

        assert result is not None
        assert result.name == "2023-24"


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

        assert data["query"] == "Curry"
        assert data["total"] == 2
        assert len(data["players"]) == 2
        player_names = [p["name"] for p in data["players"]]
        assert "Stephen Curry" in player_names
        assert "Seth Curry" in player_names

    def test_search_players_returns_empty_when_no_matches(self, test_db: Session):
        """Test that search_players returns empty list when no matches."""
        result = search_players.invoke({"query": "NonExistent", "db": test_db})
        data = json.loads(result)

        assert data["query"] == "NonExistent"
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

        assert data["query"] == "Lakers"
        assert data["total"] == 1
        assert data["teams"][0]["name"] == "Los Angeles Lakers"

    def test_search_teams_returns_empty_when_no_matches(self, test_db: Session):
        """Test that search_teams returns empty list when no matches."""
        result = search_teams.invoke({"query": "NonExistent", "db": test_db})
        data = json.loads(result)

        assert data["query"] == "NonExistent"
        assert data["total"] == 0
        assert data["teams"] == []


class TestRosterTool:
    """Tests for get_team_roster tool."""

    @pytest.fixture
    def team_with_roster(self, test_db: Session) -> tuple[Team, Season, list[Player]]:
        """Create a team with roster for testing."""
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

        team = Team(
            id=uuid4(),
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
            external_ids={},
        )
        test_db.add(team)
        test_db.flush()

        # Add team to season
        team_season = TeamSeason(team_id=team.id, season_id=season.id)
        test_db.add(team_season)
        test_db.flush()

        players = []
        for first, last, pos, num in [
            ("Stephen", "Curry", "PG", 30),
            ("Klay", "Thompson", "SG", 11),
            ("Andrew", "Wiggins", "SF", 22),
        ]:
            player = Player(
                id=uuid4(),
                first_name=first,
                last_name=last,
                position=pos,
                external_ids={},
            )
            test_db.add(player)
            test_db.flush()

            history = PlayerTeamHistory(
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
                jersey_number=num,
                position=pos,
            )
            test_db.add(history)
            players.append(player)

        test_db.commit()
        return team, season, players

    def test_get_team_roster_returns_roster(
        self, test_db: Session, team_with_roster: tuple[Team, Season, list[Player]]
    ):
        """Test that get_team_roster returns team roster."""
        team, season, players = team_with_roster
        result = get_team_roster.invoke({"team_name": "Warriors", "db": test_db})

        assert "Golden State Warriors Roster" in result
        assert "Stephen Curry" in result
        assert "Klay Thompson" in result
        assert "30" in result  # Jersey number
        assert "11" in result

    def test_get_team_roster_team_not_found(self, test_db: Session):
        """Test that get_team_roster handles team not found."""
        result = get_team_roster.invoke({"team_name": "NonExistent", "db": test_db})

        assert "not found" in result


class TestPlayerStatsTool:
    """Tests for get_player_stats tool."""

    @pytest.fixture
    def player_with_stats(self, test_db: Session) -> tuple[Player, Season]:
        """Create a player with season stats for testing."""
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

        team = Team(
            id=uuid4(),
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
            external_ids={},
        )
        test_db.add(team)
        test_db.flush()

        player = Player(
            id=uuid4(),
            first_name="Stephen",
            last_name="Curry",
            position="PG",
            external_ids={},
        )
        test_db.add(player)
        test_db.flush()

        stats = PlayerSeasonStats(
            id=uuid4(),
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
            games_played=60,
            games_started=60,
            total_minutes=120000,
            total_points=1500,
            avg_points=25.0,
            avg_rebounds=4.5,
            avg_assists=5.2,
            avg_steals=0.9,
            avg_blocks=0.2,
            field_goal_pct=0.472,
            three_point_pct=0.408,
            free_throw_pct=0.913,
            true_shooting_pct=0.634,
        )
        test_db.add(stats)
        test_db.commit()

        return player, season

    def test_get_player_stats_returns_stats(
        self, test_db: Session, player_with_stats: tuple[Player, Season]
    ):
        """Test that get_player_stats returns player statistics."""
        player, season = player_with_stats
        result = get_player_stats.invoke({"player_name": "Curry", "db": test_db})

        assert "Stephen Curry" in result
        assert "25.0" in result  # avg_points
        assert "4.5" in result  # avg_rebounds
        assert "47.2%" in result  # FG%

    def test_get_player_stats_player_not_found(self, test_db: Session):
        """Test that get_player_stats handles player not found."""
        result = get_player_stats.invoke({"player_name": "NonExistent", "db": test_db})

        assert "not found" in result


class TestLeagueLeadersTool:
    """Tests for get_league_leaders tool."""

    @pytest.fixture
    def league_leaders_data(self, test_db: Session) -> Season:
        """Create multiple players with stats for testing leaders."""
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

        team = Team(
            id=uuid4(),
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
            external_ids={},
        )
        test_db.add(team)
        test_db.flush()

        # Create multiple players with different stats
        players_data = [
            ("Stephen", "Curry", 25.0),
            ("LeBron", "James", 28.0),
            ("Luka", "Doncic", 30.0),
        ]

        for first, last, avg_pts in players_data:
            player = Player(
                id=uuid4(),
                first_name=first,
                last_name=last,
                position="PG",
                external_ids={},
            )
            test_db.add(player)
            test_db.flush()

            stats = PlayerSeasonStats(
                id=uuid4(),
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
                games_played=50,
                avg_points=avg_pts,
                avg_rebounds=5.0,
                avg_assists=7.0,
            )
            test_db.add(stats)

        test_db.commit()
        return season

    def test_get_league_leaders_returns_rankings(
        self, test_db: Session, league_leaders_data: Season
    ):
        """Test that get_league_leaders returns rankings."""
        result = get_league_leaders.invoke(
            {"category": "points", "limit": 5, "db": test_db}
        )

        assert "Points Per Game Leaders" in result
        assert "Luka Doncic" in result
        assert "30.0" in result

    def test_get_league_leaders_invalid_category(
        self, test_db: Session, league_leaders_data: Season
    ):
        """Test that get_league_leaders handles invalid category."""
        result = get_league_leaders.invoke({"category": "invalid", "db": test_db})

        assert "Error" in result


class TestPlayerGamesTool:
    """Tests for get_player_games tool."""

    @pytest.fixture
    def player_with_games(self, test_db: Session) -> Player:
        """Create a player with game stats for testing."""
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
            name="Warriors",
            short_name="GSW",
            city="SF",
            country="USA",
            external_ids={},
        )
        team2 = Team(
            id=uuid4(),
            name="Lakers",
            short_name="LAL",
            city="LA",
            country="USA",
            external_ids={},
        )
        test_db.add(team1)
        test_db.add(team2)
        test_db.flush()

        player = Player(
            id=uuid4(),
            first_name="Stephen",
            last_name="Curry",
            position="PG",
            external_ids={},
        )
        test_db.add(player)
        test_db.flush()

        # Create games
        for i in range(3):
            game = Game(
                id=uuid4(),
                season_id=season.id,
                home_team_id=team1.id,
                away_team_id=team2.id,
                game_date=datetime(2024, 1, i + 1, 19, 30),
                status="FINAL",
                home_score=110 + i,
                away_score=105 + i,
                external_ids={},
            )
            test_db.add(game)
            test_db.flush()

            stats = PlayerGameStats(
                id=uuid4(),
                game_id=game.id,
                player_id=player.id,
                team_id=team1.id,
                minutes_played=2000 + i * 60,
                points=25 + i * 5,
                total_rebounds=5,
                assists=6,
                steals=1,
                blocks=0,
                turnovers=3,
                field_goals_made=8 + i,
                field_goals_attempted=16 + i,
                is_starter=True,
                extra_stats={},
            )
            test_db.add(stats)

        test_db.commit()
        return player

    def test_get_player_games_returns_game_log(
        self, test_db: Session, player_with_games: Player
    ):
        """Test that get_player_games returns game log."""
        result = get_player_games.invoke(
            {"player_name": "Curry", "limit": 5, "db": test_db}
        )

        assert "Stephen Curry" in result
        assert "Last 3 Games" in result
        assert "PTS" in result
        assert "REB" in result

    def test_get_player_games_player_not_found(self, test_db: Session):
        """Test that get_player_games handles player not found."""
        result = get_player_games.invoke({"player_name": "NonExistent", "db": test_db})

        assert "not found" in result


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
        assert "query" in data
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
        assert "query" in data
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

        # Other tools return text errors
        other_tools = [
            (get_team_roster, {"team_name": "test"}),
            (get_player_stats, {"player_name": "test"}),
            (get_player_games, {"player_name": "test"}),
            (get_league_leaders, {"category": "points"}),
        ]

        for tool, params in other_tools:
            result = tool.invoke(params)
            assert "Error" in result or "not provided" in result

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


class TestAdvancedAnalyticsTools:
    """Tests for advanced analytics tools."""

    @pytest.fixture
    def analytics_data(self, test_db: Session) -> dict:
        """Create comprehensive test data for analytics tools."""
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

        # Create player team history
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
        test_db.flush()

        # Create games between teams
        game1 = Game(
            id=uuid4(),
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 1, 15, 19, 30),
            status="FINAL",
            home_score=115,
            away_score=110,
            external_ids={},
        )
        test_db.add(game1)
        test_db.flush()

        # Create player game stats
        stats1 = PlayerGameStats(
            id=uuid4(),
            game_id=game1.id,
            player_id=player1.id,
            team_id=team1.id,
            minutes_played=2400,
            points=35,
            total_rebounds=5,
            assists=8,
            steals=2,
            blocks=0,
            turnovers=3,
            field_goals_made=12,
            field_goals_attempted=20,
            is_starter=True,
            extra_stats={},
        )
        stats2 = PlayerGameStats(
            id=uuid4(),
            game_id=game1.id,
            player_id=player2.id,
            team_id=team2.id,
            minutes_played=2400,
            points=28,
            total_rebounds=8,
            assists=5,
            steals=1,
            blocks=2,
            turnovers=4,
            field_goals_made=10,
            field_goals_attempted=22,
            is_starter=True,
            extra_stats={},
        )
        test_db.add(stats1)
        test_db.add(stats2)

        # Create season stats for players
        season_stats1 = PlayerSeasonStats(
            id=uuid4(),
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_points=28.0,
            avg_rebounds=5.0,
            avg_assists=6.5,
        )
        season_stats2 = PlayerSeasonStats(
            id=uuid4(),
            player_id=player2.id,
            team_id=team2.id,
            season_id=season.id,
            games_played=50,
            avg_points=25.0,
            avg_rebounds=7.5,
            avg_assists=8.0,
        )
        test_db.add(season_stats1)
        test_db.add(season_stats2)

        test_db.commit()

        return {
            "league": league,
            "season": season,
            "team1": team1,
            "team2": team2,
            "player1": player1,
            "player2": player2,
            "game": game1,
        }

    def test_get_game_details_by_teams(self, test_db: Session, analytics_data: dict):
        """Test get_game_details finds game by team names."""
        result = get_game_details.invoke(
            {
                "home_team": "Warriors",
                "away_team": "Lakers",
                "db": test_db,
            }
        )

        assert "Warriors" in result or "GSW" in result
        assert "Lakers" in result or "LAL" in result

    def test_get_game_details_not_found(self, test_db: Session):
        """Test get_game_details handles missing teams."""
        result = get_game_details.invoke(
            {
                "home_team": "NonExistent1",
                "away_team": "NonExistent2",
                "db": test_db,
            }
        )

        assert "not find" in result.lower() or "not found" in result.lower()

    def test_get_game_details_requires_params(self, test_db: Session):
        """Test get_game_details requires either game_id or team names."""
        result = get_game_details.invoke({"db": test_db})

        assert "provide" in result.lower()

    def test_get_clutch_stats_team_not_found(self, test_db: Session):
        """Test get_clutch_stats handles team not found."""
        result = get_clutch_stats.invoke(
            {
                "team_name": "NonExistent",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_clutch_stats_requires_entity(self, test_db: Session):
        """Test get_clutch_stats requires team or player."""
        result = get_clutch_stats.invoke({"db": test_db})

        assert "provide" in result.lower()

    def test_get_quarter_splits_player_not_found(self, test_db: Session):
        """Test get_quarter_splits handles player not found."""
        result = get_quarter_splits.invoke(
            {
                "player_name": "NonExistent",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_quarter_splits_requires_entity(self, test_db: Session):
        """Test get_quarter_splits requires team or player."""
        result = get_quarter_splits.invoke({"db": test_db})

        assert "provide" in result.lower()

    def test_get_trend_player_not_found(self, test_db: Session):
        """Test get_trend handles player not found."""
        result = get_trend.invoke(
            {
                "stat": "points",
                "player_name": "NonExistent",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_trend_requires_entity(self, test_db: Session):
        """Test get_trend requires team or player."""
        result = get_trend.invoke(
            {
                "stat": "points",
                "db": test_db,
            }
        )

        assert "provide" in result.lower()

    def test_get_lineup_stats_player_not_found(self, test_db: Session):
        """Test get_lineup_stats handles player not found."""
        result = get_lineup_stats.invoke(
            {
                "player_names": ["NonExistent1", "NonExistent2"],
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_lineup_stats_requires_minimum_players(self, test_db: Session):
        """Test get_lineup_stats requires at least 2 players."""
        result = get_lineup_stats.invoke(
            {
                "player_names": ["OnlyOne"],
                "db": test_db,
            }
        )

        assert "2" in result

    def test_get_lineup_stats_max_players(self, test_db: Session):
        """Test get_lineup_stats allows max 5 players."""
        result = get_lineup_stats.invoke(
            {
                "player_names": ["P1", "P2", "P3", "P4", "P5", "P6"],
                "db": test_db,
            }
        )

        assert "5" in result

    def test_get_home_away_split_player_not_found(self, test_db: Session):
        """Test get_home_away_split handles player not found."""
        result = get_home_away_split.invoke(
            {
                "player_name": "NonExistent",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_on_off_stats_player_not_found(self, test_db: Session):
        """Test get_on_off_stats handles player not found."""
        result = get_on_off_stats.invoke(
            {
                "player_name": "NonExistent",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_vs_opponent_player_not_found(self, test_db: Session):
        """Test get_vs_opponent handles player not found."""
        result = get_vs_opponent.invoke(
            {
                "player_name": "NonExistent",
                "opponent_team": "Lakers",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_vs_opponent_team_not_found(
        self, test_db: Session, analytics_data: dict
    ):
        """Test get_vs_opponent handles opponent not found."""
        result = get_vs_opponent.invoke(
            {
                "player_name": "Curry",
                "opponent_team": "NonExistent",
                "db": test_db,
            }
        )

        assert "not found" in result

    def test_get_vs_opponent_returns_stats(
        self, test_db: Session, analytics_data: dict
    ):
        """Test get_vs_opponent returns player stats against opponent."""
        result = get_vs_opponent.invoke(
            {
                "player_name": "Curry",
                "opponent_team": "Lakers",
                "db": test_db,
            }
        )

        assert "Curry" in result
        assert "Lakers" in result


class TestNoDbErrorHandling:
    """Test all analytics tools handle missing db session."""

    def test_get_game_details_no_db(self):
        """Test get_game_details returns error without db."""
        result = get_game_details.invoke(
            {
                "home_team": "Lakers",
                "away_team": "Celtics",
            }
        )
        assert "Error" in result

    def test_get_clutch_stats_no_db(self):
        """Test get_clutch_stats returns error without db."""
        result = get_clutch_stats.invoke({"team_name": "Lakers"})
        assert "Error" in result

    def test_get_quarter_splits_no_db(self):
        """Test get_quarter_splits returns error without db."""
        result = get_quarter_splits.invoke({"team_name": "Lakers"})
        assert "Error" in result

    def test_get_trend_no_db(self):
        """Test get_trend returns error without db."""
        result = get_trend.invoke({"stat": "points", "player_name": "Curry"})
        assert "Error" in result

    def test_get_lineup_stats_no_db(self):
        """Test get_lineup_stats returns error without db."""
        result = get_lineup_stats.invoke({"player_names": ["A", "B"]})
        assert "Error" in result

    def test_get_home_away_split_no_db(self):
        """Test get_home_away_split returns error without db."""
        result = get_home_away_split.invoke({"player_name": "Curry"})
        assert "Error" in result

    def test_get_on_off_stats_no_db(self):
        """Test get_on_off_stats returns error without db."""
        result = get_on_off_stats.invoke({"player_name": "Curry"})
        assert "Error" in result

    def test_get_vs_opponent_no_db(self):
        """Test get_vs_opponent returns error without db."""
        result = get_vs_opponent.invoke(
            {
                "player_name": "Curry",
                "opponent_team": "Lakers",
            }
        )
        assert "Error" in result
