"""
Tests for the SyncManager class.

Tests cover:
- sync_season skips already-synced games
- sync_game creates all records
- Error handling updates SyncLog correctly
- get_sync_status returns proper status info
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.sync import SyncLog
from src.models.team import Team
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


class TestSyncSeason:
    """Tests for SyncManager.sync_season method."""

    @pytest.mark.asyncio
    async def test_sync_season_skips_already_synced(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
        test_db: Session,
    ) -> None:
        """Should skip games that are already synced."""
        # Setup mock adapter
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
            status="final",
            home_score=100,
            away_score=95,
        )

        mock_adapter.get_schedule = AsyncMock(return_value=[raw_game])
        mock_adapter.is_game_final = MagicMock(return_value=True)

        # Mock boxscore - this should NOT be called since we pre-mark the game as synced
        mock_adapter.get_game_boxscore = AsyncMock()

        # Pre-mark game as synced
        from src.models.game import Game

        existing_game = Game(
            id=uuid4(),
            season_id=season.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
            status="FINAL",
            external_ids={"winner": "game-001"},
        )
        test_db.add(existing_game)
        test_db.commit()

        # Run sync without PBP to test game skip behavior
        sync_log = await sync_manager.sync_season("winner", "2024-25", include_pbp=False)

        # Verify boxscore was NOT called (game was skipped)
        mock_adapter.get_game_boxscore.assert_not_called()

        # Verify sync log shows skipped
        assert sync_log.records_skipped == 1
        assert sync_log.records_created == 0

    @pytest.mark.asyncio
    async def test_sync_season_creates_new_games(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
        test_db: Session,
    ) -> None:
        """Should create new game records for unsynced games."""
        # Setup mock adapter
        mock_adapter.get_teams = AsyncMock(
            return_value=[
                RawTeam(external_id="mta-123", name="Maccabi Tel Aviv"),
                RawTeam(external_id="hjr-456", name="Hapoel Jerusalem"),
            ]
        )

        raw_game = RawGame(
            external_id="game-new",
            home_team_external_id="mta-123",
            away_team_external_id="hjr-456",
            game_date=datetime(2024, 12, 20, 19, 30, tzinfo=UTC),
            status="final",
            home_score=110,
            away_score=105,
        )

        mock_adapter.get_schedule = AsyncMock(return_value=[raw_game])
        mock_adapter.is_game_final = MagicMock(return_value=True)

        # Mock boxscore
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

        # Run sync
        sync_log = await sync_manager.sync_season("winner", "2024-25")

        # Verify game was created
        assert sync_log.records_created == 1
        assert sync_log.status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_sync_season_handles_errors(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should handle errors and update sync log."""
        # Setup mock to raise an error
        mock_adapter.get_teams = AsyncMock(side_effect=Exception("API Error"))

        # Run sync
        sync_log = await sync_manager.sync_season("winner", "2024-25")

        # Verify sync failed
        assert sync_log.status == "FAILED"
        assert "API Error" in sync_log.error_message


class TestSyncGame:
    """Tests for SyncManager.sync_game method."""

    @pytest.mark.asyncio
    async def test_sync_game_skips_already_synced(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        season: Season,
        home_team: Team,
        away_team: Team,
        test_db: Session,
    ) -> None:
        """Should skip if game already synced."""
        # Pre-create game
        from src.models.game import Game

        existing_game = Game(
            id=uuid4(),
            season_id=season.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
            status="FINAL",
            external_ids={"winner": "game-existing"},
        )
        test_db.add(existing_game)
        test_db.commit()

        # Run sync
        sync_log = await sync_manager.sync_game("winner", "game-existing")

        # Verify skipped
        assert sync_log.records_skipped == 1
        assert sync_log.records_created == 0


class TestSyncTeams:
    """Tests for SyncManager.sync_teams method."""

    @pytest.mark.asyncio
    async def test_sync_teams_creates_teams(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
        test_db: Session,
    ) -> None:
        """Should create team records."""
        mock_adapter.get_teams = AsyncMock(
            return_value=[
                RawTeam(external_id="t1", name="Team One", short_name="T1"),
                RawTeam(external_id="t2", name="Team Two", short_name="T2"),
            ]
        )

        sync_log = await sync_manager.sync_teams("winner", "2024-25")

        assert sync_log.status == "COMPLETED"
        assert sync_log.records_created == 2


class TestGetSyncStatus:
    """Tests for SyncManager.get_sync_status method."""

    def test_returns_source_status(
        self,
        sync_manager: SyncManager,
        mock_adapter: MagicMock,
    ) -> None:
        """Should return status for all sources."""
        status = sync_manager.get_sync_status()

        assert "sources" in status
        assert len(status["sources"]) == 1

        winner_status = status["sources"][0]
        assert winner_status["name"] == "winner"
        assert winner_status["enabled"] is True

    def test_returns_running_syncs_count(
        self,
        sync_manager: SyncManager,
        test_db: Session,
    ) -> None:
        """Should return count of running syncs."""
        # Create a running sync log
        sync_log = SyncLog(
            source="winner",
            entity_type="season",
            status="STARTED",
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            started_at=datetime.now(UTC),
        )
        test_db.add(sync_log)
        test_db.commit()

        status = sync_manager.get_sync_status()

        assert status["total_running_syncs"] == 1


class TestValidation:
    """Tests for SyncManager validation."""

    def test_raises_for_unknown_source(
        self,
        sync_manager: SyncManager,
    ) -> None:
        """Should raise ValueError for unknown source."""
        with pytest.raises(ValueError, match="Unknown source"):
            sync_manager._get_adapter("unknown")

    def test_raises_for_disabled_source(
        self,
        test_db: Session,
        mock_adapter: MagicMock,
    ) -> None:
        """Should raise ValueError for disabled source."""
        config = SyncConfig(
            sources={
                "winner": SyncSourceConfig(
                    source_name="winner",
                    enabled=False,
                )
            }
        )

        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=config,
        )

        with pytest.raises(ValueError, match="not enabled"):
            manager._get_adapter("winner")
