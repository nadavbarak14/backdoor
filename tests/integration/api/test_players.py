"""
Integration tests for the players API endpoints.

Tests:
    - GET /api/v1/players - Search players with filters
    - GET /api/v1/players/{player_id} - Get player with team history
"""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from src.schemas import (
    LeagueCreate,
    PlayerCreate,
    SeasonCreate,
    TeamCreate,
)
from src.services import LeagueService, PlayerService, SeasonService, TeamService


class TestListPlayers:
    """Tests for GET /api/v1/players endpoint."""

    def test_list_players_empty(self, client):
        """Test listing players returns empty list when no players exist."""
        response = client.get("/api/v1/players")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_players_with_data(self, client, test_db: Session):
        """Test listing players returns all players."""
        player_service = PlayerService(test_db)

        player_service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James", position="SF")
        )
        player_service.create_player(
            PlayerCreate(first_name="Stephen", last_name="Curry", position="PG")
        )

        response = client.get("/api/v1/players")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_players_with_search_filter(self, client, test_db: Session):
        """Test listing players filtered by search term."""
        player_service = PlayerService(test_db)

        player_service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James")
        )
        player_service.create_player(
            PlayerCreate(first_name="Stephen", last_name="Curry")
        )

        response = client.get("/api/v1/players?search=curry")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["last_name"] == "Curry"

    def test_list_players_with_position_filter(self, client, test_db: Session):
        """Test listing players filtered by position."""
        player_service = PlayerService(test_db)

        player_service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James", position="SF")
        )
        player_service.create_player(
            PlayerCreate(first_name="Stephen", last_name="Curry", position="PG")
        )
        player_service.create_player(
            PlayerCreate(first_name="Chris", last_name="Paul", position="PG")
        )

        response = client.get("/api/v1/players?position=PG")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(p["position"] == "PG" for p in data["items"])

    def test_list_players_with_nationality_filter(self, client, test_db: Session):
        """Test listing players filtered by nationality."""
        player_service = PlayerService(test_db)

        player_service.create_player(
            PlayerCreate(
                first_name="LeBron", last_name="James", nationality="USA"
            )
        )
        player_service.create_player(
            PlayerCreate(
                first_name="Luka", last_name="Doncic", nationality="Slovenia"
            )
        )

        response = client.get("/api/v1/players?nationality=Slovenia")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["last_name"] == "Doncic"

    def test_list_players_pagination(self, client, test_db: Session):
        """Test listing players respects skip and limit parameters."""
        player_service = PlayerService(test_db)

        for i in range(5):
            player_service.create_player(
                PlayerCreate(first_name=f"Player{i}", last_name=f"Test{i}")
            )

        response = client.get("/api/v1/players?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


class TestGetPlayer:
    """Tests for GET /api/v1/players/{player_id} endpoint."""

    def test_get_player_success(self, client, test_db: Session):
        """Test getting a player by ID returns correct data."""
        player_service = PlayerService(test_db)

        player = player_service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                birth_date=date(1984, 12, 30),
                nationality="USA",
                height_cm=206,
                position="SF",
                external_ids={"nba": "2544"},
            )
        )

        response = client.get(f"/api/v1/players/{player.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(player.id)
        assert data["first_name"] == "LeBron"
        assert data["last_name"] == "James"
        assert data["full_name"] == "LeBron James"
        assert data["nationality"] == "USA"
        assert data["height_cm"] == 206
        assert data["position"] == "SF"
        assert data["external_ids"]["nba"] == "2544"

    def test_get_player_with_team_history(self, client, test_db: Session):
        """Test getting a player includes team history."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)
        team_service = TeamService(test_db)
        player_service = PlayerService(test_db)

        # Create league, seasons, and teams
        league = league_service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )
        season1 = season_service.create_season(
            SeasonCreate(
                league_id=league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )
        season2 = season_service.create_season(
            SeasonCreate(
                league_id=league.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
            )
        )

        lakers = team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )
        cavs = team_service.create_team(
            TeamCreate(
                name="Cleveland Cavaliers",
                short_name="CLE",
                city="Cleveland",
                country="USA",
            )
        )

        # Create player with team history
        player = player_service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James")
        )
        player_service.add_to_team(
            player.id, cavs.id, season1.id, jersey_number=23, position="SF"
        )
        player_service.add_to_team(
            player.id, lakers.id, season2.id, jersey_number=23, position="SF"
        )

        response = client.get(f"/api/v1/players/{player.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["team_history"]) == 2

        # Check team history contains correct data
        team_names = [h["team_name"] for h in data["team_history"]]
        assert "Los Angeles Lakers" in team_names
        assert "Cleveland Cavaliers" in team_names

        # Check season info
        for history in data["team_history"]:
            assert "season_id" in history
            assert "season_name" in history
            assert history["jersey_number"] == 23
            assert history["position"] == "SF"

    def test_get_player_not_found(self, client):
        """Test getting a non-existent player returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/players/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
