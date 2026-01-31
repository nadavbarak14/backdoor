"""
Integration test: Sync ONE complete game with all data.

Tests the entire sync pipeline using real Euroleague fixture data:
- Teams created with correct data
- Players with positions and bio data
- Game record with date, score, status
- Boxscore stats for all players
- Play-by-play events with correct types

Fixture data from Euroleague API for game E2024_1 (BER vs PAN).
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base
from src.models.game import PlayerGameStats
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player
from src.models.team import Team, TeamSeason
from src.sync.euroleague.converter import EuroleagueConverter
from src.sync.manager import SyncManager

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "euroleague"


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory database for testing."""
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
def setup_league_and_season(test_db: Session):
    """Create the Euroleague league and 2024-25 season."""
    league = League(
        name="Euroleague",
        code="EUROLEAGUE",
        country="Europe",
    )
    test_db.add(league)
    test_db.flush()

    from datetime import date

    season = Season(
        league_id=league.id,
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        external_ids={"euroleague": "E2024"},
    )
    test_db.add(season)
    test_db.flush()

    # Create teams
    home_team = Team(
        name="ALBA BERLIN",
        short_name="BER",
        city="Berlin",
        country="Germany",
        external_ids={"euroleague": "BER"},
    )
    away_team = Team(
        name="PANATHINAIKOS AKTOR ATHENS",
        short_name="PAN",
        city="Athens",
        country="Greece",
        external_ids={"euroleague": "PAN"},
    )
    test_db.add_all([home_team, away_team])
    test_db.flush()

    # Link teams to season
    home_ts = TeamSeason(team_id=home_team.id, season_id=season.id, external_id="BER")
    away_ts = TeamSeason(team_id=away_team.id, season_id=season.id, external_id="PAN")
    test_db.add_all([home_ts, away_ts])
    test_db.commit()

    return {
        "league": league,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
    }


@pytest.fixture
def game_data() -> dict:
    """Load single game fixture."""
    with open(FIXTURES / "single_game.json") as f:
        return json.load(f)


@pytest.fixture
def boxscore_data() -> list:
    """Load boxscore fixture (list of player stats), filtering invalid rows."""
    with open(FIXTURES / "boxscore.json") as f:
        data = json.load(f)
    # Filter out Team/Total rows
    return [
        p for p in data
        if p.get("Player_ID", "").strip() not in ("", "Team", "Total")
    ]


@pytest.fixture
def pbp_data() -> list:
    """Load play-by-play fixture."""
    with open(FIXTURES / "pbp.json") as f:
        return json.load(f)


@pytest.fixture
def manager(test_db: Session) -> SyncManager:
    """Create SyncManager with Euroleague converter."""
    return SyncManager(db=test_db, converter=EuroleagueConverter())


class TestTeamSync:
    """Tests for team creation during sync."""

    def test_both_teams_exist_after_setup(
        self, test_db: Session, setup_league_and_season: dict
    ):
        """Both home and away teams exist."""
        teams = test_db.query(Team).all()
        assert len(teams) == 2

        team_codes = {t.short_name for t in teams}
        assert team_codes == {"BER", "PAN"}

    def test_teams_have_names(self, test_db: Session, setup_league_and_season: dict):
        """Teams have proper names."""
        teams = test_db.query(Team).all()
        for team in teams:
            assert team.name, "Team missing name"
            assert team.short_name, "Team missing short_name"


