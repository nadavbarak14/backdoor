"""
Integration tests for the games API endpoints.

Tests:
    - GET /api/v1/games - List games with filters
    - GET /api/v1/games/{game_id} - Get game with box score
    - GET /api/v1/games/{game_id}/pbp - Get play-by-play events
"""

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from src.schemas import (
    GameCreate,
    GameStatus,
    LeagueCreate,
    PlayerCreate,
    SeasonCreate,
    TeamCreate,
)
from src.services import (
    GameService,
    LeagueService,
    PlayByPlayService,
    PlayerGameStatsService,
    PlayerService,
    SeasonService,
    TeamGameStatsService,
    TeamService,
)


def _create_test_game_with_stats(
    test_db: Session,
) -> tuple:
    """Helper to create a game with teams, players, and stats for testing."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)
    team_service = TeamService(test_db)
    player_service = PlayerService(test_db)
    game_service = GameService(test_db)
    player_stats_service = PlayerGameStatsService(test_db)
    team_stats_service = TeamGameStatsService(test_db)

    # Create league and season
    league = league_service.create_league(
        LeagueCreate(name="NBA", code="NBA", country="USA")
    )
    season = season_service.create_season(
        SeasonCreate(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=True,
        )
    )

    # Create teams
    home_team = team_service.create_team(
        TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
    )
    away_team = team_service.create_team(
        TeamCreate(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        )
    )

    # Create players
    player1 = player_service.create_player(
        PlayerCreate(
            first_name="LeBron",
            last_name="James",
            position="SF",
        )
    )
    player2 = player_service.create_player(
        PlayerCreate(
            first_name="Anthony",
            last_name="Davis",
            position="PF",
        )
    )
    player3 = player_service.create_player(
        PlayerCreate(
            first_name="Jayson",
            last_name="Tatum",
            position="SF",
        )
    )

    # Create game
    game = game_service.create_game(
        GameCreate(
            season_id=season.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30),
            status=GameStatus.FINAL,
            venue="Crypto.com Arena",
        )
    )

    # Update game score
    game_service.update_score(game.id, home_score=112, away_score=108)

    # Create player stats
    player_stats_service.create_stats(
        {
            "game_id": game.id,
            "player_id": player1.id,
            "team_id": home_team.id,
            "minutes_played": 2100,  # 35 minutes
            "is_starter": True,
            "points": 30,
            "field_goals_made": 11,
            "field_goals_attempted": 22,
            "two_pointers_made": 8,
            "two_pointers_attempted": 14,
            "three_pointers_made": 3,
            "three_pointers_attempted": 8,
            "free_throws_made": 5,
            "free_throws_attempted": 6,
            "offensive_rebounds": 2,
            "defensive_rebounds": 8,
            "total_rebounds": 10,
            "assists": 8,
            "turnovers": 3,
            "steals": 2,
            "blocks": 1,
            "personal_fouls": 2,
            "plus_minus": 12,
            "efficiency": 38,
        }
    )

    player_stats_service.create_stats(
        {
            "game_id": game.id,
            "player_id": player2.id,
            "team_id": home_team.id,
            "minutes_played": 1800,  # 30 minutes
            "is_starter": True,
            "points": 25,
            "field_goals_made": 10,
            "field_goals_attempted": 18,
            "two_pointers_made": 8,
            "two_pointers_attempted": 14,
            "three_pointers_made": 2,
            "three_pointers_attempted": 4,
            "free_throws_made": 3,
            "free_throws_attempted": 4,
            "offensive_rebounds": 4,
            "defensive_rebounds": 10,
            "total_rebounds": 14,
            "assists": 3,
            "turnovers": 2,
            "steals": 1,
            "blocks": 3,
            "personal_fouls": 3,
            "plus_minus": 8,
            "efficiency": 35,
        }
    )

    player_stats_service.create_stats(
        {
            "game_id": game.id,
            "player_id": player3.id,
            "team_id": away_team.id,
            "minutes_played": 2040,  # 34 minutes
            "is_starter": True,
            "points": 28,
            "field_goals_made": 10,
            "field_goals_attempted": 20,
            "two_pointers_made": 6,
            "two_pointers_attempted": 10,
            "three_pointers_made": 4,
            "three_pointers_attempted": 10,
            "free_throws_made": 4,
            "free_throws_attempted": 5,
            "offensive_rebounds": 1,
            "defensive_rebounds": 6,
            "total_rebounds": 7,
            "assists": 5,
            "turnovers": 4,
            "steals": 2,
            "blocks": 0,
            "personal_fouls": 2,
            "plus_minus": -8,
            "efficiency": 25,
        }
    )

    # Create team stats
    team_stats_service.create_stats(
        {
            "game_id": game.id,
            "team_id": home_team.id,
            "is_home": True,
            "points": 112,
            "field_goals_made": 42,
            "field_goals_attempted": 88,
            "two_pointers_made": 30,
            "two_pointers_attempted": 56,
            "three_pointers_made": 12,
            "three_pointers_attempted": 32,
            "free_throws_made": 16,
            "free_throws_attempted": 20,
            "offensive_rebounds": 10,
            "defensive_rebounds": 32,
            "total_rebounds": 42,
            "assists": 25,
            "turnovers": 12,
            "steals": 8,
            "blocks": 5,
            "personal_fouls": 18,
            "fast_break_points": 15,
            "points_in_paint": 48,
            "second_chance_points": 12,
            "bench_points": 28,
            "biggest_lead": 18,
            "time_leading": 1800,
        }
    )

    team_stats_service.create_stats(
        {
            "game_id": game.id,
            "team_id": away_team.id,
            "is_home": False,
            "points": 108,
            "field_goals_made": 40,
            "field_goals_attempted": 90,
            "two_pointers_made": 28,
            "two_pointers_attempted": 54,
            "three_pointers_made": 12,
            "three_pointers_attempted": 36,
            "free_throws_made": 16,
            "free_throws_attempted": 18,
            "offensive_rebounds": 8,
            "defensive_rebounds": 28,
            "total_rebounds": 36,
            "assists": 22,
            "turnovers": 14,
            "steals": 6,
            "blocks": 3,
            "personal_fouls": 20,
            "fast_break_points": 12,
            "points_in_paint": 44,
            "second_chance_points": 10,
            "bench_points": 24,
            "biggest_lead": 5,
            "time_leading": 600,
        }
    )

    return game, season, home_team, away_team, player1, player2, player3


class TestListGames:
    """Tests for GET /api/v1/games endpoint."""

    def test_list_games_empty(self, client):
        """Test listing games returns empty list when no games exist."""
        response = client.get("/api/v1/games")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_games_with_data(self, client, test_db: Session):
        """Test listing games returns all games."""
        game, _, _, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get("/api/v1/games")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(game.id)

    def test_list_games_with_team_filter(self, client, test_db: Session):
        """Test listing games filtered by team."""
        game, _, home_team, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games?team_id={home_team.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["home_team_id"] == str(home_team.id)

    def test_list_games_with_status_filter(self, client, test_db: Session):
        """Test listing games filtered by status."""
        _create_test_game_with_stats(test_db)

        # Filter for FINAL games
        response = client.get("/api/v1/games?status=FINAL")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "FINAL"

        # Filter for SCHEDULED games (should be empty)
        response = client.get("/api/v1/games?status=SCHEDULED")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_games_with_date_filter(self, client, test_db: Session):
        """Test listing games filtered by date range."""
        _create_test_game_with_stats(test_db)

        # Should include the game
        response = client.get(
            "/api/v1/games?start_date=2024-01-01&end_date=2024-01-31"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Should exclude the game
        response = client.get(
            "/api/v1/games?start_date=2024-02-01&end_date=2024-02-28"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_games_with_season_filter(self, client, test_db: Session):
        """Test listing games filtered by season."""
        _, season, _, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games?season_id={season.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        # Wrong season
        fake_season = uuid.uuid4()
        response = client.get(f"/api/v1/games?season_id={fake_season}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_games_pagination(self, client, test_db: Session):
        """Test listing games with pagination."""
        _create_test_game_with_stats(test_db)

        # Skip 1
        response = client.get("/api/v1/games?skip=1")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 0


class TestGetGame:
    """Tests for GET /api/v1/games/{game_id} endpoint."""

    def test_get_game_success(self, client, test_db: Session):
        """Test getting a game with box score returns correct data."""
        game, _, home_team, away_team, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games/{game.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(game.id)
        assert data["home_team_name"] == "Los Angeles Lakers"
        assert data["away_team_name"] == "Boston Celtics"
        assert data["home_score"] == 112
        assert data["away_score"] == 108
        assert data["status"] == "FINAL"

    def test_get_game_with_team_stats(self, client, test_db: Session):
        """Test getting a game includes team box score data."""
        game, _, _, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games/{game.id}")

        assert response.status_code == 200
        data = response.json()

        # Home team stats
        home_stats = data["home_team_stats"]
        assert home_stats is not None
        assert home_stats["points"] == 112
        assert home_stats["is_home"] is True
        assert home_stats["field_goals_made"] == 42
        assert home_stats["field_goals_attempted"] == 88

        # Away team stats
        away_stats = data["away_team_stats"]
        assert away_stats is not None
        assert away_stats["points"] == 108
        assert away_stats["is_home"] is False

    def test_get_game_with_player_stats(self, client, test_db: Session):
        """Test getting a game includes player box score data."""
        game, _, _, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games/{game.id}")

        assert response.status_code == 200
        data = response.json()

        # Home players
        home_players = data["home_players"]
        assert len(home_players) == 2
        player_names = [p["player_name"] for p in home_players]
        assert "LeBron James" in player_names
        assert "Anthony Davis" in player_names

        # Away players
        away_players = data["away_players"]
        assert len(away_players) == 1
        assert away_players[0]["player_name"] == "Jayson Tatum"

    def test_get_game_player_stats_percentages(self, client, test_db: Session):
        """Test player stats include computed percentages."""
        game, _, _, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games/{game.id}")

        assert response.status_code == 200
        data = response.json()

        # Find LeBron's stats (11/22 FG = 50%)
        lebron = next(
            p for p in data["home_players"] if p["player_name"] == "LeBron James"
        )
        assert lebron["field_goal_pct"] == 50.0
        assert lebron["minutes_display"] == "35:00"

    def test_get_game_not_found(self, client):
        """Test getting a non-existent game returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/games/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetPlayByPlay:
    """Tests for GET /api/v1/games/{game_id}/pbp endpoint."""

    def test_get_play_by_play_empty(self, client, test_db: Session):
        """Test getting play-by-play for game with no events."""
        game, _, _, _, _, _, _ = _create_test_game_with_stats(test_db)

        response = client.get(f"/api/v1/games/{game.id}/pbp")

        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == str(game.id)
        assert data["events"] == []
        assert data["total_events"] == 0

    def test_get_play_by_play_with_events(self, client, test_db: Session):
        """Test getting play-by-play returns events."""
        game, _, home_team, _, player1, _, _ = _create_test_game_with_stats(test_db)

        # Create some play-by-play events
        pbp_service = PlayByPlayService(test_db)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "12:00",
                "event_type": "JUMP_BALL",
                "team_id": home_team.id,
                "description": "Jump ball won by Lakers",
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "11:45",
                "event_type": "SHOT",
                "event_subtype": "LAYUP",
                "player_id": player1.id,
                "team_id": home_team.id,
                "success": True,
                "coord_x": 0.5,
                "coord_y": 0.5,
                "description": "LeBron James makes layup",
            }
        )

        response = client.get(f"/api/v1/games/{game.id}/pbp")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 2
        assert len(data["events"]) == 2
        assert data["events"][0]["event_number"] == 1
        assert data["events"][1]["event_type"] == "SHOT"

    def test_get_play_by_play_with_period_filter(self, client, test_db: Session):
        """Test filtering play-by-play by period."""
        game, _, home_team, _, _, _, _ = _create_test_game_with_stats(test_db)

        pbp_service = PlayByPlayService(test_db)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "12:00",
                "event_type": "PERIOD_START",
                "team_id": home_team.id,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 2,
                "clock": "12:00",
                "event_type": "PERIOD_START",
                "team_id": home_team.id,
            }
        )

        response = client.get(f"/api/v1/games/{game.id}/pbp?period=1")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert data["events"][0]["period"] == 1

    def test_get_play_by_play_with_event_type_filter(self, client, test_db: Session):
        """Test filtering play-by-play by event type."""
        game, _, home_team, _, player1, _, _ = _create_test_game_with_stats(test_db)

        pbp_service = PlayByPlayService(test_db)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "11:45",
                "event_type": "SHOT",
                "player_id": player1.id,
                "team_id": home_team.id,
                "success": True,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "11:30",
                "event_type": "REBOUND",
                "player_id": player1.id,
                "team_id": home_team.id,
            }
        )

        response = client.get(f"/api/v1/games/{game.id}/pbp?event_type=SHOT")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert data["events"][0]["event_type"] == "SHOT"

    def test_get_play_by_play_with_player_filter(self, client, test_db: Session):
        """Test filtering play-by-play by player."""
        game, _, home_team, _, player1, player2, _ = _create_test_game_with_stats(
            test_db
        )

        pbp_service = PlayByPlayService(test_db)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "11:45",
                "event_type": "SHOT",
                "player_id": player1.id,
                "team_id": home_team.id,
                "success": True,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "11:30",
                "event_type": "SHOT",
                "player_id": player2.id,
                "team_id": home_team.id,
                "success": False,
            }
        )

        response = client.get(f"/api/v1/games/{game.id}/pbp?player_id={player1.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert data["events"][0]["player_name"] == "LeBron James"

    def test_get_play_by_play_with_team_filter(self, client, test_db: Session):
        """Test filtering play-by-play by team."""
        game, _, home_team, away_team, player1, _, player3 = _create_test_game_with_stats(
            test_db
        )

        pbp_service = PlayByPlayService(test_db)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "11:45",
                "event_type": "SHOT",
                "player_id": player1.id,
                "team_id": home_team.id,
                "success": True,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "11:30",
                "event_type": "SHOT",
                "player_id": player3.id,
                "team_id": away_team.id,
                "success": True,
            }
        )

        response = client.get(f"/api/v1/games/{game.id}/pbp?team_id={away_team.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert data["events"][0]["team_name"] == "Boston Celtics"

    def test_get_play_by_play_game_not_found(self, client):
        """Test getting play-by-play for non-existent game returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/games/{fake_id}/pbp")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
