"""
Tests for SyncManager with canonical converters.

Tests the new canonical sync pattern:
- SyncManager accepts BaseLeagueConverter
- sync_player sets positions as list
- sync_boxscore uses minutes_seconds
- sync_pbp uses canonical event types and subtypes
- Invalid data raises ConversionError
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Player, Season, Team, TeamSeason
from src.schemas.enums import Position
from src.sync.canonical import ConversionError
from src.sync.euroleague.converter import EuroleagueConverter
from src.sync.manager import SyncManager
from src.sync.winner.converter import WinnerConverter


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


@pytest.fixture
def euroleague_setup(db_session: Session):
    """Create Euroleague league and season."""
    league = League(name="Euroleague", code="EUROLEAGUE", country="Europe")
    db_session.add(league)
    db_session.flush()

    season = Season(
        league_id=league.id,
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        external_ids={"euroleague": "E2024"},
    )
    db_session.add(season)
    db_session.flush()

    # Create teams
    home_team = Team(
        name="Maccabi Tel Aviv",
        short_name="MAC",
        city="Tel Aviv",
        country="Israel",
        external_ids={"euroleague": "MAC"},
    )
    away_team = Team(
        name="Real Madrid",
        short_name="RMB",
        city="Madrid",
        country="Spain",
        external_ids={"euroleague": "RMB"},
    )
    db_session.add_all([home_team, away_team])
    db_session.flush()

    # Link teams to season
    home_team_season = TeamSeason(
        team_id=home_team.id,
        season_id=season.id,
        external_id="MAC",
    )
    away_team_season = TeamSeason(
        team_id=away_team.id,
        season_id=season.id,
        external_id="RMB",
    )
    db_session.add_all([home_team_season, away_team_season])
    db_session.commit()

    return {
        "league": league,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
    }


@pytest.fixture
def winner_setup(db_session: Session):
    """Create Winner league and season."""
    league = League(name="Winner League", code="WINNER", country="Israel")
    db_session.add(league)
    db_session.flush()

    season = Season(
        league_id=league.id,
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        external_ids={"winner": "2024-25"},
    )
    db_session.add(season)
    db_session.flush()

    # Create teams
    home_team = Team(
        name="Maccabi Tel Aviv",
        short_name="MAC",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "100"},
    )
    away_team = Team(
        name="Hapoel Jerusalem",
        short_name="JLM",
        city="Jerusalem",
        country="Israel",
        external_ids={"winner": "200"},
    )
    db_session.add_all([home_team, away_team])
    db_session.flush()

    # Link teams to season
    home_team_season = TeamSeason(
        team_id=home_team.id,
        season_id=season.id,
        external_id="100",
    )
    away_team_season = TeamSeason(
        team_id=away_team.id,
        season_id=season.id,
        external_id="200",
    )
    db_session.add_all([home_team_season, away_team_season])
    db_session.commit()

    return {
        "league": league,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
    }


class TestSyncManagerInit:
    """Tests for SyncManager initialization with converter."""

    def test_init_with_converter(self, db_session: Session):
        """SyncManager should accept a converter."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        assert manager.converter is converter
        assert manager.converter.source == "euroleague"

    def test_init_without_converter(self, db_session: Session):
        """SyncManager should work without converter for backward compat."""
        manager = SyncManager(db=db_session)

        assert manager.converter is None

    def test_require_converter_raises_if_none(self, db_session: Session):
        """_require_converter should raise if converter not set."""
        manager = SyncManager(db=db_session)

        with pytest.raises(ValueError, match="Converter not configured"):
            manager._require_converter()


class TestSyncPlayerCanonical:
    """Tests for sync_player_canonical method."""

    def test_sync_player_sets_multiple_positions(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_player_canonical should set positions as list."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        raw = {
            "code": "P001",
            "name": "JAMES, LEBRON",
            "position": "Forward",  # Maps to [SF, PF]
            "height": "2.06",
            "birthDate": "1984-12-30",
            "country": {"code": "USA", "name": "United States"},
        }

        player = manager.sync_player_canonical(raw)
        db_session.commit()

        # Note: Euroleague converter title-cases names
        assert player.first_name == "Lebron"
        assert player.last_name == "James"
        assert player.positions == [Position.SMALL_FORWARD, Position.POWER_FORWARD]
        assert player.height_cm == 206
        assert player.birth_date == date(1984, 12, 30)

    def test_sync_player_guard_position(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_player_canonical should handle guard positions."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        raw = {
            "code": "P002",
            "name": "CURRY, STEPHEN",
            "position": "Guard",  # Maps to [PG, SG]
            "height": "1.88",
        }

        player = manager.sync_player_canonical(raw)
        db_session.commit()

        assert player.positions == [Position.POINT_GUARD, Position.SHOOTING_GUARD]

    def test_sync_player_center_position(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_player_canonical should handle center position."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        raw = {
            "code": "P003",
            "name": "EMBIID, JOEL",
            "position": "Center",  # Maps to [C]
            "height": "2.13",
        }

        player = manager.sync_player_canonical(raw)
        db_session.commit()

        assert player.positions == [Position.CENTER]

    def test_sync_player_rejects_invalid_height(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_player_canonical should raise on invalid height."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        raw = {
            "code": "P004",
            "name": "INVALID, PLAYER",
            "position": "Guard",
            "height": "5.00",  # Invalid height (500cm)
        }

        with pytest.raises(ConversionError):
            manager.sync_player_canonical(raw)


