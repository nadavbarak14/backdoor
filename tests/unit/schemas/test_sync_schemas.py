"""
Sync Schema Tests

Tests for src/schemas/sync.py covering:
- SyncStatus enum values
- SyncLogResponse with computed duration_seconds
- SyncLogResponse error_details JSON handling
- SyncLogListResponse structure
- SyncLogFilter defaults and validation
"""

import uuid
from datetime import UTC, datetime

import pytest

from src.schemas.sync import (
    SyncLogFilter,
    SyncLogListResponse,
    SyncLogResponse,
    SyncStatus,
)


class TestSyncStatusEnum:
    """Tests for SyncStatus enum."""

    def test_sync_status_values(self):
        """SyncStatus should have expected values."""
        assert SyncStatus.STARTED.value == "STARTED"
        assert SyncStatus.COMPLETED.value == "COMPLETED"
        assert SyncStatus.FAILED.value == "FAILED"
        assert SyncStatus.PARTIAL.value == "PARTIAL"

    def test_all_status_types(self):
        """SyncStatus should have exactly 4 status types."""
        statuses = list(SyncStatus)
        assert len(statuses) == 4


class TestSyncLogResponse:
    """Tests for SyncLogResponse schema."""

    @pytest.fixture
    def completed_sync_log(self):
        """Create a completed sync log."""
        started = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 15, 10, 5, 30, tzinfo=UTC)
        return SyncLogResponse(
            id=uuid.uuid4(),
            source="winner",
            entity_type="games",
            status=SyncStatus.COMPLETED,
            season_id=uuid.uuid4(),
            season_name="2023-24",
            records_processed=100,
            records_created=95,
            records_updated=5,
            records_skipped=0,
            started_at=started,
            completed_at=completed,
        )

    @pytest.fixture
    def running_sync_log(self):
        """Create a running (incomplete) sync log."""
        return SyncLogResponse(
            id=uuid.uuid4(),
            source="euroleague",
            entity_type="players",
            status=SyncStatus.STARTED,
            records_processed=50,
            records_created=50,
            records_updated=0,
            records_skipped=0,
            started_at=datetime.now(UTC),
            completed_at=None,
        )

    @pytest.fixture
    def failed_sync_log(self):
        """Create a failed sync log with error details."""
        started = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 15, 10, 2, 15, tzinfo=UTC)
        return SyncLogResponse(
            id=uuid.uuid4(),
            source="winner",
            entity_type="stats",
            status=SyncStatus.FAILED,
            records_processed=25,
            records_created=20,
            records_updated=5,
            records_skipped=0,
            error_message="Connection timeout after 30 seconds",
            error_details={
                "exception_type": "TimeoutError",
                "retry_count": 3,
                "last_successful_record": 24,
            },
            started_at=started,
            completed_at=completed,
        )

    def test_duration_seconds_computed(self, completed_sync_log):
        """SyncLogResponse should compute duration_seconds correctly."""
        # 5 minutes 30 seconds = 330 seconds
        assert completed_sync_log.duration_seconds == 330.0

    def test_duration_seconds_none_when_running(self, running_sync_log):
        """SyncLogResponse should return None duration when still running."""
        assert running_sync_log.duration_seconds is None

    def test_all_fields_present(self, completed_sync_log):
        """SyncLogResponse should have all expected fields."""
        assert completed_sync_log.source == "winner"
        assert completed_sync_log.entity_type == "games"
        assert completed_sync_log.status == SyncStatus.COMPLETED
        assert completed_sync_log.season_name == "2023-24"
        assert completed_sync_log.records_processed == 100
        assert completed_sync_log.records_created == 95

    def test_error_details_json(self, failed_sync_log):
        """SyncLogResponse should store and retrieve error_details JSON."""
        assert failed_sync_log.error_message == "Connection timeout after 30 seconds"
        assert failed_sync_log.error_details["exception_type"] == "TimeoutError"
        assert failed_sync_log.error_details["retry_count"] == 3
        assert failed_sync_log.error_details["last_successful_record"] == 24

    def test_optional_fields_can_be_none(self, running_sync_log):
        """SyncLogResponse should accept None for optional fields."""
        assert running_sync_log.season_id is None
        assert running_sync_log.season_name is None
        assert running_sync_log.game_id is None
        assert running_sync_log.error_message is None
        assert running_sync_log.error_details is None
        assert running_sync_log.completed_at is None

    def test_serialization_includes_computed_field(self, completed_sync_log):
        """Serialized output should include computed duration_seconds."""
        data = completed_sync_log.model_dump()
        assert "duration_seconds" in data
        assert data["duration_seconds"] == 330.0

    def test_partial_status(self):
        """SyncLogResponse should support PARTIAL status."""
        started = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2024, 1, 15, 10, 10, 0, tzinfo=UTC)
        log = SyncLogResponse(
            id=uuid.uuid4(),
            source="winner",
            entity_type="pbp",
            status=SyncStatus.PARTIAL,
            records_processed=100,
            records_created=80,
            records_updated=0,
            records_skipped=20,
            error_message="Some records had invalid data",
            error_details={
                "skipped_records": [1, 5, 12, 34],
                "reason": "missing_player_id",
            },
            started_at=started,
            completed_at=completed,
        )

        assert log.status == SyncStatus.PARTIAL
        assert log.records_skipped == 20
        assert log.duration_seconds == 600.0


