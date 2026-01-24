"""
Integration tests for the player game log API endpoint.

Tests:
    - GET /api/v1/players/{player_id}/games - Get player game log
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
    PlayerGameStatsService,
    PlayerService,
    SeasonService,
    TeamService,
)


def _create_player_with_games(test_db: Session) -> tuple:
    """Helper to create a player with game stats for testing."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)
    team_service = TeamService(test_db)
    player_service = PlayerService(test_db)
    game_service = GameService(test_db)
    player_stats_service = PlayerGameStatsService(test_db)

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
    lakers = team_service.create_team(
        TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
    )
    celtics = team_service.create_team(
        TeamCreate(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        )
    )

    # Create player
    player = player_service.create_player(
        PlayerCreate(
            first_name="LeBron",
            last_name="James",
            position="SF",
        )
    )

    # Create game 1 (home win)
    game1 = game_service.create_game(
        GameCreate(
            season_id=season.id,
            home_team_id=lakers.id,
            away_team_id=celtics.id,
            game_date=datetime(2024, 1, 15, 19, 30),
            status=GameStatus.FINAL,
            venue="Crypto.com Arena",
        )
    )
    game_service.update_score(game1.id, home_score=112, away_score=108)

    # Create game 2 (away loss)
    game2 = game_service.create_game(
        GameCreate(
            season_id=season.id,
            home_team_id=celtics.id,
            away_team_id=lakers.id,
            game_date=datetime(2024, 1, 20, 19, 30),
            status=GameStatus.FINAL,
            venue="TD Garden",
        )
    )
    game_service.update_score(game2.id, home_score=115, away_score=105)

    # Create player stats for game 1
    player_stats_service.create_stats(
        {
            "game_id": game1.id,
            "player_id": player.id,
            "team_id": lakers.id,
            "minutes_played": 2100,
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

    # Create player stats for game 2
    player_stats_service.create_stats(
        {
            "game_id": game2.id,
            "player_id": player.id,
            "team_id": lakers.id,
            "minutes_played": 1980,
            "is_starter": True,
            "points": 25,
            "field_goals_made": 9,
            "field_goals_attempted": 20,
            "two_pointers_made": 6,
            "two_pointers_attempted": 12,
            "three_pointers_made": 3,
            "three_pointers_attempted": 8,
            "free_throws_made": 4,
            "free_throws_attempted": 5,
            "offensive_rebounds": 1,
            "defensive_rebounds": 6,
            "total_rebounds": 7,
            "assists": 6,
            "turnovers": 4,
            "steals": 1,
            "blocks": 0,
            "personal_fouls": 3,
            "plus_minus": -10,
            "efficiency": 22,
        }
    )

    return player, season, lakers, celtics, game1, game2


class TestPlayerGameLog:
    """Tests for GET /api/v1/players/{player_id}/games endpoint."""

    def test_get_player_games_success(self, client, test_db: Session):
        """Test getting player game log returns games with stats."""
        player, _, _, _, _, _ = _create_player_with_games(test_db)

        response = client.get(f"/api/v1/players/{player.id}/games")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_player_games_includes_opponent_info(self, client, test_db: Session):
        """Test game log includes opponent information."""
        player, _, _, celtics, game1, _ = _create_player_with_games(test_db)

        response = client.get(f"/api/v1/players/{player.id}/games")

        assert response.status_code == 200
        data = response.json()

        # Find the home game (game1 is more recent so might be first)
        # Games are ordered by date descending
        games = data["items"]

        # Game 2 is Jan 20, Game 1 is Jan 15, so Game 2 should be first
        away_game = games[0]  # Jan 20 - away at Celtics
        home_game = games[1]  # Jan 15 - home vs Celtics

        # Away game should have Celtics as opponent with is_home=False
        assert away_game["opponent_team_name"] == "Boston Celtics"
        assert away_game["is_home"] is False

        # Home game should have Celtics as opponent with is_home=True
        assert home_game["opponent_team_name"] == "Boston Celtics"
        assert home_game["is_home"] is True

    def test_get_player_games_includes_result(self, client, test_db: Session):
        """Test game log includes win/loss result."""
        player, _, _, _, _, _ = _create_player_with_games(test_db)

        response = client.get(f"/api/v1/players/{player.id}/games")

        assert response.status_code == 200
        data = response.json()

        # Game 2 (Jan 20 - away): Lakers lost 105-115
        # Game 1 (Jan 15 - home): Lakers won 112-108
        games = data["items"]

        # Games ordered by date desc
        away_game = games[0]  # Jan 20 loss
        home_game = games[1]  # Jan 15 win

        assert away_game["result"] == "L"
        assert away_game["team_score"] == 105
        assert away_game["opponent_score"] == 115

        assert home_game["result"] == "W"
        assert home_game["team_score"] == 112
        assert home_game["opponent_score"] == 108

    def test_get_player_games_includes_stats(self, client, test_db: Session):
        """Test game log includes player statistics."""
        player, _, _, _, _, _ = _create_player_with_games(test_db)

        response = client.get(f"/api/v1/players/{player.id}/games")

        assert response.status_code == 200
        data = response.json()

        # Check that stats are present
        game = data["items"][1]  # Home game with 30 points
        assert game["points"] == 30
        assert game["assists"] == 8
        assert game["total_rebounds"] == 10
        assert game["field_goals_made"] == 11
        assert game["field_goals_attempted"] == 22
        # Check computed field
        assert game["field_goal_pct"] == 50.0

    def test_get_player_games_with_season_filter(self, client, test_db: Session):
        """Test filtering game log by season."""
        player, season, _, _, _, _ = _create_player_with_games(test_db)

        response = client.get(
            f"/api/v1/players/{player.id}/games?season_id={season.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        # Wrong season
        fake_season = uuid.uuid4()
        response = client.get(
            f"/api/v1/players/{player.id}/games?season_id={fake_season}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_player_games_pagination(self, client, test_db: Session):
        """Test pagination of game log."""
        player, _, _, _, _, _ = _create_player_with_games(test_db)

        # Get first game only
        response = client.get(f"/api/v1/players/{player.id}/games?limit=1")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1

        # Skip first, get second
        response = client.get(f"/api/v1/players/{player.id}/games?skip=1&limit=1")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1

    def test_get_player_games_player_not_found(self, client):
        """Test getting game log for non-existent player returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/players/{fake_id}/games")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_player_games_no_games(self, client, test_db: Session):
        """Test getting game log for player with no games."""
        player_service = PlayerService(test_db)

        player = player_service.create_player(
            PlayerCreate(
                first_name="New",
                last_name="Player",
            )
        )

        response = client.get(f"/api/v1/players/{player.id}/games")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