class TestSyncPlayerWinner:
    """Tests for sync_player with Winner converter."""

    def test_winner_player_positions(
        self,
        db_session: Session,
        winner_setup: dict,
    ):
        """Winner converter should map positions correctly."""
        converter = WinnerConverter()
        manager = SyncManager(db=db_session, converter=converter)

        raw = {
            "external_id": "100",
            "name": "John Smith",
            "position": "G-F",  # Maps to [SG, SF]
            "height_cm": "198",
        }

        player = manager.sync_player_canonical(raw)
        db_session.commit()

        # G-F maps to specific positions, not general
        assert player.positions == [Position.SHOOTING_GUARD, Position.SMALL_FORWARD]


class TestSyncGameCanonical:
    """Tests for sync_game_canonical method."""

    def test_sync_game_creates_record(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_game_canonical should create a game record."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        raw = {
            "gamecode": "E2024_1",
            "homecode": "MAC",
            "awaycode": "RMB",
            "date": "2024-11-15",
            "startime": "20:00",
            "played": True,
            "homescore": 85,
            "awayscore": 78,
        }

        game = manager.sync_game_canonical(raw, euroleague_setup["season"].id)
        db_session.commit()

        assert game.home_team_id == euroleague_setup["home_team"].id
        assert game.away_team_id == euroleague_setup["away_team"].id
        assert game.home_score == 85
        assert game.away_score == 78

    def test_sync_game_safe_returns_none_on_error(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_game_safe should return None on ConversionError."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        # Invalid raw data missing required fields
        raw = {"invalid": "data"}

        result = manager.sync_game_safe(raw, euroleague_setup["season"].id)

        assert result is None


class TestSyncBoxscoreCanonical:
    """Tests for sync_boxscore_canonical method."""

    def test_sync_boxscore_uses_minutes_seconds(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_boxscore_canonical should use minutes_seconds (in seconds)."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        # Create a game first
        game = Game(
            season_id=euroleague_setup["season"].id,
            home_team_id=euroleague_setup["home_team"].id,
            away_team_id=euroleague_setup["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"euroleague": "1"},
        )
        db_session.add(game)
        db_session.flush()

        # Create a player with matching external_id
        player = Player(
            first_name="LeBron",
            last_name="James",
            external_ids={"euroleague": "P001"},
        )
        db_session.add(player)
        db_session.commit()

        # Use Euroleague API field names
        raw_boxscore = {
            "players": [
                {
                    "Player_ID": "P001",
                    "Player": "JAMES, LEBRON",
                    "Dorsal": "23",
                    "Team": "MAC",  # Matches home team external_id
                    "IsStarter": 1,
                    "Minutes": "25:30",  # MM:SS format
                    "Points": 28,
                    "Assists": 8,
                    "TotalRebounds": 7,
                    "FieldGoalsMade2": 10,
                    "FieldGoalsAttempted2": 15,
                    "FieldGoalsMade3": 2,
                    "FieldGoalsAttempted3": 5,
                    "FreeThrowsMade": 4,
                    "FreeThrowsAttempted": 5,
                    "OffensiveRebounds": 2,
                    "DefensiveRebounds": 5,
                    "Turnovers": 3,
                    "Steals": 2,
                    "BlocksAgainst": 1,
                    "FoulsCommited": 2,
                    "PlusMinus": 10,
                }
            ]
        }

        stats = manager.sync_boxscore_canonical(raw_boxscore, game)
        db_session.commit()

        assert len(stats) == 1
        assert stats[0].minutes_played == 1530  # 25*60 + 30 seconds
        assert stats[0].points == 28


class TestSyncPbpCanonical:
    """Tests for sync_pbp_canonical method."""

    def test_sync_pbp_uses_canonical_event_types(
        self,
        db_session: Session,
        euroleague_setup: dict,
    ):
        """sync_pbp_canonical should use canonical event types."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        # Create a game first
        game = Game(
            season_id=euroleague_setup["season"].id,
            home_team_id=euroleague_setup["home_team"].id,
            away_team_id=euroleague_setup["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"euroleague": "1"},
        )
        db_session.add(game)
        db_session.commit()

        raw_events = [
            {
                "numberofplay": 1,
                "period": 1,
                "markertime": "10:00",
                "playtype": "2FGM",  # Two-point shot made
                "team": {"code": "MAC"},
                "player": {"code": "P001", "name": "JAMES, LEBRON"},
            },
            {
                "numberofplay": 2,
                "period": 1,
                "markertime": "09:45",
                "playtype": "3FGA",  # Three-point shot missed
                "team": {"code": "RMB"},
                "player": {"code": "P002", "name": "DOE, JOHN"},
            },
        ]

        events = manager.sync_pbp_canonical(raw_events, game)
        db_session.commit()

        assert len(events) == 2
        # First event: 2-point shot made
        assert events[0].event_type.value == "SHOT"
        assert events[0].event_subtype == "2PT"
        assert events[0].success is True
        # Second event: 3-point shot missed
        assert events[1].event_type.value == "SHOT"
        assert events[1].event_subtype == "3PT"
        assert events[1].success is False


class TestBothConverters:
    """Tests that both converters work with SyncManager."""

    def test_euroleague_converter_works(self, db_session: Session):
        """Euroleague converter should work with SyncManager."""
        converter = EuroleagueConverter()
        manager = SyncManager(db=db_session, converter=converter)

        assert manager.converter.source == "euroleague"

    def test_winner_converter_works(self, db_session: Session):
        """Winner converter should work with SyncManager."""
        converter = WinnerConverter()
        manager = SyncManager(db=db_session, converter=converter)

        assert manager.converter.source == "winner"
