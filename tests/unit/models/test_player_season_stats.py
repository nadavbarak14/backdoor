"""
PlayerSeasonStats Model Tests

Tests for PlayerSeasonStats from src/models/stats.py covering:
- PlayerSeasonStats creation with all fields
- Relationship to Player, Team, Season
- Unique constraint (player_id, team_id, season_id)
- Multiple entries for traded player scenario
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import (
    Base,
    League,
    Player,
    PlayerSeasonStats,
    Season,
    Team,
)


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def sample_league(db_session: Session) -> League:
    """Create a sample league for testing."""
    league = League(name="NBA", code="NBA", country="USA")
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def sample_season(db_session: Session, sample_league: League) -> Season:
    """Create a sample season for testing."""
    season = Season(
        league_id=sample_league.id,
        name="2023-24",
        start_date=date(2023, 10, 24),
        end_date=date(2024, 6, 20),
        is_current=True,
    )
    db_session.add(season)
    db_session.commit()
    return season


@pytest.fixture
def sample_team(db_session: Session) -> Team:
    """Create a sample team for testing."""
    team = Team(
        name="Los Angeles Lakers",
        short_name="LAL",
        city="Los Angeles",
        country="USA",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_team_2(db_session: Session) -> Team:
    """Create a second sample team for testing trades."""
    team = Team(
        name="Phoenix Suns",
        short_name="PHX",
        city="Phoenix",
        country="USA",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_player(db_session: Session) -> Player:
    """Create a sample player for testing."""
    player = Player(
        first_name="LeBron",
        last_name="James",
        birth_date=date(1984, 12, 30),
        nationality="USA",
        height_cm=206,
        position="SF",
    )
    db_session.add(player)
    db_session.commit()
    return player


class TestPlayerSeasonStatsModel:
    """Tests for the PlayerSeasonStats model."""

    def test_player_season_stats_creation_with_all_fields(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerSeasonStats should be created with all fields."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            games_played=72,
            games_started=72,
            total_minutes=187200,  # 52 min/game * 60 * 72 games
            total_points=1800,
            total_field_goals_made=650,
            total_field_goals_attempted=1340,
            total_two_pointers_made=450,
            total_two_pointers_attempted=850,
            total_three_pointers_made=200,
            total_three_pointers_attempted=490,
            total_free_throws_made=300,
            total_free_throws_attempted=360,
            total_offensive_rebounds=72,
            total_defensive_rebounds=504,
            total_rebounds=576,
            total_assists=540,
            total_turnovers=216,
            total_steals=90,
            total_blocks=36,
            total_personal_fouls=144,
            total_plus_minus=360,
            avg_minutes=2600.0,  # ~43.3 min in seconds
            avg_points=25.0,
            avg_rebounds=8.0,
            avg_assists=7.5,
            avg_turnovers=3.0,
            avg_steals=1.25,
            avg_blocks=0.5,
            field_goal_pct=0.485,
            two_point_pct=0.529,
            three_point_pct=0.408,
            free_throw_pct=0.833,
            true_shooting_pct=0.612,
            effective_field_goal_pct=0.559,
            assist_turnover_ratio=2.5,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.id is not None
        assert isinstance(stats.id, uuid.UUID)
        assert stats.player_id == sample_player.id
        assert stats.team_id == sample_team.id
        assert stats.season_id == sample_season.id
        assert stats.games_played == 72
        assert stats.games_started == 72
        assert stats.total_points == 1800
        assert stats.avg_points == 25.0
        assert stats.field_goal_pct == 0.485
        assert stats.three_point_pct == 0.408
        assert stats.true_shooting_pct == 0.612
        assert stats.assist_turnover_ratio == 2.5
        assert stats.created_at is not None
        assert stats.updated_at is not None
        assert stats.last_calculated is not None

    def test_player_season_stats_defaults(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerSeasonStats should have correct default values."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.games_played == 0
        assert stats.games_started == 0
        assert stats.total_points == 0
        assert stats.avg_points == 0.0
        assert stats.field_goal_pct is None
        assert stats.true_shooting_pct is None

    def test_player_season_stats_repr(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerSeasonStats __repr__ should return meaningful string."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            games_played=72,
            avg_points=25.0,
        )
        db_session.add(stats)
        db_session.commit()

        assert "PlayerSeasonStats" in repr(stats)
        assert "games=72" in repr(stats)
        assert "ppg=25.0" in repr(stats)


class TestPlayerSeasonStatsUniqueConstraint:
    """Tests for PlayerSeasonStats unique constraint."""

    def test_player_season_stats_unique_constraint(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """Same player-team-season combination should not be allowed twice."""
        stats1 = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            games_played=36,
        )
        db_session.add(stats1)
        db_session.commit()

        stats2 = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            games_played=40,  # Different games count
        )
        db_session.add(stats2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_player_traded_multiple_entries(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_team_2: Team,
        sample_season: Season,
    ):
        """Player traded mid-season should have multiple entries (one per team)."""
        # Stats with original team (before trade)
        stats_team1 = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            games_played=36,
            avg_points=24.5,
        )
        db_session.add(stats_team1)

        # Stats with new team (after trade)
        stats_team2 = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team_2.id,
            season_id=sample_season.id,
            games_played=32,
            avg_points=26.0,
        )
        db_session.add(stats_team2)
        db_session.commit()

        # Both entries should exist
        player_stats = (
            db_session.query(PlayerSeasonStats)
            .filter(
                PlayerSeasonStats.player_id == sample_player.id,
                PlayerSeasonStats.season_id == sample_season.id,
            )
            .all()
        )
        assert len(player_stats) == 2

        # Verify team assignments
        team_ids = {s.team_id for s in player_stats}
        assert sample_team.id in team_ids
        assert sample_team_2.id in team_ids


class TestPlayerSeasonStatsRelationships:
    """Tests for PlayerSeasonStats relationships."""

    def test_player_season_stats_player_relationship(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerSeasonStats should have access to its player."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.player == sample_player

    def test_player_season_stats_team_relationship(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerSeasonStats should have access to its team."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.team == sample_team

    def test_player_season_stats_season_relationship(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerSeasonStats should have access to its season."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.season == sample_season

    def test_player_season_stats_relationship(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """Player should have access to its season_stats."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            avg_points=25.0,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(sample_player)

        assert len(sample_player.season_stats) == 1
        assert stats in sample_player.season_stats


