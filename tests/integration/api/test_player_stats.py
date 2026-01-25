"""
Integration tests for the player stats API endpoints.

Tests:
    - GET /api/v1/players/{player_id}/stats - Get player career stats
    - GET /api/v1/players/{player_id}/stats/{season_id} - Get player season stats
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.models.stats import PlayerSeasonStats
from src.schemas import (
    LeagueCreate,
    PlayerCreate,
    SeasonCreate,
    TeamCreate,
)
from src.services import LeagueService, PlayerService, SeasonService, TeamService


def create_test_setup(test_db: Session) -> dict:
    """Create common test data for player stats tests."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)
    team_service = TeamService(test_db)
    player_service = PlayerService(test_db)

    # Create league
    league = league_service.create_league(
        LeagueCreate(name="Winner League", code="WINNER", country="Israel")
    )

    # Create seasons
    season1 = season_service.create_season(
        SeasonCreate(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
    )
    season2 = season_service.create_season(
        SeasonCreate(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
    )

    # Create teams
    team1 = team_service.create_team(
        TeamCreate(
            name="Maccabi Tel Aviv",
            short_name="MAC",
            city="Tel Aviv",
            country="Israel",
        )
    )
    team2 = team_service.create_team(
        TeamCreate(
            name="Hapoel Jerusalem",
            short_name="HAP",
            city="Jerusalem",
            country="Israel",
        )
    )

    # Create player
    player = player_service.create_player(
        PlayerCreate(
            first_name="Scottie",
            last_name="Wilbekin",
            nationality="USA",
            position="PG",
        )
    )

    return {
        "league": league,
        "season1": season1,
        "season2": season2,
        "team1": team1,
        "team2": team2,
        "player": player,
    }


def create_season_stats(
    test_db: Session,
    player_id,
    team_id,
    season_id,
    games_played: int = 20,
    avg_points: float = 15.0,
) -> PlayerSeasonStats:
    """Create a PlayerSeasonStats record for testing."""
    stats = PlayerSeasonStats(
        player_id=player_id,
        team_id=team_id,
        season_id=season_id,
        games_played=games_played,
        games_started=games_played - 2,
        total_minutes=games_played * 1800,
        total_points=int(avg_points * games_played),
        total_field_goals_made=int(5 * games_played),
        total_field_goals_attempted=int(12 * games_played),
        total_two_pointers_made=int(3 * games_played),
        total_two_pointers_attempted=int(6 * games_played),
        total_three_pointers_made=int(2 * games_played),
        total_three_pointers_attempted=int(6 * games_played),
        total_free_throws_made=int(3 * games_played),
        total_free_throws_attempted=int(4 * games_played),
        total_offensive_rebounds=int(1 * games_played),
        total_defensive_rebounds=int(3 * games_played),
        total_rebounds=int(4 * games_played),
        total_assists=int(5 * games_played),
        total_turnovers=int(2 * games_played),
        total_steals=int(1 * games_played),
        total_blocks=int(0.5 * games_played),
        total_personal_fouls=int(2 * games_played),
        total_plus_minus=int(3 * games_played),
        avg_minutes=1800.0,
        avg_points=avg_points,
        avg_rebounds=4.0,
        avg_assists=5.0,
        avg_turnovers=2.0,
        avg_steals=1.0,
        avg_blocks=0.5,
        field_goal_pct=0.417,
        two_point_pct=0.50,
        three_point_pct=0.333,
        free_throw_pct=0.75,
        true_shooting_pct=0.55,
        effective_field_goal_pct=0.50,
        assist_turnover_ratio=2.5,
        last_calculated=datetime.now(UTC),
    )
    test_db.add(stats)
    test_db.commit()
    test_db.refresh(stats)
    return stats


class TestGetPlayerCareerStats:
    """Tests for GET /api/v1/players/{player_id}/stats endpoint."""

    def test_get_career_stats_success(self, client, test_db: Session):
        """Test getting player career stats returns correct data."""
        setup = create_test_setup(test_db)
        player = setup["player"]

        # Create season stats for two seasons
        create_season_stats(
            test_db,
            player.id,
            setup["team1"].id,
            setup["season1"].id,
            games_played=20,
            avg_points=15.0,
        )
        create_season_stats(
            test_db,
            player.id,
            setup["team1"].id,
            setup["season2"].id,
            games_played=25,
            avg_points=18.0,
        )

        response = client.get(f"/api/v1/players/{player.id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == str(player.id)
        assert data["player_name"] == "Scottie Wilbekin"
        assert data["career_games_played"] == 45
        assert len(data["seasons"]) == 2

    def test_get_career_stats_empty(self, client, test_db: Session):
        """Test getting career stats for player with no stats returns empty."""
        player_service = PlayerService(test_db)
        player = player_service.create_player(
            PlayerCreate(first_name="New", last_name="Player")
        )

        response = client.get(f"/api/v1/players/{player.id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["career_games_played"] == 0
        assert data["seasons"] == []

    def test_get_career_stats_player_not_found(self, client):
        """Test getting career stats for non-existent player returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/players/{fake_id}/stats")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_career_stats_traded_player(self, client, test_db: Session):
        """Test career stats correctly shows multiple teams in same season."""
        setup = create_test_setup(test_db)
        player = setup["player"]

        # Create stats for same season on two different teams (traded)
        create_season_stats(
            test_db,
            player.id,
            setup["team1"].id,
            setup["season1"].id,
            games_played=15,
            avg_points=14.0,
        )
        create_season_stats(
            test_db,
            player.id,
            setup["team2"].id,
            setup["season1"].id,
            games_played=10,
            avg_points=16.0,
        )

        response = client.get(f"/api/v1/players/{player.id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["career_games_played"] == 25
        assert len(data["seasons"]) == 2

        team_names = [s["team_name"] for s in data["seasons"]]
        assert "Maccabi Tel Aviv" in team_names
        assert "Hapoel Jerusalem" in team_names


class TestGetPlayerSeasonStats:
    """Tests for GET /api/v1/players/{player_id}/stats/{season_id} endpoint."""

    def test_get_season_stats_success(self, client, test_db: Session):
        """Test getting player season stats returns correct data."""
        setup = create_test_setup(test_db)
        player = setup["player"]
        season = setup["season1"]

        create_season_stats(
            test_db,
            player.id,
            setup["team1"].id,
            season.id,
            games_played=20,
            avg_points=15.0,
        )

        response = client.get(f"/api/v1/players/{player.id}/stats/{season.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_name"] == "Scottie Wilbekin"
        assert data[0]["team_name"] == "Maccabi Tel Aviv"
        assert data[0]["season_name"] == "2023-24"
        assert data[0]["games_played"] == 20
        assert data[0]["avg_points"] == 15.0

    def test_get_season_stats_traded_player(self, client, test_db: Session):
        """Test getting season stats for traded player shows multiple entries."""
        setup = create_test_setup(test_db)
        player = setup["player"]
        season = setup["season1"]

        # Stats on two teams in same season
        create_season_stats(
            test_db,
            player.id,
            setup["team1"].id,
            season.id,
            games_played=15,
            avg_points=14.0,
        )
        create_season_stats(
            test_db,
            player.id,
            setup["team2"].id,
            season.id,
            games_played=10,
            avg_points=16.0,
        )

        response = client.get(f"/api/v1/players/{player.id}/stats/{season.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        team_names = [s["team_name"] for s in data]
        assert "Maccabi Tel Aviv" in team_names
        assert "Hapoel Jerusalem" in team_names

    def test_get_season_stats_player_not_found(self, client, test_db: Session):
        """Test getting season stats for non-existent player returns 404."""
        setup = create_test_setup(test_db)
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/players/{fake_id}/stats/{setup['season1'].id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_season_stats_no_data(self, client, test_db: Session):
        """Test getting season stats when no data exists returns 404."""
        setup = create_test_setup(test_db)
        player = setup["player"]
        season = setup["season1"]

        response = client.get(f"/api/v1/players/{player.id}/stats/{season.id}")

        assert response.status_code == 404
        assert "no stats found" in response.json()["detail"].lower()
