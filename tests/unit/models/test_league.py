"""
League Model Tests

Tests for src/models/league.py covering:
- League model creation and fields
- Season model creation with FK to League
- League-Season relationship and cascade delete
- is_current flag behavior
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, League, Season


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


class TestLeagueModel:
    """Tests for the League model."""

    def test_league_creation_with_all_fields(self, db_session: Session):
        """League should be created with all required fields."""
        league = League(
            name="National Basketball Association",
            code="NBA",
            country="USA",
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

        assert league.id is not None
        assert isinstance(league.id, uuid.UUID)
        assert league.name == "National Basketball Association"
        assert league.code == "NBA"
        assert league.country == "USA"
        assert league.created_at is not None
        assert league.updated_at is not None

    def test_league_code_unique_constraint(self, db_session: Session):
        """League code should be unique."""
        league1 = League(name="League 1", code="NBA", country="USA")
        db_session.add(league1)
        db_session.commit()

        league2 = League(name="League 2", code="NBA", country="Spain")
        db_session.add(league2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_league_repr(self, db_session: Session):
        """League __repr__ should return meaningful string."""
        league = League(name="EuroLeague", code="EURO", country="Europe")
        db_session.add(league)
        db_session.commit()

        assert "EURO" in repr(league)
        assert "EuroLeague" in repr(league)


class TestSeasonModel:
    """Tests for the Season model."""

    def test_season_creation_with_all_fields(self, db_session: Session):
        """Season should be created with all required fields."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 20),
            is_current=True,
        )
        db_session.add(season)
        db_session.commit()
        db_session.refresh(season)

        assert season.id is not None
        assert isinstance(season.id, uuid.UUID)
        assert season.league_id == league.id
        assert season.name == "2023-24"
        assert season.start_date == date(2023, 10, 24)
        assert season.end_date == date(2024, 6, 20)
        assert season.is_current is True

    def test_season_foreign_key_to_league(self, db_session: Session):
        """Season should have FK relationship to League."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 20),
            is_current=True,
        )
        db_session.add(season)
        db_session.commit()
        db_session.refresh(season)

        # Access via relationship
        assert season.league == league

    def test_season_is_current_default(self, db_session: Session):
        """Season is_current should default to False."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season = Season(
            league_id=league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
        )
        db_session.add(season)
        db_session.commit()
        db_session.refresh(season)

        assert season.is_current is False

    def test_season_repr(self, db_session: Session):
        """Season __repr__ should return meaningful string."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 20),
        )
        db_session.add(season)
        db_session.commit()

        assert "2023-24" in repr(season)


class TestLeagueSeasonRelationship:
    """Tests for League-Season relationship."""

    def test_league_seasons_relationship(self, db_session: Session):
        """League should have access to its seasons via relationship."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season1 = Season(
            league_id=league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
        )
        season2 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 20),
        )
        db_session.add_all([season1, season2])
        db_session.commit()
        db_session.refresh(league)

        assert len(league.seasons) == 2
        assert season1 in league.seasons
        assert season2 in league.seasons

    def test_cascade_delete_from_league_to_seasons(self, db_session: Session):
        """Deleting a league should cascade delete its seasons."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 20),
        )
        db_session.add(season)
        db_session.commit()

        season_id = season.id

        # Delete the league
        db_session.delete(league)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # Season should also be deleted
        deleted_season = db_session.get(Season, season_id)
        assert deleted_season is None

    def test_unique_season_name_per_league(self, db_session: Session):
        """Same season name should not be allowed in the same league."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season1 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 20),
        )
        db_session.add(season1)
        db_session.commit()

        season2 = Season(
            league_id=league.id,
            name="2023-24",  # Same name
            start_date=date(2023, 11, 1),
            end_date=date(2024, 5, 1),
        )
        db_session.add(season2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestImports:
    """Tests for module imports."""

    def test_import_from_league_module(self):
        """Should be able to import from league module."""
        from src.models.league import League, Season

        assert League is not None
        assert Season is not None

    def test_import_from_models_package(self):
        """Should be able to import from models package."""
        from src.models import League, Season

        assert League is not None
        assert Season is not None
