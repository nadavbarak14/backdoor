"""
Integration tests for Sync Coverage API endpoint.

Tests the /sync/coverage endpoint for accurate sync status reporting.

Usage:
    uv run python -m pytest tests/integration/test_sync_coverage_api.py -v
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.schemas.enums import Position


@pytest.fixture
def sample_data(test_db: Session) -> dict:
    """
    Create sample data for sync coverage testing.

    Creates a league, season, teams, players, games with varying
    levels of sync completeness to test coverage calculations.

    Returns:
        Dict with created entities for reference in tests.
    """
    # Create league and season
    league = League(name="Test League", code="TST", country="Test")
    test_db.add(league)
    test_db.commit()

    season = Season(
        league_id=league.id,
        name="2024-25",
        start_date=datetime(2024, 10, 1, tzinfo=UTC),
        end_date=datetime(2025, 6, 30, tzinfo=UTC),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()

    # Create teams
    team1 = Team(name="Team Alpha", short_name="ALP", city="Alpha City", country="Test")
    team2 = Team(name="Team Beta", short_name="BET", city="Beta City", country="Test")
    test_db.add_all([team1, team2])
    test_db.commit()

    # Create players with varying bio completeness
    players = [
        Player(first_name="Player", last_name="One", positions=[Position.POINT_GUARD], height_cm=185),
        Player(first_name="Player", last_name="Two", positions=[Position.SHOOTING_GUARD], height_cm=None),
        Player(first_name="Player", last_name="Three", position=None, height_cm=200),
        Player(first_name="Player", last_name="Four", position=None, height_cm=None),
    ]
    test_db.add_all(players)
    test_db.commit()

    # Add players to season via PlayerTeamHistory
    for player in players:
        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team1.id,
            season_id=season.id,
        )
        test_db.add(history)
    test_db.commit()

    # Create games - 3 FINAL, 1 SCHEDULED
    games = [
        Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 15, tzinfo=UTC),
            status="FINAL",
            home_score=100,
            away_score=95,
        ),
        Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 10, 20, tzinfo=UTC),
            status="FINAL",
            home_score=88,
            away_score=92,
        ),
        Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 25, tzinfo=UTC),
            status="FINAL",
            home_score=105,
            away_score=100,
        ),
        Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 11, 1, tzinfo=UTC),
            status="SCHEDULED",
        ),
    ]
    test_db.add_all(games)
    test_db.commit()

    # Add boxscore to first 2 games
    for game in games[:2]:
        stat = PlayerGameStats(
            game_id=game.id,
            player_id=players[0].id,
            team_id=team1.id,
            points=20,
        )
        test_db.add(stat)

    # Add PBP to first game only
    event = PlayByPlayEvent(
        game_id=games[0].id,
        event_number=1,
        period=1,
        clock="10:00",
        event_type="SHOT",
        team_id=team1.id,
        player_id=players[0].id,
    )
    test_db.add(event)
    test_db.commit()

    return {
        "league": league,
        "season": season,
        "teams": [team1, team2],
        "players": players,
        "games": games,
    }


class TestSyncCoverageAPI:
    """Integration tests for /sync/coverage endpoint."""

    def test_sync_coverage_endpoint_returns_data(self, client, sample_data):
        """Test that coverage endpoint returns valid response structure."""
        response = client.get("/api/v1/sync/coverage")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "seasons" in data
        assert "total_games" in data
        assert "total_games_with_boxscore" in data
        assert "total_games_with_pbp" in data

    def test_sync_coverage_accurate_counts(self, client, sample_data):
        """Test that coverage counts match actual data."""
        response = client.get("/api/v1/sync/coverage")

        assert response.status_code == 200
        data = response.json()

        # We created 3 FINAL games, 2 with boxscore, 1 with PBP
        assert data["total_games"] == 3
        assert data["total_games_with_boxscore"] == 2
        assert data["total_games_with_pbp"] == 1

    def test_sync_coverage_season_detail(self, client, sample_data):
        """Test that per-season coverage is accurate."""
        response = client.get("/api/v1/sync/coverage")

        assert response.status_code == 200
        data = response.json()

        # Find our season
        seasons = data["seasons"]
        assert len(seasons) == 1

        season = seasons[0]
        assert season["season_name"] == "2024-25"
        assert season["league_name"] == "Test League"

        # Game counts
        assert season["games_total"] == 3  # 3 FINAL games
        assert season["games_with_boxscore"] == 2
        assert season["games_with_pbp"] == 1

        # Player counts - 4 players, 3 with bio (position or height)
        assert season["players_total"] == 4
        assert season["players_with_bio"] == 3  # Player4 has neither

        # Percentages
        assert season["boxscore_pct"] == pytest.approx(66.7, rel=0.1)
        assert season["pbp_pct"] == pytest.approx(33.3, rel=0.1)
        assert season["bio_pct"] == 75.0

    def test_sync_coverage_empty_database(self, client):
        """Test coverage endpoint with empty database."""
        response = client.get("/api/v1/sync/coverage")

        assert response.status_code == 200
        data = response.json()

        assert data["seasons"] == []
        assert data["total_games"] == 0
        assert data["total_games_with_boxscore"] == 0
        assert data["total_games_with_pbp"] == 0

    def test_sync_coverage_multiple_seasons(self, client, test_db):
        """Test coverage with multiple seasons."""
        # Create league
        league = League(name="Multi Season League", code="MSL", country="Test")
        test_db.add(league)
        test_db.commit()

        # Create two seasons
        season1 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=datetime(2023, 10, 1, tzinfo=UTC),
            end_date=datetime(2024, 6, 30, tzinfo=UTC),
        )
        season2 = Season(
            league_id=league.id,
            name="2024-25",
            start_date=datetime(2024, 10, 1, tzinfo=UTC),
            end_date=datetime(2025, 6, 30, tzinfo=UTC),
        )
        test_db.add_all([season1, season2])
        test_db.commit()

        response = client.get("/api/v1/sync/coverage")

        assert response.status_code == 200
        data = response.json()

        # Should have 2 seasons, ordered by name descending
        assert len(data["seasons"]) == 2
        assert data["seasons"][0]["season_name"] == "2024-25"
        assert data["seasons"][1]["season_name"] == "2023-24"
