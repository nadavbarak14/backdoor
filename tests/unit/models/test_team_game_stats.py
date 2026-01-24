"""
TeamGameStats Model Tests

Tests for TeamGameStats from src/models/game.py covering:
- Composite PK (game_id, team_id)
- is_home flag
- Team-only stats fields
- extra_stats JSON field
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Season, Team, TeamGameStats


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
def sample_home_team(db_session: Session) -> Team:
    """Create a sample home team for testing."""
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
def sample_away_team(db_session: Session) -> Team:
    """Create a sample away team for testing."""
    team = Team(
        name="Boston Celtics",
        short_name="BOS",
        city="Boston",
        country="USA",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_game(
    db_session: Session,
    sample_season: Season,
    sample_home_team: Team,
    sample_away_team: Team,
) -> Game:
    """Create a sample game for testing."""
    game = Game(
        season_id=sample_season.id,
        home_team_id=sample_home_team.id,
        away_team_id=sample_away_team.id,
        game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        status="FINAL",
    )
    db_session.add(game)
    db_session.commit()
    return game


class TestTeamGameStatsModel:
    """Tests for the TeamGameStats model."""

    def test_team_game_stats_creation_with_all_fields(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats should be created with all fields."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
            points=112,
            field_goals_made=42,
            field_goals_attempted=88,
            two_pointers_made=30,
            two_pointers_attempted=55,
            three_pointers_made=12,
            three_pointers_attempted=33,
            free_throws_made=16,
            free_throws_attempted=20,
            offensive_rebounds=10,
            defensive_rebounds=35,
            total_rebounds=45,
            assists=28,
            turnovers=12,
            steals=8,
            blocks=5,
            personal_fouls=18,
            fast_break_points=18,
            points_in_paint=52,
            second_chance_points=14,
            bench_points=38,
            biggest_lead=15,
            time_leading=1800,  # 30 minutes in seconds
            extra_stats={"timeouts_remaining": 2},
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.game_id == sample_game.id
        assert stats.team_id == sample_home_team.id
        assert stats.is_home is True
        assert stats.points == 112
        assert stats.field_goals_made == 42
        assert stats.field_goals_attempted == 88
        assert stats.two_pointers_made == 30
        assert stats.two_pointers_attempted == 55
        assert stats.three_pointers_made == 12
        assert stats.three_pointers_attempted == 33
        assert stats.free_throws_made == 16
        assert stats.free_throws_attempted == 20
        assert stats.offensive_rebounds == 10
        assert stats.defensive_rebounds == 35
        assert stats.total_rebounds == 45
        assert stats.assists == 28
        assert stats.turnovers == 12
        assert stats.steals == 8
        assert stats.blocks == 5
        assert stats.personal_fouls == 18
        assert stats.fast_break_points == 18
        assert stats.points_in_paint == 52
        assert stats.second_chance_points == 14
        assert stats.bench_points == 38
        assert stats.biggest_lead == 15
        assert stats.time_leading == 1800
        assert stats.extra_stats == {"timeouts_remaining": 2}
        assert stats.created_at is not None
        assert stats.updated_at is not None

    def test_team_game_stats_composite_pk(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats should use composite primary key."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        db_session.add(stats)
        db_session.commit()

        # Composite PK - should not have separate id field
        assert not hasattr(stats, "id") or stats.id is None
        assert stats.game_id == sample_game.id
        assert stats.team_id == sample_home_team.id

    def test_team_game_stats_defaults(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats should have correct default values."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.points == 0
        assert stats.field_goals_made == 0
        assert stats.fast_break_points == 0
        assert stats.points_in_paint == 0
        assert stats.bench_points == 0
        assert stats.extra_stats == {}

    def test_team_game_stats_is_home_flag(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """TeamGameStats should correctly track is_home flag."""
        home_stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        away_stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_away_team.id,
            is_home=False,
        )
        db_session.add_all([home_stats, away_stats])
        db_session.commit()
        db_session.refresh(home_stats)
        db_session.refresh(away_stats)

        assert home_stats.is_home is True
        assert away_stats.is_home is False

    def test_team_game_stats_extra_stats_json(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats extra_stats should store and retrieve JSON correctly."""
        extra_stats = {
            "timeouts_remaining": 2,
            "technical_fouls": 1,
            "flagrant_fouls": 0,
        }
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
            extra_stats=extra_stats,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.extra_stats["timeouts_remaining"] == 2
        assert stats.extra_stats["technical_fouls"] == 1
        assert stats.extra_stats["flagrant_fouls"] == 0

    def test_team_game_stats_repr(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats __repr__ should return meaningful string."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
            points=112,
        )
        db_session.add(stats)
        db_session.commit()

        assert "TeamGameStats" in repr(stats)
        assert "points=112" in repr(stats)


class TestTeamGameStatsUniqueConstraint:
    """Tests for TeamGameStats composite primary key constraint."""

    def test_team_game_stats_unique_constraint(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """Same team-game combination should not be allowed twice."""
        stats1 = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
            points=112,
        )
        db_session.add(stats1)
        db_session.commit()

        stats2 = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
            points=108,  # Different points
        )
        db_session.add(stats2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestTeamGameStatsRelationships:
    """Tests for TeamGameStats relationships."""

    def test_team_game_stats_game_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats should have access to its game."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.game == sample_game

    def test_team_game_stats_team_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """TeamGameStats should have access to its team."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.team == sample_home_team

    def test_game_team_game_stats_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game should have access to its team_game_stats."""
        home_stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        away_stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_away_team.id,
            is_home=False,
        )
        db_session.add_all([home_stats, away_stats])
        db_session.commit()
        db_session.refresh(sample_game)

        assert len(sample_game.team_game_stats) == 2
        assert home_stats in sample_game.team_game_stats
        assert away_stats in sample_game.team_game_stats

    def test_team_team_game_stats_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """Team should have access to its team_game_stats."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(sample_home_team)

        assert len(sample_home_team.team_game_stats) == 1
        assert stats in sample_home_team.team_game_stats


class TestTeamGameStatsCascadeDelete:
    """Tests for TeamGameStats cascade delete behavior."""

    def test_cascade_delete_game_to_team_game_stats(
        self,
        db_session: Session,
        sample_game: Game,
        sample_home_team: Team,
    ):
        """Deleting a game should cascade delete team_game_stats."""
        stats = TeamGameStats(
            game_id=sample_game.id,
            team_id=sample_home_team.id,
            is_home=True,
        )
        db_session.add(stats)
        db_session.commit()

        game_id = sample_game.id
        team_id = sample_home_team.id

        # Delete the game
        db_session.delete(sample_game)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # TeamGameStats should also be deleted
        result = (
            db_session.query(TeamGameStats)
            .filter_by(game_id=game_id, team_id=team_id)
            .first()
        )
        assert result is None
