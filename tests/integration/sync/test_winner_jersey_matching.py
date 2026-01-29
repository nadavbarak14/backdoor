"""
Integration tests for Winner League jersey number matching.

Tests that player matching works correctly when segevstats API returns
different internal IDs than basket.co.il external IDs. The only reliable
way to match players is via jersey numbers on the team roster.

This is the critical path that was broken:
1. Players are created with basket.co.il external_ids (e.g., "15421")
2. Segevstats boxscore/PBP uses different internal IDs (e.g., "1019")
3. Players must be matched by jersey number on the roster

Addresses the sync issue where 0 PlayerGameStats were being created.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Player, PlayerGameStats, Season, Team
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import PlayerTeamHistory
from src.models.team import TeamSeason
from src.sync.canonical import CanonicalPlayerStats, CanonicalPBPEvent
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities.game import GameSyncer
from src.sync.entities.player import PlayerSyncer
from src.sync.winner.mapper import WinnerMapper

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


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
def mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def boxscore_fixture() -> dict:
    """Load real segevstats boxscore fixture."""
    path = FIXTURES_DIR / "boxscore.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pbp_fixture() -> dict:
    """Load real PBP fixture."""
    path = FIXTURES_DIR / "pbp.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_league(db_session: Session) -> League:
    """Create a sample league for testing."""
    league = League(name="Winner League", code="WINNER", country="Israel")
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def sample_season(db_session: Session, sample_league: League) -> Season:
    """Create a sample season for testing."""
    season = Season(
        league_id=sample_league.id,
        name="2025-26",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 30),
        is_current=True,
    )
    db_session.add(season)
    db_session.commit()
    return season


@pytest.fixture
def home_team(db_session: Session, sample_season: Season) -> Team:
    """Create home team with basket.co.il ID (1109, not segevstats ID 2)."""
    team = Team(
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        # Real basket.co.il ID, NOT segevstats internal ID
        external_ids={"winner": "1109"},
    )
    db_session.add(team)
    db_session.commit()

    # Create TeamSeason link with basket.co.il ID
    team_season = TeamSeason(
        team_id=team.id,
        season_id=sample_season.id,
        external_id="1109",  # basket.co.il ID
    )
    db_session.add(team_season)
    db_session.commit()

    return team


@pytest.fixture
def away_team(db_session: Session, sample_season: Season) -> Team:
    """Create away team with basket.co.il ID (1112, not segevstats ID 4)."""
    team = Team(
        name="Hapoel Jerusalem",
        short_name="HJM",
        city="Jerusalem",
        country="Israel",
        # Real basket.co.il ID, NOT segevstats internal ID
        external_ids={"winner": "1112"},
    )
    db_session.add(team)
    db_session.commit()

    # Create TeamSeason link with basket.co.il ID
    team_season = TeamSeason(
        team_id=team.id,
        season_id=sample_season.id,
        external_id="1112",  # basket.co.il ID
    )
    db_session.add(team_season)
    db_session.commit()

    return team


@pytest.fixture
def sample_game(
    db_session: Session,
    sample_season: Season,
    home_team: Team,
    away_team: Team,
) -> Game:
    """Create a sample game."""
    game = Game(
        season_id=sample_season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=date(2025, 9, 21),
        status="FINAL",
        home_score=79,
        away_score=84,
        external_ids={"winner": "24"},
    )
    db_session.add(game)
    db_session.commit()
    return game


@pytest.fixture
def players_with_basket_ids(
    db_session: Session,
    boxscore_fixture: dict,
    home_team: Team,
    away_team: Team,
    sample_season: Season,
) -> list[Player]:
    """Create players with basket.co.il external IDs (NOT segevstats IDs).

    This simulates real-world scenario where:
    - Players exist with basket.co.il external_ids like "15421"
    - Segevstats boxscore uses internal IDs like "1019"
    - Jersey numbers are the only way to match them
    """
    boxscore = boxscore_fixture["result"]["boxscore"]
    players = []

    # Create home team players with BASKET.CO.IL style IDs (different from segevstats)
    for idx, p in enumerate(boxscore["homeTeam"]["players"]):
        segevstats_id = str(p["playerId"])
        jersey = int(p["jerseyNumber"])

        # Use a basket.co.il style ID - different from segevstats ID
        basket_id = f"BC{15000 + idx}"

        player = Player(
            first_name=f"HomePlayer{jersey}",
            last_name="Test",
            external_ids={"winner": basket_id},  # basket.co.il ID, NOT segevstats
        )
        db_session.add(player)
        db_session.flush()

        # Create roster entry with jersey number - this is how we match!
        pth = PlayerTeamHistory(
            player_id=player.id,
            team_id=home_team.id,
            season_id=sample_season.id,
            jersey_number=jersey,
        )
        db_session.add(pth)
        players.append(player)

    # Create away team players with basket.co.il style IDs
    for idx, p in enumerate(boxscore["awayTeam"]["players"]):
        segevstats_id = str(p["playerId"])
        jersey = int(p["jerseyNumber"])

        basket_id = f"BC{16000 + idx}"

        player = Player(
            first_name=f"AwayPlayer{jersey}",
            last_name="Test",
            external_ids={"winner": basket_id},  # basket.co.il ID, NOT segevstats
        )
        db_session.add(player)
        db_session.flush()

        pth = PlayerTeamHistory(
            player_id=player.id,
            team_id=away_team.id,
            season_id=sample_season.id,
            jersey_number=jersey,
        )
        db_session.add(pth)
        players.append(player)

    db_session.commit()
    return players


@pytest.fixture
def game_syncer(db_session: Session) -> GameSyncer:
    """Create a GameSyncer instance."""
    team_matcher = TeamMatcher(db_session)
    player_dedup = PlayerDeduplicator(db_session)
    return GameSyncer(db_session, team_matcher, player_dedup)


@pytest.fixture
def player_syncer(db_session: Session) -> PlayerSyncer:
    """Create a PlayerSyncer instance."""
    player_dedup = PlayerDeduplicator(db_session)
    return PlayerSyncer(db_session, player_dedup)


class TestBoxscoreJerseyMatching:
    """Test boxscore sync matches players via jersey number."""

    def test_boxscore_matches_players_by_jersey(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        home_team: Team,
        away_team: Team,
        players_with_basket_ids: list[Player],
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Boxscore should match players by jersey when external IDs differ.

        This tests the critical path:
        1. Players exist with basket.co.il IDs (BC15000, BC15001, etc.)
        2. Boxscore has segevstats IDs (1019, 1020, etc.)
        3. Match should happen via jersey number
        4. PlayerGameStats should be created with correct player_id
        """
        # Parse boxscore
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        # Convert to canonical format with CORRECT team IDs from schedule
        from src.sync.raw_to_canonical import raw_boxscore_to_canonical_stats
        canonical_stats, jersey_numbers = raw_boxscore_to_canonical_stats(
            raw_boxscore,
            home_team_external_id="1109",  # basket.co.il ID
            away_team_external_id="1112",  # basket.co.il ID
        )

        # Sync boxscore with jersey numbers for matching
        player_stats, team_stats = game_syncer.sync_boxscore_from_canonical(
            canonical_stats,
            sample_game,
            "winner",
            jersey_numbers=jersey_numbers,
        )
        db_session.commit()

        # Verify stats were created
        assert len(player_stats) > 0, "Should have created PlayerGameStats"

        # Verify players were matched (player_id should be set)
        matched_stats = [s for s in player_stats if s.player_id is not None]
        total_stats = len(player_stats)

        # All stats should have player_id (matched via jersey)
        assert len(matched_stats) == total_stats, (
            f"Only {len(matched_stats)}/{total_stats} stats have player_id. "
            "Jersey matching may have failed."
        )

    def test_stats_linked_to_correct_players(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        home_team: Team,
        away_team: Team,
        players_with_basket_ids: list[Player],
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Stats should be linked to the correct players via player_id."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        from src.sync.raw_to_canonical import raw_boxscore_to_canonical_stats
        canonical_stats, jersey_numbers = raw_boxscore_to_canonical_stats(
            raw_boxscore,
            home_team_external_id="1109",
            away_team_external_id="1112",
        )

        player_stats, team_stats = game_syncer.sync_boxscore_from_canonical(
            canonical_stats,
            sample_game,
            "winner",
            jersey_numbers=jersey_numbers,
        )
        db_session.commit()

        # Verify each stat references a valid Player that exists
        for stat in player_stats:
            assert stat.player_id is not None
            player = db_session.get(Player, stat.player_id)
            assert player is not None, f"player_id {stat.player_id} doesn't exist"
            # Player should have a basket.co.il style ID
            winner_id = player.external_ids.get("winner", "")
            assert winner_id.startswith("BC"), (
                f"Player {player.id} has winner ID {winner_id}, "
                "expected basket.co.il style ID starting with BC"
            )


class TestPBPJerseyMatching:
    """Test PBP sync matches players via jersey number."""

    def test_pbp_matches_players_by_jersey(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        home_team: Team,
        away_team: Team,
        players_with_basket_ids: list[Player],
        pbp_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """PBP should match players by jersey when external IDs differ.

        This tests that:
        1. PBP events have segevstats player IDs
        2. Players exist with different basket.co.il IDs
        3. player_id_to_jersey mapping is used to match
        4. PlayByPlayEvent records have correct player_id
        """
        # Parse PBP and get player_id_to_jersey mapping
        raw_events = mapper.map_pbp_events(pbp_fixture)
        player_id_to_jersey = mapper.extract_player_id_to_jersey(pbp_fixture)

        # Convert to canonical format with correct team IDs
        from src.sync.raw_to_canonical import raw_pbp_list_to_canonical
        team_id_map = {
            "2": "1109",  # segevstats home -> basket.co.il
            "4": "1112",  # segevstats away -> basket.co.il
        }
        canonical_events = raw_pbp_list_to_canonical(raw_events, team_id_map=team_id_map)

        # Sync PBP with jersey mapping
        pbp_events = game_syncer.sync_pbp_from_canonical(
            canonical_events,
            sample_game,
            "winner",
            player_id_to_jersey=player_id_to_jersey,
        )
        db_session.commit()

        # Verify events were created
        assert len(pbp_events) > 0, "Should have created PlayByPlayEvents"

        # Count events that have player_id (many events like timeouts won't have players)
        events_with_player = [e for e in canonical_events if e.player_external_id]
        matched_events = [e for e in pbp_events if e.player_id is not None]

        # At least 80% of events with player external IDs should have matched
        expected_matches = int(len(events_with_player) * 0.8)
        assert len(matched_events) >= expected_matches, (
            f"Only {len(matched_events)} events have player_id, "
            f"expected at least {expected_matches} based on {len(events_with_player)} "
            "events with player_external_id"
        )

    def test_pbp_events_have_correct_teams(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        home_team: Team,
        away_team: Team,
        players_with_basket_ids: list[Player],
        pbp_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """PBP events should have correct team_id after ID mapping."""
        raw_events = mapper.map_pbp_events(pbp_fixture)
        player_id_to_jersey = mapper.extract_player_id_to_jersey(pbp_fixture)

        from src.sync.raw_to_canonical import raw_pbp_list_to_canonical
        team_id_map = {
            "2": "1109",
            "4": "1112",
        }
        canonical_events = raw_pbp_list_to_canonical(raw_events, team_id_map=team_id_map)

        pbp_events = game_syncer.sync_pbp_from_canonical(
            canonical_events,
            sample_game,
            "winner",
            player_id_to_jersey=player_id_to_jersey,
        )
        db_session.commit()

        # Verify team IDs are correct (should be home or away team)
        valid_team_ids = {home_team.id, away_team.id}
        events_with_teams = [e for e in pbp_events if e.team_id is not None]

        for event in events_with_teams:
            assert event.team_id in valid_team_ids, (
                f"Event {event.id} has invalid team_id {event.team_id}"
            )


class TestFullSyncWithJerseyMatching:
    """Test complete sync flow with jersey matching."""

    def test_full_game_sync_creates_all_records(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        home_team: Team,
        away_team: Team,
        players_with_basket_ids: list[Player],
        boxscore_fixture: dict,
        pbp_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Full sync should create all records with correct player matches."""
        # 1. Sync boxscore
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        from src.sync.raw_to_canonical import (
            raw_boxscore_to_canonical_stats,
            raw_pbp_list_to_canonical,
        )

        canonical_stats, jersey_numbers = raw_boxscore_to_canonical_stats(
            raw_boxscore,
            home_team_external_id="1109",
            away_team_external_id="1112",
        )

        player_stats = game_syncer.sync_boxscore_from_canonical(
            canonical_stats,
            sample_game,
            "winner",
            jersey_numbers=jersey_numbers,
        )
        db_session.flush()

        # 2. Sync PBP
        raw_events = mapper.map_pbp_events(pbp_fixture)
        player_id_to_jersey = mapper.extract_player_id_to_jersey(pbp_fixture)

        team_id_map = {"2": "1109", "4": "1112"}
        canonical_events = raw_pbp_list_to_canonical(raw_events, team_id_map=team_id_map)

        pbp_events = game_syncer.sync_pbp_from_canonical(
            canonical_events,
            sample_game,
            "winner",
            player_id_to_jersey=player_id_to_jersey,
        )
        db_session.commit()

        # Verify all records created
        db_player_stats = db_session.query(PlayerGameStats).filter_by(
            game_id=sample_game.id
        ).all()
        db_pbp_events = db_session.query(PlayByPlayEvent).filter_by(
            game_id=sample_game.id
        ).all()

        assert len(db_player_stats) > 0, "Should have PlayerGameStats"
        assert len(db_pbp_events) > 0, "Should have PlayByPlayEvents"

        # Verify boxscore stats have player_id
        stats_with_player = [s for s in db_player_stats if s.player_id is not None]
        assert len(stats_with_player) == len(db_player_stats), (
            f"Only {len(stats_with_player)}/{len(db_player_stats)} stats have player_id"
        )

        # Verify PBP events have reasonable player_id coverage
        events_needing_player = [
            e for e in db_pbp_events
            if e.event_type in ("SHOT", "FREE_THROW", "REBOUND", "TURNOVER", "STEAL")
        ]
        events_with_player = [e for e in events_needing_player if e.player_id is not None]

        if len(events_needing_player) > 0:
            match_rate = len(events_with_player) / len(events_needing_player)
            assert match_rate >= 0.7, (
                f"Only {match_rate:.1%} of events have player_id, expected >= 70%"
            )
