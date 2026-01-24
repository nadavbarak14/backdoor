"""
League and Season Schema Tests

Tests for src/schemas/league.py covering:
- LeagueCreate validation (required fields, length limits)
- LeagueUpdate partial validation
- SeasonCreate date validation
- LeagueResponse from ORM object
"""

import uuid
from datetime import date, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, League, Season
from src.schemas.league import (
    LeagueCreate,
    LeagueListResponse,
    LeagueResponse,
    LeagueUpdate,
    SeasonCreate,
    SeasonFilter,
    SeasonResponse,
    SeasonUpdate,
)


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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


class TestLeagueCreate:
    """Tests for LeagueCreate schema validation."""

    def test_valid_league_create(self):
        """LeagueCreate should accept valid data."""
        data = LeagueCreate(
            name="National Basketball Association",
            code="NBA",
            country="United States",
        )
        assert data.name == "National Basketball Association"
        assert data.code == "NBA"
        assert data.country == "United States"

    def test_name_required(self):
        """LeagueCreate should require name field."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueCreate(code="NBA", country="USA")
        assert "name" in str(exc_info.value)

    def test_code_required(self):
        """LeagueCreate should require code field."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueCreate(name="NBA", country="USA")
        assert "code" in str(exc_info.value)

    def test_country_required(self):
        """LeagueCreate should require country field."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueCreate(name="NBA", code="NBA")
        assert "country" in str(exc_info.value)

    def test_name_max_length(self):
        """LeagueCreate should reject name over 100 chars."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueCreate(
                name="A" * 101,
                code="NBA",
                country="USA",
            )
        assert "name" in str(exc_info.value)

    def test_code_max_length(self):
        """LeagueCreate should reject code over 20 chars."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueCreate(
                name="NBA",
                code="A" * 21,
                country="USA",
            )
        assert "code" in str(exc_info.value)

    def test_name_min_length(self):
        """LeagueCreate should reject empty name."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueCreate(
                name="",
                code="NBA",
                country="USA",
            )
        assert "name" in str(exc_info.value)


class TestLeagueUpdate:
    """Tests for LeagueUpdate schema validation."""

    def test_partial_update(self):
        """LeagueUpdate should allow partial data."""
        data = LeagueUpdate(name="Updated League Name")
        assert data.name == "Updated League Name"
        assert data.code is None
        assert data.country is None

    def test_all_fields_optional(self):
        """LeagueUpdate should allow empty data."""
        data = LeagueUpdate()
        assert data.name is None
        assert data.code is None
        assert data.country is None

    def test_name_max_length(self):
        """LeagueUpdate should validate name max length."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueUpdate(name="A" * 101)
        assert "name" in str(exc_info.value)

    def test_code_min_length(self):
        """LeagueUpdate should validate code min length."""
        with pytest.raises(ValidationError) as exc_info:
            LeagueUpdate(code="")
        assert "code" in str(exc_info.value)


class TestLeagueResponse:
    """Tests for LeagueResponse schema."""

    def test_from_orm_object(self, db_session: Session):
        """LeagueResponse should serialize from ORM object."""
        league = League(
            name="National Basketball Association",
            code="NBA",
            country="USA",
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)

        # Manually add season_count for response
        response = LeagueResponse(
            id=league.id,
            name=league.name,
            code=league.code,
            country=league.country,
            season_count=len(league.seasons),
            created_at=league.created_at,
            updated_at=league.updated_at,
        )

        assert response.id == league.id
        assert response.name == "National Basketball Association"
        assert response.code == "NBA"
        assert response.country == "USA"
        assert response.season_count == 0
        assert response.created_at is not None
        assert response.updated_at is not None

    def test_season_count_computed(self, db_session: Session):
        """LeagueResponse should include season count."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season1 = Season(
            league_id=league.id,
            name="2022-23",
            start_date=date(2022, 10, 1),
            end_date=date(2023, 6, 30),
        )
        season2 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
        db_session.add_all([season1, season2])
        db_session.commit()
        db_session.refresh(league)

        response = LeagueResponse(
            id=league.id,
            name=league.name,
            code=league.code,
            country=league.country,
            season_count=len(league.seasons),
            created_at=league.created_at,
            updated_at=league.updated_at,
        )

        assert response.season_count == 2


class TestLeagueListResponse:
    """Tests for LeagueListResponse schema."""

    def test_list_response_structure(self):
        """LeagueListResponse should contain items and total."""
        league_id = uuid.uuid4()
        now = datetime.now()

        item = LeagueResponse(
            id=league_id,
            name="NBA",
            code="NBA",
            country="USA",
            season_count=0,
            created_at=now,
            updated_at=now,
        )

        response = LeagueListResponse(items=[item], total=1)

        assert len(response.items) == 1
        assert response.total == 1
        assert response.items[0].code == "NBA"


