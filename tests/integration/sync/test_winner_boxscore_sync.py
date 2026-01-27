"""
Integration tests for Winner League boxscore sync.

Tests the full boxscore sync pipeline including:
- PlayerGameStats record creation
- TeamGameStats record creation
- Stats validation (non-negative counts, valid ranges)
- Player name enrichment
- Correct game linkage

Addresses Issue #128: Sync game boxscores with player stats.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Player, PlayerGameStats, Season, Team
from src.models.game import TeamGameStats
from src.models.player import PlayerTeamHistory
from src.models.team import TeamSeason
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities.game import GameSyncer
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
    """Load real PBP fixture for player names."""
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
    """Create home team (Maccabi Tel Aviv - ID 2)."""
    team = Team(
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "2"},
    )
    db_session.add(team)
    db_session.commit()

    # Create TeamSeason link
    team_season = TeamSeason(
        team_id=team.id,
        season_id=sample_season.id,
        external_id="2",
    )
    db_session.add(team_season)
    db_session.commit()

    return team


@pytest.fixture
def away_team(db_session: Session, sample_season: Season) -> Team:
    """Create away team (Hapoel Jerusalem - ID 4)."""
    team = Team(
        name="Hapoel Jerusalem",
        short_name="HJM",
        city="Jerusalem",
        country="Israel",
        external_ids={"winner": "4"},
    )
    db_session.add(team)
    db_session.commit()

    # Create TeamSeason link
    team_season = TeamSeason(
        team_id=team.id,
        season_id=sample_season.id,
        external_id="4",
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
    mapper: WinnerMapper,
) -> Game:
    """Create a sample game from fixture data."""
    game = Game(
        season_id=sample_season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=mapper.parse_datetime("2025-09-21"),
        status="FINAL",
        home_score=79,
        away_score=84,
        external_ids={"winner": "24"},
    )
    db_session.add(game)
    db_session.commit()
    return game


@pytest.fixture
def game_syncer(db_session: Session) -> GameSyncer:
    """Create a GameSyncer instance."""
    team_matcher = TeamMatcher(db_session)
    player_dedup = PlayerDeduplicator(db_session)
    return GameSyncer(db_session, team_matcher, player_dedup)


@pytest.fixture(autouse=True)
def roster_players(
    db_session: Session,
    boxscore_fixture: dict,
    home_team: Team,
    away_team: Team,
    sample_season: Season,
) -> list[Player]:
    """Create roster players with jersey numbers from boxscore fixture.

    This fixture extracts player data from the boxscore and creates
    Player and PlayerTeamHistory records so jersey matching works.
    """
    boxscore = boxscore_fixture["result"]["boxscore"]
    players = []

    # Create home team players
    for p in boxscore["homeTeam"]["players"]:
        player = Player(
            first_name=f"Home{p['jerseyNumber']}",
            last_name="Player",
            external_ids={"winner": str(p["playerId"])},
        )
        db_session.add(player)
        db_session.flush()
        pth = PlayerTeamHistory(
            player_id=player.id,
            team_id=home_team.id,
            season_id=sample_season.id,
            jersey_number=int(p["jerseyNumber"]),
        )
        db_session.add(pth)
        players.append(player)

    # Create away team players
    for p in boxscore["awayTeam"]["players"]:
        player = Player(
            first_name=f"Away{p['jerseyNumber']}",
            last_name="Player",
            external_ids={"winner": str(p["playerId"])},
        )
        db_session.add(player)
        db_session.flush()
        pth = PlayerTeamHistory(
            player_id=player.id,
            team_id=away_team.id,
            season_id=sample_season.id,
            jersey_number=int(p["jerseyNumber"]),
        )
        db_session.add(pth)
        players.append(player)

    db_session.commit()
    return players


class TestSyncBoxscoreCreatesPlayerGameStats:
    """Test that sync_boxscore creates PlayerGameStats records."""

    def test_sync_boxscore_creates_player_game_stats(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """sync_boxscore should create PlayerGameStats for all players."""
        # Parse boxscore
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        # Sync boxscore
        player_stats, team_stats = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        # Verify PlayerGameStats were created
        assert len(player_stats) > 0

        # Should match total players in boxscore
        expected_count = len(raw_boxscore.home_players) + len(raw_boxscore.away_players)
        assert len(player_stats) == expected_count

        # Verify records are in database
        db_stats = db_session.query(PlayerGameStats).all()
        assert len(db_stats) == expected_count

    def test_player_game_stats_linked_to_game(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """All PlayerGameStats should be linked to the correct game."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        for stats in player_stats:
            assert stats.game_id == sample_game.id

    def test_player_game_stats_have_valid_team_id(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        home_team: Team,
        away_team: Team,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """PlayerGameStats should have valid team_id (home or away)."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        valid_team_ids = {home_team.id, away_team.id}
        for stats in player_stats:
            assert stats.team_id in valid_team_ids


class TestSyncBoxscoreCreatesTeamGameStats:
    """Test that sync_boxscore creates TeamGameStats records."""

    def test_sync_boxscore_creates_team_game_stats(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """sync_boxscore should create TeamGameStats for both teams."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        _, team_stats = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        # Should have 2 team stats (home and away)
        assert len(team_stats) == 2

        # Verify records are in database
        db_stats = db_session.query(TeamGameStats).all()
        assert len(db_stats) == 2

    def test_team_game_stats_has_home_and_away(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """TeamGameStats should have one home and one away record."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        _, team_stats = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        home_stats = [s for s in team_stats if s.is_home is True]
        away_stats = [s for s in team_stats if s.is_home is False]

        assert len(home_stats) == 1
        assert len(away_stats) == 1

    def test_team_game_stats_linked_to_game(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """TeamGameStats should be linked to correct game."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        _, team_stats = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        for stats in team_stats:
            assert stats.game_id == sample_game.id

    def test_team_game_stats_aggregates_player_stats(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """TeamGameStats should aggregate player stats correctly."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, team_stats = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        # Get home team stats
        home_team_stats = next(s for s in team_stats if s.is_home is True)
        home_player_stats = [
            s for s in player_stats if s.team_id == sample_game.home_team_id
        ]

        # Sum player points
        player_points_sum = sum(s.points for s in home_player_stats)

        # Team points should equal sum of player points
        assert home_team_stats.points == player_points_sum


class TestSyncBoxscoreAllPlayersHaveStats:
    """Test that all players from boxscore have stats records."""

    def test_all_players_have_stats(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Every player in boxscore should have a PlayerGameStats record."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        # Get all external IDs from boxscore
        boxscore_player_ids = set()
        for p in raw_boxscore.home_players:
            boxscore_player_ids.add(p.player_external_id)
        for p in raw_boxscore.away_players:
            boxscore_player_ids.add(p.player_external_id)

        # Get all players with stats
        players_with_stats = db_session.query(Player).join(PlayerGameStats).all()

        # Should have same count (allowing for dedup)
        assert len(players_with_stats) >= 1
        assert len(player_stats) == len(boxscore_player_ids)


class TestSyncBoxscoreStatsAreValid:
    """Test that synced stats have valid values."""

    def test_stats_have_non_negative_counts(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Count stats should be non-negative (except plus_minus)."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        for stats in player_stats:
            assert stats.points >= 0, "Points should be non-negative"
            assert stats.minutes_played >= 0, "Minutes should be non-negative"
            assert stats.field_goals_made >= 0, "FGM should be non-negative"
            assert stats.field_goals_attempted >= 0, "FGA should be non-negative"
            assert stats.offensive_rebounds >= 0, "OReb should be non-negative"
            assert stats.defensive_rebounds >= 0, "DReb should be non-negative"
            assert stats.assists >= 0, "Assists should be non-negative"
            assert stats.turnovers >= 0, "Turnovers should be non-negative"
            assert stats.steals >= 0, "Steals should be non-negative"
            assert stats.blocks >= 0, "Blocks should be non-negative"
            assert stats.personal_fouls >= 0, "Fouls should be non-negative"

    def test_made_does_not_exceed_attempted(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Made shots should not exceed attempted shots."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        for stats in player_stats:
            assert stats.field_goals_made <= stats.field_goals_attempted
            assert stats.two_pointers_made <= stats.two_pointers_attempted
            assert stats.three_pointers_made <= stats.three_pointers_attempted
            assert stats.free_throws_made <= stats.free_throws_attempted

    def test_total_rebounds_equals_sum(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Total rebounds should equal offensive + defensive."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        for stats in player_stats:
            expected = stats.offensive_rebounds + stats.defensive_rebounds
            assert stats.total_rebounds == expected

    def test_points_calculation_valid(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Points should equal 2*2PT + 3*3PT + FT."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        for stats in player_stats:
            calculated = (
                stats.two_pointers_made * 2
                + stats.three_pointers_made * 3
                + stats.free_throws_made
            )
            assert (
                stats.points == calculated
            ), f"Points mismatch: {stats.points} != {calculated}"


class TestBoxscorePlayerNamesNotEmpty:
    """Test that player names are populated after enrichment."""

    def test_boxscore_enriched_with_names_from_pbp(
        self,
        mapper: WinnerMapper,
        boxscore_fixture: dict,
        pbp_fixture: dict,
    ) -> None:
        """Boxscore should have player names after PBP enrichment."""
        # Parse boxscore (no names initially)
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        # Verify no names initially
        for p in raw_boxscore.home_players:
            assert p.player_name == ""

        # Extract roster from PBP
        roster = mapper.extract_player_roster(pbp_fixture)

        # Enrich boxscore
        enriched = mapper.enrich_boxscore_with_names(raw_boxscore, roster)

        # Verify names are now present
        players_with_names = 0
        for p in enriched.home_players:
            if p.player_name:
                players_with_names += 1

        # Most players should have names (some may be missing from roster)
        assert players_with_names > 0

    def test_enriched_names_match_pbp_roster(
        self,
        mapper: WinnerMapper,
        boxscore_fixture: dict,
        pbp_fixture: dict,
    ) -> None:
        """Enriched player names should match PBP roster data."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)
        roster = mapper.extract_player_roster(pbp_fixture)
        enriched = mapper.enrich_boxscore_with_names(raw_boxscore, roster)

        # Player 1019 should be "ROMAN SORKIN"
        player_1019 = next(
            (p for p in enriched.home_players if p.player_external_id == "1019"), None
        )
        if player_1019:
            assert player_1019.player_name == "ROMAN SORKIN"


class TestBoxscoreLinkedToCorrectGame:
    """Test that stats are linked to the correct game."""

    def test_stats_reference_correct_game_id(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """All stats should reference the correct game_id."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        player_stats, team_stats = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        # All player stats should reference correct game
        for stats in player_stats:
            assert stats.game_id == sample_game.id

        # All team stats should reference correct game
        for stats in team_stats:
            assert stats.game_id == sample_game.id

    def test_game_relationship_works(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Stats should be accessible via game relationship."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        # Refresh game to load relationships
        db_session.refresh(sample_game)

        # Game should have player_game_stats
        assert len(sample_game.player_game_stats) > 0

        # Game should have team_game_stats
        assert len(sample_game.team_game_stats) == 2

    def test_resync_replaces_stats(
        self,
        db_session: Session,
        game_syncer: GameSyncer,
        sample_game: Game,
        boxscore_fixture: dict,
        mapper: WinnerMapper,
    ) -> None:
        """Re-syncing should replace existing stats, not duplicate."""
        raw_boxscore = mapper.map_boxscore(boxscore_fixture)

        # First sync
        player_stats_1, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        count_1 = (
            db_session.query(PlayerGameStats).filter_by(game_id=sample_game.id).count()
        )

        # Second sync (same boxscore)
        player_stats_2, _ = game_syncer.sync_boxscore(raw_boxscore, sample_game)
        db_session.commit()

        count_2 = (
            db_session.query(PlayerGameStats).filter_by(game_id=sample_game.id).count()
        )

        # Count should be the same (replaced, not duplicated)
        assert count_1 == count_2
