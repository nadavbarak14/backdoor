"""
Unit tests for AnalyticsService base functionality.

Tests the analytics service base class including service composition,
score calculation from play-by-play events, and clutch moment detection.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.enums import GameStatus
from src.schemas.game import GameCreate
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.team import TeamService


class TestAnalyticsServiceBase:
    """Tests for AnalyticsService base operations."""

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

    def test_analytics_service_init(self, test_db: Session):
        """Test that all composed services are initialized."""
        service = AnalyticsService(test_db)

        assert service.db is test_db
        assert service.pbp_service is not None
        assert service.player_stats_service is not None
        assert service.team_stats_service is not None
        assert service.season_stats_service is not None
        assert service.game_service is not None

    def test_parse_clock_to_seconds(self, test_db: Session):
        """Test parsing clock string to seconds."""
        service = AnalyticsService(test_db)

        assert service._parse_clock_to_seconds("5:30") == 330
        assert service._parse_clock_to_seconds("10:00") == 600
        assert service._parse_clock_to_seconds("0:45") == 45
        assert service._parse_clock_to_seconds("0:00") == 0
        assert service._parse_clock_to_seconds("12:00") == 720

    def test_parse_clock_to_seconds_invalid(self, test_db: Session):
        """Test parsing invalid clock string raises ValueError."""
        service = AnalyticsService(test_db)

        with pytest.raises(ValueError):
            service._parse_clock_to_seconds("invalid")

    def test_get_game_score_at_time_no_events(self, test_db: Session, game: Game):
        """Test score calculation with no events returns 0-0."""
        service = AnalyticsService(test_db)

        home, away = service._get_game_score_at_time(
            game.id, period=1, time_remaining=600
        )

        assert home == 0
        assert away == 0

    def test_get_game_score_at_time_with_shots(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Test correctly calculates running score from shot events."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create some scoring events
        # Q1: Lakers 2PT at 10:00, Celtics 3PT at 9:00, Lakers 2PT at 8:00
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
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
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "8:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Score at 9:30 (only Lakers 2PT counted)
        home, away = service._get_game_score_at_time(
            game.id, period=1, time_remaining=570
        )
        assert home == 2
        assert away == 0

        # Score at 8:30 (Lakers 2PT + Celtics 3PT)
        home, away = service._get_game_score_at_time(
            game.id, period=1, time_remaining=510
        )
        assert home == 2
        assert away == 3

        # Score at 7:00 (all three baskets)
        home, away = service._get_game_score_at_time(
            game.id, period=1, time_remaining=420
        )
        assert home == 4
        assert away == 3

    def test_get_game_score_at_time_includes_free_throws(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Test score calculation includes made free throws."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create free throw events
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "FREE_THROW",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "FREE_THROW",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "10:00",
                "event_type": "FREE_THROW",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,  # Missed
            }
        )

        home, away = service._get_game_score_at_time(
            game.id, period=1, time_remaining=500
        )
        assert home == 2  # 2 made FTs
        assert away == 0

    def test_get_game_score_at_time_excludes_missed_shots(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Test that missed shots are not counted in score."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,  # Missed
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,  # Made
            }
        )

        home, away = service._get_game_score_at_time(
            game.id, period=1, time_remaining=0
        )
        assert home == 2  # Only the made 2PT
        assert away == 0

    def test_get_game_score_at_time_across_periods(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Test score calculation accumulates across periods."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Q1 basket
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "5:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        # Q2 basket
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 50,
                "period": 2,
                "clock": "5:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
            }
        )
        # Q3 basket
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 3,
                "clock": "5:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        # Score at start of Q4 (all previous periods counted)
        home, away = service._get_game_score_at_time(
            game.id, period=4, time_remaining=720
        )
        assert home == 4  # 2 + 2
        assert away == 3

    def test_is_clutch_moment_true(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Test is_clutch_moment returns True for clutch situation."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Set up a close game: Lakers 98, Celtics 95 going into clutch time
        # We need to create events that result in this score by Q4
        for i in range(49):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + (i // 15),  # Spread across periods
                    "clock": "10:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )

        for i in range(47):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": 100 + i + 1,
                    "period": 1 + (i // 15),
                    "clock": "9:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )

        # Lakers: 98 pts, Celtics: 94 pts, margin = 4 (within 5)
        is_clutch = service._is_clutch_moment(
            game.id, period=4, time_remaining=300, score_margin_threshold=5
        )
        assert is_clutch is True

    def test_is_clutch_moment_false_blowout(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Test is_clutch_moment returns False when margin is too large."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Lakers leading by 20+
        for i in range(30):
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

        for i in range(10):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": 100 + i + 1,
                    "period": 1 + (i // 5),
                    "clock": "9:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )

        # Lakers: 60 pts, Celtics: 20 pts, margin = 40 (NOT clutch)
        is_clutch = service._is_clutch_moment(
            game.id, period=4, time_remaining=300, score_margin_threshold=5
        )
        assert is_clutch is False

    def test_is_clutch_moment_false_early_period(self, test_db: Session, game: Game):
        """Test is_clutch_moment returns False for periods before Q4."""
        service = AnalyticsService(test_db)

        # Q1 is never clutch, regardless of score
        is_clutch = service._is_clutch_moment(
            game.id, period=1, time_remaining=300, score_margin_threshold=5
        )
        assert is_clutch is False

        # Q2 is never clutch
        is_clutch = service._is_clutch_moment(
            game.id, period=2, time_remaining=300, score_margin_threshold=5
        )
        assert is_clutch is False

        # Q3 is never clutch
        is_clutch = service._is_clutch_moment(
            game.id, period=3, time_remaining=300, score_margin_threshold=5
        )
        assert is_clutch is False

    def test_is_clutch_moment_overtime(self, test_db: Session, game: Game):
        """Test is_clutch_moment works for overtime periods."""
        service = AnalyticsService(test_db)

        # OT (period 5) should be considered clutch if score is close
        # With no events, score is 0-0, which is within threshold
        is_clutch = service._is_clutch_moment(
            game.id, period=5, time_remaining=180, score_margin_threshold=5
        )
        assert is_clutch is True

    def test_get_game_nonexistent(self, test_db: Session):
        """Test get_game returns None for non-existent game."""
        import uuid

        service = AnalyticsService(test_db)
        fake_id = uuid.uuid4()

        result = service.get_game(fake_id)
        assert result is None

    def test_get_game_score_nonexistent_game(self, test_db: Session):
        """Test score calculation for non-existent game returns 0-0."""
        import uuid

        service = AnalyticsService(test_db)
        fake_id = uuid.uuid4()

        home, away = service._get_game_score_at_time(
            fake_id, period=1, time_remaining=600
        )
        assert home == 0
        assert away == 0
