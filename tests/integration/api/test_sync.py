"""
Integration tests for the sync API endpoints.

Tests:
    - GET /api/v1/sync/status - Get sync status
    - POST /api/v1/sync/{source}/season/{season_id} - Sync season
    - POST /api/v1/sync/{source}/game/{game_id} - Sync game
    - POST /api/v1/sync/{source}/teams/{season_id} - Sync teams
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.team import Team
from src.schemas import LeagueCreate, SeasonCreate
from src.services import LeagueService, SeasonService, SyncLogService
from src.sync.types import RawBoxScore, RawGame, RawPlayerStats, RawSeason, RawTeam


def create_test_setup(test_db: Session) -> dict:
    """Create common test data for sync tests."""
    league_service = LeagueService(test_db)
    season_service = SeasonService(test_db)

    # Create league and season
    league = league_service.create_league(
        LeagueCreate(name="Winner League", code="WINNER", country="Israel")
    )
    season = season_service.create_season(
        SeasonCreate(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 6, 30),
        )
    )

    # Create teams
    home_team = Team(
        id=uuid4(),
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "mta-123"},
    )
    away_team = Team(
        id=uuid4(),
        name="Hapoel Jerusalem",
        short_name="HJR",
        city="Jerusalem",
        country="Israel",
        external_ids={"winner": "hjr-456"},
    )
    test_db.add(home_team)
    test_db.add(away_team)
    test_db.commit()

    return {
        "league": league,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
    }


class TestGetSyncStatus:
    """Tests for GET /api/v1/sync/status endpoint."""

    def test_get_sync_status(self, client):
        """Test getting sync status returns source info."""
        response = client.get("/api/v1/sync/status")

        assert response.status_code == 200
        data = response.json()

        assert "sources" in data
        assert "total_running_syncs" in data
        assert isinstance(data["sources"], list)

    def test_get_sync_status_shows_enabled_sources(self, client):
        """Test sync status shows enabled flag for sources."""
        response = client.get("/api/v1/sync/status")

        assert response.status_code == 200
        data = response.json()

        # Should have at least winner source
        winner_sources = [s for s in data["sources"] if s["name"] == "winner"]
        assert len(winner_sources) == 1
        assert "enabled" in winner_sources[0]

    def test_get_sync_status_shows_running_count(self, client, test_db: Session):
        """Test sync status includes running syncs count."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create a running sync
        sync_service.start_sync(
            source="winner", entity_type="season", season_id=setup["season"].id
        )

        response = client.get("/api/v1/sync/status")

        assert response.status_code == 200
        data = response.json()

        assert data["total_running_syncs"] >= 1


