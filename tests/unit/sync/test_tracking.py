"""
Tests for the SyncTracker class.

Tests cover:
- Checking if games are synced (new vs already synced)
- Filtering unsynced games from a list
- Marking games as synced
- Getting games by external ID
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.team import Team
from src.sync.tracking import SyncTracker


@pytest.fixture
def league(test_db: Session) -> League:
    """Create a test league."""
    league = League(
        id=uuid4(),
        name="Test League",
        code="TST",
        country="Test Country",
    )
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def season(test_db: Session, league: League) -> Season:
    """Create a test season."""
    from datetime import date

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
        name="Home Team",
        short_name="HOM",
        city="Home City",
        country="Test Country",
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def away_team(test_db: Session) -> Team:
    """Create an away team."""
    team = Team(
        id=uuid4(),
        name="Away Team",
        short_name="AWY",
        city="Away City",
        country="Test Country",
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def game_with_external_id(
    test_db: Session, season: Season, home_team: Team, away_team: Team
) -> Game:
    """Create a game with an external ID."""
    game = Game(
        id=uuid4(),
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
        status="FINAL",
        home_score=100,
        away_score=95,
        external_ids={"winner": "game-123", "euroleague": "EL-456"},
    )
    test_db.add(game)
    test_db.commit()
    return game


@pytest.fixture
def game_without_external_id(
    test_db: Session, season: Season, home_team: Team, away_team: Team
) -> Game:
    """Create a game without external IDs."""
    game = Game(
        id=uuid4(),
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=datetime(2024, 12, 20, 19, 30, tzinfo=UTC),
        status="SCHEDULED",
        external_ids={},
    )
    test_db.add(game)
    test_db.commit()
    return game


@pytest.fixture
def tracker(test_db: Session) -> SyncTracker:
    """Create a SyncTracker instance."""
    return SyncTracker(test_db)


class TestIsGameSynced:
    """Tests for SyncTracker.is_game_synced method."""

    def test_returns_true_for_synced_game(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return True when game has external_id for source."""
        result = tracker.is_game_synced("winner", "game-123")
        assert result is True

    def test_returns_false_for_unsynced_game(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return False when no game has the external_id."""
        result = tracker.is_game_synced("winner", "game-999")
        assert result is False

    def test_returns_false_for_different_source(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return False when checking wrong source."""
        result = tracker.is_game_synced("nba", "game-123")
        assert result is False

    def test_returns_false_when_no_games_exist(self, tracker: SyncTracker) -> None:
        """Should return False when no games in database."""
        result = tracker.is_game_synced("winner", "game-123")
        assert result is False


class TestGetUnsyncedGames:
    """Tests for SyncTracker.get_unsynced_games method."""

    def test_filters_synced_games(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should filter out already synced game IDs."""
        external_ids = ["game-123", "game-456", "game-789"]
        result = tracker.get_unsynced_games("winner", external_ids)

        assert "game-123" not in result
        assert "game-456" in result
        assert "game-789" in result

    def test_returns_all_when_none_synced(self, tracker: SyncTracker) -> None:
        """Should return all IDs when none are synced."""
        external_ids = ["game-1", "game-2", "game-3"]
        result = tracker.get_unsynced_games("winner", external_ids)

        assert result == external_ids

    def test_returns_empty_when_all_synced(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return empty list when all games are synced."""
        external_ids = ["game-123"]
        result = tracker.get_unsynced_games("winner", external_ids)

        assert result == []

    def test_handles_empty_input(self, tracker: SyncTracker) -> None:
        """Should return empty list for empty input."""
        result = tracker.get_unsynced_games("winner", [])
        assert result == []

    def test_different_source_returns_all(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return all IDs when checking different source."""
        external_ids = ["game-123", "game-456"]
        result = tracker.get_unsynced_games("nba", external_ids)

        # All should be returned since none are synced for "nba" source
        assert "game-123" in result
        assert "game-456" in result


class TestMarkGameSynced:
    """Tests for SyncTracker.mark_game_synced method."""

    def test_adds_external_id_to_game(
        self,
        tracker: SyncTracker,
        game_without_external_id: Game,
        test_db: Session,
    ) -> None:
        """Should add external_id to game's external_ids."""
        tracker.mark_game_synced("winner", "new-game-123", game_without_external_id.id)
        test_db.refresh(game_without_external_id)

        assert game_without_external_id.external_ids.get("winner") == "new-game-123"

    def test_preserves_existing_external_ids(
        self,
        tracker: SyncTracker,
        game_with_external_id: Game,
        test_db: Session,
    ) -> None:
        """Should preserve existing external_ids when adding new one."""
        tracker.mark_game_synced("nba", "nba-789", game_with_external_id.id)
        test_db.refresh(game_with_external_id)

        assert game_with_external_id.external_ids.get("winner") == "game-123"
        assert game_with_external_id.external_ids.get("euroleague") == "EL-456"
        assert game_with_external_id.external_ids.get("nba") == "nba-789"

    def test_updates_existing_external_id(
        self,
        tracker: SyncTracker,
        game_with_external_id: Game,
        test_db: Session,
    ) -> None:
        """Should update external_id if source already exists."""
        tracker.mark_game_synced("winner", "updated-123", game_with_external_id.id)
        test_db.refresh(game_with_external_id)

        assert game_with_external_id.external_ids.get("winner") == "updated-123"

    def test_raises_for_nonexistent_game(self, tracker: SyncTracker) -> None:
        """Should raise ValueError for non-existent game ID."""
        fake_id = uuid4()
        with pytest.raises(ValueError, match=f"Game with id {fake_id} not found"):
            tracker.mark_game_synced("winner", "game-123", fake_id)


class TestGetGameByExternalId:
    """Tests for SyncTracker.get_game_by_external_id method."""

    def test_returns_game_when_found(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return game when external_id exists."""
        result = tracker.get_game_by_external_id("winner", "game-123")

        assert result is not None
        assert result.id == game_with_external_id.id

    def test_returns_none_when_not_found(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return None when external_id not found."""
        result = tracker.get_game_by_external_id("winner", "nonexistent")
        assert result is None

    def test_returns_none_for_wrong_source(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return None when source doesn't match."""
        result = tracker.get_game_by_external_id("nba", "game-123")
        assert result is None


class TestGetExternalId:
    """Tests for SyncTracker.get_external_id method."""

    def test_returns_external_id_when_present(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return external_id when present."""
        result = tracker.get_external_id(game_with_external_id, "winner")
        assert result == "game-123"

    def test_returns_none_when_not_present(
        self, tracker: SyncTracker, game_with_external_id: Game
    ) -> None:
        """Should return None when source not in external_ids."""
        result = tracker.get_external_id(game_with_external_id, "nba")
        assert result is None

    def test_returns_none_for_empty_external_ids(
        self, tracker: SyncTracker, game_without_external_id: Game
    ) -> None:
        """Should return None when external_ids is empty."""
        result = tracker.get_external_id(game_without_external_id, "winner")
        assert result is None
