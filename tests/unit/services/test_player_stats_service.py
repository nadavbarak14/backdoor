"""
Unit tests for PlayerSeasonStatsService.

Tests player season statistics service operations including
multi-team handling, career stats, and league leaders.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.player import Player
from src.models.stats import PlayerSeasonStats
from src.models.team import Team
from src.services.player_stats import PlayerSeasonStatsService


@pytest.fixture
def league(test_db: Session) -> League:
    """Create a test league."""
    league = League(name="Test League", code="TL", country="Test")
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def season(test_db: Session, league: League) -> Season:
    """Create a test season."""
    season = Season(
        league_id=league.id,
        name="2023-24",
        start_date=datetime(2023, 10, 1, tzinfo=UTC),
        end_date=datetime(2024, 6, 30, tzinfo=UTC),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def second_season(test_db: Session, league: League) -> Season:
    """Create a second test season."""
    season = Season(
        league_id=league.id,
        name="2022-23",
        start_date=datetime(2022, 10, 1, tzinfo=UTC),
        end_date=datetime(2023, 6, 30, tzinfo=UTC),
        is_current=False,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def team1(test_db: Session) -> Team:
    """Create first test team."""
    team = Team(
        name="Team One",
        short_name="T1",
        city="City One",
        country="Test Country",
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def team2(test_db: Session) -> Team:
    """Create second test team."""
    team = Team(
        name="Team Two",
        short_name="T2",
        city="City Two",
        country="Test Country",
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def player1(test_db: Session) -> Player:
    """Create first test player."""
    player = Player(
        first_name="Test",
        last_name="Player",
        position="PG",
    )
    test_db.add(player)
    test_db.commit()
    return player


@pytest.fixture
def player2(test_db: Session) -> Player:
    """Create second test player."""
    player = Player(
        first_name="Another",
        last_name="Player",
        position="SG",
    )
    test_db.add(player)
    test_db.commit()
    return player


@pytest.fixture
def player3(test_db: Session) -> Player:
    """Create third test player."""
    player = Player(
        first_name="Third",
        last_name="Player",
        position="SF",
    )
    test_db.add(player)
    test_db.commit()
    return player


class TestPlayerSeasonStatsService:
    """Tests for PlayerSeasonStatsService."""

    def test_get_player_season_single_team(
        self,
        test_db: Session,
        player1: Player,
        team1: Team,
        season: Season,
    ):
        """Test getting player's season stats with single team."""
        service = PlayerSeasonStatsService(test_db)

        # Create season stats
        stats = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            games_started=50,
            total_points=1000,
            avg_points=20.0,
        )
        test_db.add(stats)
        test_db.commit()

        # Query
        result = service.get_player_season(player1.id, season.id)

        assert len(result) == 1
        assert result[0].games_played == 50
        assert result[0].avg_points == 20.0

    def test_get_player_season_traded_player(
        self,
        test_db: Session,
        player1: Player,
        team1: Team,
        team2: Team,
        season: Season,
    ):
        """Test getting season stats for traded player (multiple teams)."""
        service = PlayerSeasonStatsService(test_db)

        # Create stats for first team
        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=40,
            games_started=40,
            total_points=800,
            avg_points=20.0,
        )
        # Create stats for second team (after trade)
        stats2 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team2.id,
            season_id=season.id,
            games_played=30,
            games_started=30,
            total_points=750,
            avg_points=25.0,
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        # Query
        result = service.get_player_season(player1.id, season.id)

        assert len(result) == 2
        # Should be ordered by games_played descending
        assert result[0].games_played == 40
        assert result[1].games_played == 30

    def test_get_player_season_no_stats(
        self,
        test_db: Session,
        player1: Player,
        season: Season,
    ):
        """Test getting season stats when none exist."""
        service = PlayerSeasonStatsService(test_db)

        result = service.get_player_season(player1.id, season.id)

        assert result == []

    def test_get_player_career(
        self,
        test_db: Session,
        player1: Player,
        team1: Team,
        season: Season,
        second_season: Season,
    ):
        """Test getting player's career stats (multiple seasons)."""
        service = PlayerSeasonStatsService(test_db)

        # Create stats for two seasons
        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=70,
            avg_points=22.0,
        )
        stats2 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=second_season.id,
            games_played=65,
            avg_points=18.0,
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        # Query
        result = service.get_player_career(player1.id)

        assert len(result) == 2
        # Should include stats from both seasons

    def test_get_player_career_no_stats(
        self,
        test_db: Session,
        player1: Player,
    ):
        """Test getting career stats when none exist."""
        service = PlayerSeasonStatsService(test_db)

        result = service.get_player_career(player1.id)

        assert result == []

    def test_get_league_leaders_points(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        player3: Player,
        team1: Team,
        season: Season,
    ):
        """Test getting league leaders for points."""
        service = PlayerSeasonStatsService(test_db)

        # Create stats with different scoring averages
        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_points=25.0,
        )
        stats2 = PlayerSeasonStats(
            player_id=player2.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_points=30.0,  # Highest
        )
        stats3 = PlayerSeasonStats(
            player_id=player3.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_points=20.0,
        )
        test_db.add_all([stats1, stats2, stats3])
        test_db.commit()

        # Query
        result = service.get_league_leaders(season.id, "points", limit=10)

        assert len(result) == 3
        assert result[0].avg_points == 30.0  # player2 leads
        assert result[1].avg_points == 25.0
        assert result[2].avg_points == 20.0

    def test_get_league_leaders_with_min_games(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        team1: Team,
        season: Season,
    ):
        """Test league leaders with minimum games filter."""
        service = PlayerSeasonStatsService(test_db)

        # Player 1: Many games, lower average
        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_points=22.0,
        )
        # Player 2: Few games, higher average
        stats2 = PlayerSeasonStats(
            player_id=player2.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=5,
            avg_points=35.0,
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        # Query with min_games=20
        result = service.get_league_leaders(season.id, "points", limit=10, min_games=20)

        # Only player1 qualifies
        assert len(result) == 1
        assert result[0].player_id == player1.id

    def test_get_league_leaders_rebounds(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        team1: Team,
        season: Season,
    ):
        """Test league leaders for rebounds."""
        service = PlayerSeasonStatsService(test_db)

        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_rebounds=12.0,
        )
        stats2 = PlayerSeasonStats(
            player_id=player2.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_rebounds=8.0,
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        result = service.get_league_leaders(season.id, "rebounds")

        assert len(result) == 2
        assert result[0].avg_rebounds == 12.0

    def test_get_league_leaders_field_goal_pct(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        team1: Team,
        season: Season,
    ):
        """Test league leaders for field goal percentage."""
        service = PlayerSeasonStatsService(test_db)

        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            field_goal_pct=0.55,  # 55%
        )
        stats2 = PlayerSeasonStats(
            player_id=player2.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            field_goal_pct=0.62,  # 62%
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        result = service.get_league_leaders(season.id, "field_goal_pct")

        assert len(result) == 2
        assert result[0].field_goal_pct == 0.62

    def test_get_league_leaders_efficiency(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        team1: Team,
        season: Season,
    ):
        """Test league leaders for efficiency (true shooting %)."""
        service = PlayerSeasonStatsService(test_db)

        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            true_shooting_pct=0.65,
        )
        stats2 = PlayerSeasonStats(
            player_id=player2.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            true_shooting_pct=0.58,
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        result = service.get_league_leaders(season.id, "efficiency")

        assert len(result) == 2
        assert result[0].true_shooting_pct == 0.65

    def test_get_league_leaders_invalid_category(
        self,
        test_db: Session,
        season: Season,
    ):
        """Test league leaders with invalid category raises error."""
        service = PlayerSeasonStatsService(test_db)

        with pytest.raises(ValueError, match="Unknown category"):
            service.get_league_leaders(season.id, "invalid_stat")

    def test_get_league_leaders_limit(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        player3: Player,
        team1: Team,
        season: Season,
    ):
        """Test league leaders respects limit parameter."""
        service = PlayerSeasonStatsService(test_db)

        # Create 3 players
        for i, player in enumerate([player1, player2, player3]):
            stats = PlayerSeasonStats(
                player_id=player.id,
                team_id=team1.id,
                season_id=season.id,
                games_played=50,
                avg_points=20.0 + i,
            )
            test_db.add(stats)
        test_db.commit()

        result = service.get_league_leaders(season.id, "points", limit=2)

        assert len(result) == 2

    def test_get_team_season_stats(
        self,
        test_db: Session,
        player1: Player,
        player2: Player,
        team1: Team,
        season: Season,
    ):
        """Test getting all player stats for a team in a season."""
        service = PlayerSeasonStatsService(test_db)

        stats1 = PlayerSeasonStats(
            player_id=player1.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=70,
            avg_points=20.0,
        )
        stats2 = PlayerSeasonStats(
            player_id=player2.id,
            team_id=team1.id,
            season_id=season.id,
            games_played=50,
            avg_points=15.0,
        )
        test_db.add_all([stats1, stats2])
        test_db.commit()

        result = service.get_team_season_stats(team1.id, season.id)

        assert len(result) == 2
        # Ordered by games_played descending
        assert result[0].games_played == 70
        assert result[1].games_played == 50
