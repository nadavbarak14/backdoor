"""
Team Model Tests

Tests for src/models/team.py covering:
- Team model creation with external_ids JSON
- TeamSeason composite primary key
- Team-Season many-to-many relationship
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, League, Season, Team, TeamSeason


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


class TestTeamModel:
    """Tests for the Team model."""

    def test_team_creation_with_all_fields(self, db_session: Session):
        """Team should be created with all required fields."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={"winner": "123", "nba": "1610612747"},
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        assert team.id is not None
        assert isinstance(team.id, uuid.UUID)
        assert team.name == "Los Angeles Lakers"
        assert team.short_name == "LAL"
        assert team.city == "Los Angeles"
        assert team.country == "USA"
        assert team.external_ids == {"winner": "123", "nba": "1610612747"}
        assert team.created_at is not None
        assert team.updated_at is not None

    def test_team_external_ids_json(self, db_session: Session):
        """Team external_ids should store and retrieve JSON correctly."""
        external_ids = {
            "winner": "123",
            "euroleague": "ABC",
            "fiba": "XYZ",
        }
        team = Team(
            name="Real Madrid",
            short_name="RMB",
            city="Madrid",
            country="Spain",
            external_ids=external_ids,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        assert team.external_ids["winner"] == "123"
        assert team.external_ids["euroleague"] == "ABC"
        assert team.external_ids["fiba"] == "XYZ"

    def test_team_external_ids_default_empty_dict(self, db_session: Session):
        """Team external_ids should default to empty dict."""
        team = Team(
            name="Golden State Warriors",
            short_name="GSW",
            city="San Francisco",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        assert team.external_ids == {}

    def test_team_repr(self, db_session: Session):
        """Team __repr__ should return meaningful string."""
        team = Team(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        assert "Boston Celtics" in repr(team)
        assert "BOS" in repr(team)


class TestTeamSeasonModel:
    """Tests for the TeamSeason model."""

    def test_team_season_composite_pk(self, db_session: Session, sample_season: Season):
        """TeamSeason should use composite primary key."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        team_season = TeamSeason(
            team_id=team.id,
            season_id=sample_season.id,
        )
        db_session.add(team_season)
        db_session.commit()

        # Composite PK - should not have separate id field
        assert not hasattr(team_season, "id") or team_season.id is None
        assert team_season.team_id == team.id
        assert team_season.season_id == sample_season.id

    def test_team_season_unique_constraint(
        self, db_session: Session, sample_season: Season
    ):
        """Same team-season combination should not be allowed twice."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        ts1 = TeamSeason(team_id=team.id, season_id=sample_season.id)
        db_session.add(ts1)
        db_session.commit()

        ts2 = TeamSeason(team_id=team.id, season_id=sample_season.id)
        db_session.add(ts2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_team_season_repr(self, db_session: Session, sample_season: Season):
        """TeamSeason __repr__ should return meaningful string."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        team_season = TeamSeason(team_id=team.id, season_id=sample_season.id)
        db_session.add(team_season)
        db_session.commit()

        assert "team_id" in repr(team_season)
        assert "season_id" in repr(team_season)


class TestTeamSeasonRelationship:
    """Tests for Team-Season many-to-many relationship."""

    def test_team_has_team_seasons(self, db_session: Session, sample_season: Season):
        """Team should have access to its team_seasons."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        team_season = TeamSeason(team_id=team.id, season_id=sample_season.id)
        db_session.add(team_season)
        db_session.commit()
        db_session.refresh(team)

        assert len(team.team_seasons) == 1
        assert team.team_seasons[0].season_id == sample_season.id

    def test_season_has_team_seasons(self, db_session: Session, sample_season: Season):
        """Season should have access to its team_seasons."""
        team1 = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        team2 = Team(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        )
        db_session.add_all([team1, team2])
        db_session.commit()

        ts1 = TeamSeason(team_id=team1.id, season_id=sample_season.id)
        ts2 = TeamSeason(team_id=team2.id, season_id=sample_season.id)
        db_session.add_all([ts1, ts2])
        db_session.commit()
        db_session.refresh(sample_season)

        assert len(sample_season.team_seasons) == 2

    def test_team_season_relationships(
        self, db_session: Session, sample_season: Season
    ):
        """TeamSeason should have team and season relationships."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        team_season = TeamSeason(team_id=team.id, season_id=sample_season.id)
        db_session.add(team_season)
        db_session.commit()
        db_session.refresh(team_season)

        assert team_season.team == team
        assert team_season.season == sample_season

    def test_cascade_delete_team_to_team_season(
        self, db_session: Session, sample_season: Season
    ):
        """Deleting a team should cascade delete team_seasons."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()

        team_season = TeamSeason(team_id=team.id, season_id=sample_season.id)
        db_session.add(team_season)
        db_session.commit()

        team_id = team.id

        # Delete the team
        db_session.delete(team)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # TeamSeason should also be deleted
        result = db_session.query(TeamSeason).filter_by(team_id=team_id).first()
        assert result is None


class TestImports:
    """Tests for module imports."""

    def test_import_from_team_module(self):
        """Should be able to import from team module."""
        from src.models.team import Team, TeamSeason

        assert Team is not None
        assert TeamSeason is not None

    def test_import_from_models_package(self):
        """Should be able to import from models package."""
        from src.models import Team, TeamSeason

        assert Team is not None
        assert TeamSeason is not None
