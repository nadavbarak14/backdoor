"""
Unit tests for the browse API endpoints.

Tests hierarchical navigation:
    - GET /api/v1/browse/leagues - List all leagues (root level)
    - GET /api/v1/browse/leagues/{id}/seasons - List seasons in a league
    - GET /api/v1/browse/seasons/{id}/teams - List teams in a season
    - GET /api/v1/browse/teams/{id}/players - List players on a team
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models import League, Player, PlayerTeamHistory, Season, Team, TeamSeason


class TestBrowseLeagues:
    """Tests for GET /api/v1/browse/leagues endpoint."""

    def test_browse_leagues_empty(self, client, test_db: Session):
        """Returns empty list when no leagues exist."""
        response = client.get("/api/v1/browse/leagues")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["parent"] is None

    def test_browse_leagues_returns_all(self, client, test_db: Session):
        """Returns all leagues."""
        league1 = League(name="NBA", code="NBA", country="USA")
        league2 = League(name="EuroLeague", code="EL", country="Europe")
        test_db.add_all([league1, league2])
        test_db.commit()

        response = client.get("/api/v1/browse/leagues")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["parent"] is None
        names = {item["name"] for item in data["items"]}
        assert "NBA" in names
        assert "EuroLeague" in names

    def test_browse_leagues_has_children_true(self, client, test_db: Session):
        """Leagues have has_children=True."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.commit()

        response = client.get("/api/v1/browse/leagues")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["has_children"] is True
        assert data["items"][0]["type"] == "league"


class TestBrowseSeasons:
    """Tests for GET /api/v1/browse/leagues/{id}/seasons endpoint."""

    def test_browse_seasons_for_league(self, client, test_db: Session):
        """Returns seasons for a specific league."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season1 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
        season2 = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add_all([season1, season2])
        test_db.commit()

        response = client.get(f"/api/v1/browse/leagues/{league.id}/seasons")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        # Parent should be the league
        assert data["parent"]["id"] == str(league.id)
        assert data["parent"]["name"] == "NBA"
        assert data["parent"]["type"] == "league"

    def test_browse_seasons_invalid_league_404(self, client):
        """Returns 404 for invalid league ID."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/browse/leagues/{fake_id}/seasons")

        assert response.status_code == 404

    def test_browse_seasons_ordered_descending(self, client, test_db: Session):
        """Seasons are ordered by name descending (most recent first)."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season1 = Season(
            league_id=league.id,
            name="2022-23",
            start_date=date(2022, 10, 1),
            end_date=date(2023, 6, 30),
        )
        season2 = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add_all([season1, season2])
        test_db.commit()

        response = client.get(f"/api/v1/browse/leagues/{league.id}/seasons")

        assert response.status_code == 200
        data = response.json()
        # 2024-25 should be first
        assert data["items"][0]["name"] == "2024-25"
        assert data["items"][1]["name"] == "2022-23"


class TestBrowseTeams:
    """Tests for GET /api/v1/browse/seasons/{id}/teams endpoint."""

    def test_browse_teams_for_season(self, client, test_db: Session):
        """Returns teams participating in a specific season."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        team1 = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        team2 = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        test_db.add_all([team1, team2])
        test_db.flush()

        # Link teams to season
        ts1 = TeamSeason(team_id=team1.id, season_id=season.id)
        ts2 = TeamSeason(team_id=team2.id, season_id=season.id)
        test_db.add_all([ts1, ts2])
        test_db.commit()

        response = client.get(f"/api/v1/browse/seasons/{season.id}/teams")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        # Parent should be the season
        assert data["parent"]["id"] == str(season.id)
        assert data["parent"]["name"] == "2024-25"
        assert data["parent"]["type"] == "season"

    def test_browse_teams_invalid_season_404(self, client):
        """Returns 404 for invalid season ID."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/browse/seasons/{fake_id}/teams")

        assert response.status_code == 404

    def test_browse_teams_only_in_season(self, client, test_db: Session):
        """Only returns teams that are in the specified season."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season1 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
        season2 = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add_all([season1, season2])
        test_db.flush()

        team1 = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        team2 = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        test_db.add_all([team1, team2])
        test_db.flush()

        # Team1 in season1, Team2 in season2
        ts1 = TeamSeason(team_id=team1.id, season_id=season1.id)
        ts2 = TeamSeason(team_id=team2.id, season_id=season2.id)
        test_db.add_all([ts1, ts2])
        test_db.commit()

        response = client.get(f"/api/v1/browse/seasons/{season1.id}/teams")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Golden State Warriors"


