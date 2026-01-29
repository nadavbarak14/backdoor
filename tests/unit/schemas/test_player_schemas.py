"""
Player Schema Tests

Tests for src/schemas/player.py covering:
- PlayerCreate height_cm range validation
- PlayerFilter search field
- PlayerResponse full_name included
- PlayerWithHistoryResponse nested structure
"""

import uuid
from datetime import date, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Player
from src.schemas.enums import Position
from src.schemas.player import (
    PlayerCreate,
    PlayerFilter,
    PlayerListResponse,
    PlayerResponse,
    PlayerTeamHistoryResponse,
    PlayerUpdate,
    PlayerWithHistoryResponse,
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


class TestPlayerCreate:
    """Tests for PlayerCreate schema validation."""

    def test_valid_player_create(self):
        """PlayerCreate should accept valid data."""
        data = PlayerCreate(
            first_name="LeBron",
            last_name="James",
            birth_date=date(1984, 12, 30),
            nationality="United States",
            height_cm=206,
            position="SF",
            external_ids={"nba": "2544"},
        )
        assert data.first_name == "LeBron"
        assert data.last_name == "James"
        assert data.birth_date == date(1984, 12, 30)
        assert data.nationality == "United States"
        assert data.height_cm == 206
        assert data.position == "SF"
        assert data.external_ids == {"nba": "2544"}

    def test_first_name_required(self):
        """PlayerCreate should require first_name."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerCreate(last_name="James")
        assert "first_name" in str(exc_info.value)

    def test_last_name_required(self):
        """PlayerCreate should require last_name."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerCreate(first_name="LeBron")
        assert "last_name" in str(exc_info.value)

    def test_optional_fields(self):
        """PlayerCreate should allow optional fields to be None."""
        data = PlayerCreate(
            first_name="LeBron",
            last_name="James",
        )
        assert data.birth_date is None
        assert data.nationality is None
        assert data.height_cm is None
        assert data.position is None
        assert data.external_ids is None

    def test_height_cm_min_value(self):
        """PlayerCreate should validate height_cm minimum (100)."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                height_cm=99,
            )
        assert "height_cm" in str(exc_info.value)

    def test_height_cm_max_value(self):
        """PlayerCreate should validate height_cm maximum (250)."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                height_cm=251,
            )
        assert "height_cm" in str(exc_info.value)

    def test_height_cm_valid_range(self):
        """PlayerCreate should accept height_cm in valid range (100-250)."""
        # Minimum valid height
        data_min = PlayerCreate(
            first_name="Short",
            last_name="Player",
            height_cm=100,
        )
        assert data_min.height_cm == 100

        # Maximum valid height
        data_max = PlayerCreate(
            first_name="Tall",
            last_name="Player",
            height_cm=250,
        )
        assert data_max.height_cm == 250

    def test_first_name_max_length(self):
        """PlayerCreate should validate first_name max length."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerCreate(
                first_name="A" * 101,
                last_name="James",
            )
        assert "first_name" in str(exc_info.value)

    def test_first_name_min_length(self):
        """PlayerCreate should validate first_name min length."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerCreate(
                first_name="",
                last_name="James",
            )
        assert "first_name" in str(exc_info.value)


