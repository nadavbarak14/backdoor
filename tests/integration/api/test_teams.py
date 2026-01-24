"""
Integration tests for the teams API endpoints.

Tests:
    - GET /api/v1/teams - List teams with filters
    - GET /api/v1/teams/{team_id} - Get team by ID
    - GET /api/v1/teams/{team_id}/roster - Get team roster
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


class TestListTeams:
    """Tests for GET /api/v1/teams endpoint."""

    def test_list_teams_empty(self, client):
        """Test listing teams returns empty list when no teams exist."""
        response = client.get("/api/v1/teams")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_teams_with_data(self, client, test_db: Session):
        """Test listing teams returns all teams."""
        team_service = TeamService(test_db)

        team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )
        team_service.create_team(
            TeamCreate(
                name="Boston Celtics",
                short_name="BOS",
                city="Boston",
                country="USA",
            )
        )

        response = client.get("/api/v1/teams")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_teams_with_country_filter(self, client, test_db: Session):
        """Test listing teams filtered by country."""
        team_service = TeamService(test_db)

        team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )
        team_service.create_team(
            TeamCreate(
                name="Real Madrid",
                short_name="RMD",
                city="Madrid",
                country="Spain",
            )
        )

        response = client.get("/api/v1/teams?country=USA")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Los Angeles Lakers"

    def test_list_teams_with_search_filter(self, client, test_db: Session):
        """Test listing teams filtered by search term."""
        team_service = TeamService(test_db)

        team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )
        team_service.create_team(
            TeamCreate(
                name="Boston Celtics",
                short_name="BOS",
                city="Boston",
                country="USA",
            )
        )

        response = client.get("/api/v1/teams?search=lakers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Los Angeles Lakers"


class TestGetTeam:
    """Tests for GET /api/v1/teams/{team_id} endpoint."""

    def test_get_team_success(self, client, test_db: Session):
        """Test getting a team by ID returns correct data."""
        team_service = TeamService(test_db)

        team = team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
                external_ids={"nba": "1610612747"},
            )
        )

        response = client.get(f"/api/v1/teams/{team.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team.id)
        assert data["name"] == "Los Angeles Lakers"
        assert data["short_name"] == "LAL"
        assert data["city"] == "Los Angeles"
        assert data["country"] == "USA"
        assert data["external_ids"]["nba"] == "1610612747"

    def test_get_team_not_found(self, client):
        """Test getting a non-existent team returns 404."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/teams/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetTeamRoster:
    """Tests for GET /api/v1/teams/{team_id}/roster endpoint."""

    def test_get_team_roster_with_season_id(self, client, test_db: Session):
        """Test getting team roster for a specific season."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)
        team_service = TeamService(test_db)
        player_service = PlayerService(test_db)

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

        # Create team
        team = team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )

        # Create players and add to roster
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

        player_service.add_to_team(player1.id, team.id, season.id, jersey_number=23)
        player_service.add_to_team(player2.id, team.id, season.id, jersey_number=3)

        response = client.get(f"/api/v1/teams/{team.id}/roster?season_id={season.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["team"]["name"] == "Los Angeles Lakers"
        assert data["season_name"] == "2023-24"
        assert len(data["players"]) == 2

        player_names = [p["full_name"] for p in data["players"]]
        assert "LeBron James" in player_names
        assert "Anthony Davis" in player_names

    def test_get_team_roster_default_current_season(self, client, test_db: Session):
        """Test getting team roster defaults to current season."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)
        team_service = TeamService(test_db)
        player_service = PlayerService(test_db)

        # Create league and current season
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

        # Create team and player
        team = team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )
        player = player_service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James")
        )
        player_service.add_to_team(player.id, team.id, season.id)

        # Request without season_id
        response = client.get(f"/api/v1/teams/{team.id}/roster")

        assert response.status_code == 200
        data = response.json()
        assert data["season_name"] == "2023-24"
        assert len(data["players"]) == 1

    def test_get_team_roster_no_current_season(self, client, test_db: Session):
        """Test roster endpoint returns 404 when no current season and no season_id."""
        team_service = TeamService(test_db)

        team = team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )

        response = client.get(f"/api/v1/teams/{team.id}/roster")

        assert response.status_code == 404
        assert "current season" in response.json()["detail"].lower()

    def test_get_team_roster_team_not_found(self, client):
        """Test roster endpoint returns 404 for non-existent team."""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/teams/{fake_id}/roster")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_team_roster_season_not_found(self, client, test_db: Session):
        """Test roster endpoint returns 404 for non-existent season."""
        team_service = TeamService(test_db)

        team = team_service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )
        fake_season_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/teams/{team.id}/roster?season_id={fake_season_id}"
        )

        assert response.status_code == 404
        assert "season" in response.json()["detail"].lower()
