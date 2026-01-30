"""
Team Schema Tests

Tests for src/schemas/team.py covering:
- TeamCreate with external_ids dict
- TeamFilter optional fields
- TeamResponse from ORM object
"""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Team
from src.schemas.enums import Position
from src.schemas.team import (
    TeamCreate,
    TeamFilter,
    TeamListResponse,
    TeamResponse,
    TeamRosterPlayerResponse,
    TeamRosterResponse,
    TeamUpdate,
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


class TestTeamCreate:
    """Tests for TeamCreate schema validation."""

    def test_valid_team_create(self):
        """TeamCreate should accept valid data."""
        data = TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="United States",
            external_ids={"nba": "1610612747"},
        )
        assert data.name == "Los Angeles Lakers"
        assert data.short_name == "LAL"
        assert data.city == "Los Angeles"
        assert data.country == "United States"
        assert data.external_ids == {"nba": "1610612747"}

    def test_external_ids_optional(self):
        """TeamCreate should allow external_ids to be None."""
        data = TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="United States",
        )
        assert data.external_ids is None

    def test_external_ids_multiple_providers(self):
        """TeamCreate should accept multiple external IDs."""
        data = TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="United States",
            external_ids={"nba": "1610612747", "espn": "12345", "yahoo": "LAL"},
        )
        assert data.external_ids["nba"] == "1610612747"
        assert data.external_ids["espn"] == "12345"
        assert data.external_ids["yahoo"] == "LAL"

    def test_name_required(self):
        """TeamCreate should require name field."""
        with pytest.raises(ValidationError) as exc_info:
            TeamCreate(
                short_name="LAL",
                city="Los Angeles",
                country="United States",
            )
        assert "name" in str(exc_info.value)

    def test_short_name_required(self):
        """TeamCreate should require short_name field."""
        with pytest.raises(ValidationError) as exc_info:
            TeamCreate(
                name="Los Angeles Lakers",
                city="Los Angeles",
                country="United States",
            )
        assert "short_name" in str(exc_info.value)

    def test_name_max_length(self):
        """TeamCreate should validate name max length."""
        with pytest.raises(ValidationError) as exc_info:
            TeamCreate(
                name="A" * 101,
                short_name="LAL",
                city="Los Angeles",
                country="United States",
            )
        assert "name" in str(exc_info.value)

    def test_short_name_max_length(self):
        """TeamCreate should validate short_name max length."""
        with pytest.raises(ValidationError) as exc_info:
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="A" * 21,
                city="Los Angeles",
                country="United States",
            )
        assert "short_name" in str(exc_info.value)


class TestTeamUpdate:
    """Tests for TeamUpdate schema validation."""

    def test_partial_update(self):
        """TeamUpdate should allow partial data."""
        data = TeamUpdate(city="San Francisco")
        assert data.city == "San Francisco"
        assert data.name is None
        assert data.short_name is None
        assert data.country is None
        assert data.external_ids is None

    def test_all_fields_optional(self):
        """TeamUpdate should allow empty data."""
        data = TeamUpdate()
        assert data.name is None
        assert data.short_name is None
        assert data.city is None
        assert data.country is None
        assert data.external_ids is None

    def test_update_external_ids(self):
        """TeamUpdate should accept external_ids update."""
        data = TeamUpdate(external_ids={"nba": "new_id"})
        assert data.external_ids == {"nba": "new_id"}


