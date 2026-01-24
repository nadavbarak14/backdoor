"""
Integration tests for the leagues API endpoints.

Tests:
    - GET /api/v1/leagues - List all leagues
    - GET /api/v1/leagues/{league_id} - Get league by ID
    - GET /api/v1/leagues/{league_id}/seasons - List seasons for a league
"""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from src.schemas import LeagueCreate, SeasonCreate
from src.services import LeagueService, SeasonService


class TestListLeagues:
    """Tests for GET /api/v1/leagues endpoint."""

    def test_list_leagues_empty(self, client):
        """Test listing leagues returns empty list when no leagues exist."""
        response = client.get("/api/v1/leagues")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_leagues_with_data(self, client, test_db: Session):
        """Test listing leagues returns all leagues with season counts."""
        # Create test data
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)

        nba = league_service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )
        league_service.create_league(
            LeagueCreate(name="EuroLeague", code="EL", country="Europe")
        )

        # Add seasons to NBA
        season_service.create_season(
            SeasonCreate(
                league_id=nba.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
            )
        )

        response = client.get("/api/v1/leagues")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Check NBA has season count
        nba_item = next(item for item in data["items"] if item["code"] == "NBA")
        assert nba_item["season_count"] == 1

        # Check EuroLeague has 0 seasons
        el_item = next(item for item in data["items"] if item["code"] == "EL")
        assert el_item["season_count"] == 0

    def test_list_leagues_pagination(self, client, test_db: Session):
        """Test listing leagues respects skip and limit parameters."""
        league_service = LeagueService(test_db)

        # Create 5 leagues
        for i in range(5):
            league_service.create_league(
                LeagueCreate(name=f"League {i}", code=f"L{i}", country="Test")
            )

        # Test skip and limit
        response = client.get("/api/v1/leagues?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


class TestGetLeague:
    """Tests for GET /api/v1/leagues/{league_id} endpoint."""

    def test_get_league_success(self, client, test_db: Session):
        """Test getting a league by ID returns correct data."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)

        league = league_service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )
        season_service.create_season(
            SeasonCreate(
                league_id=league.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
            )
        )

        response = client.get(f"/api/v1/leagues/{league.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(league.id)
        assert data["name"] == "NBA"
        assert data["code"] == "NBA"
        assert data["country"] == "USA"
        assert data["season_count"] == 1

    def test_get_league_not_found(self, client):
        """Test getting a non-existent league returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/leagues/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListLeagueSeasons:
    """Tests for GET /api/v1/leagues/{league_id}/seasons endpoint."""

    def test_list_league_seasons_success(self, client, test_db: Session):
        """Test listing seasons for a league returns all seasons."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)

        league = league_service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )
        season_service.create_season(
            SeasonCreate(
                league_id=league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )
        season_service.create_season(
            SeasonCreate(
                league_id=league.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
                is_current=True,
            )
        )

        response = client.get(f"/api/v1/leagues/{league.id}/seasons")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(s["name"] == "2022-23" for s in data)
        assert any(s["name"] == "2023-24" for s in data)

    def test_list_league_seasons_empty(self, client, test_db: Session):
        """Test listing seasons for league with no seasons returns empty list."""
        league_service = LeagueService(test_db)
        league = league_service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )

        response = client.get(f"/api/v1/leagues/{league.id}/seasons")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_league_seasons_not_found(self, client):
        """Test listing seasons for non-existent league returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/leagues/{fake_id}/seasons")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
