"""
Unit tests for PlayByPlayService.

Tests play-by-play event business logic including event retrieval,
filtering, event linking, bulk creation, and shot chart data.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.game import GameCreate, GameStatus
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.play_by_play import PlayByPlayFilter
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.team import TeamService
from src.schemas.enums import GameStatus, Position


class TestPlayByPlayService:
    """Tests for PlayByPlayService operations."""

    @pytest.fixture
    def nba_league(self, test_db: Session) -> League:
        """Create an NBA league for testing."""
        service = LeagueService(test_db)
        return service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )

    @pytest.fixture
    def nba_season(self, test_db: Session, nba_league: League) -> Season:
        """Create an NBA season for testing."""
        service = SeasonService(test_db)
        return service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
                is_current=True,
            )
        )

    @pytest.fixture
    def lakers(self, test_db: Session) -> Team:
        """Create a Lakers team for testing."""
        service = TeamService(test_db)
        return service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )

    @pytest.fixture
    def celtics(self, test_db: Session) -> Team:
        """Create a Celtics team for testing."""
        service = TeamService(test_db)
        return service.create_team(
            TeamCreate(
                name="Boston Celtics",
                short_name="BOS",
                city="Boston",
                country="USA",
            )
        )

    @pytest.fixture
    def lebron(self, test_db: Session) -> Player:
        """Create LeBron James for testing."""
        service = PlayerService(test_db)
        return service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James", position="SF")
        )

    @pytest.fixture
    def ad(self, test_db: Session) -> Player:
        """Create Anthony Davis for testing."""
        service = PlayerService(test_db)
        return service.create_player(
            PlayerCreate(first_name="Anthony", last_name="Davis", position="PF")
        )

    @pytest.fixture
    def game(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ) -> Game:
        """Create a game for testing."""
        service = GameService(test_db)
        return service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

    def test_create_event(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Test creating a play-by-play event."""
        service = PlayByPlayService(test_db)

        event = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "coord_x": 5.5,
                "coord_y": 8.2,
                "description": "James makes 2PT driving layup",
            }
        )

        assert event.id is not None
        assert event.game_id == game.id
        assert event.event_number == 1
        assert event.event_type == "SHOT"
        assert event.success is True
        assert event.coord_x == 5.5
        assert event.attributes == {}

    def test_get_by_game(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team, celtics: Team
    ):
        """Test getting all events for a game."""
        service = PlayByPlayService(test_db)

        # Create events in different order to test ordering
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "10:00",
                "event_type": "REBOUND",
                "team_id": celtics.id,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:15",
                "event_type": "ASSIST",
                "team_id": lakers.id,
            }
        )

        events = service.get_by_game(game.id)

        assert len(events) == 3
        # Verify ordering by event_number
        assert events[0].event_number == 1
        assert events[1].event_number == 2
        assert events[2].event_number == 3

    def test_get_by_game_with_filter_period(
        self, test_db: Session, game: Game, lakers: Team
    ):
        """Test filtering events by period."""
        service = PlayByPlayService(test_db)

        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "team_id": lakers.id,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 50,
                "period": 2,
                "clock": "10:00",
                "event_type": "SHOT",
                "team_id": lakers.id,
            }
        )

        events = service.get_by_game(game.id, PlayByPlayFilter(period=1))

        assert len(events) == 1
        assert events[0].period == 1

    def test_get_by_game_with_filter_event_type(
        self, test_db: Session, game: Game, lakers: Team
    ):
        """Test filtering events by event type."""
        service = PlayByPlayService(test_db)

        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "team_id": lakers.id,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "REBOUND",
                "team_id": lakers.id,
            }
        )

        events = service.get_by_game(game.id, PlayByPlayFilter(event_type="SHOT"))

        assert len(events) == 1
        assert events[0].event_type == "SHOT"

    def test_get_by_game_with_filter_player(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test filtering events by player."""
        service = PlayByPlayService(test_db)

        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "player_id": ad.id,
                "team_id": lakers.id,
            }
        )

        events = service.get_by_game(game.id, PlayByPlayFilter(player_id=lebron.id))

        assert len(events) == 1
        assert events[0].player_id == lebron.id

    def test_link_events(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test linking events together."""
        service = PlayByPlayService(test_db)

        # Create shot event
        shot = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Create assist event
        assist = service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:30",
                "event_type": "ASSIST",
                "player_id": ad.id,
                "team_id": lakers.id,
            }
        )

        # Link assist to shot
        service.link_events(assist.id, [shot.id])

        # Verify link
        related = service.get_related_events(assist.id)
        assert len(related) == 1
        assert related[0].id == shot.id

    def test_link_events_idempotent(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test that linking same events twice doesn't create duplicates."""
        service = PlayByPlayService(test_db)

        shot = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        assist = service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:30",
                "event_type": "ASSIST",
                "player_id": ad.id,
                "team_id": lakers.id,
            }
        )

        # Link twice
        service.link_events(assist.id, [shot.id])
        service.link_events(assist.id, [shot.id])

        related = service.get_related_events(assist.id)
        assert len(related) == 1

    def test_unlink_events(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test unlinking events."""
        service = PlayByPlayService(test_db)

        shot = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        assist = service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:30",
                "event_type": "ASSIST",
                "player_id": ad.id,
                "team_id": lakers.id,
            }
        )

        service.link_events(assist.id, [shot.id])
        service.unlink_events(assist.id, [shot.id])

        related = service.get_related_events(assist.id)
        assert len(related) == 0

    def test_get_events_linking_to(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test getting events that link to a specific event."""
        service = PlayByPlayService(test_db)

        shot = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        assist = service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:30",
                "event_type": "ASSIST",
                "player_id": ad.id,
                "team_id": lakers.id,
            }
        )

        service.link_events(assist.id, [shot.id])

        # Get events that link TO the shot (the assist)
        linked_to_shot = service.get_events_linking_to(shot.id)
        assert len(linked_to_shot) == 1
        assert linked_to_shot[0].id == assist.id

    def test_get_with_related(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test getting event with related events loaded."""
        service = PlayByPlayService(test_db)

        shot = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        assist = service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:30",
                "event_type": "ASSIST",
                "player_id": ad.id,
                "team_id": lakers.id,
            }
        )

        service.link_events(assist.id, [shot.id])

        event = service.get_with_related(assist.id)
        assert event is not None
        assert len(event.related_events) == 1

    def test_bulk_create_with_links(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test bulk creating events with links."""
        service = PlayByPlayService(test_db)

        events = [
            {  # index 0: shot
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            },
            {  # index 1: assist
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:30",
                "event_type": "ASSIST",
                "player_id": ad.id,
                "team_id": lakers.id,
            },
        ]
        links = [
            (1, [0]),  # assist (index 1) links to shot (index 0)
        ]

        created = service.bulk_create_with_links(events, links)

        assert len(created) == 2
        # Verify the link was created
        assist_event = created[1]
        related = service.get_related_events(assist_event.id)
        assert len(related) == 1
        assert related[0].id == created[0].id

    def test_get_shot_chart_data(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test getting shot chart data."""
        service = PlayByPlayService(test_db)

        # Shot with coordinates
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "coord_x": 7.5,
                "coord_y": 0.5,
            }
        )
        # Shot without coordinates (should not be included)
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "player_id": ad.id,
                "team_id": lakers.id,
                "success": False,
            }
        )
        # Non-shot event (should not be included)
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "9:50",
                "event_type": "REBOUND",
                "player_id": ad.id,
                "team_id": lakers.id,
                "coord_x": 5.0,
                "coord_y": 5.0,
            }
        )

        shots = service.get_shot_chart_data(game.id)

        assert len(shots) == 1
        assert shots[0].event_type == "SHOT"
        assert shots[0].coord_x == 7.5

    def test_get_shot_chart_data_by_team(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team, celtics: Team
    ):
        """Test getting shot chart data filtered by team."""
        service = PlayByPlayService(test_db)

        # Lakers shot
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "coord_x": 5.0,
                "coord_y": 5.0,
            }
        )
        # Celtics shot
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "team_id": celtics.id,
                "coord_x": 3.0,
                "coord_y": 3.0,
            }
        )

        lakers_shots = service.get_shot_chart_data(game.id, team_id=lakers.id)

        assert len(lakers_shots) == 1
        assert lakers_shots[0].team_id == lakers.id

    def test_get_shot_chart_data_by_player(
        self, test_db: Session, game: Game, lebron: Player, ad: Player, lakers: Team
    ):
        """Test getting shot chart data filtered by player."""
        service = PlayByPlayService(test_db)

        # LeBron shot
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "coord_x": 5.0,
                "coord_y": 5.0,
            }
        )
        # AD shot
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "player_id": ad.id,
                "team_id": lakers.id,
                "coord_x": 3.0,
                "coord_y": 3.0,
            }
        )

        lebron_shots = service.get_shot_chart_data(game.id, player_id=lebron.id)

        assert len(lebron_shots) == 1
        assert lebron_shots[0].player_id == lebron.id

    def test_get_events_by_type(self, test_db: Session, game: Game, lakers: Team):
        """Test getting events by type."""
        service = PlayByPlayService(test_db)

        service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "team_id": lakers.id,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "team_id": lakers.id,
            }
        )
        service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "9:50",
                "event_type": "REBOUND",
                "team_id": lakers.id,
            }
        )

        # All shots
        shots = service.get_events_by_type(game.id, "SHOT")
        assert len(shots) == 2

        # Only 3-pointers
        threes = service.get_events_by_type(game.id, "SHOT", event_subtype="3PT")
        assert len(threes) == 1

    def test_count_by_game(self, test_db: Session, game: Game, lakers: Team):
        """Test counting events in a game."""
        service = PlayByPlayService(test_db)

        for i in range(5):
            service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1,
                    "clock": f"10:{i:02d}",
                    "event_type": "SHOT",
                    "team_id": lakers.id,
                }
            )

        count = service.count_by_game(game.id)

        assert count == 5

    def test_delete_by_game(self, test_db: Session, game: Game, lakers: Team):
        """Test deleting all events for a game."""
        service = PlayByPlayService(test_db)

        for i in range(3):
            service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1,
                    "clock": f"10:{i:02d}",
                    "event_type": "SHOT",
                    "team_id": lakers.id,
                }
            )

        deleted = service.delete_by_game(game.id)

        assert deleted == 3
        assert service.count_by_game(game.id) == 0

    def test_update_event(self, test_db: Session, game: Game, lakers: Team):
        """Test updating an event."""
        service = PlayByPlayService(test_db)

        event = service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:30",
                "event_type": "SHOT",
                "team_id": lakers.id,
                "description": "Original description",
            }
        )

        updated = service.update_event(event.id, {"description": "Updated description"})

        assert updated is not None
        assert updated.description == "Updated description"

    def test_get_with_related_not_found(self, test_db: Session):
        """Test get_with_related returns None for non-existent event."""
        service = PlayByPlayService(test_db)
        fake_id = uuid.uuid4()

        result = service.get_with_related(fake_id)

        assert result is None

    def test_get_related_events_not_found(self, test_db: Session):
        """Test get_related_events returns empty list for non-existent event."""
        service = PlayByPlayService(test_db)
        fake_id = uuid.uuid4()

        result = service.get_related_events(fake_id)

        assert result == []
