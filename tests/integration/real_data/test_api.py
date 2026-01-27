"""
Tests for API endpoints with real data.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestLeaguesAPI:
    """Tests for leagues endpoints."""

    def test_list_leagues(self, real_client: TestClient):
        """Test listing all leagues."""
        response = real_client.get("/api/v1/leagues")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert "id" in data["items"][0]

    def test_get_league_by_id(self, real_client: TestClient, real_db: Session):
        """Test getting a specific league."""
        from src.models.league import League
        league = real_db.query(League).first()

        response = real_client.get(f"/api/v1/leagues/{league.id}")
        assert response.status_code == 200
        assert response.json()["name"] == league.name


class TestTeamsAPI:
    """Tests for teams endpoints."""

    def test_list_teams(self, real_client: TestClient):
        """Test listing all teams."""
        response = real_client.get("/api/v1/teams")
        assert response.status_code == 200
        assert response.json()["total"] >= 10

    def test_get_team_by_id(self, real_client: TestClient, real_db: Session):
        """Test getting a specific team."""
        from src.models.team import Team
        team = real_db.query(Team).first()

        response = real_client.get(f"/api/v1/teams/{team.id}")
        assert response.status_code == 200
        assert response.json()["name"] == team.name

    def test_get_team_games(self, real_client: TestClient, real_db: Session):
        """Test getting team game history."""
        from src.models.game import Game
        game = real_db.query(Game).first()

        response = real_client.get(f"/api/v1/teams/{game.home_team_id}/games")
        assert response.status_code == 200
        assert response.json()["total"] >= 1


class TestPlayersAPI:
    """Tests for players endpoints."""

    def test_list_players(self, real_client: TestClient):
        """Test listing all players."""
        response = real_client.get("/api/v1/players")
        assert response.status_code == 200
        assert response.json()["total"] >= 100

    def test_search_players(self, real_client: TestClient, real_db: Session):
        """Test searching players by name."""
        from src.models.player import Player
        player = real_db.query(Player).first()

        response = real_client.get("/api/v1/players", params={"search": player.last_name[:3]})
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_get_player_by_id(self, real_client: TestClient, real_db: Session):
        """Test getting a specific player."""
        from src.models.player import Player
        player = real_db.query(Player).first()

        response = real_client.get(f"/api/v1/players/{player.id}")
        assert response.status_code == 200
        assert response.json()["first_name"] == player.first_name

    def test_get_player_games(self, real_client: TestClient, real_db: Session):
        """Test getting player game log."""
        from src.models.game import PlayerGameStats
        stat = real_db.query(PlayerGameStats).first()

        response = real_client.get(f"/api/v1/players/{stat.player_id}/games")
        assert response.status_code == 200
        assert response.json()["total"] >= 1


class TestGamesAPI:
    """Tests for games endpoints."""

    def test_list_games(self, real_client: TestClient):
        """Test listing all games."""
        response = real_client.get("/api/v1/games")
        assert response.status_code == 200
        assert response.json()["total"] >= 50

    def test_get_game_by_id(self, real_client: TestClient, real_db: Session):
        """Test getting a specific game with box score."""
        from src.models.game import Game
        game = real_db.query(Game).first()

        response = real_client.get(f"/api/v1/games/{game.id}")
        assert response.status_code == 200
        assert response.json()["status"] == game.status

    def test_get_game_play_by_play(self, real_client: TestClient, real_db: Session):
        """Test getting play-by-play for a game."""
        from src.models.play_by_play import PlayByPlayEvent
        pbp = real_db.query(PlayByPlayEvent).first()

        response = real_client.get(f"/api/v1/games/{pbp.game_id}/pbp")
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestStatsAPI:
    """Tests for stats/leaders endpoints."""

    def test_get_leaders_points(self, real_client: TestClient, real_db: Session):
        """Test getting league leaders in points."""
        from src.models.league import Season
        season = real_db.query(Season).first()

        response = real_client.get(
            "/api/v1/stats/leaders",
            params={"season_id": season.id, "category": "points"}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_leaders_rebounds(self, real_client: TestClient, real_db: Session):
        """Test getting league leaders in rebounds."""
        from src.models.league import Season
        season = real_db.query(Season).first()

        response = real_client.get(
            "/api/v1/stats/leaders",
            params={"season_id": season.id, "category": "rebounds"}
        )
        assert response.status_code == 200


class TestHealthAPI:
    """Tests for health endpoint."""

    def test_health_check(self, real_client: TestClient):
        """Test health endpoint returns OK."""
        response = real_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
