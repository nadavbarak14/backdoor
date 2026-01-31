"""
Unit tests for AnalyticsService clutch time filtering.

Tests clutch event filtering with:
- Fixture-based validation: known scenarios with exact expected results
- Property-based validation: all results satisfy filter properties
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.analytics import ClutchFilter
from src.schemas.enums import GameStatus
from src.schemas.game import GameCreate, GameStatus
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.team import TeamService


class TestClutchFilter:
    """Tests for ClutchFilter schema."""

    def test_clutch_filter_defaults(self):
        """Verify default values match NBA clutch definition."""
        filter = ClutchFilter()

        assert filter.time_remaining_seconds == 300  # 5 minutes
        assert filter.score_margin == 5
        assert filter.include_overtime is True
        assert filter.min_period == 4

    def test_clutch_filter_custom_values(self):
        """Test custom filter values for super clutch."""
        filter = ClutchFilter(
            time_remaining_seconds=120,  # 2 minutes
            score_margin=3,
            include_overtime=False,
            min_period=4,
        )

        assert filter.time_remaining_seconds == 120
        assert filter.score_margin == 3
        assert filter.include_overtime is False


class TestGetClutchEvents:
    """Tests for AnalyticsService.get_clutch_events()."""

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
    def tatum(self, test_db: Session) -> Player:
        """Create Jayson Tatum for testing."""
        service = PlayerService(test_db)
        return service.create_player(
            PlayerCreate(first_name="Jayson", last_name="Tatum", position="SF")
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

    # =========================================================================
    # Fixture-based tests: known scenarios with exact expected results
    # =========================================================================

    def test_get_clutch_events_returns_expected(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """
        Create a simple game scenario with known clutch events.
        Verify we get exactly the expected events.

        Score scenario:
        - Q1-Q3: Lakers 10, Celtics 10 (5 baskets each) - tied game
        - Q4 6:00: Lakers +2 (12-10, margin 2) - NOT clutch (> 5 min)
        - Q4 4:00: Celtics +2 (12-12, margin 0) - CLUTCH
        - Q4 2:00: Lakers +2 (14-12, margin 2) - CLUTCH
        - Q4 0:30: Celtics +1 (14-13, margin 1) - CLUTCH
        """
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Q1-Q3: Build tied score 10-10
        for i in range(5):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + (i // 2),
                    "clock": "10:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": 10 + i + 1,
                    "period": 1 + (i // 2),
                    "clock": "9:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )

        # Q4 6:00 - NOT clutch (> 5 min remaining)
        not_clutch_event = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 4,
                "clock": "6:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Q4 4:00 - CLUTCH (< 5 min, margin 2 before this shot)
        clutch_event_1 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 101,
                "period": 4,
                "clock": "4:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
            }
        )

        # Q4 2:00 - CLUTCH (< 5 min, margin 0 before this shot)
        clutch_event_2 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 102,
                "period": 4,
                "clock": "2:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Q4 0:30 - CLUTCH (< 5 min, margin 2 before this FT)
        clutch_event_3 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 103,
                "period": 4,
                "clock": "0:30",
                "event_type": "FREE_THROW",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
            }
        )

        # Get clutch events
        clutch_events = service.get_clutch_events(game.id)
        clutch_event_ids = {e.id for e in clutch_events}

        # Verify expected clutch events are present
        assert clutch_event_1.id in clutch_event_ids, "4:00 event should be clutch"
        assert clutch_event_2.id in clutch_event_ids, "2:00 event should be clutch"
        assert clutch_event_3.id in clutch_event_ids, "0:30 event should be clutch"

        # Verify non-clutch event is NOT present
        assert (
            not_clutch_event.id not in clutch_event_ids
        ), "6:00 event should NOT be clutch"

    def test_no_clutch_events_in_blowout(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Verify NO events returned when game is a blowout (margin > 5)."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Build a blowout: Lakers 80, Celtics 50 by Q4
        for i in range(40):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + (i // 12),
                    "clock": "10:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )

        for i in range(25):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": 50 + i + 1,
                    "period": 1 + (i // 8),
                    "clock": "9:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )

        # Q4 event at 3:00 - score is 80-50 = 30 pt margin, NOT clutch
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 4,
                "clock": "3:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        clutch_events = service.get_clutch_events(game.id)

        assert len(clutch_events) == 0

    def test_super_clutch_stricter_filter(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """
        Test super clutch (2 min, 3 pts) returns subset of standard clutch.

        Score scenario:
        - Start: 10-10 (tied)
        - Q4 3:00: Lakers +2 (12-10, margin 2) - standard clutch only (> 2 min)
        - Q4 1:30: Celtics +2 (12-12, margin 0) - SUPER clutch (< 2 min, < 3 pts)
        """
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Build tied score: 10-10
        for i in range(5):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + (i // 2),
                    "clock": "10:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": 10 + i + 1,
                    "period": 1 + (i // 2),
                    "clock": "9:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )

        # Event at 3:00 Q4 - standard clutch but NOT super clutch (> 2 min)
        standard_only_event = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 4,
                "clock": "3:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Event at 1:30 Q4 - IS super clutch (< 2 min, margin 2 < 3 pts)
        super_clutch_event = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 101,
                "period": 4,
                "clock": "1:30",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
            }
        )

        # Standard clutch should have both events
        standard_clutch = service.get_clutch_events(game.id)
        standard_ids = {e.id for e in standard_clutch}
        assert standard_only_event.id in standard_ids
        assert super_clutch_event.id in standard_ids

        # Super clutch (2 min, 3 pts) should only have the 1:30 event
        super_filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)
        super_clutch = service.get_clutch_events(game.id, super_filter)
        super_ids = {e.id for e in super_clutch}

        assert super_clutch_event.id in super_ids, "1:30 event should be super clutch"
        assert (
            standard_only_event.id not in super_ids
        ), "3:00 event should NOT be super clutch"
        assert len(super_clutch) < len(standard_clutch)

    # =========================================================================
    # Property-based tests: all results satisfy filter properties
    # =========================================================================

    def test_all_clutch_events_in_valid_period(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Assert ALL returned events have period >= 4."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create events in various periods
        for period in range(1, 6):  # Q1-Q4 + OT
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": period * 10,
                    "period": period,
                    "clock": "2:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )

        clutch_events = service.get_clutch_events(game.id)

        # Property: ALL returned events must have period >= 4
        for event in clutch_events:
            assert event.period >= 4, f"Event {event.id} has period {event.period} < 4"

    def test_all_clutch_events_within_time(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Assert ALL returned events have time_remaining <= threshold."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create Q4 events at various times
        times = ["10:00", "7:00", "5:00", "4:00", "2:00", "0:30"]
        for i, clock in enumerate(times):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 4,
                    "clock": clock,
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )

        clutch_events = service.get_clutch_events(game.id)

        # Property: ALL returned events must have time <= 5 min (300 sec)
        for event in clutch_events:
            seconds = service._parse_clock_to_seconds(event.clock)
            assert seconds <= 300, f"Event at {event.clock} ({seconds}s) > 300s"

    def test_all_clutch_events_within_margin(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Assert ALL returned events occurred when score margin <= threshold."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Build a 50-48 lead going into Q4
        for i in range(25):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + (i // 10),
                    "clock": "10:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )

        for i in range(24):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": 50 + i + 1,
                    "period": 1 + (i // 10),
                    "clock": "9:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )

        # Q4 event
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 4,
                "clock": "3:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        clutch_events = service.get_clutch_events(game.id)

        # Property: ALL returned events must have margin <= 5 BEFORE the event
        for event in clutch_events:
            event_seconds = service._parse_clock_to_seconds(event.clock)
            # Check score before this event (add 1 second to exclude it)
            home, away = service._get_game_score_at_time(
                game.id, event.period, event_seconds + 1
            )
            margin = abs(home - away)
            assert margin <= 5, f"Event at {event.clock} has margin {margin} > 5"

    def test_clutch_includes_overtime(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Test OT events included when include_overtime=True."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create an OT event
        ot_event = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 5,  # OT
                "clock": "3:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Default filter includes OT
        clutch_events = service.get_clutch_events(game.id)
        assert ot_event.id in {e.id for e in clutch_events}

        # Filter excluding OT
        no_ot_filter = ClutchFilter(include_overtime=False)
        no_ot_events = service.get_clutch_events(game.id, no_ot_filter)
        assert ot_event.id not in {e.id for e in no_ot_events}

    # =========================================================================
    # Edge cases
    # =========================================================================

    def test_empty_game_returns_empty(self, test_db: Session, game: Game):
        """Test that a game with no events returns empty list."""
        service = AnalyticsService(test_db)

        clutch_events = service.get_clutch_events(game.id)

        assert clutch_events == []

    def test_nonexistent_game_returns_empty(self, test_db: Session):
        """Test that a non-existent game returns empty list."""
        import uuid

        service = AnalyticsService(test_db)
        fake_id = uuid.uuid4()

        clutch_events = service.get_clutch_events(fake_id)

        assert clutch_events == []