class TestPlayerUpdate:
    """Tests for PlayerUpdate schema validation."""

    def test_partial_update(self):
        """PlayerUpdate should allow partial data."""
        data = PlayerUpdate(position="PF")
        assert data.position == "PF"
        assert data.first_name is None
        assert data.last_name is None
        assert data.height_cm is None

    def test_all_fields_optional(self):
        """PlayerUpdate should allow empty data."""
        data = PlayerUpdate()
        assert data.first_name is None
        assert data.last_name is None
        assert data.birth_date is None
        assert data.nationality is None
        assert data.height_cm is None
        assert data.position is None
        assert data.external_ids is None

    def test_height_cm_validation(self):
        """PlayerUpdate should validate height_cm range."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerUpdate(height_cm=50)
        assert "height_cm" in str(exc_info.value)


class TestPlayerResponse:
    """Tests for PlayerResponse schema."""

    def test_from_orm_object(self, db_session: Session):
        """PlayerResponse should serialize from ORM object."""
        player = Player(
            first_name="LeBron",
            last_name="James",
            birth_date=date(1984, 12, 30),
            nationality="USA",
            height_cm=206,
            position="SF",
            external_ids={"nba": "2544"},
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        response = PlayerResponse.model_validate(player)

        assert response.id == player.id
        assert response.first_name == "LeBron"
        assert response.last_name == "James"
        assert response.full_name == "LeBron James"
        assert response.birth_date == date(1984, 12, 30)
        assert response.nationality == "USA"
        assert response.height_cm == 206
        assert response.position == "SF"
        assert response.external_ids == {"nba": "2544"}
        assert response.created_at is not None
        assert response.updated_at is not None

    def test_full_name_included(self, db_session: Session):
        """PlayerResponse should include full_name computed property."""
        player = Player(
            first_name="Stephen",
            last_name="Curry",
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        response = PlayerResponse.model_validate(player)

        assert response.full_name == "Stephen Curry"

    def test_external_ids_default_empty_dict(self, db_session: Session):
        """PlayerResponse should handle default empty external_ids."""
        player = Player(
            first_name="Unknown",
            last_name="Player",
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        response = PlayerResponse.model_validate(player)

        assert response.external_ids == {}


class TestPlayerListResponse:
    """Tests for PlayerListResponse schema."""

    def test_list_response_structure(self):
        """PlayerListResponse should contain items and total."""
        player_id = uuid.uuid4()
        now = datetime.now()

        item = PlayerResponse(
            id=player_id,
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            birth_date=None,
            nationality=None,
            height_cm=None,
            position=None,
            external_ids={},
            created_at=now,
            updated_at=now,
        )

        response = PlayerListResponse(items=[item], total=1)

        assert len(response.items) == 1
        assert response.total == 1
        assert response.items[0].full_name == "LeBron James"


class TestPlayerFilter:
    """Tests for PlayerFilter schema."""

    def test_all_fields_optional(self):
        """PlayerFilter should allow empty data."""
        data = PlayerFilter()
        assert data.team_id is None
        assert data.season_id is None
        assert data.position is None
        assert data.nationality is None
        assert data.search is None

    def test_filter_by_team_id(self):
        """PlayerFilter should accept team_id."""
        team_id = uuid.uuid4()
        data = PlayerFilter(team_id=team_id)
        assert data.team_id == team_id

    def test_filter_by_season_id(self):
        """PlayerFilter should accept season_id."""
        season_id = uuid.uuid4()
        data = PlayerFilter(season_id=season_id)
        assert data.season_id == season_id

    def test_filter_by_position(self):
        """PlayerFilter should accept position."""
        data = PlayerFilter(position="PG")
        assert data.position == "PG"

    def test_filter_by_nationality(self):
        """PlayerFilter should accept nationality."""
        data = PlayerFilter(nationality="USA")
        assert data.nationality == "USA"

    def test_filter_by_search(self):
        """PlayerFilter should accept search term."""
        data = PlayerFilter(search="LeBron")
        assert data.search == "LeBron"

    def test_search_min_length(self):
        """PlayerFilter should validate search min length."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerFilter(search="")
        assert "search" in str(exc_info.value)

    def test_combined_filters(self):
        """PlayerFilter should accept multiple filters."""
        team_id = uuid.uuid4()
        data = PlayerFilter(
            team_id=team_id,
            position="SF",
            search="James",
        )
        assert data.team_id == team_id
        assert data.position == "SF"
        assert data.search == "James"


class TestPlayerTeamHistoryResponse:
    """Tests for PlayerTeamHistoryResponse schema."""

    def test_history_response(self):
        """PlayerTeamHistoryResponse should contain team history data."""
        team_id = uuid.uuid4()
        season_id = uuid.uuid4()

        data = PlayerTeamHistoryResponse(
            team_id=team_id,
            team_name="Los Angeles Lakers",
            season_id=season_id,
            season_name="2023-24",
            jersey_number=23,
            position="SF",
        )

        assert data.team_id == team_id
        assert data.team_name == "Los Angeles Lakers"
        assert data.season_id == season_id
        assert data.season_name == "2023-24"
        assert data.jersey_number == 23
        assert data.position == "SF"

    def test_optional_fields(self):
        """PlayerTeamHistoryResponse should allow optional fields."""
        team_id = uuid.uuid4()
        season_id = uuid.uuid4()

        data = PlayerTeamHistoryResponse(
            team_id=team_id,
            team_name="Los Angeles Lakers",
            season_id=season_id,
            season_name="2023-24",
            jersey_number=None,
            position=None,
        )

        assert data.jersey_number is None
        assert data.position is None


