"""
Integration tests for the league leaders API endpoints.

Tests:
    - GET /api/v1/stats/leaders - Get league leaders by category
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
from src.schemas.enums import Position


def create_test_setup(test_db: Session) -> dict:
    """Create common test data for league leaders tests."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)
    team_service = TeamService(test_db)
    player_service = PlayerService(test_db)

    # Create league
    league = league_service.create_league(
        LeagueCreate(name="Winner League", code="WINNER", country="Israel")
    )

    # Create season
    season = season_service.create_season(
        SeasonCreate(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
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

    # Create players
    players = []
    for i, (first, last, ppg) in enumerate(
        [
            ("Scottie", "Wilbekin", 18.5),
            ("Wade", "Baldwin", 16.2),
            ("Tamir", "Blatt", 14.8),
            ("John", "DiBartolomeo", 12.1),
            ("Yovel", "Zoosman", 10.5),
        ]
    ):
        player = player_service.create_player(
            PlayerCreate(first_name=first, last_name=last, position="PG")
        )
        players.append((player, ppg, i + 1))

    return {
        "league": league,
        "season": season,
        "team1": team1,
        "team2": team2,
        "players": players,
    }


def create_player_stats(
    test_db: Session,
    player_id,
    team_id,
    season_id,
    games_played: int,
    avg_points: float,
    fg_pct: float = 0.45,
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
        total_field_goals_made=int(6 * games_played),
        total_field_goals_attempted=int(13 * games_played),
        total_two_pointers_made=int(3 * games_played),
        total_two_pointers_attempted=int(6 * games_played),
        total_three_pointers_made=int(3 * games_played),
        total_three_pointers_attempted=int(7 * games_played),
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
        field_goal_pct=fg_pct,
        two_point_pct=0.50,
        three_point_pct=0.43,
        free_throw_pct=0.75,
        true_shooting_pct=0.58,
        effective_field_goal_pct=fg_pct + 0.05,
        assist_turnover_ratio=2.5,
        last_calculated=datetime.now(UTC),
    )
    test_db.add(stats)
    test_db.commit()
    test_db.refresh(stats)
    return stats


class TestGetLeagueLeaders:
    """Tests for GET /api/v1/stats/leaders endpoint."""

    def test_get_leaders_points(self, client, test_db: Session):
        """Test getting league leaders for points category."""
        setup = create_test_setup(test_db)

        # Create stats for all players
        for player, ppg, rank in setup["players"]:
            team = setup["team1"] if rank <= 3 else setup["team2"]
            create_player_stats(
                test_db,
                player.id,
                team.id,
                setup["season"].id,
                games_played=20,
                avg_points=ppg,
            )

        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": setup["season"].id, "category": "points"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "points"
        assert data["season_name"] == "2023-24"
        assert len(data["leaders"]) == 5

        # Verify ordering (highest points first)
        assert data["leaders"][0]["player_name"] == "Scottie Wilbekin"
        assert data["leaders"][0]["rank"] == 1
        assert data["leaders"][0]["value"] == 18.5
        assert data["leaders"][1]["player_name"] == "Wade Baldwin"

    def test_get_leaders_with_limit(self, client, test_db: Session):
        """Test getting league leaders with limit parameter."""
        setup = create_test_setup(test_db)

        for player, ppg, _rank in setup["players"]:
            create_player_stats(
                test_db,
                player.id,
                setup["team1"].id,
                setup["season"].id,
                games_played=20,
                avg_points=ppg,
            )

        response = client.get(
            "/api/v1/stats/leaders",
            params={
                "season_id": setup["season"].id,
                "category": "points",
                "limit": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["leaders"]) == 3

    def test_get_leaders_min_games_filter(self, client, test_db: Session):
        """Test min_games filter excludes low-game players."""
        setup = create_test_setup(test_db)
        player1, _, _ = setup["players"][0]
        player2, _, _ = setup["players"][1]

        # Player 1 with many games
        create_player_stats(
            test_db,
            player1.id,
            setup["team1"].id,
            setup["season"].id,
            games_played=25,
            avg_points=15.0,
        )
        # Player 2 with few games
        create_player_stats(
            test_db,
            player2.id,
            setup["team1"].id,
            setup["season"].id,
            games_played=5,
            avg_points=20.0,
        )

        response = client.get(
            "/api/v1/stats/leaders",
            params={
                "season_id": setup["season"].id,
                "category": "points",
                "min_games": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["leaders"]) == 1
        assert data["leaders"][0]["player_name"] == "Scottie Wilbekin"
        assert data["min_games"] == 10

    def test_get_leaders_other_categories(self, client, test_db: Session):
        """Test getting leaders for different categories."""
        setup = create_test_setup(test_db)
        player, _, _ = setup["players"][0]

        create_player_stats(
            test_db,
            player.id,
            setup["team1"].id,
            setup["season"].id,
            games_played=20,
            avg_points=15.0,
            fg_pct=0.48,
        )

        # Test rebounds category
        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": setup["season"].id, "category": "rebounds"},
        )
        assert response.status_code == 200
        assert response.json()["category"] == "rebounds"

        # Test assists category
        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": setup["season"].id, "category": "assists"},
        )
        assert response.status_code == 200
        assert response.json()["category"] == "assists"

        # Test field_goal_pct category
        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": setup["season"].id, "category": "field_goal_pct"},
        )
        assert response.status_code == 200
        assert response.json()["category"] == "field_goal_pct"

    def test_get_leaders_season_not_found(self, client):
        """Test getting leaders for non-existent season returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": fake_id, "category": "points"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_leaders_missing_season_id(self, client):
        """Test request without season_id returns 422."""
        response = client.get(
            "/api/v1/stats/leaders",
            params={"category": "points"},
        )

        assert response.status_code == 422

    def test_get_leaders_default_category(self, client, test_db: Session):
        """Test default category is points."""
        setup = create_test_setup(test_db)
        player, _, _ = setup["players"][0]

        create_player_stats(
            test_db,
            player.id,
            setup["team1"].id,
            setup["season"].id,
            games_played=20,
            avg_points=15.0,
        )

        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": setup["season"].id},
        )

        assert response.status_code == 200
        assert response.json()["category"] == "points"

    def test_get_leaders_empty_results(self, client, test_db: Session):
        """Test getting leaders when no stats exist returns empty list."""
        setup = create_test_setup(test_db)

        response = client.get(
            "/api/v1/stats/leaders",
            params={"season_id": setup["season"].id, "category": "points"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["leaders"] == []
