"""Unit tests for player on/off court analysis."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.game import GameCreate, GameStatus
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.stats import PlayerGameStatsService
from src.services.team import TeamService
from src.schemas.enums import GameStatus, Position


class TestPlayerOnOffStats:
    """Tests for player on/off court analysis."""

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

    def _create_player_stats(self, db, game, player, team, is_starter=True):
        """Helper to create PlayerGameStats."""
        svc = PlayerGameStatsService(db)
        return svc.create_stats(
            {
                "game_id": game.id,
                "player_id": player.id,
                "team_id": team.id,
                "is_starter": is_starter,
                "minutes_played": 1800,
                "points": 20,
                "total_rebounds": 5,
                "assists": 5,
            }
        )

    def _create_event(
        self,
        db,
        game,
        event_num,
        period,
        clock,
        event_type,
        team,
        player=None,
        subtype=None,
        success=None,
    ):
        """Helper to create PBP event."""
        return PlayByPlayService(db).create_event(
            {
                "game_id": game.id,
                "event_number": event_num,
                "period": period,
                "clock": clock,
                "event_type": event_type,
                "event_subtype": subtype,
                "player_id": player.id if player else None,
                "team_id": team.id,
                "success": success,
            }
        )

    def test_on_off_stats_match_expected(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Player on for stints with known scoring - verify exact totals."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        # LeBron starts on, scores 2PT at 10:00, opponent scores 3PT at 9:00
        # LeBron subs out at 6:00, opponent scores 2PT at 5:00
        # LeBron subs in at 3:00, scores 3PT at 2:00
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "9:00", "SHOT", celtics, tatum, "3PT", True
        )
        self._create_event(
            test_db, game, 3, 1, "6:00", "SUBSTITUTION", lakers, lebron, "OUT"
        )
        self._create_event(
            test_db, game, 4, 1, "5:00", "SHOT", celtics, tatum, "2PT", True
        )
        self._create_event(
            test_db, game, 5, 1, "3:00", "SUBSTITUTION", lakers, lebron, "IN"
        )
        self._create_event(
            test_db, game, 6, 1, "2:00", "SHOT", lakers, lebron, "3PT", True
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)

        # On court: team=5 (2+3), opp=3
        assert stats["on"]["team_pts"] == 5
        assert stats["on"]["opp_pts"] == 3
        assert stats["on"]["plus_minus"] == 2
        # Off court: team=0, opp=2
        assert stats["off"]["team_pts"] == 0
        assert stats["off"]["opp_pts"] == 2
        assert stats["off"]["plus_minus"] == -2

    def test_on_minutes_plus_off_minutes_equals_game(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Total on + off minutes should equal game duration."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        # Create events spanning Q1 only (12 min)
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "6:00", "SUBSTITUTION", lakers, lebron, "OUT"
        )
        self._create_event(
            test_db, game, 3, 1, "3:00", "SUBSTITUTION", lakers, lebron, "IN"
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        total_minutes = stats["on"]["minutes"] + stats["off"]["minutes"]
        assert total_minutes == 12.0  # One period = 12 min

    def test_on_off_team_pts_from_valid_events(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """All counted points must come from SHOT/FREE_THROW with success=True."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        # Made shot - should count
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        # Missed shot - should not count
        self._create_event(
            test_db, game, 2, 1, "9:00", "SHOT", lakers, lebron, "3PT", False
        )
        # Made FT - should count
        self._create_event(
            test_db, game, 3, 1, "8:00", "FREE_THROW", lakers, lebron, None, True
        )
        # Rebound - should not count
        self._create_event(
            test_db, game, 4, 1, "7:00", "REBOUND", lakers, lebron, "OFFENSIVE"
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        assert stats["on"]["team_pts"] == 3  # 2PT + 1FT

    def test_on_stints_player_was_on_court(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Verify scoring during 'on' periods happened while player was on court."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        # LeBron on from start, subs out at 6:00
        # Score at 8:00 (on court) and 4:00 (off court)
        self._create_event(
            test_db, game, 1, 1, "8:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "6:00", "SUBSTITUTION", lakers, lebron, "OUT"
        )
        self._create_event(
            test_db, game, 3, 1, "4:00", "SHOT", celtics, tatum, "2PT", True
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        # 8:00 shot when LeBron on -> on_team_pts
        assert stats["on"]["team_pts"] == 2
        # 4:00 shot when LeBron off -> off_opp_pts
        assert stats["off"]["opp_pts"] == 2

    def test_off_stints_player_was_off_court(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Verify scoring during 'off' periods happened while player was off court."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        self._create_event(
            test_db, game, 1, 1, "10:00", "SUBSTITUTION", lakers, lebron, "OUT"
        )
        self._create_event(
            test_db, game, 2, 1, "8:00", "SHOT", celtics, tatum, "3PT", True
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        assert stats["off"]["opp_pts"] == 3
        assert stats["on"]["opp_pts"] == 0

    def test_plus_minus_equals_team_minus_opp(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Verify plus_minus == team_pts - opp_pts."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "9:00", "SHOT", celtics, tatum, "3PT", True
        )
        self._create_event(
            test_db, game, 3, 1, "8:00", "SHOT", lakers, lebron, "3PT", True
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        assert (
            stats["on"]["plus_minus"]
            == stats["on"]["team_pts"] - stats["on"]["opp_pts"]
        )
        assert (
            stats["off"]["plus_minus"]
            == stats["off"]["team_pts"] - stats["off"]["opp_pts"]
        )

    def test_starter_begins_on_court(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team, celtics: Team
    ):
        """Starters should begin as 'on' court."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        # Score before any substitution
        self._create_event(
            test_db, game, 1, 1, "11:00", "SHOT", lakers, lebron, "2PT", True
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        assert stats["on"]["team_pts"] == 2  # Counted as "on"
        assert stats["off"]["team_pts"] == 0

    def test_player_never_subbed_out(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Player who plays full game has all minutes as 'on'."""
        svc = AnalyticsService(test_db)
        self._create_player_stats(test_db, game, lebron, lakers, is_starter=True)

        # No substitution events for LeBron - played full Q1
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "5:00", "SHOT", celtics, tatum, "3PT", True
        )

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        assert stats["on"]["minutes"] == 12.0
        assert stats["off"]["minutes"] == 0.0
        assert stats["on"]["team_pts"] == 2
        assert stats["on"]["opp_pts"] == 3

    def test_player_dnp_returns_zero_on(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Player who didn't play returns zeros."""
        svc = AnalyticsService(test_db)
        # No PlayerGameStats for LeBron - DNP

        stats = svc.get_player_on_off_stats(lebron.id, game.id)
        assert stats["on"]["team_pts"] == 0
        assert stats["on"]["minutes"] == 0.0
        assert stats["off"]["minutes"] == 0.0

    def test_season_aggregates_multiple_games(
        self,
        test_db: Session,
        season: Season,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Season stats aggregate across multiple games correctly."""
        svc = AnalyticsService(test_db)
        game_svc = GameService(test_db)

        # Game 1
        game1 = game_svc.create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        self._create_player_stats(test_db, game1, lebron, lakers, is_starter=True)
        self._create_event(
            test_db, game1, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )

        # Game 2
        game2 = game_svc.create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 20, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        self._create_player_stats(test_db, game2, lebron, lakers, is_starter=True)
        self._create_event(
            test_db, game2, 1, 1, "10:00", "SHOT", lakers, lebron, "3PT", True
        )

        stats = svc.get_player_on_off_for_season(lebron.id, season.id)
        assert stats["on"]["team_pts"] == 5  # 2 + 3
        assert stats["on"]["games"] == 2
        assert stats["off"]["games"] == 2
