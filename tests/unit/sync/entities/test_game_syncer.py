"""
Tests for the GameSyncer class.

Tests cover:
- Creating game records from raw data
- Syncing box scores (creating PlayerGameStats and TeamGameStats)
- Syncing play-by-play events with links
- Re-syncing (deleting old data first)
"""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats, TeamGameStats
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink
from src.models.player import Player
from src.models.team import Team
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities import GameSyncer
from src.sync.types import RawBoxScore, RawGame, RawPBPEvent, RawPlayerStats


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
        external_ids={"winner": "home-123"},
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
        external_ids={"winner": "away-456"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def home_player(test_db: Session) -> Player:
    """Create a home team player."""
    player = Player(
        id=uuid4(),
        first_name="Home",
        last_name="Player",
        external_ids={"winner": "hp-1"},
    )
    test_db.add(player)
    test_db.commit()
    return player


@pytest.fixture
def away_player(test_db: Session) -> Player:
    """Create an away team player."""
    player = Player(
        id=uuid4(),
        first_name="Away",
        last_name="Player",
        external_ids={"winner": "ap-1"},
    )
    test_db.add(player)
    test_db.commit()
    return player


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
def raw_game(home_team: Team, away_team: Team) -> RawGame:
    """Create a raw game."""
    return RawGame(
        external_id="game-999",
        home_team_external_id="home-123",
        away_team_external_id="away-456",
        game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
        status="final",
        home_score=100,
        away_score=95,
    )


@pytest.fixture
def raw_boxscore(raw_game: RawGame) -> RawBoxScore:
    """Create a raw boxscore."""
    home_stats = RawPlayerStats(
        player_external_id="hp-1",
        player_name="Home Player",
        team_external_id="home-123",
        minutes_played=1800,
        is_starter=True,
        points=25,
        field_goals_made=10,
        field_goals_attempted=20,
        three_pointers_made=3,
        three_pointers_attempted=8,
        free_throws_made=2,
        free_throws_attempted=2,
        total_rebounds=7,
        assists=5,
        turnovers=2,
        steals=1,
        blocks=1,
    )

    away_stats = RawPlayerStats(
        player_external_id="ap-1",
        player_name="Away Player",
        team_external_id="away-456",
        minutes_played=1500,
        is_starter=True,
        points=20,
        field_goals_made=8,
        field_goals_attempted=18,
        three_pointers_made=2,
        three_pointers_attempted=6,
        total_rebounds=5,
        assists=3,
    )

    return RawBoxScore(
        game=raw_game,
        home_players=[home_stats],
        away_players=[away_stats],
    )


class TestSyncGame:
    """Tests for GameSyncer.sync_game method."""

    def test_creates_new_game(
        self,
        game_syncer: GameSyncer,
        raw_game: RawGame,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should create a new game record."""
        game = game_syncer.sync_game(raw_game, season.id, "winner")

        assert game is not None
        assert game.season_id == season.id
        assert game.status == "FINAL"
        assert game.home_score == 100
        assert game.away_score == 95
        assert game.external_ids.get("winner") == "game-999"

    def test_raises_when_teams_not_found(
        self,
        game_syncer: GameSyncer,
        season: Season,
    ) -> None:
        """Should raise ValueError when teams don't exist."""
        raw_game = RawGame(
            external_id="game-bad",
            home_team_external_id="nonexistent-home",
            away_team_external_id="nonexistent-away",
            game_date=datetime(2024, 12, 15, 19, 30, tzinfo=UTC),
            status="final",
        )

        with pytest.raises(ValueError, match="Teams not found"):
            game_syncer.sync_game(raw_game, season.id, "winner")

    def test_updates_existing_game(
        self,
        game_syncer: GameSyncer,
        raw_game: RawGame,
        season: Season,
        home_team: Team,
        away_team: Team,
        test_db: Session,
    ) -> None:
        """Should update existing game when synced again."""
        # Create initial game
        game = game_syncer.sync_game(raw_game, season.id, "winner")
        game_id = game.id

        # Sync again with updated score
        raw_game.home_score = 105
        raw_game.away_score = 100

        updated_game = game_syncer.sync_game(raw_game, season.id, "winner")

        assert updated_game.id == game_id
        assert updated_game.home_score == 105
        assert updated_game.away_score == 100


class TestSyncBoxscore:
    """Tests for GameSyncer.sync_boxscore method."""

    def test_creates_player_stats(
        self,
        game_syncer: GameSyncer,
        raw_boxscore: RawBoxScore,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should create PlayerGameStats for all players."""
        game = game_syncer.sync_game(raw_boxscore.game, season.id, "winner")
        player_stats, team_stats = game_syncer.sync_boxscore(
            raw_boxscore, game, "winner"
        )

        assert len(player_stats) == 2

        # Check home player stats
        home_stats = [s for s in player_stats if s.team_id == game.home_team_id]
        assert len(home_stats) == 1
        assert home_stats[0].points == 25
        assert home_stats[0].field_goals_made == 10
        assert home_stats[0].is_starter is True

    def test_creates_team_stats(
        self,
        game_syncer: GameSyncer,
        raw_boxscore: RawBoxScore,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should create TeamGameStats for both teams."""
        game = game_syncer.sync_game(raw_boxscore.game, season.id, "winner")
        player_stats, team_stats = game_syncer.sync_boxscore(
            raw_boxscore, game, "winner"
        )

        assert len(team_stats) == 2

        # Check home team stats
        home_team_stats = [s for s in team_stats if s.is_home]
        assert len(home_team_stats) == 1
        assert home_team_stats[0].points == 25  # Aggregated from player stats

    def test_resync_deletes_old_stats(
        self,
        game_syncer: GameSyncer,
        raw_boxscore: RawBoxScore,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should delete old stats when re-syncing."""
        game = game_syncer.sync_game(raw_boxscore.game, season.id, "winner")

        # First sync
        game_syncer.sync_boxscore(raw_boxscore, game, "winner")
        test_db.commit()

        # Count stats
        initial_count = (
            test_db.query(PlayerGameStats).filter_by(game_id=game.id).count()
        )
        assert initial_count == 2

        # Re-sync (should replace)
        game_syncer.sync_boxscore(raw_boxscore, game, "winner")
        test_db.commit()

        final_count = test_db.query(PlayerGameStats).filter_by(game_id=game.id).count()
        assert final_count == 2  # Same count, not doubled


class TestSyncPbp:
    """Tests for GameSyncer.sync_pbp method."""

    def test_creates_pbp_events(
        self,
        game_syncer: GameSyncer,
        raw_boxscore: RawBoxScore,
        season: Season,
        home_team: Team,
        test_db: Session,
    ) -> None:
        """Should create PlayByPlayEvent records."""
        game = game_syncer.sync_game(raw_boxscore.game, season.id, "winner")

        raw_events = [
            RawPBPEvent(
                event_number=1,
                period=1,
                clock="10:00",
                event_type="shot",
                player_name="Home Player",
                team_external_id="home-123",
                success=True,
            ),
            RawPBPEvent(
                event_number=2,
                period=1,
                clock="10:00",
                event_type="assist",
                player_name="Home Player",
                team_external_id="home-123",
                related_event_numbers=[1],
            ),
        ]

        events = game_syncer.sync_pbp(raw_events, game, "winner")

        assert len(events) == 2
        assert events[0].event_type == "SHOT"
        assert events[1].event_type == "ASSIST"

    def test_creates_event_links(
        self,
        game_syncer: GameSyncer,
        raw_boxscore: RawBoxScore,
        season: Season,
        home_team: Team,
        test_db: Session,
    ) -> None:
        """Should create links between related events."""
        game = game_syncer.sync_game(raw_boxscore.game, season.id, "winner")

        raw_events = [
            RawPBPEvent(
                event_number=1,
                period=1,
                clock="10:00",
                event_type="shot",
                team_external_id="home-123",
                success=True,
            ),
            RawPBPEvent(
                event_number=2,
                period=1,
                clock="10:00",
                event_type="assist",
                team_external_id="home-123",
                related_event_numbers=[1],
            ),
        ]

        game_syncer.sync_pbp(raw_events, game, "winner")
        test_db.commit()

        # Check links were created
        links = test_db.query(PlayByPlayEventLink).all()
        assert len(links) == 1

    def test_resync_deletes_old_events(
        self,
        game_syncer: GameSyncer,
        raw_boxscore: RawBoxScore,
        season: Season,
        home_team: Team,
        test_db: Session,
    ) -> None:
        """Should delete old events when re-syncing."""
        game = game_syncer.sync_game(raw_boxscore.game, season.id, "winner")

        raw_events = [
            RawPBPEvent(
                event_number=1,
                period=1,
                clock="10:00",
                event_type="shot",
                team_external_id="home-123",
            ),
        ]

        # First sync
        game_syncer.sync_pbp(raw_events, game, "winner")
        test_db.commit()

        initial_count = (
            test_db.query(PlayByPlayEvent).filter_by(game_id=game.id).count()
        )
        assert initial_count == 1

        # Re-sync
        game_syncer.sync_pbp(raw_events, game, "winner")
        test_db.commit()

        final_count = test_db.query(PlayByPlayEvent).filter_by(game_id=game.id).count()
        assert final_count == 1  # Same count, not doubled