class TestTeamResponse:
    """Tests for TeamResponse schema."""

    def test_from_orm_object(self, db_session: Session):
        """TeamResponse should serialize from ORM object."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={"nba": "1610612747"},
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        response = TeamResponse.model_validate(team)

        assert response.id == team.id
        assert response.name == "Los Angeles Lakers"
        assert response.short_name == "LAL"
        assert response.city == "Los Angeles"
        assert response.country == "USA"
        assert response.external_ids == {"nba": "1610612747"}
        assert response.created_at is not None
        assert response.updated_at is not None

    def test_external_ids_default_empty_dict(self, db_session: Session):
        """TeamResponse should handle default empty external_ids."""
        team = Team(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        response = TeamResponse.model_validate(team)

        assert response.external_ids == {}


class TestTeamListResponse:
    """Tests for TeamListResponse schema."""

    def test_list_response_structure(self):
        """TeamListResponse should contain items and total."""
        team_id = uuid.uuid4()
        now = datetime.now()

        item = TeamResponse(
            id=team_id,
            name="Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={},
            created_at=now,
            updated_at=now,
        )

        response = TeamListResponse(items=[item], total=1)

        assert len(response.items) == 1
        assert response.total == 1
        assert response.items[0].short_name == "LAL"


class TestTeamFilter:
    """Tests for TeamFilter schema."""

    def test_all_fields_optional(self):
        """TeamFilter should allow empty data."""
        data = TeamFilter()
        assert data.league_id is None
        assert data.season_id is None
        assert data.country is None
        assert data.search is None

    def test_filter_by_league_id(self):
        """TeamFilter should accept league_id."""
        league_id = uuid.uuid4()
        data = TeamFilter(league_id=league_id)
        assert data.league_id == league_id

    def test_filter_by_season_id(self):
        """TeamFilter should accept season_id."""
        season_id = uuid.uuid4()
        data = TeamFilter(season_id=season_id)
        assert data.season_id == season_id

    def test_filter_by_country(self):
        """TeamFilter should accept country."""
        data = TeamFilter(country="United States")
        assert data.country == "United States"

    def test_filter_by_search(self):
        """TeamFilter should accept search term."""
        data = TeamFilter(search="Lakers")
        assert data.search == "Lakers"

    def test_search_min_length(self):
        """TeamFilter should validate search min length."""
        with pytest.raises(ValidationError) as exc_info:
            TeamFilter(search="")
        assert "search" in str(exc_info.value)


class TestTeamRosterPlayerResponse:
    """Tests for TeamRosterPlayerResponse schema."""

    def test_roster_player_response(self):
        """TeamRosterPlayerResponse should contain player info."""
        player_id = uuid.uuid4()
        data = TeamRosterPlayerResponse(
            id=player_id,
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            jersey_number=23,
            positions=["SF"],
        )
        assert data.id == player_id
        assert data.first_name == "LeBron"
        assert data.last_name == "James"
        assert data.full_name == "LeBron James"
        assert data.jersey_number == 23
        assert data.positions == ["SF"]

    def test_optional_fields(self):
        """TeamRosterPlayerResponse should allow optional fields."""
        player_id = uuid.uuid4()
        data = TeamRosterPlayerResponse(
            id=player_id,
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            jersey_number=None,
            positions=[],
        )
        assert data.jersey_number is None
        assert data.positions == []


class TestTeamRosterResponse:
    """Tests for TeamRosterResponse schema."""

    def test_roster_response_structure(self):
        """TeamRosterResponse should contain team, season, and players."""
        team_id = uuid.uuid4()
        season_id = uuid.uuid4()
        player_id = uuid.uuid4()
        now = datetime.now()

        team = TeamResponse(
            id=team_id,
            name="Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={},
            created_at=now,
            updated_at=now,
        )

        player = TeamRosterPlayerResponse(
            id=player_id,
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            jersey_number=23,
            position="SF",
        )

        response = TeamRosterResponse(
            team=team,
            season_id=season_id,
            season_name="2023-24",
            players=[player],
        )

        assert response.team.id == team_id
        assert response.season_id == season_id
        assert response.season_name == "2023-24"
        assert len(response.players) == 1
        assert response.players[0].first_name == "LeBron"


class TestImports:
    """Tests for module imports."""

    def test_import_from_team_module(self):
        """Should be able to import from team schema module."""
        from src.schemas.team import (
            TeamCreate,
            TeamFilter,
            TeamListResponse,
            TeamResponse,
            TeamRosterPlayerResponse,
            TeamRosterResponse,
            TeamUpdate,
        )

        assert TeamCreate is not None
        assert TeamUpdate is not None
        assert TeamResponse is not None
        assert TeamListResponse is not None
        assert TeamFilter is not None
        assert TeamRosterPlayerResponse is not None
        assert TeamRosterResponse is not None

    def test_import_from_schemas_package(self):
        """Should be able to import from schemas package."""
        from src.schemas import (
            TeamCreate,
            TeamResponse,
            TeamRosterResponse,
        )

        assert TeamCreate is not None
        assert TeamResponse is not None
        assert TeamRosterResponse is not None
