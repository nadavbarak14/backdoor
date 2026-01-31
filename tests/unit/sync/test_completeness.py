"""
Tests for sync completeness detection module.

Tests the functions that detect incomplete data in the sync pipeline:
- get_incomplete_players: finds players missing bio data
- get_games_without_stats: finds games without boxscore
- get_games_without_pbp: finds games without play-by-play
- get_sync_completeness_report: aggregate stats
"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base
from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player
from src.models.team import Team, TeamSeason
from src.schemas.enums import Position
from src.sync.completeness import (
    get_games_without_pbp,
    get_games_without_stats,
    get_incomplete_players,
    get_incomplete_teams,
    get_sync_completeness_report,
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


@pytest.fixture
def setup_base(db_session: Session):
    """Create basic league, season, and teams."""
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


class TestGetIncompletePlayers:
    """Tests for get_incomplete_players function."""

    def test_player_without_height_is_incomplete(self, db_session: Session):
        """Player missing height_cm is detected as incomplete."""
        player = Player(
            first_name="Test",
            last_name="Player",
            height_cm=None,
            birth_date=date(1995, 1, 1),
            positions=[Position.POINT_GUARD],
            external_ids={"test": "123"},
        )
        db_session.add(player)
        db_session.commit()

        incomplete = get_incomplete_players(db_session)
        assert player in incomplete

    def test_player_without_birth_date_is_incomplete(self, db_session: Session):
        """Player missing birth_date is detected as incomplete."""
        player = Player(
            first_name="Test",
            last_name="Player",
            height_cm=198,
            birth_date=None,
            positions=[Position.POINT_GUARD],
            external_ids={"test": "123"},
        )
        db_session.add(player)
        db_session.commit()

        incomplete = get_incomplete_players(db_session)
        assert player in incomplete

    def test_player_without_positions_is_incomplete(self, db_session: Session):
        """Player with empty positions list is detected as incomplete."""
        player = Player(
            first_name="Test",
            last_name="Player",
            height_cm=198,
            birth_date=date(1995, 1, 1),
            positions=[],
            external_ids={"test": "123"},
        )
        db_session.add(player)
        db_session.commit()

        incomplete = get_incomplete_players(db_session)
        assert player in incomplete

    def test_complete_player_not_flagged(self, db_session: Session):
        """Player with all required data is not detected as incomplete."""
        player = Player(
            first_name="Complete",
            last_name="Player",
            height_cm=198,
            birth_date=date(1995, 1, 1),
            positions=[Position.POINT_GUARD, Position.SHOOTING_GUARD],
            external_ids={"test": "123"},
        )
        db_session.add(player)
        db_session.commit()

        incomplete = get_incomplete_players(db_session)
        assert player not in incomplete

    def test_filter_by_source(self, db_session: Session):
        """Filter incomplete players by external source."""
        player1 = Player(
            first_name="Test",
            last_name="Player1",
            height_cm=None,
            external_ids={"euroleague": "E001"},
        )
        player2 = Player(
            first_name="Test",
            last_name="Player2",
            height_cm=None,
            external_ids={"winner": "W001"},
        )
        db_session.add_all([player1, player2])
        db_session.commit()

        euroleague_incomplete = get_incomplete_players(db_session, source="euroleague")
        assert player1 in euroleague_incomplete
        assert player2 not in euroleague_incomplete

        winner_incomplete = get_incomplete_players(db_session, source="winner")
        assert player2 in winner_incomplete
        assert player1 not in winner_incomplete

    def test_limit_results(self, db_session: Session):
        """Limit parameter restricts number of results."""
        for i in range(5):
            player = Player(
                first_name=f"Test{i}",
                last_name="Player",
                height_cm=None,
                external_ids={"test": str(i)},
            )
            db_session.add(player)
        db_session.commit()

        incomplete = get_incomplete_players(db_session, limit=3)
        assert len(incomplete) == 3


class TestGetGamesWithoutStats:
    """Tests for get_games_without_stats function."""

    def test_game_without_stats_is_found(
        self, db_session: Session, setup_base: dict
    ):
        """FINAL game without PlayerGameStats is detected."""
        game = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"test": "game1"},
        )
        db_session.add(game)
        db_session.commit()

        missing = get_games_without_stats(db_session)
        assert game in missing

    def test_game_with_stats_not_found(
        self, db_session: Session, setup_base: dict
    ):
        """FINAL game with PlayerGameStats is not detected."""
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"test": "p1"},
        )
        db_session.add(player)
        db_session.flush()

        game = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"test": "game1"},
        )
        db_session.add(game)
        db_session.flush()

        stats = PlayerGameStats(
            game_id=game.id,
            player_id=player.id,
            team_id=setup_base["home_team"].id,
            minutes_played=1200,
            points=20,
        )
        db_session.add(stats)
        db_session.commit()

        missing = get_games_without_stats(db_session)
        assert game not in missing

    def test_non_final_game_excluded(
        self, db_session: Session, setup_base: dict
    ):
        """Games not marked FINAL are excluded from results."""
        game = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="SCHEDULED",
            external_ids={"test": "game1"},
        )
        db_session.add(game)
        db_session.commit()

        missing = get_games_without_stats(db_session)
        assert game not in missing

    def test_filter_by_source(
        self, db_session: Session, setup_base: dict
    ):
        """Filter games without stats by external source."""
        game1 = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            external_ids={"euroleague": "E1"},
        )
        game2 = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 16, 20, 0),
            status="FINAL",
            external_ids={"winner": "W1"},
        )
        db_session.add_all([game1, game2])
        db_session.commit()

        euroleague_missing = get_games_without_stats(db_session, source="euroleague")
        assert game1 in euroleague_missing
        assert game2 not in euroleague_missing


class TestGetGamesWithoutPbp:
    """Tests for get_games_without_pbp function."""

    def test_game_without_pbp_is_found(
        self, db_session: Session, setup_base: dict
    ):
        """FINAL game without PlayByPlayEvent is detected."""
        game = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"test": "game1"},
        )
        db_session.add(game)
        db_session.commit()

        missing = get_games_without_pbp(db_session)
        assert game in missing

    def test_game_with_pbp_not_found(
        self, db_session: Session, setup_base: dict
    ):
        """FINAL game with PlayByPlayEvent is not detected."""
        game = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"test": "game1"},
        )
        db_session.add(game)
        db_session.flush()

        from src.sync.canonical import EventType

        pbp_event = PlayByPlayEvent(
            game_id=game.id,
            team_id=setup_base["home_team"].id,
            event_number=1,
            period=1,
            clock="10:00",
            event_type=EventType.SHOT,
        )
        db_session.add(pbp_event)
        db_session.commit()

        missing = get_games_without_pbp(db_session)
        assert game not in missing


class TestGetIncompleteTeams:
    """Tests for get_incomplete_teams function."""

    def test_team_with_empty_name_is_incomplete(self, db_session: Session):
        """Team with empty name is detected as incomplete."""
        team = Team(
            name="",
            short_name="TST",
            city="Test City",
            country="Test",
            external_ids={"test": "123"},
        )
        db_session.add(team)
        db_session.commit()

        incomplete = get_incomplete_teams(db_session)
        assert team in incomplete

    def test_complete_team_not_flagged(self, db_session: Session):
        """Team with all required data is not detected as incomplete."""
        team = Team(
            name="Complete Team",
            short_name="COM",
            city="Complete City",
            country="Test",
            external_ids={"test": "123"},
        )
        db_session.add(team)
        db_session.commit()

        incomplete = get_incomplete_teams(db_session)
        assert team not in incomplete


class TestGetSyncCompletenessReport:
    """Tests for get_sync_completeness_report function."""

    def test_empty_database_returns_100_percent(self, db_session: Session):
        """Empty database shows 100% complete (no incomplete records)."""
        report = get_sync_completeness_report(db_session)

        assert report["players"]["total"] == 0
        assert report["players"]["incomplete"] == 0
        assert report["players"]["complete_pct"] == 100.0

        assert report["games"]["total"] == 0
        assert report["games"]["without_stats"] == 0
        assert report["games"]["without_pbp"] == 0

        assert report["teams"]["total"] == 0
        assert report["teams"]["incomplete"] == 0

    def test_report_with_incomplete_data(
        self, db_session: Session, setup_base: dict
    ):
        """Report correctly counts incomplete records."""
        # Add complete player
        complete_player = Player(
            first_name="Complete",
            last_name="Player",
            height_cm=198,
            birth_date=date(1995, 1, 1),
            positions=[Position.POINT_GUARD],
            external_ids={"test": "c1"},
        )
        # Add incomplete player
        incomplete_player = Player(
            first_name="Incomplete",
            last_name="Player",
            height_cm=None,
            external_ids={"test": "i1"},
        )
        db_session.add_all([complete_player, incomplete_player])
        db_session.flush()

        # Add game without stats
        game = Game(
            season_id=setup_base["season"].id,
            home_team_id=setup_base["home_team"].id,
            away_team_id=setup_base["away_team"].id,
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            external_ids={"test": "game1"},
        )
        db_session.add(game)
        db_session.commit()

        report = get_sync_completeness_report(db_session)

        assert report["players"]["total"] == 2
        assert report["players"]["incomplete"] == 1
        assert report["players"]["complete_pct"] == 50.0

        assert report["games"]["total"] == 1
        assert report["games"]["without_stats"] == 1
        assert report["games"]["without_pbp"] == 1

    def test_filter_by_source(self, db_session: Session, setup_base: dict):
        """Report can be filtered by source."""
        player1 = Player(
            first_name="Test",
            last_name="Player1",
            height_cm=None,
            external_ids={"euroleague": "E001"},
        )
        player2 = Player(
            first_name="Test",
            last_name="Player2",
            height_cm=None,
            external_ids={"winner": "W001"},
        )
        db_session.add_all([player1, player2])
        db_session.commit()

        euroleague_report = get_sync_completeness_report(db_session, source="euroleague")
        assert euroleague_report["players"]["total"] == 1
        assert euroleague_report["players"]["incomplete"] == 1

        winner_report = get_sync_completeness_report(db_session, source="winner")
        assert winner_report["players"]["total"] == 1
        assert winner_report["players"]["incomplete"] == 1
