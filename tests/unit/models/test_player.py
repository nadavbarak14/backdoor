"""
Player Model Tests

Tests for src/models/player.py covering:
- Player model creation with all fields
- full_name property
- PlayerTeamHistory creation
- Unique constraint on (player_id, team_id, season_id)
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, League, Player, PlayerTeamHistory, Season, Team
from src.schemas.enums import Position


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


class TestPlayerModel:
    """Tests for the Player model."""

    def test_player_creation_with_all_fields(self, db_session: Session):
        """Player should be created with all fields."""
        player = Player(
            first_name="LeBron",
            last_name="James",
            birth_date=date(1984, 12, 30),
            nationality="USA",
            height_cm=206,
            positions=[Position.SMALL_FORWARD],
            external_ids={"nba": "2544", "winner": "abc123"},
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        assert player.id is not None
        assert isinstance(player.id, uuid.UUID)
        assert player.first_name == "LeBron"
        assert player.last_name == "James"
        assert player.birth_date == date(1984, 12, 30)
        assert player.nationality == "USA"
        assert player.height_cm == 206
        assert player.positions == [Position.SMALL_FORWARD]
        assert player.external_ids == {"nba": "2544", "winner": "abc123"}
        assert player.created_at is not None
        assert player.updated_at is not None

    def test_player_optional_fields(self, db_session: Session):
        """Player optional fields should allow None."""
        player = Player(
            first_name="John",
            last_name="Doe",
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        assert player.birth_date is None
        assert player.nationality is None
        assert player.height_cm is None
        assert player.positions == []
        assert player.external_ids == {}

    def test_player_full_name_property(self, db_session: Session):
        """Player full_name property should return first + last name."""
        player = Player(
            first_name="Stephen",
            last_name="Curry",
        )
        db_session.add(player)
        db_session.commit()

        assert player.full_name == "Stephen Curry"

    def test_player_full_name_with_special_characters(self, db_session: Session):
        """Player full_name should handle names with special characters."""
        player = Player(
            first_name="Giannis",
            last_name="Antetokounmpo",
        )
        db_session.add(player)
        db_session.commit()

        assert player.full_name == "Giannis Antetokounmpo"

    def test_player_external_ids_json(self, db_session: Session):
        """Player external_ids should store and retrieve JSON correctly."""
        external_ids = {
            "nba": "201939",
            "fiba": "123456",
            "euroleague": "ABC",
        }
        player = Player(
            first_name="Stephen",
            last_name="Curry",
            external_ids=external_ids,
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        assert player.external_ids["nba"] == "201939"
        assert player.external_ids["fiba"] == "123456"
        assert player.external_ids["euroleague"] == "ABC"

    def test_player_repr(self, db_session: Session):
        """Player __repr__ should return meaningful string."""
        player = Player(
            first_name="LeBron",
            last_name="James",
            positions=[Position.SMALL_FORWARD],
        )
        db_session.add(player)
        db_session.commit()

        assert "LeBron James" in repr(player)
        assert "SF" in repr(player)


class TestPlayerTeamHistoryModel:
    """Tests for the PlayerTeamHistory model."""

    def test_player_team_history_creation(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerTeamHistory should be created with all fields."""
        player = Player(first_name="LeBron", last_name="James")
        db_session.add(player)
        db_session.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            jersey_number=23,
            positions=[Position.SMALL_FORWARD],
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)

        assert history.id is not None
        assert isinstance(history.id, uuid.UUID)
        assert history.player_id == player.id
        assert history.team_id == sample_team.id
        assert history.season_id == sample_season.id
        assert history.jersey_number == 23
        assert history.positions == [Position.SMALL_FORWARD]

    def test_player_team_history_optional_fields(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerTeamHistory optional fields should allow None."""
        player = Player(first_name="John", last_name="Doe")
        db_session.add(player)
        db_session.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)

        assert history.jersey_number is None
        assert history.positions == []

    def test_player_team_history_unique_constraint(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """Same player-team-season combination should not be allowed twice."""
        player = Player(first_name="LeBron", last_name="James")
        db_session.add(player)
        db_session.commit()

        history1 = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            jersey_number=23,
        )
        db_session.add(history1)
        db_session.commit()

        history2 = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
            jersey_number=6,  # Different jersey but same player-team-season
        )
        db_session.add(history2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_player_team_history_relationships(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerTeamHistory should have player, team, season relationships."""
        player = Player(first_name="LeBron", last_name="James")
        db_session.add(player)
        db_session.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)

        assert history.player == player
        assert history.team == sample_team
        assert history.season == sample_season

    def test_player_team_history_repr(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """PlayerTeamHistory __repr__ should return meaningful string."""
        player = Player(first_name="LeBron", last_name="James")
        db_session.add(player)
        db_session.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(history)
        db_session.commit()

        assert "player_id" in repr(history)
        assert "team_id" in repr(history)
        assert "season_id" in repr(history)


class TestPlayerRelationships:
    """Tests for Player relationships."""

    def test_player_has_team_histories(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """Player should have access to team_histories."""
        player = Player(first_name="LeBron", last_name="James")
        db_session.add(player)
        db_session.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(player)

        assert len(player.team_histories) == 1
        assert player.team_histories[0].team_id == sample_team.id

    def test_cascade_delete_player_to_history(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """Deleting a player should cascade delete team histories."""
        player = Player(first_name="LeBron", last_name="James")
        db_session.add(player)
        db_session.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add(history)
        db_session.commit()

        history_id = history.id

        # Delete the player
        db_session.delete(player)
        db_session.commit()

        # Expire session to ensure fresh query
        db_session.expire_all()

        # History should also be deleted
        deleted_history = db_session.get(PlayerTeamHistory, history_id)
        assert deleted_history is None


class TestPlayerPositions:
    """Tests for Player multiple positions support."""

    def test_player_with_multiple_positions(self, db_session: Session):
        """Player should store and retrieve multiple positions."""
        player = Player(
            first_name="LeBron",
            last_name="James",
            positions=[Position.SMALL_FORWARD, Position.POWER_FORWARD],
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        assert player.positions == [Position.SMALL_FORWARD, Position.POWER_FORWARD]

    def test_player_empty_positions(self, db_session: Session):
        """Player should handle empty positions list."""
        player = Player(
            first_name="Unknown",
            last_name="Player",
            positions=[],
        )
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        assert player.positions == []


class TestTeamPlayerRelationship:
    """Tests for Team-Player relationships via PlayerTeamHistory."""

    def test_team_has_player_team_histories(
        self,
        db_session: Session,
        sample_team: Team,
        sample_season: Season,
    ):
        """Team should have access to player_team_histories."""
        player1 = Player(first_name="LeBron", last_name="James")
        player2 = Player(first_name="Anthony", last_name="Davis")
        db_session.add_all([player1, player2])
        db_session.commit()

        history1 = PlayerTeamHistory(
            player_id=player1.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        history2 = PlayerTeamHistory(
            player_id=player2.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        db_session.add_all([history1, history2])
        db_session.commit()
        db_session.refresh(sample_team)

        assert len(sample_team.player_team_histories) == 2


class TestImports:
    """Tests for module imports."""

    def test_import_from_player_module(self):
        """Should be able to import from player module."""
        from src.models.player import Player, PlayerTeamHistory

        assert Player is not None
        assert PlayerTeamHistory is not None

    def test_import_from_models_package(self):
        """Should be able to import from models package."""
        from src.models import Player, PlayerTeamHistory

        assert Player is not None
        assert PlayerTeamHistory is not None
