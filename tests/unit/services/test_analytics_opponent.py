"""
Unit tests for AnalyticsService opponent-based and home/away filters.

Tests opponent filtering and home/away splits with:
- Fixture-based validation: known scenarios with exact expected results
- Property-based validation: all results satisfy filter properties
- Edge cases: empty results, season filtering
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.analytics import OpponentFilter
from src.schemas.game import GameCreate, GameStatus
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.player import PlayerService
from src.services.stats import PlayerGameStatsService
from src.services.team import TeamService


class TestOpponentFilter:
    """Tests for OpponentFilter schema."""

    def test_opponent_filter_defaults(self):
        """Verify default values."""
        filter = OpponentFilter()

        assert filter.opponent_team_id is None
        assert filter.home_only is False
        assert filter.away_only is False

    def test_opponent_filter_with_opponent_id(self):
        """Test filter with opponent team specified."""
        opponent_id = uuid.uuid4()
        filter = OpponentFilter(opponent_team_id=opponent_id)

        assert filter.opponent_team_id == opponent_id
        assert filter.home_only is False
        assert filter.away_only is False

    def test_opponent_filter_home_only(self):
        """Test home_only filter."""
        filter = OpponentFilter(home_only=True)

        assert filter.home_only is True
        assert filter.away_only is False

    def test_opponent_filter_away_only(self):
        """Test away_only filter."""
        filter = OpponentFilter(away_only=True)

        assert filter.home_only is False
        assert filter.away_only is True

    def test_opponent_filter_home_away_mutual_exclusion(self):
        """Verify home_only and away_only cannot both be True."""
        with pytest.raises(
            ValueError, match="home_only and away_only cannot both be True"
        ):
            OpponentFilter(home_only=True, away_only=True)


class TestGetGamesVsOpponent:
    """Tests for AnalyticsService.get_games_vs_opponent()."""

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
    def another_season(self, test_db: Session, nba_league: League) -> Season:
        """Create another season for testing season filtering."""
        service = SeasonService(test_db)
        return service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2024-25",
                start_date=date(2024, 10, 22),
                end_date=date(2025, 6, 15),
                is_current=False,
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
    def warriors(self, test_db: Session) -> Team:
        """Create a Warriors team for testing."""
        service = TeamService(test_db)
        return service.create_team(
            TeamCreate(
                name="Golden State Warriors",
                short_name="GSW",
                city="San Francisco",
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

    # =========================================================================
    # Fixture-based tests: known scenarios with exact expected results
    # =========================================================================

    def test_get_games_vs_opponent_returns_expected(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        warriors: Team,
    ):
        """
        Create 10 games, 3 vs Celtics, verify exactly 3 returned.

        Scenario:
        - 3 games: Lakers vs Celtics
        - 4 games: Lakers vs Warriors
        - 3 games: Warriors vs Celtics (Lakers not involved)
        """
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)

        # 3 Lakers vs Celtics games
        for i in range(3):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id if i % 2 == 0 else celtics.id,
                    away_team_id=celtics.id if i % 2 == 0 else lakers.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        # 4 Lakers vs Warriors games
        for i in range(4):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=warriors.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        # 3 Warriors vs Celtics games (Lakers not involved)
        for i in range(3):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=warriors.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 3, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        # Get Lakers vs Celtics games
        games = service.get_games_vs_opponent(lakers.id, celtics.id)

        assert len(games) == 3

    def test_player_stats_vs_opponent_returns_expected(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        warriors: Team,
        lebron: Player,
    ):
        """Verify exact game stats returned for player vs opponent."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # Create 2 games: Lakers vs Celtics
        games_vs_celtics = []
        for i in range(2):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            games_vs_celtics.append(game)
            # Add LeBron stats
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 25 + i,
                    "total_rebounds": 8,
                    "assists": 10,
                }
            )

        # Create 3 games: Lakers vs Warriors (should not be returned)
        for i in range(3):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=warriors.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 30,
                    "total_rebounds": 7,
                    "assists": 8,
                }
            )

        # Get LeBron's stats vs Celtics
        stats = service.get_player_stats_vs_opponent(lebron.id, celtics.id)

        assert len(stats) == 2
        game_ids = {s.game_id for s in stats}
        for game in games_vs_celtics:
            assert game.id in game_ids

    def test_home_away_split_correct_games(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        warriors: Team,
        lebron: Player,
    ):
        """5 home, 5 away, verify split counts match."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # 5 home games for Lakers
        for i in range(5):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id if i % 2 == 0 else warriors.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 28,
                    "total_rebounds": 8,
                    "assists": 9,
                }
            )

        # 5 away games for Lakers
        for i in range(5):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=celtics.id if i % 2 == 0 else warriors.id,
                    away_team_id=lakers.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 24,
                    "total_rebounds": 7,
                    "assists": 8,
                }
            )

        split = service.get_player_home_away_split(lebron.id, nba_season.id)

        assert split["home"]["games"] == 5
        assert split["away"]["games"] == 5

    # =========================================================================
    # Property-based tests: all results satisfy filter properties
    # =========================================================================

    def test_all_games_vs_opponent_have_correct_teams(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        warriors: Team,
    ):
        """ALL returned games involve both teams."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)

        # Create various games
        for i in range(3):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        for i in range(2):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=warriors.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        games = service.get_games_vs_opponent(lakers.id, celtics.id)

        # Property: ALL returned games must involve both lakers and celtics
        for game in games:
            team_ids = {game.home_team_id, game.away_team_id}
            assert lakers.id in team_ids, f"Lakers not in game {game.id}"
            assert celtics.id in team_ids, f"Celtics not in game {game.id}"

    def test_all_home_games_have_player_team_as_home(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """ALL home stats from games where team is home_team_id."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # 3 home games
        for i in range(3):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 25,
                    "total_rebounds": 8,
                    "assists": 10,
                }
            )

        # 2 away games
        for i in range(2):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=celtics.id,
                    away_team_id=lakers.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 22,
                    "total_rebounds": 7,
                    "assists": 9,
                }
            )

        split = service.get_player_home_away_split(lebron.id, nba_season.id)

        # Get individual stats to verify
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        stmt = (
            select(PlayerGameStats)
            .options(joinedload(PlayerGameStats.game))
            .join(Game)
            .where(PlayerGameStats.player_id == lebron.id)
            .where(Game.season_id == nba_season.id)
        )
        all_stats = list(test_db.scalars(stmt).unique().all())

        home_count = 0
        for stat in all_stats:
            if stat.team_id == stat.game.home_team_id:
                home_count += 1

        assert split["home"]["games"] == home_count == 3

    def test_all_away_games_have_player_team_as_away(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """ALL away stats from games where team is away_team_id."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # 2 home games
        for i in range(2):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 25,
                    "total_rebounds": 8,
                    "assists": 10,
                }
            )

        # 4 away games
        for i in range(4):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=celtics.id,
                    away_team_id=lakers.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 22,
                    "total_rebounds": 7,
                    "assists": 9,
                }
            )

        split = service.get_player_home_away_split(lebron.id, nba_season.id)

        # Get individual stats to verify
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        stmt = (
            select(PlayerGameStats)
            .options(joinedload(PlayerGameStats.game))
            .join(Game)
            .where(PlayerGameStats.player_id == lebron.id)
            .where(Game.season_id == nba_season.id)
        )
        all_stats = list(test_db.scalars(stmt).unique().all())

        away_count = 0
        for stat in all_stats:
            if stat.team_id == stat.game.away_team_id:
                away_count += 1

        assert split["away"]["games"] == away_count == 4

    def test_home_away_split_totals_equal_season(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """home_games + away_games == total_games."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        total_games = 7

        # Create mixed home/away games
        for i in range(total_games):
            is_home = i < 4  # First 4 are home games
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id if is_home else celtics.id,
                    away_team_id=celtics.id if is_home else lakers.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 25,
                    "total_rebounds": 8,
                    "assists": 10,
                }
            )

        split = service.get_player_home_away_split(lebron.id, nba_season.id)

        # Property: home + away = total
        assert split["home"]["games"] + split["away"]["games"] == total_games

    # =========================================================================
    # Edge cases
    # =========================================================================

    def test_no_games_vs_opponent_returns_empty(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        warriors: Team,
    ):
        """Teams never played returns empty list."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)

        # Only create Lakers vs Warriors games (no Celtics)
        for i in range(3):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=warriors.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        # Lakers vs Celtics should return empty
        games = service.get_games_vs_opponent(lakers.id, celtics.id)

        assert games == []

    def test_filter_by_season(
        self,
        test_db: Session,
        nba_season: Season,
        another_season: Season,
        lakers: Team,
        celtics: Team,
    ):
        """Respects season_id parameter."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)

        # 2 games in nba_season
        for i in range(2):
            game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        # 3 games in another_season
        for i in range(3):
            game_service.create_game(
                GameCreate(
                    season_id=another_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 11, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )

        # Without season filter, should get all 5
        all_games = service.get_games_vs_opponent(lakers.id, celtics.id)
        assert len(all_games) == 5

        # With season filter, should get only that season's games
        season1_games = service.get_games_vs_opponent(
            lakers.id, celtics.id, season_id=nba_season.id
        )
        assert len(season1_games) == 2

        season2_games = service.get_games_vs_opponent(
            lakers.id, celtics.id, season_id=another_season.id
        )
        assert len(season2_games) == 3

    def test_player_stats_vs_opponent_empty_when_no_games(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        warriors: Team,
        lebron: Player,
    ):
        """Returns empty list when player has no games vs opponent."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # Only create Lakers vs Warriors games
        for i in range(3):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=warriors.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 30,
                    "total_rebounds": 8,
                    "assists": 10,
                }
            )

        # LeBron vs Celtics should return empty
        stats = service.get_player_stats_vs_opponent(lebron.id, celtics.id)

        assert stats == []

    def test_home_away_split_empty_season(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        lebron: Player,
    ):
        """Returns zeros when player has no games in season."""
        service = AnalyticsService(test_db)

        # No games created
        split = service.get_player_home_away_split(lebron.id, nba_season.id)

        assert split["home"]["games"] == 0
        assert split["away"]["games"] == 0
        assert split["home"]["avg_points"] == 0.0
        assert split["away"]["avg_points"] == 0.0

    def test_home_away_split_averages_calculated_correctly(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Verify averages are computed correctly."""
        service = AnalyticsService(test_db)
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # 2 home games with known stats
        home_points = [30, 20]  # avg = 25
        for i, pts in enumerate(home_points):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": pts,
                    "total_rebounds": 10,
                    "assists": 8,
                }
            )

        # 3 away games with known stats
        away_points = [15, 18, 12]  # avg = 15
        for i, pts in enumerate(away_points):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=celtics.id,
                    away_team_id=lakers.id,
                    game_date=datetime(2024, 2, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": pts,
                    "total_rebounds": 6,
                    "assists": 5,
                }
            )

        split = service.get_player_home_away_split(lebron.id, nba_season.id)

        assert split["home"]["games"] == 2
        assert split["home"]["points"] == 50
        assert split["home"]["avg_points"] == 25.0

        assert split["away"]["games"] == 3
        assert split["away"]["points"] == 45
        assert split["away"]["avg_points"] == 15.0
