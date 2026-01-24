"""
Game Model Tests

Tests for src/models/game.py covering:
- Game model creation with all fields
- Game relationships to Season, Teams
- Home/away team relationships
- external_ids JSON storage
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Season, Team


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


class TestGameModel:
    """Tests for the Game model."""

    def test_game_creation_with_all_fields(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game should be created with all required fields."""
        game_date = datetime(2024, 1, 15, 19, 30, tzinfo=UTC)
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=game_date,
            status="FINAL",
            home_score=112,
            away_score=108,
            venue="Crypto.com Arena",
            attendance=18997,
            external_ids={"winner": "123", "nba": "0022300567"},
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.id is not None
        assert isinstance(game.id, uuid.UUID)
        assert game.season_id == sample_season.id
        assert game.home_team_id == sample_home_team.id
        assert game.away_team_id == sample_away_team.id
        # SQLite doesn't preserve timezone info, so compare without tzinfo
        assert game.game_date.replace(tzinfo=None) == game_date.replace(tzinfo=None)
        assert game.status == "FINAL"
        assert game.home_score == 112
        assert game.away_score == 108
        assert game.venue == "Crypto.com Arena"
        assert game.attendance == 18997
        assert game.external_ids == {"winner": "123", "nba": "0022300567"}
        assert game.created_at is not None
        assert game.updated_at is not None

    def test_game_creation_minimal_fields(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game should be created with only required fields."""
        game_date = datetime(2024, 1, 15, 19, 30, tzinfo=UTC)
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=game_date,
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.id is not None
        assert game.status == "SCHEDULED"  # Default value
        assert game.home_score is None
        assert game.away_score is None
        assert game.venue is None
        assert game.attendance is None
        assert game.external_ids == {}

    def test_game_external_ids_json(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game external_ids should store and retrieve JSON correctly."""
        external_ids = {
            "winner": "123",
            "euroleague": "ABC",
            "fiba": "XYZ",
        }
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            external_ids=external_ids,
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.external_ids["winner"] == "123"
        assert game.external_ids["euroleague"] == "ABC"
        assert game.external_ids["fiba"] == "XYZ"

    def test_game_repr(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game __repr__ should return meaningful string."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            status="FINAL",
        )
        db_session.add(game)
        db_session.commit()

        assert "Game" in repr(game)
        assert "FINAL" in repr(game)


class TestGameRelationships:
    """Tests for Game relationships."""

    def test_game_season_relationship(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game should have access to its season."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.season == sample_season

    def test_game_home_team_relationship(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game should have access to its home team."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.home_team == sample_home_team

    def test_game_away_team_relationship(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Game should have access to its away team."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)

        assert game.away_team == sample_away_team

    def test_season_games_relationship(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Season should have access to its games."""
        game1 = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        game2 = Game(
            season_id=sample_season.id,
            home_team_id=sample_away_team.id,
            away_team_id=sample_home_team.id,
            game_date=datetime(2024, 1, 20, 19, 30, tzinfo=UTC),
        )
        db_session.add_all([game1, game2])
        db_session.commit()
        db_session.refresh(sample_season)

        assert len(sample_season.games) == 2
        assert game1 in sample_season.games
        assert game2 in sample_season.games

    def test_team_home_games_relationship(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Team should have access to its home games."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(sample_home_team)

        assert len(sample_home_team.home_games) == 1
        assert game in sample_home_team.home_games

    def test_team_away_games_relationship(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Team should have access to its away games."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(sample_away_team)

        assert len(sample_away_team.away_games) == 1
        assert game in sample_away_team.away_games


class TestGameCascadeDelete:
    """Tests for Game cascade delete behavior."""

    def test_cascade_delete_season_to_games(
        self,
        db_session: Session,
        sample_season: Season,
        sample_home_team: Team,
        sample_away_team: Team,
    ):
        """Deleting a season should cascade delete games."""
        game = Game(
            season_id=sample_season.id,
            home_team_id=sample_home_team.id,
            away_team_id=sample_away_team.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )
        db_session.add(game)
        db_session.commit()

        game_id = game.id

        # Delete the season
        db_session.delete(sample_season)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # Game should also be deleted
        deleted_game = db_session.get(Game, game_id)
        assert deleted_game is None


class TestImports:
    """Tests for module imports."""

    def test_import_from_game_module(self):
        """Should be able to import from game module."""
        from src.models.game import Game, PlayerGameStats, TeamGameStats

        assert Game is not None
        assert PlayerGameStats is not None
        assert TeamGameStats is not None

    def test_import_from_models_package(self):
        """Should be able to import from models package."""
        from src.models import Game, PlayerGameStats, TeamGameStats

        assert Game is not None
        assert PlayerGameStats is not None
        assert TeamGameStats is not None