class TestPlayerWithHistoryResponse:
    """Tests for PlayerWithHistoryResponse schema."""

    def test_nested_structure(self):
        """PlayerWithHistoryResponse should include player and history."""
        player_id = uuid.uuid4()
        team_id = uuid.uuid4()
        season_id = uuid.uuid4()
        now = datetime.now()

        history_entry = PlayerTeamHistoryResponse(
            team_id=team_id,
            team_name="Los Angeles Lakers",
            season_id=season_id,
            season_name="2023-24",
            jersey_number=23,
            position="SF",
        )

        response = PlayerWithHistoryResponse(
            id=player_id,
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            birth_date=date(1984, 12, 30),
            nationality="USA",
            height_cm=206,
            position="SF",
            external_ids={"nba": "2544"},
            created_at=now,
            updated_at=now,
            team_history=[history_entry],
        )

        assert response.id == player_id
        assert response.full_name == "LeBron James"
        assert len(response.team_history) == 1
        assert response.team_history[0].team_name == "Los Angeles Lakers"
        assert response.team_history[0].season_name == "2023-24"

    def test_multiple_history_entries(self):
        """PlayerWithHistoryResponse should handle multiple history entries."""
        player_id = uuid.uuid4()
        now = datetime.now()

        history1 = PlayerTeamHistoryResponse(
            team_id=uuid.uuid4(),
            team_name="Cleveland Cavaliers",
            season_id=uuid.uuid4(),
            season_name="2003-04",
            jersey_number=23,
            position="SF",
        )

        history2 = PlayerTeamHistoryResponse(
            team_id=uuid.uuid4(),
            team_name="Miami Heat",
            season_id=uuid.uuid4(),
            season_name="2010-11",
            jersey_number=6,
            position="SF",
        )

        history3 = PlayerTeamHistoryResponse(
            team_id=uuid.uuid4(),
            team_name="Los Angeles Lakers",
            season_id=uuid.uuid4(),
            season_name="2018-19",
            jersey_number=23,
            position="SF",
        )

        response = PlayerWithHistoryResponse(
            id=player_id,
            first_name="LeBron",
            last_name="James",
            full_name="LeBron James",
            birth_date=date(1984, 12, 30),
            nationality="USA",
            height_cm=206,
            position="SF",
            external_ids={},
            created_at=now,
            updated_at=now,
            team_history=[history1, history2, history3],
        )

        assert len(response.team_history) == 3
        assert response.team_history[0].team_name == "Cleveland Cavaliers"
        assert response.team_history[1].team_name == "Miami Heat"
        assert response.team_history[2].team_name == "Los Angeles Lakers"


class TestImports:
    """Tests for module imports."""

    def test_import_from_player_module(self):
        """Should be able to import from player schema module."""
        from src.schemas.player import (
            PlayerCreate,
            PlayerFilter,
            PlayerListResponse,
            PlayerResponse,
            PlayerTeamHistoryResponse,
            PlayerUpdate,
            PlayerWithHistoryResponse,
        )

        assert PlayerCreate is not None
        assert PlayerUpdate is not None
        assert PlayerResponse is not None
        assert PlayerListResponse is not None
        assert PlayerFilter is not None
        assert PlayerTeamHistoryResponse is not None
        assert PlayerWithHistoryResponse is not None

    def test_import_from_schemas_package(self):
        """Should be able to import from schemas package."""
        from src.schemas import (
            PlayerCreate,
            PlayerResponse,
            PlayerWithHistoryResponse,
        )

        assert PlayerCreate is not None
        assert PlayerResponse is not None
        assert PlayerWithHistoryResponse is not None
