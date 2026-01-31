"""
Unit tests for AnalyticsService season-level analytics methods.

Tests:
- get_clutch_stats_for_season(): Season clutch performance aggregation
- get_quarter_splits_for_season(): Quarter-by-quarter breakdown
- get_performance_trend(): Recent performance trend analysis
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

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
from src.services.stats import PlayerGameStatsService
from src.services.team import TeamService


class TestClutchStatsForSeason:
    """Tests for AnalyticsService.get_clutch_stats_for_season()."""

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

    def test_returns_zero_stats_for_empty_season(
        self, test_db: Session, nba_season: Season
    ):
        """Test that empty season returns zero-filled stats."""
        service = AnalyticsService(test_db)

        stats = service.get_clutch_stats_for_season(nba_season.id)

        assert stats.games_in_clutch == 0
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.fg_pct_clutch == 0.0
        assert stats.fg_pct_overall == 0.0

    def test_counts_clutch_games_correctly(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test that games with clutch events are counted."""
        game_service = GameService(test_db)
        pbp_service = PlayByPlayService(test_db)
        service = AnalyticsService(test_db)

        # Create a game with clutch events
        game = game_service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

        # Update game with final scores (Lakers win 100-98)
        game_service.update_score(game.id, home_score=100, away_score=98)

        # Create clutch event (Q4, 3:00 remaining, tied game)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 4,
                "clock": "3:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        stats = service.get_clutch_stats_for_season(nba_season.id, team_id=lakers.id)

        assert stats.games_in_clutch == 1
        assert stats.wins == 1
        assert stats.losses == 0

    def test_calculates_clutch_shooting_percentages(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test that clutch FG% is calculated correctly."""
        game_service = GameService(test_db)
        pbp_service = PlayByPlayService(test_db)
        player_stats_service = PlayerGameStatsService(test_db)
        service = AnalyticsService(test_db)

        game = game_service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

        # Create player game stats for overall comparison
        player_stats_service.create(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "field_goals_made": 10,
                "field_goals_attempted": 20,
                "three_pointers_made": 2,
                "three_pointers_attempted": 5,
                "free_throws_made": 5,
                "free_throws_attempted": 6,
            }
        )

        # Create clutch shots: 2 made, 1 missed (66.7%)
        for i, success in enumerate([True, True, False]):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 4,
                    "clock": f"{4 - i}:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": success,
                }
            )

        stats = service.get_clutch_stats_for_season(nba_season.id, player_id=lebron.id)

        assert stats.fg_pct_clutch == pytest.approx(0.667, rel=0.01)
        assert stats.fg_pct_overall == pytest.approx(0.5, rel=0.01)


class TestQuarterSplitsForSeason:
    """Tests for AnalyticsService.get_quarter_splits_for_season()."""

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

    def test_returns_empty_for_no_games(self, test_db: Session, nba_season: Season):
        """Test that empty season returns empty quarter stats."""
        service = AnalyticsService(test_db)

        splits = service.get_quarter_splits_for_season(nba_season.id)

        # Should have Q1-Q4 keys but with zero values
        assert "Q1" in splits
        assert "Q2" in splits
        assert "Q3" in splits
        assert "Q4" in splits
        assert splits["Q1"].points == 0.0

    def test_aggregates_by_quarter(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test that stats are correctly aggregated by quarter."""
        game_service = GameService(test_db)
        pbp_service = PlayByPlayService(test_db)
        service = AnalyticsService(test_db)

        game = game_service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

        # Q1: 2 made shots = 4 pts, Q2: 1 made 3PT = 3 pts
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
                "clock": "8:00",
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
                "event_number": 3,
                "period": 2,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
            }
        )

        splits = service.get_quarter_splits_for_season(nba_season.id, team_id=lakers.id)

        assert splits["Q1"].points == 4.0
        assert splits["Q2"].points == 3.0
        assert splits["Q3"].points == 0.0
        assert splits["Q4"].points == 0.0


class TestPerformanceTrend:
    """Tests for AnalyticsService.get_performance_trend()."""

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

    def test_requires_player_or_team(self, test_db: Session):
        """Test that ValueError is raised without player or team."""
        service = AnalyticsService(test_db)

        with pytest.raises(ValueError, match="Either player_id or team_id"):
            service.get_performance_trend("points")

    def test_returns_empty_for_no_games(
        self, test_db: Session, lebron: Player, nba_season: Season
    ):
        """Test that empty history returns zero values."""
        service = AnalyticsService(test_db)

        trend = service.get_performance_trend(
            "points", player_id=lebron.id, season_id=nba_season.id
        )

        assert trend.stat_name == "points"
        assert trend.values == []
        assert trend.average == 0.0
        assert trend.direction == "stable"

    def test_calculates_trend_correctly(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test that trend is calculated correctly from game stats."""
        game_service = GameService(test_db)
        player_stats_service = PlayerGameStatsService(test_db)
        service = AnalyticsService(test_db)

        # Create games with varying point totals
        point_values = [25, 30, 28, 22, 35]  # Avg: 28, Season avg same

        for i, pts in enumerate(point_values):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 10 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            player_stats_service.create(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": pts,
                }
            )

        trend = service.get_performance_trend(
            "points", last_n_games=5, player_id=lebron.id, season_id=nba_season.id
        )

        assert trend.stat_name == "points"
        assert len(trend.values) == 5
        assert trend.average == 28.0
        assert trend.season_average == 28.0
        assert trend.direction == "stable"  # Same as season avg

    def test_identifies_improving_trend(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test that improving trend is correctly identified."""
        game_service = GameService(test_db)
        player_stats_service = PlayerGameStatsService(test_db)
        service = AnalyticsService(test_db)

        # Season avg = 20, recent avg = 30 (50% improvement)
        point_values = [10, 10, 10, 10, 10, 30, 30, 30, 30, 30]

        for i, pts in enumerate(point_values):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 1 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            player_stats_service.create(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": pts,
                }
            )

        trend = service.get_performance_trend(
            "points", last_n_games=5, player_id=lebron.id, season_id=nba_season.id
        )

        assert trend.direction == "improving"
        assert trend.change_pct > 5  # > 5% threshold

    def test_identifies_declining_trend(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test that declining trend is correctly identified."""
        game_service = GameService(test_db)
        player_stats_service = PlayerGameStatsService(test_db)
        service = AnalyticsService(test_db)

        # Season avg = 20, recent avg = 10 (50% decline)
        point_values = [30, 30, 30, 30, 30, 10, 10, 10, 10, 10]

        for i, pts in enumerate(point_values):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, 1 + i, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            player_stats_service.create(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": pts,
                }
            )

        trend = service.get_performance_trend(
            "points", last_n_games=5, player_id=lebron.id, season_id=nba_season.id
        )

        assert trend.direction == "declining"
        assert trend.change_pct < -5  # < -5% threshold
