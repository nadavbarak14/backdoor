"""
Integration tests for the team game history API endpoint.

Tests:
    - GET /api/v1/teams/{team_id}/games - Get team game history
"""

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from src.schemas import (
    GameCreate,
    GameStatus,
    LeagueCreate,
    SeasonCreate,
    TeamCreate,
)
from src.services import (
    GameService,
    LeagueService,
    SeasonService,
    TeamGameStatsService,
    TeamService,
)


def _create_team_with_games(test_db: Session) -> tuple:
    """Helper to create a team with games for testing."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)
    team_service = TeamService(test_db)
    game_service = GameService(test_db)
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
    warriors = team_service.create_team(
        TeamCreate(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
    )

    # Create game 1 (Lakers home win vs Celtics)
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

    # Create game 2 (Lakers away loss at Celtics)
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

    # Create game 3 (Lakers home win vs Warriors)
    game3 = game_service.create_game(
        GameCreate(
            season_id=season.id,
            home_team_id=lakers.id,
            away_team_id=warriors.id,
            game_date=datetime(2024, 1, 25, 19, 30),
            status=GameStatus.FINAL,
            venue="Crypto.com Arena",
        )
    )
    game_service.update_score(game3.id, home_score=120, away_score=118)

    # Create team stats for Lakers
    team_stats_service.create_stats(
        {
            "game_id": game1.id,
            "team_id": lakers.id,
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
            "game_id": game2.id,
            "team_id": lakers.id,
            "is_home": False,
            "points": 105,
            "field_goals_made": 38,
            "field_goals_attempted": 85,
            "two_pointers_made": 26,
            "two_pointers_attempted": 50,
            "three_pointers_made": 12,
            "three_pointers_attempted": 35,
            "free_throws_made": 17,
            "free_throws_attempted": 22,
            "offensive_rebounds": 8,
            "defensive_rebounds": 28,
            "total_rebounds": 36,
            "assists": 20,
            "turnovers": 15,
            "steals": 5,
            "blocks": 3,
            "personal_fouls": 22,
            "fast_break_points": 10,
            "points_in_paint": 40,
            "second_chance_points": 8,
            "bench_points": 22,
            "biggest_lead": 3,
            "time_leading": 600,
        }
    )

    team_stats_service.create_stats(
        {
            "game_id": game3.id,
            "team_id": lakers.id,
            "is_home": True,
            "points": 120,
            "field_goals_made": 45,
            "field_goals_attempted": 90,
            "two_pointers_made": 32,
            "two_pointers_attempted": 58,
            "three_pointers_made": 13,
            "three_pointers_attempted": 32,
            "free_throws_made": 17,
            "free_throws_attempted": 20,
            "offensive_rebounds": 12,
            "defensive_rebounds": 35,
            "total_rebounds": 47,
            "assists": 28,
            "turnovers": 10,
            "steals": 9,
            "blocks": 6,
            "personal_fouls": 16,
            "fast_break_points": 18,
            "points_in_paint": 52,
            "second_chance_points": 14,
            "bench_points": 30,
            "biggest_lead": 12,
            "time_leading": 2100,
        }
    )

    return lakers, season, celtics, warriors, game1, game2, game3


class TestTeamGameHistory:
    """Tests for GET /api/v1/teams/{team_id}/games endpoint."""

    def test_get_team_games_success(self, client, test_db: Session):
        """Test getting team game history returns games."""
        lakers, _, _, _, _, _, _ = _create_team_with_games(test_db)

        response = client.get(f"/api/v1/teams/{lakers.id}/games")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_get_team_games_includes_opponent_info(self, client, test_db: Session):
        """Test game history includes opponent information."""
        lakers, _, celtics, warriors, _, _, _ = _create_team_with_games(test_db)

        response = client.get(f"/api/v1/teams/{lakers.id}/games")

        assert response.status_code == 200
        data = response.json()

        # Games are ordered by date descending
        # Jan 25 vs Warriors, Jan 20 vs Celtics, Jan 15 vs Celtics
        games = data["items"]
        assert len(games) == 3

        # Most recent game - vs Warriors at home
        assert games[0]["opponent_team_name"] == "Golden State Warriors"
        assert games[0]["is_home"] is True

        # Second game - away at Celtics
        assert games[1]["opponent_team_name"] == "Boston Celtics"
        assert games[1]["is_home"] is False

        # Third game - home vs Celtics
        assert games[2]["opponent_team_name"] == "Boston Celtics"
        assert games[2]["is_home"] is True

    def test_get_team_games_includes_result(self, client, test_db: Session):
        """Test game history includes win/loss result."""
        lakers, _, _, _, _, _, _ = _create_team_with_games(test_db)

        response = client.get(f"/api/v1/teams/{lakers.id}/games")

        assert response.status_code == 200
        data = response.json()

        # Games ordered by date desc: Jan 25 (W), Jan 20 (L), Jan 15 (W)
        games = data["items"]

        # Jan 25 - Win vs Warriors 120-118
        assert games[0]["result"] == "W"
        assert games[0]["team_score"] == 120
        assert games[0]["opponent_score"] == 118

        # Jan 20 - Loss at Celtics 105-115
        assert games[1]["result"] == "L"
        assert games[1]["team_score"] == 105
        assert games[1]["opponent_score"] == 115

        # Jan 15 - Win vs Celtics 112-108
        assert games[2]["result"] == "W"
        assert games[2]["team_score"] == 112
        assert games[2]["opponent_score"] == 108

    def test_get_team_games_includes_venue(self, client, test_db: Session):
        """Test game history includes venue information."""
        lakers, _, _, _, _, _, _ = _create_team_with_games(test_db)

        response = client.get(f"/api/v1/teams/{lakers.id}/games")

        assert response.status_code == 200
        data = response.json()

        games = data["items"]
        # Home games should show Crypto.com Arena
        assert games[0]["venue"] == "Crypto.com Arena"  # vs Warriors
        assert games[1]["venue"] == "TD Garden"  # at Celtics
        assert games[2]["venue"] == "Crypto.com Arena"  # vs Celtics

    def test_get_team_games_with_season_filter(self, client, test_db: Session):
        """Test filtering game history by season."""
        lakers, season, _, _, _, _, _ = _create_team_with_games(test_db)

        response = client.get(f"/api/v1/teams/{lakers.id}/games?season_id={season.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

        # Wrong season
        fake_season = uuid.uuid4()
        response = client.get(
            f"/api/v1/teams/{lakers.id}/games?season_id={fake_season}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_team_games_pagination(self, client, test_db: Session):
        """Test pagination of game history."""
        lakers, _, _, _, _, _, _ = _create_team_with_games(test_db)

        # Get first 2 games only
        response = client.get(f"/api/v1/teams/{lakers.id}/games?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

        # Skip first 2, get last 1
        response = client.get(f"/api/v1/teams/{lakers.id}/games?skip=2&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1

    def test_get_team_games_team_not_found(self, client):
        """Test getting game history for non-existent team returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/teams/{fake_id}/games")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_team_games_no_games(self, client, test_db: Session):
        """Test getting game history for team with no games."""
        team_service = TeamService(test_db)

        team = team_service.create_team(
            TeamCreate(
                name="New Team",
                short_name="NEW",
                city="New City",
                country="USA",
            )
        )

        response = client.get(f"/api/v1/teams/{team.id}/games")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