class TestPlayerSeasonStatsCascadeDelete:
    """Tests for PlayerSeasonStats cascade delete behavior."""

    def test_cascade_delete_player_to_season_stats(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """Deleting a player should cascade delete season_stats."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()

        stats_id = stats.id

        # Delete the player
        db_session.delete(sample_player)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # PlayerSeasonStats should also be deleted
        deleted_stats = db_session.get(PlayerSeasonStats, stats_id)
        assert deleted_stats is None

    def test_cascade_delete_season_to_season_stats(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """Deleting a season should cascade delete season_stats."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()

        stats_id = stats.id

        # Delete the season
        db_session.delete(sample_season)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # PlayerSeasonStats should also be deleted
        deleted_stats = db_session.get(PlayerSeasonStats, stats_id)
        assert deleted_stats is None

    def test_cascade_delete_team_to_season_stats(
        self,
        db_session: Session,
        sample_player: Player,
        sample_team: Team,
        sample_season: Season,
    ):
        """Deleting a team should cascade delete season_stats."""
        stats = PlayerSeasonStats(
            player_id=sample_player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(stats)
        db_session.commit()

        stats_id = stats.id

        # Delete the team
        db_session.delete(sample_team)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # PlayerSeasonStats should also be deleted
        deleted_stats = db_session.get(PlayerSeasonStats, stats_id)
        assert deleted_stats is None
