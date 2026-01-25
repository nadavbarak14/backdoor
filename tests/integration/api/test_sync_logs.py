"""
Integration tests for the sync logs API endpoints.

Tests:
    - GET /api/v1/sync/logs - Get sync operation history
"""

from datetime import date

from sqlalchemy.orm import Session

from src.schemas import LeagueCreate, SeasonCreate
from src.services import LeagueService, SeasonService, SyncLogService


def create_test_setup(test_db: Session) -> dict:
    """Create common test data for sync logs tests."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)

    # Create league and season
    league = league_service.create_league(
        LeagueCreate(name="Winner League", code="WINNER", country="Israel")
    )
    season = season_service.create_season(
        SeasonCreate(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
        )
    )

    return {"league": league, "season": season}


class TestListSyncLogs:
    """Tests for GET /api/v1/sync/logs endpoint."""

    def test_list_sync_logs_empty(self, client):
        """Test listing sync logs returns empty list when no logs exist."""
        response = client.get("/api/v1/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_sync_logs_with_data(self, client, test_db: Session):
        """Test listing sync logs returns all logs."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create completed sync
        sync1 = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync1.id, 100, 95, 5, 0)

        # Create failed sync
        sync2 = sync_service.start_sync(
            source="winner", entity_type="players", season_id=setup["season"].id
        )
        sync_service.fail_sync(sync2.id, "Connection timeout")

        response = client.get("/api/v1/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_sync_logs_filter_by_source(self, client, test_db: Session):
        """Test filtering sync logs by source."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create syncs from different sources
        sync1 = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync1.id, 100, 95, 5, 0)

        sync2 = sync_service.start_sync(
            source="euroleague", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync2.id, 50, 48, 2, 0)

        response = client.get("/api/v1/sync/logs", params={"source": "winner"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["source"] == "winner"

    def test_list_sync_logs_filter_by_entity_type(self, client, test_db: Session):
        """Test filtering sync logs by entity type."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create syncs for different entity types
        sync1 = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync1.id, 100, 95, 5, 0)

        sync2 = sync_service.start_sync(
            source="winner", entity_type="players", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync2.id, 50, 48, 2, 0)

        response = client.get("/api/v1/sync/logs", params={"entity_type": "players"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "players"

    def test_list_sync_logs_filter_by_status(self, client, test_db: Session):
        """Test filtering sync logs by status."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create completed sync
        sync1 = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync1.id, 100, 95, 5, 0)

        # Create failed sync
        sync2 = sync_service.start_sync(
            source="winner", entity_type="players", season_id=setup["season"].id
        )
        sync_service.fail_sync(sync2.id, "Connection timeout")

        response = client.get("/api/v1/sync/logs", params={"status": "FAILED"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "FAILED"
        assert data["items"][0]["error_message"] == "Connection timeout"

    def test_list_sync_logs_pagination(self, client, test_db: Session):
        """Test pagination of sync logs."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create multiple syncs
        for i in range(5):
            sync = sync_service.start_sync(
                source="winner",
                entity_type=f"entity{i}",
                season_id=setup["season"].id,
            )
            sync_service.complete_sync(sync.id, i * 10, i * 10, 0, 0)

        response = client.get(
            "/api/v1/sync/logs", params={"page": 2, "page_size": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_list_sync_logs_shows_duration(self, client, test_db: Session):
        """Test sync logs include computed duration."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        sync = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync.id, 100, 95, 5, 0)

        response = client.get("/api/v1/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert "duration_seconds" in data["items"][0]
        assert data["items"][0]["duration_seconds"] is not None

    def test_list_sync_logs_running_no_duration(self, client, test_db: Session):
        """Test running sync logs have no duration."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create a sync that is still running
        sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )

        response = client.get("/api/v1/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["status"] == "STARTED"
        assert data["items"][0]["duration_seconds"] is None

    def test_list_sync_logs_includes_season_name(self, client, test_db: Session):
        """Test sync logs include season name when available."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        sync = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync.id, 100, 95, 5, 0)

        response = client.get("/api/v1/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["season_id"] == str(setup["season"].id)
        assert data["items"][0]["season_name"] == "2023-24"

    def test_list_sync_logs_multiple_filters(self, client, test_db: Session):
        """Test combining multiple filters."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create variety of syncs
        sync1 = sync_service.start_sync(
            source="winner", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync1.id, 100, 95, 5, 0)

        sync2 = sync_service.start_sync(
            source="winner", entity_type="players", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync2.id, 50, 48, 2, 0)

        sync3 = sync_service.start_sync(
            source="euroleague", entity_type="games", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync3.id, 30, 30, 0, 0)

        response = client.get(
            "/api/v1/sync/logs",
            params={"source": "winner", "entity_type": "games"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["source"] == "winner"
        assert data["items"][0]["entity_type"] == "games"
