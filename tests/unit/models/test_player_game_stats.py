"""
PlayerGameStats Model Tests

Tests for PlayerGameStats from src/models/game.py covering:
- PlayerGameStats creation with all fields
- Relationship to Game, Player, Team
- extra_stats JSON field
- Unique constraint (game_id, player_id)
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Player, PlayerGameStats, Season, Team


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraints for SQLite
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
def sample_league(db_session: Session) -> League:
    """Create a sample league for testing."""
    league = League(name="NBA", code="NBA", country="USA")
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def sample_season(db_session: Session, sample_league: League) -> Season:
    """Create a sample season for testing."""
    season = Season(
        league_id=sample_league.id,
        name="2023-24",
        start_date=date(2023, 10, 24),
        end_date=date(2024, 6, 20),
        is_current=True,
    )
    db_session.add(season)
    db_session.commit()
    return season


@pytest.fixture
def sample_team(db_session: Session) -> Team:
    """Create a sample team for testing."""
    team = Team(
        name="Los Angeles Lakers",
        short_name="LAL",
        city="Los Angeles",
        country="USA",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_away_team(db_session: Session) -> Team:
    """Create a sample away team for testing."""
    team = Team(
        name="Boston Celtics",
        short_name="BOS",
        city="Boston",
        country="USA",
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_player(db_session: Session) -> Player:
    """Create a sample player for testing."""
    player = Player(
        first_name="LeBron",
        last_name="James",
        birth_date=date(1984, 12, 30),
        nationality="USA",
        height_cm=206,
        position="SF",
    )
    db_session.add(player)
    db_session.commit()
    return player


@pytest.fixture
def sample_game(
    db_session: Session,
    sample_season: Season,
    sample_team: Team,
    sample_away_team: Team,
) -> Game:
    """Create a sample game for testing."""
    game = Game(
        season_id=sample_season.id,
        home_team_id=sample_team.id,
        away_team_id=sample_away_team.id,
        game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        status="FINAL",
    )
    db_session.add(game)
    db_session.commit()
    return game


class TestPlayerGameStatsModel:
    """Tests for the PlayerGameStats model."""

    def test_player_game_stats_creation_with_all_fields(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats should be created with all fields."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            minutes_played=2040,  # 34 minutes in seconds
            is_starter=True,
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            two_pointers_made=6,
            two_pointers_attempted=11,
            three_pointers_made=3,
            three_pointers_attempted=7,
            free_throws_made=4,
            free_throws_attempted=5,
            offensive_rebounds=2,
            defensive_rebounds=6,
            total_rebounds=8,
            assists=7,
            turnovers=3,
            steals=2,
            blocks=1,
            personal_fouls=2,
            plus_minus=12,
            efficiency=28,
            extra_stats={"dunks": 3, "fast_break_points": 8},
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.id is not None
        assert isinstance(stats.id, uuid.UUID)
        assert stats.game_id == sample_game.id
        assert stats.player_id == sample_player.id
        assert stats.team_id == sample_team.id
        assert stats.minutes_played == 2040
        assert stats.is_starter is True
        assert stats.points == 25
        assert stats.field_goals_made == 9
        assert stats.field_goals_attempted == 18
        assert stats.two_pointers_made == 6
        assert stats.two_pointers_attempted == 11
        assert stats.three_pointers_made == 3
        assert stats.three_pointers_attempted == 7
        assert stats.free_throws_made == 4
        assert stats.free_throws_attempted == 5
        assert stats.offensive_rebounds == 2
        assert stats.defensive_rebounds == 6
        assert stats.total_rebounds == 8
        assert stats.assists == 7
        assert stats.turnovers == 3
        assert stats.steals == 2
        assert stats.blocks == 1
        assert stats.personal_fouls == 2
        assert stats.plus_minus == 12
        assert stats.efficiency == 28
        assert stats.extra_stats == {"dunks": 3, "fast_break_points": 8}
        assert stats.created_at is not None
        assert stats.updated_at is not None

    def test_player_game_stats_defaults(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats should have correct default values."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.minutes_played == 0
        assert stats.is_starter is False
        assert stats.points == 0
        assert stats.field_goals_made == 0
        assert stats.assists == 0
        assert stats.extra_stats == {}

    def test_player_game_stats_extra_stats_json(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats extra_stats should store and retrieve JSON correctly."""
        extra_stats = {
            "dunks": 3,
            "fast_break_points": 8,
            "points_in_paint": 12,
            "contested_shots": 5,
        }
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            extra_stats=extra_stats,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.extra_stats["dunks"] == 3
        assert stats.extra_stats["fast_break_points"] == 8
        assert stats.extra_stats["points_in_paint"] == 12
        assert stats.extra_stats["contested_shots"] == 5

    def test_player_game_stats_repr(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats __repr__ should return meaningful string."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            points=25,
        )
        db_session.add(stats)
        db_session.commit()

        assert "PlayerGameStats" in repr(stats)
        assert "points=25" in repr(stats)


class TestPlayerGameStatsUniqueConstraint:
    """Tests for PlayerGameStats unique constraint."""

    def test_player_game_stats_unique_constraint(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """Same player-game combination should not be allowed twice."""
        stats1 = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            points=25,
        )
        db_session.add(stats1)
        db_session.commit()

        stats2 = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            points=30,  # Different points
        )
        db_session.add(stats2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestPlayerGameStatsRelationships:
    """Tests for PlayerGameStats relationships."""

    def test_player_game_stats_game_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats should have access to its game."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.game == sample_game

    def test_player_game_stats_player_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats should have access to its player."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.player == sample_player

    def test_player_game_stats_team_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayerGameStats should have access to its team."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)

        assert stats.team == sample_team

    def test_game_player_game_stats_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """Game should have access to its player_game_stats."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            points=25,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(sample_game)

        assert len(sample_game.player_game_stats) == 1
        assert stats in sample_game.player_game_stats

    def test_player_game_stats_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """Player should have access to its game_stats."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
            points=25,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(sample_player)

        assert len(sample_player.game_stats) == 1
        assert stats in sample_player.game_stats


class TestPlayerGameStatsCascadeDelete:
    """Tests for PlayerGameStats cascade delete behavior."""

    def test_cascade_delete_game_to_player_game_stats(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """Deleting a game should cascade delete player_game_stats."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(stats)
        db_session.commit()

        stats_id = stats.id

        # Delete the game
        db_session.delete(sample_game)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # PlayerGameStats should also be deleted
        deleted_stats = db_session.get(PlayerGameStats, stats_id)
        assert deleted_stats is None

    def test_cascade_delete_player_to_player_game_stats(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """Deleting a player should cascade delete player_game_stats."""
        stats = PlayerGameStats(
            game_id=sample_game.id,
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(stats)
        db_session.commit()

        stats_id = stats.id

        # Delete the player
        db_session.delete(sample_player)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # PlayerGameStats should also be deleted
        deleted_stats = db_session.get(PlayerGameStats, stats_id)
        assert deleted_stats is None