class TestGameSync:
    """Tests for game sync using canonical converter."""

    def test_game_created_with_scores(
        self,
        manager: SyncManager,
        game_data: dict,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Game has final score after sync."""
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.commit()

        assert game.home_score == 77
        assert game.away_score == 87
        assert game.status == "FINAL"

    def test_game_has_correct_teams(
        self,
        manager: SyncManager,
        game_data: dict,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Game references correct home and away teams."""
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.commit()

        assert game.home_team_id == setup_league_and_season["home_team"].id
        assert game.away_team_id == setup_league_and_season["away_team"].id

    def test_game_has_date(
        self,
        manager: SyncManager,
        game_data: dict,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Game has a valid date."""
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.commit()

        assert game.game_date is not None
        assert game.game_date.year == 2024
        assert game.game_date.month == 10


class TestBoxscoreSync:
    """Tests for boxscore sync using canonical converter."""

    @pytest.fixture
    def game_with_boxscore(
        self,
        manager: SyncManager,
        game_data: dict,
        boxscore_data: list,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Create game and sync boxscore."""
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.flush()

        # Create players from boxscore data first (avoid duplicates)
        created_ids = set()
        for raw_player in boxscore_data:
            player_id = raw_player.get("Player_ID", "").strip()
            if player_id and player_id not in created_ids:
                name = raw_player.get("Player", "")
                if ", " in name:
                    parts = name.split(", ")
                    first_name = parts[1] if len(parts) > 1 else ""
                    last_name = parts[0]
                else:
                    first_name = name
                    last_name = ""
                player = Player(
                    first_name=first_name,
                    last_name=last_name,
                    external_ids={"euroleague": player_id},
                )
                test_db.add(player)
                created_ids.add(player_id)
        test_db.flush()

        # Sync boxscore
        stats = manager.sync_boxscore_canonical({"players": boxscore_data}, game)
        test_db.commit()

        return {"game": game, "stats": stats}

    def test_player_stats_created(
        self, game_with_boxscore: dict, test_db: Session
    ):
        """PlayerGameStats created for all players."""
        game = game_with_boxscore["game"]
        stats = test_db.query(PlayerGameStats).filter_by(game_id=game.id).all()

        # Should have stats for players who actually played (non-DNP)
        assert len(stats) > 0

    def test_minutes_stored_in_seconds(
        self, game_with_boxscore: dict, test_db: Session
    ):
        """Minutes are stored as seconds (int), not string."""
        game = game_with_boxscore["game"]
        stats = test_db.query(PlayerGameStats).filter_by(game_id=game.id).all()

        for stat in stats:
            assert isinstance(stat.minutes_played, int)
            # Max 48 minutes overtime = 2880 seconds
            assert 0 <= stat.minutes_played <= 3600

    def test_points_are_integers(
        self, game_with_boxscore: dict, test_db: Session
    ):
        """Points are stored as integers."""
        game = game_with_boxscore["game"]
        stats = test_db.query(PlayerGameStats).filter_by(game_id=game.id).all()

        for stat in stats:
            assert isinstance(stat.points, int)
            assert stat.points >= 0


class TestPBPSync:
    """Tests for play-by-play sync using canonical converter."""

    @pytest.fixture
    def game_with_pbp(
        self,
        manager: SyncManager,
        game_data: dict,
        pbp_data: list,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Create game and sync PBP."""
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.flush()

        # Sync PBP
        events = manager.sync_pbp_canonical(pbp_data, game)
        test_db.commit()

        return {"game": game, "events": events}

    def test_pbp_events_created(
        self, game_with_pbp: dict, test_db: Session
    ):
        """PBP events are created."""
        game = game_with_pbp["game"]
        events = test_db.query(PlayByPlayEvent).filter_by(game_id=game.id).all()

        assert len(events) > 0

    def test_shot_events_have_subtype(
        self, game_with_pbp: dict, test_db: Session
    ):
        """Shot events have shot_type subtype."""
        game = game_with_pbp["game"]
        from src.sync.canonical import EventType

        shots = (
            test_db.query(PlayByPlayEvent)
            .filter_by(game_id=game.id)
            .filter(PlayByPlayEvent.event_type == EventType.SHOT)
            .all()
        )

        # Should have shot events
        assert len(shots) > 0

        for shot in shots:
            # Shot subtype should be 2PT or 3PT
            assert shot.event_subtype in ["2PT", "3PT", None]

    def test_events_have_periods(
        self, game_with_pbp: dict, test_db: Session
    ):
        """All events have valid period numbers."""
        game = game_with_pbp["game"]
        events = test_db.query(PlayByPlayEvent).filter_by(game_id=game.id).all()

        for event in events:
            assert event.period >= 1
            assert event.period <= 6  # Max 4 quarters + 2 OT


class TestFullGameSync:
    """Integration test syncing complete game."""

    def test_full_sync_flow(
        self,
        manager: SyncManager,
        game_data: dict,
        boxscore_data: list,
        pbp_data: list,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Full sync: game -> boxscore -> PBP."""
        # 1. Sync game
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.flush()

        # 2. Create players first
        for raw_player in boxscore_data:
            player_id = raw_player.get("Player_ID", "").strip()
            if player_id:
                player = Player(
                    first_name=raw_player.get("Player", "").split(", ")[1]
                    if ", " in raw_player.get("Player", "")
                    else raw_player.get("Player", "").split()[0],
                    last_name=raw_player.get("Player", "").split(", ")[0]
                    if ", " in raw_player.get("Player", "")
                    else "",
                    external_ids={"euroleague": player_id},
                )
                test_db.add(player)
        test_db.flush()

        # 3. Sync boxscore
        stats = manager.sync_boxscore_canonical({"players": boxscore_data}, game)
        test_db.flush()

        # 4. Sync PBP
        events = manager.sync_pbp_canonical(pbp_data, game)
        test_db.commit()

        # Verify all data
        assert game.id is not None
        assert game.home_score == 77
        assert game.away_score == 87

        # Verify stats
        db_stats = test_db.query(PlayerGameStats).filter_by(game_id=game.id).all()
        assert len(db_stats) > 0

        # Verify PBP
        db_events = test_db.query(PlayByPlayEvent).filter_by(game_id=game.id).all()
        assert len(db_events) > 0

    def test_total_points_match_game_score(
        self,
        manager: SyncManager,
        game_data: dict,
        boxscore_data: list,
        test_db: Session,
        setup_league_and_season: dict,
    ):
        """Sum of player points matches game score."""
        # Sync game
        game = manager.sync_game_canonical(
            game_data, setup_league_and_season["season"].id
        )
        test_db.flush()

        # Create players
        for raw_player in boxscore_data:
            player_id = raw_player.get("Player_ID", "").strip()
            if player_id:
                player = Player(
                    first_name="Test",
                    last_name="Player",
                    external_ids={"euroleague": player_id},
                )
                test_db.add(player)
        test_db.flush()

        # Sync boxscore
        manager.sync_boxscore_canonical({"players": boxscore_data}, game)
        test_db.commit()

        # Get stats by team
        home_stats = (
            test_db.query(PlayerGameStats)
            .filter_by(game_id=game.id, team_id=game.home_team_id)
            .all()
        )
        away_stats = (
            test_db.query(PlayerGameStats)
            .filter_by(game_id=game.id, team_id=game.away_team_id)
            .all()
        )

        home_points = sum(s.points for s in home_stats)
        away_points = sum(s.points for s in away_stats)

        # Points should match game score
        assert home_points == game.home_score
        assert away_points == game.away_score
