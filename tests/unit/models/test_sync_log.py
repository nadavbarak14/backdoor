"""
SyncLog Model Tests

Tests for SyncLog from src/models/sync.py covering:
- SyncLog creation with all fields
- All status types (STARTED, COMPLETED, FAILED, PARTIAL)
- error_details JSON field
- Relationship to Season and Game
- Index on (source, entity_type, started_at)
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import (
    Base,
    Game,
    League,
    Season,
    SyncLog,
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
    league = League(name="EuroLeague", code="EURO", country="Europe")
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def sample_season(db_session: Session, sample_league: League) -> Season:
    """Create a sample season for testing."""
    season = Season(
        league_id=sample_league.id,
        name="2023-24",
        start_date=date(2023, 10, 5),
        end_date=date(2024, 5, 26),
        is_current=True,
    )
    db_session.add(season)
    db_session.commit()
    return season


@pytest.fixture
def sample_team(db_session: Session) -> Team:
    """Create a sample team for testing."""
    team = Team(
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_away_team(db_session: Session) -> Team:
    """Create a sample away team for testing."""
    team = Team(
        name="Real Madrid",
        short_name="RMA",
        city="Madrid",
        country="Spain",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_game(
    db_session: Session,
    sample_season: Season,
    sample_team: Team,
    sample_away_team: Team,
) -> Game:
    """Create a sample game for testing."""
    game = Game(
        season_id=sample_season.id,
        home_team_id=sample_team.id,
        away_team_id=sample_away_team.id,
        game_date=datetime(2024, 1, 15, 20, 0, tzinfo=UTC),
        status="FINAL",
    )
    db_session.add(game)
    db_session.commit()
    return game


class TestSyncLogModel:
    """Tests for the SyncLog model."""

    def test_sync_log_creation_with_all_fields(
        self,
        db_session: Session,
        sample_season: Season,
        sample_game: Game,
    ):
        """SyncLog should be created with all fields."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="COMPLETED",
            season_id=sample_season.id,
            game_id=sample_game.id,
            records_processed=100,
            records_created=95,
            records_updated=5,
            records_skipped=0,
            error_message=None,
            error_details=None,
            completed_at=datetime.now(UTC),
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.id is not None
        assert isinstance(sync_log.id, uuid.UUID)
        assert sync_log.source == "winner"
        assert sync_log.entity_type == "games"
        assert sync_log.status == "COMPLETED"
        assert sync_log.season_id == sample_season.id
        assert sync_log.game_id == sample_game.id
        assert sync_log.records_processed == 100
        assert sync_log.records_created == 95
        assert sync_log.records_updated == 5
        assert sync_log.records_skipped == 0
        assert sync_log.started_at is not None
        assert sync_log.completed_at is not None

    def test_sync_log_defaults(self, db_session: Session):
        """SyncLog should have correct default values."""
        sync_log = SyncLog(
            source="euroleague",
            entity_type="players",
            status="STARTED",
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.records_processed == 0
        assert sync_log.records_created == 0
        assert sync_log.records_updated == 0
        assert sync_log.records_skipped == 0
        assert sync_log.error_message is None
        assert sync_log.error_details is None
        assert sync_log.season_id is None
        assert sync_log.game_id is None
        assert sync_log.completed_at is None
        assert sync_log.started_at is not None

    def test_sync_log_repr(self, db_session: Session):
        """SyncLog __repr__ should return meaningful string."""
        sync_log = SyncLog(
            source="winner",
            entity_type="stats",
            status="STARTED",
        )
        db_session.add(sync_log)
        db_session.commit()

        assert "SyncLog" in repr(sync_log)
        assert "source='winner'" in repr(sync_log)
        assert "entity_type='stats'" in repr(sync_log)
        assert "status='STARTED'" in repr(sync_log)


class TestSyncLogStatusTypes:
    """Tests for all SyncLog status types."""

    def test_status_started(self, db_session: Session):
        """SyncLog should support STARTED status."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="STARTED",
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.status == "STARTED"

    def test_status_completed(self, db_session: Session):
        """SyncLog should support COMPLETED status."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="COMPLETED",
            records_processed=50,
            records_created=50,
            completed_at=datetime.now(UTC),
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.status == "COMPLETED"
        assert sync_log.completed_at is not None

    def test_status_failed(self, db_session: Session):
        """SyncLog should support FAILED status with error details."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="FAILED",
            records_processed=25,
            error_message="Connection timeout after 30 seconds",
            error_details={
                "exception_type": "TimeoutError",
                "retry_count": 3,
                "last_successful_record": 24,
            },
            completed_at=datetime.now(UTC),
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.status == "FAILED"
        assert sync_log.error_message == "Connection timeout after 30 seconds"
        assert sync_log.error_details["exception_type"] == "TimeoutError"
        assert sync_log.error_details["retry_count"] == 3

    def test_status_partial(self, db_session: Session):
        """SyncLog should support PARTIAL status."""
        sync_log = SyncLog(
            source="euroleague",
            entity_type="pbp",
            status="PARTIAL",
            records_processed=100,
            records_created=80,
            records_skipped=20,
            error_message="Some records had invalid data",
            error_details={
                "skipped_records": [1, 5, 12, 34],
                "reason": "missing_player_id",
            },
            completed_at=datetime.now(UTC),
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.status == "PARTIAL"
        assert sync_log.records_skipped == 20


class TestSyncLogErrorDetailsJson:
    """Tests for SyncLog error_details JSON field."""

    def test_error_details_stores_complex_json(self, db_session: Session):
        """error_details should store and retrieve complex JSON correctly."""
        error_details = {
            "exception_type": "ValidationError",
            "traceback": [
                "File 'sync.py', line 42",
                "File 'parser.py', line 18",
            ],
            "failed_records": [
                {"id": 1, "reason": "invalid_date"},
                {"id": 5, "reason": "duplicate_key"},
            ],
            "context": {
                "batch_number": 3,
                "total_batches": 10,
            },
        }
        sync_log = SyncLog(
            source="winner",
            entity_type="stats",
            status="FAILED",
            error_message="Validation failed",
            error_details=error_details,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.error_details["exception_type"] == "ValidationError"
        assert len(sync_log.error_details["traceback"]) == 2
        assert len(sync_log.error_details["failed_records"]) == 2
        assert sync_log.error_details["context"]["batch_number"] == 3

    def test_error_details_null(self, db_session: Session):
        """error_details should allow null values."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="COMPLETED",
            error_details=None,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.error_details is None


class TestSyncLogRelationships:
    """Tests for SyncLog relationships."""

    def test_sync_log_season_relationship(
        self, db_session: Session, sample_season: Season
    ):
        """SyncLog should have access to its season."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="STARTED",
            season_id=sample_season.id,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.season == sample_season

    def test_sync_log_game_relationship(
        self, db_session: Session, sample_game: Game
    ):
        """SyncLog should have access to its game."""
        sync_log = SyncLog(
            source="winner",
            entity_type="pbp",
            status="STARTED",
            game_id=sample_game.id,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)

        assert sync_log.game == sample_game

    def test_season_sync_logs_relationship(
        self, db_session: Session, sample_season: Season
    ):
        """Season should have access to its sync_logs."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="COMPLETED",
            season_id=sample_season.id,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sample_season)

        assert len(sample_season.sync_logs) == 1
        assert sync_log in sample_season.sync_logs

    def test_game_sync_logs_relationship(
        self, db_session: Session, sample_game: Game
    ):
        """Game should have access to its sync_logs."""
        sync_log = SyncLog(
            source="winner",
            entity_type="pbp",
            status="COMPLETED",
            game_id=sample_game.id,
        )
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sample_game)

        assert len(sample_game.sync_logs) == 1
        assert sync_log in sample_game.sync_logs


