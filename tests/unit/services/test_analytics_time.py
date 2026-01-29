"""Unit tests for AnalyticsService time-based period filtering."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.analytics import TimeFilter
from src.schemas.game import EventType, GameCreate, GameStatus
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.team import TeamService
from src.schemas.enums import GameStatus, Position


class TestTimeFilter:
    """Tests for TimeFilter schema."""

    def test_defaults(self):
        f = TimeFilter()
        assert f.period is None
        assert f.periods is None
        assert f.exclude_garbage_time is False

    def test_period_and_periods_mutually_exclusive(self):
        with pytest.raises(ValueError, match="cannot both be set"):
            TimeFilter(period=4, periods=[3, 4])

    def test_min_max_time_validation(self):
        with pytest.raises(ValueError, match="must be <="):
            TimeFilter(min_time_remaining=300, max_time_remaining=100)


class TestGetEventsByTime:
    """Tests for AnalyticsService.get_events_by_time()."""

    @pytest.fixture
    def league(self, test_db: Session) -> League:
        return LeagueService(test_db).create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )

    @pytest.fixture
    def season(self, test_db: Session, league: League) -> Season:
        return SeasonService(test_db).create_season(
            SeasonCreate(
                league_id=league.id,
                name="2023-24",
                start_date=date(2023, 10, 1),
                end_date=date(2024, 6, 1),
                is_current=True,
            )
        )

    @pytest.fixture
    def lakers(self, test_db: Session) -> Team:
        return TeamService(test_db).create_team(
            TeamCreate(name="Lakers", short_name="LAL", city="LA", country="USA")
        )

    @pytest.fixture
    def celtics(self, test_db: Session) -> Team:
        return TeamService(test_db).create_team(
            TeamCreate(name="Celtics", short_name="BOS", city="Boston", country="USA")
        )

    @pytest.fixture
    def lebron(self, test_db: Session) -> Player:
        return PlayerService(test_db).create_player(
            PlayerCreate(first_name="LeBron", last_name="James", position="SF")
        )

    @pytest.fixture
    def tatum(self, test_db: Session) -> Player:
        return PlayerService(test_db).create_player(
            PlayerCreate(first_name="Jayson", last_name="Tatum", position="SF")
        )

    @pytest.fixture
    def game(
        self, test_db: Session, season: Season, lakers: Team, celtics: Team
    ) -> Game:
        return GameService(test_db).create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

    @pytest.fixture
    def game_with_events(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Create game with events across all periods including OT."""
        pbp = PlayByPlayService(test_db)
        event_num = 1
        # Q1-Q4 events
        for period in range(1, 5):
            for clock in ["10:00", "5:00", "2:00"]:
                pbp.create_event(
                    {
                        "game_id": game.id,
                        "event_number": event_num,
                        "period": period,
                        "clock": clock,
                        "event_type": EventType.SHOT.value,
                        "event_subtype": "2PT",
                        "player_id": lebron.id,
                        "team_id": lakers.id,
                        "success": True,
                    }
                )
                event_num += 1
        # OT events
        for clock in ["4:00", "2:00"]:
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": event_num,
                    "period": 5,
                    "clock": clock,
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )
            event_num += 1
        return game

    # Fixture-based validation
    def test_single_quarter_returns_expected(
        self, test_db: Session, game_with_events: Game
    ):
        """Q4 filter returns exactly Q4 events."""
        service = AnalyticsService(test_db)
        events = service.get_events_by_time(game_with_events.id, TimeFilter(period=4))
        assert len(events) == 3
        assert all(e.period == 4 for e in events)

    def test_multiple_quarters_returns_expected(
        self, test_db: Session, game_with_events: Game
    ):
        """Q3+Q4 returns union of both."""
        service = AnalyticsService(test_db)
        events = service.get_events_by_time(
            game_with_events.id, TimeFilter(periods=[3, 4])
        )
        assert len(events) == 6
        periods = {e.period for e in events}
        assert periods == {3, 4}

    # Property-based validation
    def test_all_events_in_filtered_period(
        self, test_db: Session, game_with_events: Game
    ):
        """ALL returned events have period == filter.period."""
        service = AnalyticsService(test_db)
        events = service.get_events_by_time(game_with_events.id, TimeFilter(period=2))
        for event in events:
            assert event.period == 2

    def test_all_events_within_time_range(
        self, test_db: Session, game_with_events: Game
    ):
        """ALL events have min <= time_remaining <= max."""
        service = AnalyticsService(test_db)
        f = TimeFilter(min_time_remaining=120, max_time_remaining=360)
        events = service.get_events_by_time(game_with_events.id, f)
        for event in events:
            secs = service._parse_clock_to_seconds(event.clock)
            assert 120 <= secs <= 360

    def test_garbage_time_excluded_has_large_margin(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Excluded events all have margin > 20."""
        service = AnalyticsService(test_db)
        pbp = PlayByPlayService(test_db)
        # Build 50-10 blowout (40 pts margin)
        for i in range(25):
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + i // 8,
                    "clock": "10:00",
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )
        for i in range(5):
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": 30 + i,
                    "period": 1,
                    "clock": "9:00",
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )
        # Q4 event in garbage time
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": 100,
                "period": 4,
                "clock": "3:00",
                "event_type": EventType.SHOT.value,
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        events = service.get_events_by_time(
            game.id, TimeFilter(period=4, exclude_garbage_time=True)
        )
        assert len(events) == 0

    def test_overtime_events_have_period_gte_5(
        self, test_db: Session, game_with_events: Game
    ):
        """OT filter returns only period >= 5."""
        service = AnalyticsService(test_db)
        events = service.get_events_by_time(game_with_events.id, TimeFilter(period=5))
        assert len(events) == 2
        for event in events:
            assert event.period >= 5

    # Edge cases
    def test_no_overtime_returns_empty(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Game without OT, OT filter returns empty."""
        service = AnalyticsService(test_db)
        pbp = PlayByPlayService(test_db)
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 4,
                "clock": "1:00",
                "event_type": EventType.SHOT.value,
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        events = service.get_events_by_time(game.id, TimeFilter(period=5))
        assert events == []

    def test_garbage_time_blowout(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Entire Q4 is garbage time in 30-point game."""
        service = AnalyticsService(test_db)
        pbp = PlayByPlayService(test_db)
        # 60-30 lead going into Q4
        for i in range(30):
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1 + i // 10,
                    "clock": "10:00",
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )
        for i in range(15):
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": 40 + i,
                    "period": 1 + i // 5,
                    "clock": "9:00",
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": tatum.id,
                    "team_id": celtics.id,
                    "success": True,
                }
            )
        # Q4 events
        for i, clock in enumerate(["11:00", "8:00", "4:00", "1:00"]):
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": 60 + i,
                    "period": 4,
                    "clock": clock,
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )

        all_q4 = service.get_events_by_time(game.id, TimeFilter(period=4))
        no_garbage = service.get_events_by_time(
            game.id, TimeFilter(period=4, exclude_garbage_time=True)
        )
        assert len(all_q4) == 4
        assert len(no_garbage) == 0

    def test_time_range_filter(self, test_db: Session, game_with_events: Game):
        """min/max time_remaining boundary conditions."""
        service = AnalyticsService(test_db)
        # Only events with exactly 5:00 (300 seconds)
        events = service.get_events_by_time(
            game_with_events.id,
            TimeFilter(min_time_remaining=300, max_time_remaining=300),
        )
        for event in events:
            assert event.clock == "5:00"


class TestGetPlayerStatsByQuarter:
    """Tests for AnalyticsService.get_player_stats_by_quarter()."""

    @pytest.fixture
    def league(self, test_db: Session) -> League:
        return LeagueService(test_db).create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )

    @pytest.fixture
    def season(self, test_db: Session, league: League) -> Season:
        return SeasonService(test_db).create_season(
            SeasonCreate(
                league_id=league.id,
                name="2023-24",
                start_date=date(2023, 10, 1),
                end_date=date(2024, 6, 1),
                is_current=True,
            )
        )

    @pytest.fixture
    def lakers(self, test_db: Session) -> Team:
        return TeamService(test_db).create_team(
            TeamCreate(name="Lakers", short_name="LAL", city="LA", country="USA")
        )

    @pytest.fixture
    def celtics(self, test_db: Session) -> Team:
        return TeamService(test_db).create_team(
            TeamCreate(name="Celtics", short_name="BOS", city="Boston", country="USA")
        )

    @pytest.fixture
    def lebron(self, test_db: Session) -> Player:
        return PlayerService(test_db).create_player(
            PlayerCreate(first_name="LeBron", last_name="James", position="SF")
        )

    @pytest.fixture
    def game(
        self, test_db: Session, season: Season, lakers: Team, celtics: Team
    ) -> Game:
        return GameService(test_db).create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

    @pytest.fixture
    def game_with_player_stats(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Create game with varied stats per quarter."""
        pbp = PlayByPlayService(test_db)
        event_num = 1
        # Q1: 6 pts (2 2PT made), 1 rebound, 1 assist
        for _ in range(2):
            pbp.create_event(
                {
                    "game_id": game.id,
                    "event_number": event_num,
                    "period": 1,
                    "clock": "10:00",
                    "event_type": EventType.SHOT.value,
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                }
            )
            event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 1,
                "clock": "8:00",
                "event_type": EventType.SHOT.value,
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,
            }
        )
        event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 1,
                "clock": "7:00",
                "event_type": EventType.REBOUND.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 1,
                "clock": "6:00",
                "event_type": EventType.ASSIST.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        event_num += 1

        # Q2: 5 pts (1 2PT + 1 3PT made)
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 2,
                "clock": "10:00",
                "event_type": EventType.SHOT.value,
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 2,
                "clock": "8:00",
                "event_type": EventType.SHOT.value,
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        event_num += 1

        # Q3: 2 FT made
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 3,
                "clock": "5:00",
                "event_type": EventType.FREE_THROW.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 3,
                "clock": "5:00",
                "event_type": EventType.FREE_THROW.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        event_num += 1

        # Q4: 1 steal, 1 block, 1 turnover
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 4,
                "clock": "3:00",
                "event_type": EventType.STEAL.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 4,
                "clock": "2:00",
                "event_type": EventType.BLOCK.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        event_num += 1
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 4,
                "clock": "1:00",
                "event_type": EventType.TURNOVER.value,
                "player_id": lebron.id,
                "team_id": lakers.id,
            }
        )
        event_num += 1

        # OT: 3 pts (1 3PT)
        pbp.create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": 5,
                "clock": "3:00",
                "event_type": EventType.SHOT.value,
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )
        return game

    def test_player_stats_by_quarter_match_expected(
        self, test_db: Session, game_with_player_stats: Game, lebron: Player
    ):
        """Verify per-quarter totals are correct."""
        service = AnalyticsService(test_db)
        stats = service.get_player_stats_by_quarter(
            lebron.id, game_with_player_stats.id
        )

        assert stats[1]["points"] == 4  # 2 x 2PT
        assert stats[1]["fgm"] == 2
        assert stats[1]["fga"] == 3
        assert stats[1]["rebounds"] == 1
        assert stats[1]["assists"] == 1

        assert stats[2]["points"] == 5  # 2PT + 3PT
        assert stats[2]["fg3m"] == 1
        assert stats[2]["fg3a"] == 1

        assert stats[3]["points"] == 2  # 2 FT
        assert stats[3]["ftm"] == 2
        assert stats[3]["fta"] == 2

        assert stats[4]["steals"] == 1
        assert stats[4]["blocks"] == 1
        assert stats[4]["turnovers"] == 1
        assert stats[4]["points"] == 0

        assert "OT" in stats
        assert stats["OT"]["points"] == 3
        assert stats["OT"]["fg3m"] == 1

    def test_quarter_stats_sum_to_game_totals(
        self, test_db: Session, game_with_player_stats: Game, lebron: Player
    ):
        """Q1+Q2+Q3+Q4+OT == game totals."""
        service = AnalyticsService(test_db)
        stats = service.get_player_stats_by_quarter(
            lebron.id, game_with_player_stats.id
        )

        total_pts = sum(stats[q]["points"] for q in [1, 2, 3, 4]) + stats.get(
            "OT", {}
        ).get("points", 0)
        total_reb = sum(stats[q]["rebounds"] for q in [1, 2, 3, 4]) + stats.get(
            "OT", {}
        ).get("rebounds", 0)
        total_ast = sum(stats[q]["assists"] for q in [1, 2, 3, 4]) + stats.get(
            "OT", {}
        ).get("assists", 0)

        assert total_pts == 4 + 5 + 2 + 0 + 3  # 14 total
        assert total_reb == 1
        assert total_ast == 1

    def test_empty_game_returns_empty_quarters(
        self, test_db: Session, game: Game, lebron: Player
    ):
        """Game with no events returns quarters with zeros."""
        service = AnalyticsService(test_db)
        stats = service.get_player_stats_by_quarter(lebron.id, game.id)
        for q in [1, 2, 3, 4]:
            assert stats[q]["points"] == 0
            assert stats[q]["rebounds"] == 0
        assert "OT" not in stats

    def test_nonexistent_game_returns_empty(self, test_db: Session, lebron: Player):
        """Non-existent game returns empty dict."""
        import uuid

        service = AnalyticsService(test_db)
        stats = service.get_player_stats_by_quarter(lebron.id, uuid.uuid4())
        assert stats == {}
