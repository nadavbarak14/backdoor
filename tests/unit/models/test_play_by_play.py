"""
Play-by-Play Model Tests

Tests for src/models/play_by_play.py covering:
- PlayByPlayEvent creation with all types
- Coordinate fields for shots
- attributes JSON flexibility
- event_number ordering
- PlayByPlayEventLink creation
- related_events relationship (bidirectional)
- Multiple links for one event (and-1 scenario)
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, Game, League, Player, Season, Team
from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink


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
def sample_player2(db_session: Session) -> Player:
    """Create a second sample player for testing."""
    player = Player(
        first_name="Anthony",
        last_name="Davis",
        birth_date=date(1993, 3, 11),
        nationality="USA",
        height_cm=208,
        position="PF",
    )
    db_session.add(player)
    db_session.commit()
    return player


@pytest.fixture
def sample_game(
    db_session: Session, sample_season: Season, sample_team: Team, sample_away_team: Team
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


class TestPlayByPlayEventModel:
    """Tests for the PlayByPlayEvent model."""

    def test_play_by_play_event_creation_with_all_fields(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent should be created with all fields."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
            coord_x=5.5,
            coord_y=8.2,
            attributes={"shot_distance": 7.5, "fast_break": True},
            description="James makes 2PT driving layup",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.id is not None
        assert isinstance(event.id, uuid.UUID)
        assert event.game_id == sample_game.id
        assert event.event_number == 1
        assert event.period == 1
        assert event.clock == "10:30"
        assert event.event_type == "SHOT"
        assert event.event_subtype == "2PT"
        assert event.player_id == sample_player.id
        assert event.team_id == sample_team.id
        assert event.success is True
        assert event.coord_x == 5.5
        assert event.coord_y == 8.2
        assert event.attributes == {"shot_distance": 7.5, "fast_break": True}
        assert event.description == "James makes 2PT driving layup"
        assert event.created_at is not None
        assert event.updated_at is not None

    def test_play_by_play_event_shot_types(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent should handle different shot types."""
        # 2-point shot
        event_2pt = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
            coord_x=5.0,
            coord_y=5.0,
        )
        # 3-point shot
        event_3pt = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:00",
            event_type="SHOT",
            event_subtype="3PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=False,
            coord_x=24.0,
            coord_y=0.5,
        )
        db_session.add_all([event_2pt, event_3pt])
        db_session.commit()

        assert event_2pt.event_subtype == "2PT"
        assert event_2pt.success is True
        assert event_3pt.event_subtype == "3PT"
        assert event_3pt.success is False

    def test_play_by_play_event_team_event_nullable_player(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """PlayByPlayEvent should allow null player_id for team events."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="5:00",
            event_type="TIMEOUT",
            event_subtype="FULL",
            player_id=None,
            team_id=sample_team.id,
            description="Lakers full timeout",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.player_id is None
        assert event.team_id == sample_team.id

    def test_play_by_play_event_attributes_json(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent attributes should store and retrieve JSON correctly."""
        attributes = {
            "shot_distance": 24.5,
            "fast_break": False,
            "contested": True,
            "shot_clock": 8,
        }
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="3PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            attributes=attributes,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.attributes["shot_distance"] == 24.5
        assert event.attributes["fast_break"] is False
        assert event.attributes["contested"] is True
        assert event.attributes["shot_clock"] == 8

    def test_play_by_play_event_defaults(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """PlayByPlayEvent should have correct default values."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="FOUL",
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.event_subtype is None
        assert event.player_id is None
        assert event.success is None
        assert event.coord_x is None
        assert event.coord_y is None
        assert event.attributes == {}
        assert event.description is None

    def test_play_by_play_event_repr(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent __repr__ should return meaningful string."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=42,
            period=2,
            clock="5:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()

        assert "PlayByPlayEvent" in repr(event)
        assert "event_number=42" in repr(event)
        assert "SHOT" in repr(event)


class TestPlayByPlayEventUniqueConstraint:
    """Tests for PlayByPlayEvent unique constraint."""

    def test_play_by_play_event_unique_constraint(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """Same game-event_number combination should not be allowed twice."""
        event1 = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            team_id=sample_team.id,
        )
        db_session.add(event1)
        db_session.commit()

        event2 = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,  # Same event number
            period=1,
            clock="10:25",  # Different clock
            event_type="REBOUND",
            team_id=sample_team.id,
        )
        db_session.add(event2)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestPlayByPlayEventRelationships:
    """Tests for PlayByPlayEvent relationships."""

    def test_play_by_play_event_game_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """PlayByPlayEvent should have access to its game."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.game == sample_game

    def test_play_by_play_event_player_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent should have access to its player."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.player == sample_player

    def test_play_by_play_event_team_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """PlayByPlayEvent should have access to its team."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        assert event.team == sample_team

    def test_game_play_by_play_events_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """Game should have access to its play_by_play_events."""
        event1 = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            team_id=sample_team.id,
        )
        event2 = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:25",
            event_type="REBOUND",
            team_id=sample_team.id,
        )
        db_session.add_all([event1, event2])
        db_session.commit()
        db_session.refresh(sample_game)

        assert len(sample_game.play_by_play_events) == 2
        assert event1 in sample_game.play_by_play_events
        assert event2 in sample_game.play_by_play_events

    def test_player_play_by_play_events_relationship(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_team: Team,
    ):
        """Player should have access to its play_by_play_events."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(sample_player)

        assert len(sample_player.play_by_play_events) == 1
        assert event in sample_player.play_by_play_events


class TestPlayByPlayEventLinkModel:
    """Tests for the PlayByPlayEventLink model."""

    def test_play_by_play_event_link_creation(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """PlayByPlayEventLink should link two events."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link)
        db_session.commit()

        assert link.event_id == assist.id
        assert link.related_event_id == shot.id

    def test_play_by_play_event_link_composite_pk(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """PlayByPlayEventLink should use composite primary key."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link)
        db_session.commit()

        # Composite PK - should not have separate id field
        assert not hasattr(link, "id") or link.id is None

    def test_play_by_play_event_link_unique_constraint(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """Same event-related_event link should not be allowed twice."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link1 = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link1)
        db_session.commit()

        link2 = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_play_by_play_event_link_repr(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """PlayByPlayEventLink __repr__ should return meaningful string."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link)
        db_session.commit()

        assert "PlayByPlayEventLink" in repr(link)
        assert "event_id" in repr(link)
        assert "related_event_id" in repr(link)


class TestPlayByPlayEventLinkRelationships:
    """Tests for PlayByPlayEventLink relationships."""

    def test_play_by_play_event_related_events(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent should access related events via link table."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link)
        db_session.commit()
        db_session.refresh(assist)

        # Assist should link TO the shot
        assert len(assist.related_events) == 1
        assert shot in assist.related_events

    def test_play_by_play_event_linked_from(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """PlayByPlayEvent should access events that link TO it."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link)
        db_session.commit()
        db_session.refresh(shot)

        # Shot should be linked FROM the assist
        assert len(shot.linked_from) == 1
        assert assist in shot.linked_from

    def test_play_by_play_event_multiple_links_and_one_scenario(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
        sample_away_team: Team,
    ):
        """Test and-1 scenario with multiple links to one event."""
        # Player makes a shot
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            event_subtype="2PT",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
            description="James makes 2PT driving layup",
        )
        # Teammate gets the assist
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
            description="Davis assist",
        )
        # Opponent commits a shooting foul
        foul = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=3,
            period=1,
            clock="10:30",
            event_type="FOUL",
            event_subtype="SHOOTING",
            player_id=None,
            team_id=sample_away_team.id,
            description="Shooting foul",
        )
        # Player makes the free throw
        free_throw = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=4,
            period=1,
            clock="10:30",
            event_type="FREE_THROW",
            player_id=sample_player.id,
            team_id=sample_team.id,
            success=True,
            description="James makes free throw 1 of 1",
        )
        db_session.add_all([shot, assist, foul, free_throw])
        db_session.commit()

        # Create links
        link_assist_to_shot = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        link_foul_to_shot = PlayByPlayEventLink(
            event_id=foul.id,
            related_event_id=shot.id,
        )
        link_ft_to_shot = PlayByPlayEventLink(
            event_id=free_throw.id,
            related_event_id=shot.id,
        )
        link_ft_to_foul = PlayByPlayEventLink(
            event_id=free_throw.id,
            related_event_id=foul.id,
        )
        db_session.add_all(
            [link_assist_to_shot, link_foul_to_shot, link_ft_to_shot, link_ft_to_foul]
        )
        db_session.commit()
        db_session.refresh(shot)
        db_session.refresh(free_throw)

        # Shot should be linked FROM assist, foul, and free throw
        assert len(shot.linked_from) == 3
        assert assist in shot.linked_from
        assert foul in shot.linked_from
        assert free_throw in shot.linked_from

        # Free throw should link TO both shot and foul
        assert len(free_throw.related_events) == 2
        assert shot in free_throw.related_events
        assert foul in free_throw.related_events


class TestPlayByPlayCascadeDelete:
    """Tests for play-by-play cascade delete behavior."""

    def test_cascade_delete_game_to_play_by_play_events(
        self,
        db_session: Session,
        sample_game: Game,
        sample_team: Team,
    ):
        """Deleting a game should cascade delete play_by_play_events."""
        event = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            team_id=sample_team.id,
        )
        db_session.add(event)
        db_session.commit()

        event_id = event.id

        # Delete the game
        db_session.delete(sample_game)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # PlayByPlayEvent should also be deleted
        deleted_event = db_session.get(PlayByPlayEvent, event_id)
        assert deleted_event is None

    def test_cascade_delete_event_to_links(
        self,
        db_session: Session,
        sample_game: Game,
        sample_player: Player,
        sample_player2: Player,
        sample_team: Team,
    ):
        """Deleting an event should cascade delete its links."""
        shot = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=1,
            period=1,
            clock="10:30",
            event_type="SHOT",
            player_id=sample_player.id,
            team_id=sample_team.id,
        )
        assist = PlayByPlayEvent(
            game_id=sample_game.id,
            event_number=2,
            period=1,
            clock="10:30",
            event_type="ASSIST",
            player_id=sample_player2.id,
            team_id=sample_team.id,
        )
        db_session.add_all([shot, assist])
        db_session.commit()

        link = PlayByPlayEventLink(
            event_id=assist.id,
            related_event_id=shot.id,
        )
        db_session.add(link)
        db_session.commit()

        assist_id = assist.id
        shot_id = shot.id

        # Delete the assist event
        db_session.delete(assist)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # Link should also be deleted
        result = (
            db_session.query(PlayByPlayEventLink)
            .filter_by(event_id=assist_id, related_event_id=shot_id)
            .first()
        )
        assert result is None


class TestImports:
    """Tests for module imports."""

    def test_import_from_play_by_play_module(self):
        """Should be able to import from play_by_play module."""
        from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink

        assert PlayByPlayEvent is not None
        assert PlayByPlayEventLink is not None

    def test_import_from_models_package(self):
        """Should be able to import from models package."""
        from src.models import PlayByPlayEvent, PlayByPlayEventLink

        assert PlayByPlayEvent is not None
        assert PlayByPlayEventLink is not None