class TestBrowsePlayers:
    """Tests for GET /api/v1/browse/teams/{id}/players endpoint."""

    def test_browse_players_for_team(self, client, test_db: Session):
        """Returns players on a specific team."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        test_db.add(team)
        test_db.flush()

        player1 = Player(first_name="Stephen", last_name="Curry", position="PG")
        player2 = Player(first_name="Klay", last_name="Thompson", position="SG")
        test_db.add_all([player1, player2])
        test_db.flush()

        # Link players to team
        pth1 = PlayerTeamHistory(
            player_id=player1.id, team_id=team.id, season_id=season.id
        )
        pth2 = PlayerTeamHistory(
            player_id=player2.id, team_id=team.id, season_id=season.id
        )
        test_db.add_all([pth1, pth2])
        test_db.commit()

        response = client.get(f"/api/v1/browse/teams/{team.id}/players")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        # Parent should be the team
        assert data["parent"]["id"] == str(team.id)
        assert data["parent"]["name"] == "Golden State Warriors"
        assert data["parent"]["type"] == "team"

    def test_browse_players_are_leaf_nodes(self, client, test_db: Session):
        """Players have has_children=False (leaf nodes)."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        test_db.add(team)
        test_db.flush()

        player = Player(first_name="Stephen", last_name="Curry")
        test_db.add(player)
        test_db.flush()

        pth = PlayerTeamHistory(
            player_id=player.id, team_id=team.id, season_id=season.id
        )
        test_db.add(pth)
        test_db.commit()

        response = client.get(f"/api/v1/browse/teams/{team.id}/players")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["has_children"] is False
        assert data["items"][0]["type"] == "player"

    def test_browse_players_invalid_team_404(self, client):
        """Returns 404 for invalid team ID."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/browse/teams/{fake_id}/players")

        assert response.status_code == 404

    def test_browse_players_with_season_filter(self, client, test_db: Session):
        """Can filter players by season."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season1 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
        season2 = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add_all([season1, season2])
        test_db.flush()

        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        test_db.add(team)
        test_db.flush()

        player1 = Player(first_name="Stephen", last_name="Curry")
        player2 = Player(first_name="Chris", last_name="Paul")
        test_db.add_all([player1, player2])
        test_db.flush()

        # Player1 in season1, Player2 in season2
        pth1 = PlayerTeamHistory(
            player_id=player1.id, team_id=team.id, season_id=season1.id
        )
        pth2 = PlayerTeamHistory(
            player_id=player2.id, team_id=team.id, season_id=season2.id
        )
        test_db.add_all([pth1, pth2])
        test_db.commit()

        response = client.get(
            f"/api/v1/browse/teams/{team.id}/players?season_id={season1.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Stephen Curry"

    def test_browse_players_ordered_by_last_name(self, client, test_db: Session):
        """Players are ordered by last name, then first name."""
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        test_db.add(team)
        test_db.flush()

        # Add players in random order
        players = [
            Player(first_name="Klay", last_name="Thompson"),
            Player(first_name="Stephen", last_name="Curry"),
            Player(first_name="Andrew", last_name="Wiggins"),
        ]
        test_db.add_all(players)
        test_db.flush()

        for player in players:
            pth = PlayerTeamHistory(
                player_id=player.id, team_id=team.id, season_id=season.id
            )
            test_db.add(pth)
        test_db.commit()

        response = client.get(f"/api/v1/browse/teams/{team.id}/players")

        assert response.status_code == 200
        data = response.json()
        names = [item["name"] for item in data["items"]]
        # Should be ordered: Curry, Thompson, Wiggins
        assert names == ["Stephen Curry", "Klay Thompson", "Andrew Wiggins"]


class TestBrowseIntegration:
    """Integration tests for the full browse flow."""

    def test_full_browse_flow(self, client, test_db: Session):
        """Test complete navigation: League -> Season -> Team -> Player."""
        # Setup full hierarchy
        league = League(name="NBA", code="NBA", country="USA")
        test_db.add(league)
        test_db.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        test_db.add(team)
        test_db.flush()

        ts = TeamSeason(team_id=team.id, season_id=season.id)
        test_db.add(ts)
        test_db.flush()

        player = Player(first_name="Stephen", last_name="Curry")
        test_db.add(player)
        test_db.flush()

        pth = PlayerTeamHistory(
            player_id=player.id, team_id=team.id, season_id=season.id
        )
        test_db.add(pth)
        test_db.commit()

        # Step 1: Browse leagues
        response = client.get("/api/v1/browse/leagues")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        league_id = data["items"][0]["id"]

        # Step 2: Browse seasons
        response = client.get(f"/api/v1/browse/leagues/{league_id}/seasons")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        season_id = data["items"][0]["id"]

        # Step 3: Browse teams
        response = client.get(f"/api/v1/browse/seasons/{season_id}/teams")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        team_id = data["items"][0]["id"]

        # Step 4: Browse players
        response = client.get(f"/api/v1/browse/teams/{team_id}/players")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Stephen Curry"
        assert data["items"][0]["has_children"] is False