class TestSyncSeason:
    """Tests for POST /api/v1/sync/{source}/season/{season_id} endpoint."""

    def test_sync_season_returns_sync_log(self, client, test_db: Session):
        """Test syncing season returns a sync log response."""
        setup = create_test_setup(test_db)

        # Mock the adapter to return empty schedule
        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.sync_season = AsyncMock(
                return_value=MagicMock(
                    id=uuid4(),
                    source="winner",
                    entity_type="season",
                    status="COMPLETED",
                    season_id=setup["season"].id,
                    season=setup["season"],
                    game_id=None,
                    records_processed=0,
                    records_created=0,
                    records_updated=0,
                    records_skipped=0,
                    error_message=None,
                    error_details=None,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/winner/season/2024-25")

            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "winner"
            assert data["entity_type"] == "season"
            assert data["status"] == "COMPLETED"

    def test_sync_season_with_include_pbp_param(self, client, test_db: Session):
        """Test syncing season respects include_pbp parameter."""
        setup = create_test_setup(test_db)

        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.sync_season = AsyncMock(
                return_value=MagicMock(
                    id=uuid4(),
                    source="winner",
                    entity_type="season",
                    status="COMPLETED",
                    season_id=setup["season"].id,
                    season=setup["season"],
                    game_id=None,
                    records_processed=0,
                    records_created=0,
                    records_updated=0,
                    records_skipped=0,
                    error_message=None,
                    error_details=None,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            mock_get_manager.return_value = mock_manager

            response = client.post(
                "/api/v1/sync/winner/season/2024-25?include_pbp=false"
            )

            assert response.status_code == 200

            # Verify sync_season was called with include_pbp=False
            mock_manager.sync_season.assert_called_once()
            call_args = mock_manager.sync_season.call_args
            assert call_args.kwargs.get("include_pbp") is False

    def test_sync_season_invalid_source_returns_error(self, client):
        """Test syncing with invalid source returns 400."""
        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.sync_season = AsyncMock(
                side_effect=ValueError("Unknown source: invalid")
            )
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/invalid/season/2024-25")

            assert response.status_code == 400
            assert "Unknown source" in response.json()["detail"]


class TestSyncGame:
    """Tests for POST /api/v1/sync/{source}/game/{game_id} endpoint."""

    def test_sync_game_returns_sync_log(self, client, test_db: Session):
        """Test syncing game returns a sync log response."""
        setup = create_test_setup(test_db)

        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.sync_game = AsyncMock(
                return_value=MagicMock(
                    id=uuid4(),
                    source="winner",
                    entity_type="game",
                    status="COMPLETED",
                    season_id=None,
                    season=None,
                    game_id=uuid4(),
                    records_processed=1,
                    records_created=1,
                    records_updated=0,
                    records_skipped=0,
                    error_message=None,
                    error_details=None,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/winner/game/12345")

            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "winner"
            assert data["entity_type"] == "game"
            assert data["records_created"] == 1

    def test_sync_game_already_synced_shows_skipped(self, client, test_db: Session):
        """Test syncing already synced game shows as skipped."""
        setup = create_test_setup(test_db)

        # Create existing game
        game = Game(
            id=uuid4(),
            season_id=setup["season"].id,
            home_team_id=setup["home_team"].id,
            away_team_id=setup["away_team"].id,
            game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
            status="FINAL",
            external_ids={"winner": "game-123"},
        )
        test_db.add(game)
        test_db.commit()

        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.sync_game = AsyncMock(
                return_value=MagicMock(
                    id=uuid4(),
                    source="winner",
                    entity_type="game",
                    status="COMPLETED",
                    season_id=None,
                    season=None,
                    game_id=game.id,
                    records_processed=1,
                    records_created=0,
                    records_updated=0,
                    records_skipped=1,
                    error_message=None,
                    error_details=None,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/winner/game/game-123")

            assert response.status_code == 200
            data = response.json()
            assert data["records_skipped"] == 1
            assert data["records_created"] == 0


class TestSyncTeams:
    """Tests for POST /api/v1/sync/{source}/teams/{season_id} endpoint."""

    def test_sync_teams_returns_sync_log(self, client, test_db: Session):
        """Test syncing teams returns a sync log response."""
        setup = create_test_setup(test_db)

        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.sync_teams = AsyncMock(
                return_value=MagicMock(
                    id=uuid4(),
                    source="winner",
                    entity_type="teams",
                    status="COMPLETED",
                    season_id=setup["season"].id,
                    season=setup["season"],
                    game_id=None,
                    records_processed=12,
                    records_created=10,
                    records_updated=2,
                    records_skipped=0,
                    error_message=None,
                    error_details=None,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )
            )
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/winner/teams/2024-25")

            assert response.status_code == 200
            data = response.json()
            assert data["source"] == "winner"
            assert data["entity_type"] == "teams"
            assert data["records_created"] == 10
            assert data["records_updated"] == 2


class TestSyncLogsAfterSync:
    """Tests verifying sync operations create proper logs."""

    def test_sync_creates_log_entry(self, client, test_db: Session):
        """Test that sync operations create log entries visible in /sync/logs."""
        setup = create_test_setup(test_db)
        sync_service = SyncLogService(test_db)

        # Create a sync log manually (simulating what manager would do)
        sync = sync_service.start_sync(
            source="winner", entity_type="season", season_id=setup["season"].id
        )
        sync_service.complete_sync(sync.id, 50, 45, 5, 0)

        # Verify it shows in logs
        response = client.get("/api/v1/sync/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Find our sync log
        our_log = next(
            (
                log
                for log in data["items"]
                if log["entity_type"] == "season" and log["source"] == "winner"
            ),
            None,
        )
        assert our_log is not None
        assert our_log["records_processed"] == 50
        assert our_log["records_created"] == 45