class TestSyncLogListResponse:
    """Tests for SyncLogListResponse schema."""

    def test_list_response_structure(self):
        """SyncLogListResponse should contain items and total."""
        log1 = SyncLogResponse(
            id=uuid.uuid4(),
            source="winner",
            entity_type="games",
            status=SyncStatus.COMPLETED,
            records_processed=100,
            records_created=100,
            records_updated=0,
            records_skipped=0,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        log2 = SyncLogResponse(
            id=uuid.uuid4(),
            source="euroleague",
            entity_type="players",
            status=SyncStatus.COMPLETED,
            records_processed=50,
            records_created=50,
            records_updated=0,
            records_skipped=0,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        response = SyncLogListResponse(items=[log1, log2], total=150)

        assert len(response.items) == 2
        assert response.total == 150

    def test_empty_list_response(self):
        """SyncLogListResponse should allow empty items list."""
        response = SyncLogListResponse(items=[], total=0)

        assert len(response.items) == 0
        assert response.total == 0


class TestSyncLogFilter:
    """Tests for SyncLogFilter schema."""

    def test_filter_defaults(self):
        """SyncLogFilter should have correct defaults."""
        filter = SyncLogFilter()

        assert filter.source is None
        assert filter.entity_type is None
        assert filter.status is None
        assert filter.season_id is None
        assert filter.start_date is None
        assert filter.end_date is None
        assert filter.page == 1
        assert filter.page_size == 20

    def test_filter_custom_values(self):
        """SyncLogFilter should accept custom values."""
        filter = SyncLogFilter(
            source="winner",
            entity_type="games",
            status=SyncStatus.FAILED,
            season_id=uuid.uuid4(),
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 31, tzinfo=UTC),
            page=2,
            page_size=50,
        )

        assert filter.source == "winner"
        assert filter.entity_type == "games"
        assert filter.status == SyncStatus.FAILED
        assert filter.page == 2
        assert filter.page_size == 50

    def test_filter_page_validation(self):
        """SyncLogFilter page must be at least 1."""
        SyncLogFilter(page=1)

        with pytest.raises(ValueError):
            SyncLogFilter(page=0)

    def test_filter_page_size_validation(self):
        """SyncLogFilter page_size should be between 1 and 100."""
        SyncLogFilter(page_size=1)
        SyncLogFilter(page_size=100)

        with pytest.raises(ValueError):
            SyncLogFilter(page_size=0)
        with pytest.raises(ValueError):
            SyncLogFilter(page_size=101)

    def test_filter_status_enum(self):
        """SyncLogFilter should accept SyncStatus enum values."""
        for status in SyncStatus:
            filter = SyncLogFilter(status=status)
            assert filter.status == status
