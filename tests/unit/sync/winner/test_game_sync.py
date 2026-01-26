"""
Winner Game Sync Unit Tests

Tests for syncing game data from Winner League API to the database.

Tests cover:
- Creating game records from raw data
- Skipping duplicate games (same external_id)
- Resolving team external IDs to Team records
"""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.team import Team
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities import GameSyncer
from src.sync.types import RawGame


@pytest.fixture
def league(test_db: Session) -> League:
    """Create a test league for Winner."""
    league = League(
        id=uuid4(),
        name="Winner League",
        code="WNR",
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
        name="2025-26",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 30),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def maccabi_team(test_db: Session) -> Team:
    """Create Maccabi Tel-Aviv team."""
    team = Team(
        id=uuid4(),
        name="Maccabi Tel-Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "1109"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def hapoel_jerusalem_team(test_db: Session) -> Team:
    """Create Hapoel Jerusalem team."""
    team = Team(
        id=uuid4(),
        name="Hapoel Jerusalem",
        short_name="HPJ",
        city="Jerusalem",
        country="Israel",
        external_ids={"winner": "1112"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def team_matcher(test_db: Session) -> TeamMatcher:
    """Create a TeamMatcher instance."""
    return TeamMatcher(test_db)


@pytest.fixture
def player_deduplicator(test_db: Session) -> PlayerDeduplicator:
    """Create a PlayerDeduplicator instance."""
    return PlayerDeduplicator(test_db)


@pytest.fixture
def game_syncer(
    test_db: Session, team_matcher: TeamMatcher, player_deduplicator: PlayerDeduplicator
) -> GameSyncer:
    """Create a GameSyncer instance."""
    return GameSyncer(test_db, team_matcher, player_deduplicator)


@pytest.fixture
def raw_game_from_api() -> RawGame:
    """Create a RawGame based on real Winner API data."""
    return RawGame(
        external_id="24",
        home_team_external_id="1109",
        away_team_external_id="1112",
        game_date=datetime(2025, 9, 21, 21, 5, tzinfo=UTC),
        status="final",
        home_score=79,
        away_score=84,
    )


class TestSyncGameCreatesRecord:
    """Tests for GameSyncer.sync_game creating database records."""

    def test_creates_game_record(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
        test_db: Session,
    ) -> None:
        """Test that sync_game creates a Game record in the database."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")
        test_db.commit()

        # Verify game was created
        assert game is not None
        assert game.id is not None

        # Verify in database
        db_game = test_db.query(Game).filter_by(id=game.id).first()
        assert db_game is not None

    def test_stores_season_id(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that season_id is stored correctly."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.season_id == season.id

    def test_stores_game_date(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that game_date is stored correctly."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.game_date.year == 2025
        assert game.game_date.month == 9
        assert game.game_date.day == 21

    def test_stores_scores(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that home_score and away_score are stored correctly."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.home_score == 79
        assert game.away_score == 84

    def test_stores_status_uppercase(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that status is stored in uppercase."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.status == "FINAL"

    def test_stores_external_id(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that external_id is stored in external_ids JSON field."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.external_ids.get("winner") == "24"

    def test_stores_home_team_id(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that home_team_id references correct Team."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.home_team_id == maccabi_team.id

    def test_stores_away_team_id(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that away_team_id references correct Team."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game.away_team_id == hapoel_jerusalem_team.id


class TestSyncGameSkipsDuplicate:
    """Tests for skipping duplicate games based on external_id."""

    def test_returns_existing_game_on_resync(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
        test_db: Session,
    ) -> None:
        """Test that syncing same external_id returns existing game."""
        # First sync
        game1 = game_syncer.sync_game(raw_game_from_api, season.id, "winner")
        test_db.commit()
        game1_id = game1.id

        # Second sync with same external_id
        game2 = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        assert game2.id == game1_id

    def test_does_not_create_duplicate(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
        test_db: Session,
    ) -> None:
        """Test that syncing twice doesn't create duplicate records."""
        # First sync
        game_syncer.sync_game(raw_game_from_api, season.id, "winner")
        test_db.commit()

        initial_count = test_db.query(Game).count()

        # Second sync
        game_syncer.sync_game(raw_game_from_api, season.id, "winner")
        test_db.commit()

        final_count = test_db.query(Game).count()

        assert final_count == initial_count

    def test_updates_score_on_resync(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
        test_db: Session,
    ) -> None:
        """Test that re-syncing updates scores (for live game updates)."""
        # First sync
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")
        test_db.commit()

        # Modify raw data (simulating live score update)
        raw_game_from_api.home_score = 85
        raw_game_from_api.away_score = 90

        # Re-sync
        updated_game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")
        test_db.commit()

        assert updated_game.id == game.id
        assert updated_game.home_score == 85
        assert updated_game.away_score == 90

    def test_multiple_different_games_created(
        self,
        game_syncer: GameSyncer,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
        test_db: Session,
    ) -> None:
        """Test that different external_ids create separate games."""
        game1 = RawGame(
            external_id="24",
            home_team_external_id="1109",
            away_team_external_id="1112",
            game_date=datetime(2025, 9, 21, tzinfo=UTC),
            status="final",
            home_score=79,
            away_score=84,
        )
        game2 = RawGame(
            external_id="47",
            home_team_external_id="1112",
            away_team_external_id="1109",
            game_date=datetime(2025, 10, 12, tzinfo=UTC),
            status="final",
            home_score=90,
            away_score=88,
        )

        synced_game1 = game_syncer.sync_game(game1, season.id, "winner")
        synced_game2 = game_syncer.sync_game(game2, season.id, "winner")
        test_db.commit()

        assert synced_game1.id != synced_game2.id
        assert test_db.query(Game).count() == 2


class TestSyncGameResolvesTeams:
    """Tests for resolving team external IDs to Team records."""

    def test_resolves_home_team_by_external_id(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that home team is resolved by winner external_id."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        # Maccabi has external_ids={"winner": "1109"}
        # raw_game has home_team_external_id="1109"
        assert game.home_team_id == maccabi_team.id

    def test_resolves_away_team_by_external_id(
        self,
        game_syncer: GameSyncer,
        raw_game_from_api: RawGame,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that away team is resolved by winner external_id."""
        game = game_syncer.sync_game(raw_game_from_api, season.id, "winner")

        # Hapoel Jerusalem has external_ids={"winner": "1112"}
        # raw_game has away_team_external_id="1112"
        assert game.away_team_id == hapoel_jerusalem_team.id

    def test_raises_when_home_team_not_found(
        self,
        game_syncer: GameSyncer,
        season: Season,
        hapoel_jerusalem_team: Team,  # Only away team exists
    ) -> None:
        """Test ValueError raised when home team not found."""
        raw_game = RawGame(
            external_id="99",
            home_team_external_id="9999",  # Doesn't exist
            away_team_external_id="1112",
            game_date=datetime(2025, 9, 21, tzinfo=UTC),
            status="final",
        )

        with pytest.raises(ValueError, match="Teams not found"):
            game_syncer.sync_game(raw_game, season.id, "winner")

    def test_raises_when_away_team_not_found(
        self,
        game_syncer: GameSyncer,
        season: Season,
        maccabi_team: Team,  # Only home team exists
    ) -> None:
        """Test ValueError raised when away team not found."""
        raw_game = RawGame(
            external_id="99",
            home_team_external_id="1109",
            away_team_external_id="9999",  # Doesn't exist
            game_date=datetime(2025, 9, 21, tzinfo=UTC),
            status="final",
        )

        with pytest.raises(ValueError, match="Teams not found"):
            game_syncer.sync_game(raw_game, season.id, "winner")

    def test_raises_when_both_teams_not_found(
        self,
        game_syncer: GameSyncer,
        season: Season,
        test_db: Session,
    ) -> None:
        """Test ValueError raised when neither team exists."""
        raw_game = RawGame(
            external_id="99",
            home_team_external_id="9998",
            away_team_external_id="9999",
            game_date=datetime(2025, 9, 21, tzinfo=UTC),
            status="final",
        )

        with pytest.raises(ValueError, match="Teams not found"):
            game_syncer.sync_game(raw_game, season.id, "winner")


class TestSyncGameWithScheduledStatus:
    """Tests for syncing scheduled (future) games."""

    def test_syncs_scheduled_game_with_null_scores(
        self,
        game_syncer: GameSyncer,
        season: Season,
        maccabi_team: Team,
        hapoel_jerusalem_team: Team,
    ) -> None:
        """Test that scheduled games with null scores are synced."""
        raw_game = RawGame(
            external_id="100",
            home_team_external_id="1109",
            away_team_external_id="1112",
            game_date=datetime(2026, 3, 15, 20, 0, tzinfo=UTC),
            status="scheduled",
            home_score=None,
            away_score=None,
        )

        game = game_syncer.sync_game(raw_game, season.id, "winner")

        assert game.status == "SCHEDULED"
        assert game.home_score is None
        assert game.away_score is None
        assert game.game_date.year == 2026
        assert game.game_date.month == 3
        assert game.game_date.day == 15
