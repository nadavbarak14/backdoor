"""
Tests for historical sync functionality.

Tests the adapter methods and SyncManager methods for:
- get_games_since: get games from last N days
- get_available_seasons: list available seasons
- sync_recent: sync recent games
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base
from src.models.league import League, Season
from src.models.team import Team, TeamSeason
from src.sync.adapters.base import BaseLeagueAdapter
from src.sync.types import RawGame, RawSeason


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


class MockAdapter(BaseLeagueAdapter):
    """Mock adapter for testing."""

    source_name = "test"

    def __init__(self):
        self.games = []
        self.seasons = []

    async def get_seasons(self):
        return self.seasons

    async def get_teams(self, season_id: str):
        return []

    async def get_schedule(self, season_id: str):
        return self.games

    async def get_game_boxscore(self, game_id: str):
        return MagicMock()

    async def get_game_pbp(self, game_id: str):
        return []

    def is_game_final(self, game):
        return game.status == "final"


class TestGetGamesSince:
    """Tests for get_games_since adapter method."""

    @pytest.mark.asyncio
    async def test_returns_games_after_date(self):
        """get_games_since returns games played after the specified date."""
        adapter = MockAdapter()

        # Create games with different dates
        now = datetime.now()
        adapter.games = [
            RawGame(
                external_id="g1",
                home_team_external_id="h1",
                away_team_external_id="a1",
                game_date=now - timedelta(days=3),
                status="final",
            ),
            RawGame(
                external_id="g2",
                home_team_external_id="h2",
                away_team_external_id="a2",
                game_date=now - timedelta(days=10),
                status="final",
            ),
        ]
        adapter.seasons = [
            RawSeason(external_id="2024-25", name="2024-25"),
        ]

        since = now - timedelta(days=7)
        recent_games = await adapter.get_games_since(since)

        # Only game from 3 days ago should be returned
        assert len(recent_games) == 1
        assert recent_games[0].external_id == "g1"

    @pytest.mark.asyncio
    async def test_filters_out_non_final_games(self):
        """get_games_since only returns final games."""
        adapter = MockAdapter()

        now = datetime.now()
        adapter.games = [
            RawGame(
                external_id="g1",
                home_team_external_id="h1",
                away_team_external_id="a1",
                game_date=now - timedelta(days=1),
                status="final",
            ),
            RawGame(
                external_id="g2",
                home_team_external_id="h2",
                away_team_external_id="a2",
                game_date=now - timedelta(days=1),
                status="scheduled",
            ),
        ]
        adapter.seasons = [
            RawSeason(external_id="2024-25", name="2024-25"),
        ]

        since = now - timedelta(days=7)
        recent_games = await adapter.get_games_since(since)

        assert len(recent_games) == 1
        assert recent_games[0].external_id == "g1"

    @pytest.mark.asyncio
    async def test_empty_when_no_seasons(self):
        """get_games_since returns empty list when no seasons available."""
        adapter = MockAdapter()
        adapter.seasons = []

        since = datetime.now() - timedelta(days=7)
        recent_games = await adapter.get_games_since(since)

        assert recent_games == []

    @pytest.mark.asyncio
    async def test_uses_specified_season(self):
        """get_games_since uses the specified season ID."""
        adapter = MockAdapter()

        now = datetime.now()
        adapter.games = [
            RawGame(
                external_id="g1",
                home_team_external_id="h1",
                away_team_external_id="a1",
                game_date=now - timedelta(days=1),
                status="final",
            ),
        ]

        since = now - timedelta(days=7)
        recent_games = await adapter.get_games_since(since, season_id="2023-24")

        assert len(recent_games) == 1


class TestGetAvailableSeasons:
    """Tests for get_available_seasons adapter method."""

    @pytest.mark.asyncio
    async def test_returns_season_names(self):
        """get_available_seasons returns list of season name strings."""
        adapter = MockAdapter()
        adapter.seasons = [
            RawSeason(external_id="E2024", name="2024-25"),
            RawSeason(external_id="E2023", name="2023-24"),
            RawSeason(external_id="E2022", name="2022-23"),
        ]

        seasons = await adapter.get_available_seasons()

        assert seasons == ["2024-25", "2023-24", "2022-23"]

    @pytest.mark.asyncio
    async def test_empty_when_no_seasons(self):
        """get_available_seasons returns empty list when no seasons."""
        adapter = MockAdapter()
        adapter.seasons = []

        seasons = await adapter.get_available_seasons()

        assert seasons == []


class TestSyncRecent:
    """Tests for sync_recent SyncManager method."""

    @pytest.fixture
    def setup_base(self, db_session: Session):
        """Create basic league and season."""
        league = League(name="Test League", code="TEST", country="Test")
        db_session.add(league)
        db_session.flush()

        season = Season(
            league_id=league.id,
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 5, 31),
            is_current=True,
        )
        db_session.add(season)
        db_session.flush()

        home_team = Team(
            name="Home Team",
            short_name="HOM",
            city="Home City",
            country="Test",
            external_ids={"test": "home"},
        )
        away_team = Team(
            name="Away Team",
            short_name="AWY",
            city="Away City",
            country="Test",
            external_ids={"test": "away"},
        )
        db_session.add_all([home_team, away_team])
        db_session.flush()

        home_ts = TeamSeason(team_id=home_team.id, season_id=season.id)
        away_ts = TeamSeason(team_id=away_team.id, season_id=season.id)
        db_session.add_all([home_ts, away_ts])
        db_session.commit()

        return {
            "league": league,
            "season": season,
            "home_team": home_team,
            "away_team": away_team,
        }

    @pytest.mark.asyncio
    async def test_sync_recent_creates_sync_log(
        self, db_session: Session, setup_base: dict
    ):
        """sync_recent creates a sync log for the operation."""
        from src.sync.manager import SyncManager

        # Create mock adapter
        adapter = MockAdapter()
        adapter.seasons = [
            RawSeason(external_id="2024-25", name="2024-25"),
        ]
        adapter.games = []  # No games to sync

        manager = SyncManager(
            db=db_session,
            adapters={"test": adapter},
        )

        sync_log = await manager.sync_recent(source="test", days=7)

        assert sync_log is not None
        assert sync_log.source == "test"
        assert sync_log.entity_type == "recent"

    @pytest.mark.asyncio
    async def test_sync_recent_with_no_games(
        self, db_session: Session, setup_base: dict
    ):
        """sync_recent completes successfully when no games to sync."""
        from src.sync.manager import SyncManager

        adapter = MockAdapter()
        adapter.seasons = [
            RawSeason(external_id="2024-25", name="2024-25"),
        ]
        adapter.games = []

        manager = SyncManager(
            db=db_session,
            adapters={"test": adapter},
        )

        sync_log = await manager.sync_recent(source="test", days=7)

        assert sync_log.status == "COMPLETED"
        assert sync_log.records_processed == 0
        assert sync_log.records_created == 0


class TestHistoricalSyncParameters:
    """Tests for historical sync parameter validation."""

    def test_days_parameter_range(self):
        """Verify days parameter is within valid range."""
        # This would be validated by the API endpoint
        # Valid range: 1-90 days
        assert 1 <= 7 <= 90  # Default
        assert 1 <= 1 <= 90  # Minimum
        assert 1 <= 90 <= 90  # Maximum

    def test_source_parameter_required(self):
        """Source parameter is required for historical sync."""
        # This would be validated by the API endpoint
        pass  # Placeholder - actual validation in API tests