class TestSeasonCreate:
    """Tests for SeasonCreate schema validation."""

    def test_valid_season_create(self):
        """SeasonCreate should accept valid data."""
        league_id = uuid.uuid4()
        data = SeasonCreate(
            league_id=league_id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        assert data.league_id == league_id
        assert data.name == "2023-24"
        assert data.start_date == date(2023, 10, 1)
        assert data.end_date == date(2024, 6, 30)
        assert data.is_current is True

    def test_is_current_default(self):
        """SeasonCreate should default is_current to False."""
        league_id = uuid.uuid4()
        data = SeasonCreate(
            league_id=league_id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
        assert data.is_current is False

    def test_league_id_required(self):
        """SeasonCreate should require league_id."""
        with pytest.raises(ValidationError) as exc_info:
            SeasonCreate(
                name="2023-24",
                start_date=date(2023, 10, 1),
                end_date=date(2024, 6, 30),
            )
        assert "league_id" in str(exc_info.value)

    def test_dates_required(self):
        """SeasonCreate should require start_date and end_date."""
        league_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SeasonCreate(
                league_id=league_id,
                name="2023-24",
            )
        assert "start_date" in str(exc_info.value) or "end_date" in str(exc_info.value)

    def test_name_max_length(self):
        """SeasonCreate should validate name max length."""
        league_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            SeasonCreate(
                league_id=league_id,
                name="A" * 51,
                start_date=date(2023, 10, 1),
                end_date=date(2024, 6, 30),
            )
        assert "name" in str(exc_info.value)


class TestSeasonUpdate:
    """Tests for SeasonUpdate schema validation."""

    def test_partial_update(self):
        """SeasonUpdate should allow partial data."""
        data = SeasonUpdate(is_current=False)
        assert data.is_current is False
        assert data.name is None
        assert data.start_date is None
        assert data.end_date is None

    def test_all_fields_optional(self):
        """SeasonUpdate should allow empty data."""
        data = SeasonUpdate()
        assert data.name is None
        assert data.start_date is None
        assert data.end_date is None
        assert data.is_current is None


class TestSeasonResponse:
    """Tests for SeasonResponse schema."""

    def test_from_orm_object(self, db_session: Session):
        """SeasonResponse should serialize from ORM object."""
        league = League(name="NBA", code="NBA", country="USA")
        db_session.add(league)
        db_session.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        db_session.add(season)
        db_session.commit()
        db_session.refresh(season)

        response = SeasonResponse.model_validate(season)

        assert response.id == season.id
        assert response.league_id == league.id
        assert response.name == "2023-24"
        assert response.start_date == date(2023, 10, 1)
        assert response.end_date == date(2024, 6, 30)
        assert response.is_current is True


class TestSeasonFilter:
    """Tests for SeasonFilter schema."""

    def test_all_fields_optional(self):
        """SeasonFilter should allow empty data."""
        data = SeasonFilter()
        assert data.league_id is None
        assert data.is_current is None

    def test_filter_by_league_id(self):
        """SeasonFilter should accept league_id."""
        league_id = uuid.uuid4()
        data = SeasonFilter(league_id=league_id)
        assert data.league_id == league_id

    def test_filter_by_is_current(self):
        """SeasonFilter should accept is_current."""
        data = SeasonFilter(is_current=True)
        assert data.is_current is True


class TestImports:
    """Tests for module imports."""

    def test_import_from_league_module(self):
        """Should be able to import from league schema module."""
        from src.schemas.league import (
            LeagueCreate,
            LeagueListResponse,
            LeagueResponse,
            LeagueUpdate,
            SeasonCreate,
            SeasonFilter,
            SeasonResponse,
            SeasonUpdate,
        )

        assert LeagueCreate is not None
        assert LeagueUpdate is not None
        assert LeagueResponse is not None
        assert LeagueListResponse is not None
        assert SeasonCreate is not None
        assert SeasonUpdate is not None
        assert SeasonResponse is not None
        assert SeasonFilter is not None

    def test_import_from_schemas_package(self):
        """Should be able to import from schemas package."""
        from src.schemas import (
            LeagueCreate,
            LeagueResponse,
            SeasonCreate,
            SeasonResponse,
        )

        assert LeagueCreate is not None
        assert LeagueResponse is not None
        assert SeasonCreate is not None
        assert SeasonResponse is not None
