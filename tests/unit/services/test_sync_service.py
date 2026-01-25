"""
Unit tests for SyncLogService.

Tests sync log tracking operations including starting, completing,
and querying synchronization operations.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.schemas.sync import SyncLogFilter, SyncStatus
from src.services.sync_service import SyncLogService


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


class TestSyncLogService:
    """Tests for SyncLogService."""

    def test_start_sync_basic(self, test_db: Session):
        """Test starting a basic sync operation."""
        service = SyncLogService(test_db)

        sync = service.start_sync(source="winner", entity_type="games")

        assert sync.id is not None
        assert sync.source == "winner"
        assert sync.entity_type == "games"
        assert sync.status == "STARTED"
        assert sync.records_processed == 0
        assert sync.records_created == 0
        assert sync.started_at is not None
        assert sync.completed_at is None

    def test_start_sync_with_season(self, test_db: Session, season: Season):
        """Test starting sync with season context."""
        service = SyncLogService(test_db)

        sync = service.start_sync(
            source="winner",
            entity_type="games",
            season_id=season.id,
        )

        assert sync.season_id == season.id

    def test_complete_sync(self, test_db: Session):
        """Test completing a sync operation."""
        service = SyncLogService(test_db)

        # Start sync
        sync = service.start_sync(source="winner", entity_type="games")

        # Complete sync
        completed = service.complete_sync(
            sync_id=sync.id,
            records_processed=100,
            records_created=95,
            records_updated=5,
            records_skipped=0,
        )

        assert completed is not None
        assert completed.status == "COMPLETED"
        assert completed.records_processed == 100
        assert completed.records_created == 95
        assert completed.records_updated == 5
        assert completed.records_skipped == 0
        assert completed.completed_at is not None
        assert completed.error_message is None

    def test_complete_sync_not_found(self, test_db: Session):
        """Test completing non-existent sync returns None."""
        service = SyncLogService(test_db)
        fake_id = uuid.uuid4()

        result = service.complete_sync(
            sync_id=fake_id,
            records_processed=100,
            records_created=100,
            records_updated=0,
        )

        assert result is None

    def test_partial_sync(self, test_db: Session):
        """Test marking sync as partial completion."""
        service = SyncLogService(test_db)

        sync = service.start_sync(source="winner", entity_type="stats")

        partial = service.partial_sync(
            sync_id=sync.id,
            records_processed=100,
            records_created=90,
            records_updated=5,
            records_skipped=5,
            error_message="5 records had invalid data",
        )

        assert partial is not None
        assert partial.status == "PARTIAL"
        assert partial.records_skipped == 5
        assert partial.error_message == "5 records had invalid data"
        assert partial.completed_at is not None

    def test_fail_sync(self, test_db: Session):
        """Test marking sync as failed."""
        service = SyncLogService(test_db)

        sync = service.start_sync(source="winner", entity_type="games")

        failed = service.fail_sync(
            sync_id=sync.id,
            error_message="API connection timeout",
            error_details={"endpoint": "/api/games", "timeout_seconds": 30},
        )

        assert failed is not None
        assert failed.status == "FAILED"
        assert failed.error_message == "API connection timeout"
        assert failed.error_details["endpoint"] == "/api/games"
        assert failed.completed_at is not None

    def test_fail_sync_not_found(self, test_db: Session):
        """Test failing non-existent sync returns None."""
        service = SyncLogService(test_db)
        fake_id = uuid.uuid4()

        result = service.fail_sync(
            sync_id=fake_id,
            error_message="Error",
        )

        assert result is None

    def test_get_latest_by_source(self, test_db: Session):
        """Test getting most recent sync for source/entity."""
        service = SyncLogService(test_db)

        # Create two syncs
        sync1 = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync1.id, 50, 50, 0, 0)

        sync2 = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync2.id, 100, 100, 0, 0)

        # Get latest
        latest = service.get_latest_by_source("winner", "games")

        assert latest is not None
        assert latest.id == sync2.id
        assert latest.records_processed == 100

    def test_get_latest_by_source_different_entity(self, test_db: Session):
        """Test latest sync only returns matching entity type."""
        service = SyncLogService(test_db)

        # Create sync for games
        sync_games = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync_games.id, 100, 100, 0, 0)

        # Create sync for stats
        sync_stats = service.start_sync(source="winner", entity_type="stats")
        service.complete_sync(sync_stats.id, 500, 500, 0, 0)

        # Get latest games sync
        latest = service.get_latest_by_source("winner", "games")

        assert latest is not None
        assert latest.entity_type == "games"
        assert latest.records_processed == 100

    def test_get_latest_by_source_not_found(self, test_db: Session):
        """Test getting latest when none exist."""
        service = SyncLogService(test_db)

        result = service.get_latest_by_source("nonexistent", "games")

        assert result is None

    def test_get_latest_successful(self, test_db: Session):
        """Test getting most recent successful sync."""
        service = SyncLogService(test_db)

        # Create successful sync
        sync1 = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync1.id, 100, 100, 0, 0)

        # Create failed sync (more recent)
        sync2 = service.start_sync(source="winner", entity_type="games")
        service.fail_sync(sync2.id, "Error")

        # Get latest successful
        latest = service.get_latest_successful("winner", "games")

        assert latest is not None
        assert latest.id == sync1.id
        assert latest.status == "COMPLETED"

    def test_get_latest_successful_with_season(self, test_db: Session, season: Season):
        """Test getting latest successful sync filtered by season."""
        service = SyncLogService(test_db)

        # Create successful sync for season
        sync1 = service.start_sync(
            source="winner", entity_type="games", season_id=season.id
        )
        service.complete_sync(sync1.id, 50, 50, 0, 0)

        # Create successful sync without season (more recent)
        sync2 = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync2.id, 100, 100, 0, 0)

        # Get latest for specific season
        latest = service.get_latest_successful("winner", "games", season_id=season.id)

        assert latest is not None
        assert latest.id == sync1.id
        assert latest.season_id == season.id

    def test_get_filtered_by_source(self, test_db: Session):
        """Test filtering sync logs by source."""
        service = SyncLogService(test_db)

        # Create syncs from different sources
        sync1 = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync1.id, 100, 100, 0, 0)

        sync2 = service.start_sync(source="euroleague", entity_type="games")
        service.complete_sync(sync2.id, 50, 50, 0, 0)

        # Filter by source
        filter_params = SyncLogFilter(source="winner")
        logs, total = service.get_filtered(filter_params)

        assert total == 1
        assert len(logs) == 1
        assert logs[0].source == "winner"

    def test_get_filtered_by_status(self, test_db: Session):
        """Test filtering sync logs by status."""
        service = SyncLogService(test_db)

        sync1 = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync1.id, 100, 100, 0, 0)

        sync2 = service.start_sync(source="winner", entity_type="stats")
        service.fail_sync(sync2.id, "Error")

        # Filter by failed status
        filter_params = SyncLogFilter(status=SyncStatus.FAILED)
        logs, total = service.get_filtered(filter_params)

        assert total == 1
        assert logs[0].status == "FAILED"

    def test_get_filtered_by_date_range(self, test_db: Session):
        """Test filtering sync logs by date range."""
        service = SyncLogService(test_db)

        # Create a sync
        sync = service.start_sync(source="winner", entity_type="games")
        service.complete_sync(sync.id, 100, 100, 0, 0)

        # Filter with date range that includes the sync
        now = datetime.now(UTC)
        filter_params = SyncLogFilter(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1),
        )
        logs, total = service.get_filtered(filter_params)

        assert total == 1

        # Filter with date range that excludes the sync
        filter_params_future = SyncLogFilter(
            start_date=now + timedelta(days=1),
        )
        logs_future, total_future = service.get_filtered(filter_params_future)

        assert total_future == 0

    def test_get_filtered_pagination(self, test_db: Session):
        """Test pagination in filtered results."""
        service = SyncLogService(test_db)

        # Create 5 syncs
        for i in range(5):
            sync = service.start_sync(source="winner", entity_type="games")
            service.complete_sync(sync.id, i * 10, i * 10, 0, 0)

        # Get first page (2 items)
        filter_params = SyncLogFilter(page=1, page_size=2)
        logs, total = service.get_filtered(filter_params)

        assert total == 5
        assert len(logs) == 2

        # Get second page
        filter_params2 = SyncLogFilter(page=2, page_size=2)
        logs2, total2 = service.get_filtered(filter_params2)

        assert total2 == 5
        assert len(logs2) == 2

    def test_get_running_syncs(self, test_db: Session):
        """Test getting currently running syncs."""
        service = SyncLogService(test_db)

        # Create running sync
        running = service.start_sync(source="winner", entity_type="games")

        # Create completed sync
        completed = service.start_sync(source="winner", entity_type="stats")
        service.complete_sync(completed.id, 100, 100, 0, 0)

        # Get running syncs
        result = service.get_running_syncs()

        assert len(result) == 1
        assert result[0].id == running.id
        assert result[0].status == "STARTED"

    def test_get_running_syncs_filtered_by_source(self, test_db: Session):
        """Test getting running syncs filtered by source."""
        service = SyncLogService(test_db)

        # Create running syncs from different sources
        service.start_sync(source="winner", entity_type="games")
        service.start_sync(source="euroleague", entity_type="games")

        # Get running syncs for winner only
        result = service.get_running_syncs(source="winner")

        assert len(result) == 1
        assert result[0].source == "winner"

    def test_get_running_syncs_none(self, test_db: Session):
        """Test getting running syncs when none exist."""
        service = SyncLogService(test_db)

        result = service.get_running_syncs()

        assert result == []

    def test_base_service_methods(self, test_db: Session):
        """Test inherited BaseService methods work correctly."""
        service = SyncLogService(test_db)

        # Create via start_sync
        sync = service.start_sync(source="winner", entity_type="games")

        # Test get_by_id
        fetched = service.get_by_id(sync.id)
        assert fetched is not None
        assert fetched.source == "winner"

        # Test get_all
        all_logs = service.get_all()
        assert len(all_logs) == 1

        # Test count
        count = service.count()
        assert count == 1

        # Test delete
        deleted = service.delete(sync.id)
        assert deleted is True
        assert service.count() == 0
