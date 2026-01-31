"""
Tests for the sync streaming endpoint.

Tests cover:
- SSE format output
- Progress event structure
- Error handling mid-sync
- Complete event with sync log summary
"""

import json
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.team import Team
from src.schemas.enums import GameStatus
from src.schemas.sync import SyncProgressEvent
from src.sync.adapters.base import BaseLeagueAdapter
from src.sync.config import SyncConfig, SyncSourceConfig
from src.sync.manager import SyncManager
from src.sync.types import RawBoxScore, RawGame, RawPlayerStats, RawTeam


@pytest.fixture
def league(test_db: Session) -> League:
    """Create a test league."""
    league = League(
        id=uuid4(),
        name="Winner League",
        code="WINNER",
        country="Israel",
    )
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def season(test_db: Session, league: League) -> Season:
    """Create a test season."""
    season = Season(
        id=uuid4(),
        league_id=league.id,
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 6, 30),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def home_team(test_db: Session) -> Team:
    """Create a home team."""
    team = Team(
        id=uuid4(),
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "mta-123"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def away_team(test_db: Session) -> Team:
    """Create an away team."""
    team = Team(
        id=uuid4(),
        name="Hapoel Jerusalem",
        short_name="HJR",
        city="Jerusalem",
        country="Israel",
        external_ids={"winner": "hjr-456"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def sync_config() -> SyncConfig:
    """Create a sync config with winner enabled."""
    return SyncConfig(
        sources={
            "winner": SyncSourceConfig(
                source_name="winner",
                enabled=True,
                auto_sync_enabled=False,
                sync_interval_minutes=60,
            )
        }
    )


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Create a mock adapter."""
    adapter = MagicMock(spec=BaseLeagueAdapter)
    adapter.source_name = "winner"
    return adapter


@pytest.fixture
def sync_manager(
    test_db: Session, sync_config: SyncConfig, mock_adapter: MagicMock
) -> SyncManager:
    """Create a SyncManager instance."""
    return SyncManager(
        db=test_db,
        adapters={"winner": mock_adapter},
        config=sync_config,
    )


class TestSyncProgressEventSchema:
    """Tests for the SyncProgressEvent Pydantic schema."""

    def test_start_event(self) -> None:
        """Should create a valid start event."""
        event = SyncProgressEvent(
            event="start",
            phase="games",
            total=120,
        )
        assert event.event == "start"
        assert event.phase == "games"
        assert event.total == 120

    def test_progress_event(self) -> None:
        """Should create a valid progress event."""
        event = SyncProgressEvent(
            event="progress",
            phase="games",
            current=5,
            total=120,
            game_id="12345",
            status="syncing",
        )
        assert event.event == "progress"
        assert event.current == 5
        assert event.total == 120
        assert event.game_id == "12345"
        assert event.status == "syncing"

    def test_synced_event(self) -> None:
        """Should create a valid synced event."""
        event = SyncProgressEvent(
            event="synced",
            game_id="12345",
        )
        assert event.event == "synced"
        assert event.game_id == "12345"

    def test_error_event(self) -> None:
        """Should create a valid error event."""
        event = SyncProgressEvent(
            event="error",
            game_id="12346",
            error="Failed to fetch boxscore",
        )
        assert event.event == "error"
        assert event.game_id == "12346"
        assert event.error == "Failed to fetch boxscore"

    def test_complete_event(self) -> None:
        """Should create a valid complete event."""
        event = SyncProgressEvent(
            event="complete",
            sync_log={
                "id": "uuid",
                "status": "COMPLETED",
                "records_created": 15,
                "records_skipped": 105,
            },
        )
        assert event.event == "complete"
        assert event.sync_log is not None
        assert event.sync_log["status"] == "COMPLETED"


class TestSyncSeasonWithProgress:
    """Tests for SyncManager.sync_season_with_progress method."""

    @pytest.mark.asyncio
    async def test_yields_start_event(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
    ) -> None:
        """Should yield a start event with total game count."""
        mock_adapter.get_teams = AsyncMock(
            return_value=[
                RawTeam(external_id="mta-123", name="Maccabi Tel Aviv"),
                RawTeam(external_id="hjr-456", name="Hapoel Jerusalem"),
            ]
        )

        raw_game = RawGame(
            external_id="game-001",
            home_team_external_id="mta-123",
            away_team_external_id="hjr-456",
            game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
            status=GameStatus.FINAL,
            home_score=100,
            away_score=95,
        )

        mock_adapter.get_schedule = AsyncMock(return_value=[raw_game])
        mock_adapter.is_game_final = MagicMock(return_value=True)

        boxscore = RawBoxScore(
            game=raw_game,
            home_players=[
                RawPlayerStats(
                    player_external_id="p1",
                    player_name="Player One",
                    team_external_id="mta-123",
                    points=20,
                )
            ],
            away_players=[
                RawPlayerStats(
                    player_external_id="p2",
                    player_name="Player Two",
                    team_external_id="hjr-456",
                    points=15,
                )
            ],
        )
        mock_adapter.get_game_boxscore = AsyncMock(return_value=boxscore)
        mock_adapter.get_game_pbp = AsyncMock(return_value=[])

        events = []
        async for event in sync_manager.sync_season_with_progress("winner", "2024-25"):
            events.append(event)

        # First event should be start
        assert events[0]["event"] == "start"
        assert events[0]["phase"] == "games"
        assert "total" in events[0]

    @pytest.mark.asyncio
    async def test_yields_progress_and_synced_events(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
    ) -> None:
        """Should yield progress and synced events for each game."""
        mock_adapter.get_teams = AsyncMock(
            return_value=[
                RawTeam(external_id="mta-123", name="Maccabi Tel Aviv"),
                RawTeam(external_id="hjr-456", name="Hapoel Jerusalem"),
            ]
        )

        raw_game = RawGame(
            external_id="game-002",
            home_team_external_id="mta-123",
            away_team_external_id="hjr-456",
            game_date=datetime(2024, 12, 20, 19, 30, tzinfo=UTC),
            status=GameStatus.FINAL,
            home_score=110,
            away_score=105,
        )

        mock_adapter.get_schedule = AsyncMock(return_value=[raw_game])
        mock_adapter.is_game_final = MagicMock(return_value=True)

        boxscore = RawBoxScore(
            game=raw_game,
            home_players=[
                RawPlayerStats(
                    player_external_id="p1",
                    player_name="Player One",
                    team_external_id="mta-123",
                    points=20,
                )
            ],
            away_players=[
                RawPlayerStats(
                    player_external_id="p2",
                    player_name="Player Two",
                    team_external_id="hjr-456",
                    points=15,
                )
            ],
        )
        mock_adapter.get_game_boxscore = AsyncMock(return_value=boxscore)
        mock_adapter.get_game_pbp = AsyncMock(return_value=[])

        events = []
        async for event in sync_manager.sync_season_with_progress("winner", "2024-25"):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert "progress" in event_types
        assert "synced" in event_types

        # Find progress event
        progress_events = [e for e in events if e["event"] == "progress"]
        assert len(progress_events) == 1
        assert progress_events[0]["game_id"] == "game-002"
        assert progress_events[0]["status"] == "syncing"

    @pytest.mark.asyncio
    async def test_yields_error_event_on_game_failure(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
    ) -> None:
        """Should yield error event when a game fails to sync."""
        mock_adapter.get_teams = AsyncMock(
            return_value=[
                RawTeam(external_id="mta-123", name="Maccabi Tel Aviv"),
                RawTeam(external_id="hjr-456", name="Hapoel Jerusalem"),
            ]
        )

        raw_game = RawGame(
            external_id="game-error",
            home_team_external_id="mta-123",
            away_team_external_id="hjr-456",
            game_date=datetime(2024, 12, 25, 19, 30, tzinfo=UTC),
            status=GameStatus.FINAL,
            home_score=100,
            away_score=95,
        )

        mock_adapter.get_schedule = AsyncMock(return_value=[raw_game])
        mock_adapter.is_game_final = MagicMock(return_value=True)
        mock_adapter.get_game_boxscore = AsyncMock(
            side_effect=Exception("Network error")
        )

        events = []
        async for event in sync_manager.sync_season_with_progress("winner", "2024-25"):
            events.append(event)

        event_types = [e["event"] for e in events]
        assert "error" in event_types

        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["game_id"] == "game-error"
        assert "Network error" in error_events[0]["error"]

    @pytest.mark.asyncio
    async def test_yields_complete_event(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
    ) -> None:
        """Should yield complete event with sync log summary."""
        mock_adapter.get_teams = AsyncMock(
            return_value=[
                RawTeam(external_id="mta-123", name="Maccabi Tel Aviv"),
                RawTeam(external_id="hjr-456", name="Hapoel Jerusalem"),
            ]
        )

        mock_adapter.get_schedule = AsyncMock(return_value=[])
        mock_adapter.is_game_final = MagicMock(return_value=True)

        events = []
        async for event in sync_manager.sync_season_with_progress("winner", "2024-25"):
            events.append(event)

        # Last event should be complete
        assert events[-1]["event"] == "complete"
        assert "sync_log" in events[-1]
        assert "id" in events[-1]["sync_log"]
        assert "status" in events[-1]["sync_log"]

    @pytest.mark.asyncio
    async def test_handles_fatal_error(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
    ) -> None:
        """Should yield complete event with error on fatal failure."""
        mock_adapter.get_teams = AsyncMock(side_effect=Exception("Fatal error"))

        events = []
        async for event in sync_manager.sync_season_with_progress("winner", "2024-25"):
            events.append(event)

        # Should still have complete event
        assert events[-1]["event"] == "complete"
        assert events[-1]["sync_log"]["status"] == "FAILED"
        assert "Fatal error" in events[-1]["sync_log"]["error_message"]


class TestStreamingEndpoint:
    """Tests for the streaming API endpoint."""

    def test_returns_event_stream_content_type(self, client) -> None:
        """Should return text/event-stream content type."""
        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()

            async def mock_generator():
                yield {"event": "start", "phase": "games", "total": 0, "skipped": 0}
                yield {
                    "event": "complete",
                    "sync_log": {"id": "test", "status": "COMPLETED"},
                }

            mock_manager.sync_season_with_progress = MagicMock(
                return_value=mock_generator()
            )
            mock_manager._get_adapter = MagicMock()
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/winner/season/2024-25/stream")

            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_returns_400_for_invalid_source(self, client) -> None:
        """Should return 400 for unknown source."""
        response = client.post("/api/v1/sync/invalid/season/2024-25/stream")
        assert response.status_code == 400

    def test_sse_format(self, client) -> None:
        """Should return properly formatted SSE events."""
        with patch("src.api.v1.sync._get_sync_manager") as mock_get_manager:
            mock_manager = MagicMock()

            async def mock_generator():
                yield {"event": "start", "phase": "games", "total": 1, "skipped": 0}
                yield {
                    "event": "complete",
                    "sync_log": {"id": "test", "status": "COMPLETED"},
                }

            mock_manager.sync_season_with_progress = MagicMock(
                return_value=mock_generator()
            )
            mock_manager._get_adapter = MagicMock()
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/v1/sync/winner/season/2024-25/stream")
            content = response.text

            # Check SSE format
            assert "event: start" in content
            assert "event: complete" in content
            assert "data: " in content

            # Parse data lines
            lines = content.strip().split("\n")
            data_lines = [line for line in lines if line.startswith("data: ")]

            for data_line in data_lines:
                json_str = data_line[6:]  # Remove "data: " prefix
                parsed = json.loads(json_str)
                assert "event" in parsed
