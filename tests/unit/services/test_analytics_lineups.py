"""Unit tests for lineup combination analysis."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
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
from src.services.stats import PlayerGameStatsService
from src.services.team import TeamService


class TestLineupStats:
    """Tests for lineup combination analysis."""

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
    def players(self, test_db: Session) -> list[Player]:
        """Create 6 Lakers players (5 starters + 1 bench)."""
        svc = PlayerService(test_db)
        names = [
            ("LeBron", "James"),
            ("Anthony", "Davis"),
            ("Austin", "Reaves"),
            ("DAngelo", "Russell"),
            ("Rui", "Hachimura"),
            ("Gabe", "Vincent"),
        ]
        return [
            svc.create_player(PlayerCreate(first_name=fn, last_name=ln, position="SF"))
            for fn, ln in names
        ]

    @pytest.fixture
    def opp_player(self, test_db: Session) -> Player:
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

    def _create_stats(self, db, game, player, team, is_starter=True):
        return PlayerGameStatsService(db).create_stats(
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
        num,
        period,
        clock,
        etype,
        team,
        player=None,
        sub=None,
        success=None,
    ):
        return PlayByPlayService(db).create_event(
            {
                "game_id": game.id,
                "event_number": num,
                "period": period,
                "clock": clock,
                "event_type": etype,
                "event_subtype": sub,
                "player_id": player.id if player else None,
                "team_id": team.id,
                "success": success,
            }
        )

    # Fixture-based validation
    def test_2man_lineup_stats_match_expected(
        self,
        test_db: Session,
        game: Game,
        players: list[Player],
        opp_player: Player,
        lakers: Team,
        celtics: Team,
    ):
        """LeBron+AD together for known stints, verify exact stats."""
        svc = AnalyticsService(test_db)
        lebron, ad = players[0], players[1]
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        # Both on: LeBron scores 2PT at 10:00, opp scores 3PT at 9:00
        # AD subs out at 6:00, LeBron scores 2PT at 5:00 (AD off - shouldn't count)
        # AD back in at 3:00, LeBron scores 3PT at 2:00
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "9:00", "SHOT", celtics, opp_player, "3PT", True
        )
        self._create_event(
            test_db, game, 3, 1, "6:00", "SUBSTITUTION", lakers, ad, "OUT"
        )
        self._create_event(
            test_db, game, 4, 1, "5:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 5, 1, "3:00", "SUBSTITUTION", lakers, ad, "IN"
        )
        self._create_event(
            test_db, game, 6, 1, "2:00", "SHOT", lakers, lebron, "3PT", True
        )

        stats = svc.get_lineup_stats([lebron.id, ad.id], game.id)

        assert stats["team_pts"] == 5  # 2+3 (not the 2PT when AD was out)
        assert stats["opp_pts"] == 3
        assert stats["plus_minus"] == 2

    def test_5man_lineup_stats_match_expected(
        self,
        test_db: Session,
        game: Game,
        players: list[Player],
        opp_player: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Full starting 5 stats match expected."""
        svc = AnalyticsService(test_db)
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        # All 5 on, team scores 2PT
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, players[0], "2PT", True
        )
        # One player subs out
        self._create_event(
            test_db, game, 2, 1, "8:00", "SUBSTITUTION", lakers, players[4], "OUT"
        )
        # Team scores 3PT (only 4 starters on - shouldn't count)
        self._create_event(
            test_db, game, 3, 1, "7:00", "SHOT", lakers, players[0], "3PT", True
        )

        stats = svc.get_lineup_stats([p.id for p in players[:5]], game.id)
        assert stats["team_pts"] == 2  # Only the first shot when all 5 on

    def test_best_lineups_returns_correct_order(
        self,
        test_db: Session,
        game: Game,
        players: list[Player],
        opp_player: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Verify sorted by plus_minus descending."""
        svc = AnalyticsService(test_db)
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        # Create scoring so different 2-man combos have different plus/minus
        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, players[0], "3PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "9:00", "SHOT", celtics, opp_player, "2PT", True
        )

        lineups = svc.get_best_lineups(
            lakers.id, game.id, lineup_size=2, min_minutes=0.0
        )

        # Verify sorted descending by plus_minus
        for i in range(len(lineups) - 1):
            assert lineups[i]["plus_minus"] >= lineups[i + 1]["plus_minus"]

    # Property-based validation
    def test_lineup_only_counts_when_all_on(
        self,
        test_db: Session,
        game: Game,
        players: list[Player],
        lakers: Team,
        celtics: Team,
    ):
        """ALL counted events occurred when ALL specified players on court."""
        svc = AnalyticsService(test_db)
        lebron, ad = players[0], players[1]
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        # AD subs out, scoring happens, AD comes back
        self._create_event(
            test_db, game, 1, 1, "8:00", "SUBSTITUTION", lakers, ad, "OUT"
        )
        self._create_event(
            test_db, game, 2, 1, "7:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 3, 1, "4:00", "SUBSTITUTION", lakers, ad, "IN"
        )

        stats = svc.get_lineup_stats([lebron.id, ad.id], game.id)
        # Shot at 7:00 when AD off shouldn't count
        assert stats["team_pts"] == 0

    def test_lineup_minutes_less_than_game(
        self, test_db: Session, game: Game, players: list[Player], lakers: Team
    ):
        """Lineup minutes <= total game minutes."""
        svc = AnalyticsService(test_db)
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        self._create_event(
            test_db, game, 1, 1, "6:00", "SUBSTITUTION", lakers, players[0], "OUT"
        )

        stats = svc.get_lineup_stats([p.id for p in players[:2]], game.id)
        assert stats["minutes"] <= 12.0  # One period max

    def test_best_lineups_all_have_min_minutes(
        self, test_db: Session, game: Game, players: list[Player], lakers: Team
    ):
        """ALL returned lineups have minutes >= min_minutes."""
        svc = AnalyticsService(test_db)
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        min_minutes = 5.0
        lineups = svc.get_best_lineups(
            lakers.id, game.id, lineup_size=2, min_minutes=min_minutes
        )

        for lineup in lineups:
            assert lineup["minutes"] >= min_minutes

    # Edge cases
    def test_players_never_on_together(
        self, test_db: Session, game: Game, players: list[Player], lakers: Team
    ):
        """Returns empty/zero stats when players never on together."""
        svc = AnalyticsService(test_db)
        lebron, ad = players[0], players[1]
        # 5 starters: 0,2,3,4,5 (not AD who is index 1)
        starters = [players[0], players[2], players[3], players[4], players[5]]
        for p in starters:
            self._create_stats(test_db, game, p, lakers, is_starter=True)
        self._create_stats(test_db, game, ad, lakers, is_starter=False)

        # LeBron starts, AD comes in when LeBron goes out
        self._create_event(
            test_db, game, 1, 1, "6:00", "SUBSTITUTION", lakers, lebron, "OUT"
        )
        self._create_event(
            test_db, game, 2, 1, "6:00", "SUBSTITUTION", lakers, ad, "IN"
        )

        stats = svc.get_lineup_stats([lebron.id, ad.id], game.id)
        assert stats["minutes"] == 0.0
        assert stats["team_pts"] == 0

    def test_single_player_lineup(
        self,
        test_db: Session,
        game: Game,
        players: list[Player],
        lakers: Team,
        celtics: Team,
    ):
        """1-man lineup equals that player's on-court stats."""
        svc = AnalyticsService(test_db)
        lebron = players[0]
        self._create_stats(test_db, game, lebron, lakers, is_starter=True)

        self._create_event(
            test_db, game, 1, 1, "10:00", "SHOT", lakers, lebron, "2PT", True
        )
        self._create_event(
            test_db, game, 2, 1, "6:00", "SUBSTITUTION", lakers, lebron, "OUT"
        )

        lineup_stats = svc.get_lineup_stats([lebron.id], game.id)
        on_off_stats = svc.get_player_on_off_stats(lebron.id, game.id)

        assert lineup_stats["team_pts"] == on_off_stats["on"]["team_pts"]
        assert lineup_stats["minutes"] == on_off_stats["on"]["minutes"]

    def test_min_minutes_filter(
        self, test_db: Session, game: Game, players: list[Player], lakers: Team
    ):
        """Filters out short stints."""
        svc = AnalyticsService(test_db)
        for p in players[:5]:
            self._create_stats(test_db, game, p, lakers, is_starter=True)

        # Sub out one player quickly to create short stint
        self._create_event(
            test_db, game, 1, 1, "11:00", "SUBSTITUTION", lakers, players[0], "OUT"
        )

        # With high min_minutes, should filter out lineups with short stints
        lineups = svc.get_best_lineups(
            lakers.id, game.id, lineup_size=5, min_minutes=10.0
        )
        assert len(lineups) == 0  # All 5-man lineups have < 10 min together

    def test_lineup_across_multiple_games(
        self,
        test_db: Session,
        season: Season,
        players: list[Player],
        lakers: Team,
        celtics: Team,
    ):
        """Season aggregation works correctly."""
        svc = AnalyticsService(test_db)
        game_svc = GameService(test_db)
        lebron, ad = players[0], players[1]

        # Game 1 - need 5 starters so both LeBron and AD are detected as on court
        game1 = game_svc.create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        for p in players[:5]:
            self._create_stats(test_db, game1, p, lakers)
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
        for p in players[:5]:
            self._create_stats(test_db, game2, p, lakers)
        self._create_event(
            test_db, game2, 1, 1, "10:00", "SHOT", lakers, lebron, "3PT", True
        )

        stats = svc.get_lineup_stats_for_season([lebron.id, ad.id], season.id)

        assert stats["team_pts"] == 5  # 2 + 3
        assert stats["games"] == 2