class TestSyncLogCascadeDelete:
    """Tests for SyncLog foreign key behavior on delete."""

    def test_season_delete_sets_null(
        self, db_session: Session, sample_season: Season
    ):
        """Deleting a season should set sync_log.season_id to NULL."""
        sync_log = SyncLog(
            source="winner",
            entity_type="games",
            status="COMPLETED",
            season_id=sample_season.id,
        )
        db_session.add(sync_log)
        db_session.commit()

        sync_log_id = sync_log.id

        # Delete the season
        db_session.delete(sample_season)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # SyncLog should still exist but with NULL season_id
        remaining_log = db_session.get(SyncLog, sync_log_id)
        assert remaining_log is not None
        assert remaining_log.season_id is None

    def test_game_delete_sets_null(
        self, db_session: Session, sample_game: Game
    ):
        """Deleting a game should set sync_log.game_id to NULL."""
        sync_log = SyncLog(
            source="winner",
            entity_type="pbp",
            status="COMPLETED",
            game_id=sample_game.id,
        )
        db_session.add(sync_log)
        db_session.commit()

        sync_log_id = sync_log.id

        # Delete the game
        db_session.delete(sample_game)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # SyncLog should still exist but with NULL game_id
        remaining_log = db_session.get(SyncLog, sync_log_id)
        assert remaining_log is not None
        assert remaining_log.game_id is None


class TestSyncLogIndex:
    """Tests for SyncLog indexes."""

    def test_source_entity_started_index_exists(self, db_session: Session):
        """Index on (source, entity_type, started_at) should exist."""
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("sync_logs")

        index_names = [idx["name"] for idx in indexes]
        assert "ix_sync_logs_source_entity_started" in index_names

        # Verify the index columns
        for idx in indexes:
            if idx["name"] == "ix_sync_logs_source_entity_started":
                assert "source" in idx["column_names"]
                assert "entity_type" in idx["column_names"]
                assert "started_at" in idx["column_names"]
