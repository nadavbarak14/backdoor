"""
Unit tests for PlayerGameStatsService and TeamGameStatsService.

Tests statistics business logic including per-game retrieval,
game logs, bulk creation, and team stats aggregation.
"""

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
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.player import PlayerService
from src.services.stats import PlayerGameStatsService, TeamGameStatsService
from src.services.team import TeamService


class TestPlayerGameStatsService:
    """Tests for PlayerGameStatsService operations."""

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
        game = service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        service.update_score(game.id, home_score=112, away_score=108)
        return game

    def test_create_stats(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Test creating player game stats."""
        service = PlayerGameStatsService(test_db)

        stats = service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "minutes_played": 2040,  # 34 minutes
                "points": 25,
                "field_goals_made": 9,
                "field_goals_attempted": 18,
                "three_pointers_made": 2,
                "three_pointers_attempted": 5,
                "assists": 8,
                "total_rebounds": 7,
                "is_starter": True,
            }
        )

        assert stats.id is not None
        assert stats.game_id == game.id
        assert stats.player_id == lebron.id
        assert stats.points == 25
        assert stats.is_starter is True
        assert stats.extra_stats == {}

    def test_get_by_game(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        ad: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Test getting all player stats for a game."""
        service = PlayerGameStatsService(test_db)

        service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
                "is_starter": True,
            }
        )
        service.create_stats(
            {
                "game_id": game.id,
                "player_id": ad.id,
                "team_id": lakers.id,
                "points": 20,
                "is_starter": True,
            }
        )
        service.create_stats(
            {
                "game_id": game.id,
                "player_id": tatum.id,
                "team_id": celtics.id,
                "points": 30,
                "is_starter": True,
            }
        )

        stats = service.get_by_game(game.id)

        assert len(stats) == 3
        # Verify players are loaded
        for stat in stats:
            assert stat.player is not None
            assert stat.team is not None

    def test_get_by_game_and_team(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        ad: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Test getting player stats for one team in a game."""
        service = PlayerGameStatsService(test_db)

        service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
            }
        )
        service.create_stats(
            {"game_id": game.id, "player_id": ad.id, "team_id": lakers.id, "points": 20}
        )
        service.create_stats(
            {
                "game_id": game.id,
                "player_id": tatum.id,
                "team_id": celtics.id,
                "points": 30,
            }
        )

        lakers_stats = service.get_by_game_and_team(game.id, lakers.id)

        assert len(lakers_stats) == 2
        for stat in lakers_stats:
            assert stat.team_id == lakers.id

    def test_get_player_game_log(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test getting a player's game log."""
        game_service = GameService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        # Create multiple games and stats
        for i in range(3):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, i + 10, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            game_service.update_score(game.id, home_score=110 + i, away_score=100 + i)
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "points": 20 + i,
                }
            )

        game_log, total = stats_service.get_player_game_log(lebron.id)

        assert total == 3
        assert len(game_log) == 3
        # Verify game context is loaded
        for stat in game_log:
            assert stat.game is not None
            assert stat.game.home_team is not None
            assert stat.game.away_team is not None

    def test_get_player_game_log_with_season_filter(
        self,
        test_db: Session,
        nba_league: League,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Test getting a player's game log filtered by season."""
        game_service = GameService(test_db)
        season_service = SeasonService(test_db)
        stats_service = PlayerGameStatsService(test_db)

        old_season = season_service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )

        # Current season game
        game1 = game_service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )
        stats_service.create_stats(
            {
                "game_id": game1.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
            }
        )

        # Old season game
        game2 = game_service.create_game(
            GameCreate(
                season_id=old_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2023, 1, 15, 19, 30, tzinfo=UTC),
            )
        )
        stats_service.create_stats(
            {
                "game_id": game2.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 20,
            }
        )

        game_log, total = stats_service.get_player_game_log(
            lebron.id, season_id=nba_season.id
        )

        assert total == 1
        assert len(game_log) == 1

    def test_get_by_player_and_game(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Test getting stats for a specific player in a specific game."""
        service = PlayerGameStatsService(test_db)

        service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
            }
        )

        stats = service.get_by_player_and_game(lebron.id, game.id)

        assert stats is not None
        assert stats.points == 25

    def test_get_by_player_and_game_not_found(
        self, test_db: Session, game: Game, lebron: Player
    ):
        """Test get_by_player_and_game returns None when not found."""
        service = PlayerGameStatsService(test_db)

        stats = service.get_by_player_and_game(lebron.id, game.id)

        assert stats is None

    def test_bulk_create(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        ad: Player,
        lakers: Team,
    ):
        """Test bulk creating player stats."""
        service = PlayerGameStatsService(test_db)

        stats_list = [
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
            },
            {
                "game_id": game.id,
                "player_id": ad.id,
                "team_id": lakers.id,
                "points": 20,
            },
        ]

        created = service.bulk_create(stats_list)

        assert len(created) == 2
        for stat in created:
            assert stat.id is not None
            assert stat.extra_stats == {}

    def test_update_stats(
        self, test_db: Session, game: Game, lebron: Player, lakers: Team
    ):
        """Test updating player game stats."""
        service = PlayerGameStatsService(test_db)

        service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
            }
        )

        updated = service.update_stats(
            game.id, lebron.id, {"points": 30, "assists": 10}
        )

        assert updated is not None
        assert updated.points == 30
        assert updated.assists == 10

    def test_update_stats_not_found(self, test_db: Session, game: Game, lebron: Player):
        """Test update_stats returns None when not found."""
        service = PlayerGameStatsService(test_db)

        updated = service.update_stats(game.id, lebron.id, {"points": 30})

        assert updated is None


class TestTeamGameStatsService:
    """Tests for TeamGameStatsService operations."""

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
        game = service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        service.update_score(game.id, home_score=112, away_score=108)
        return game

    def test_create_stats(self, test_db: Session, game: Game, lakers: Team):
        """Test creating team game stats."""
        service = TeamGameStatsService(test_db)

        stats = service.create_stats(
            {
                "game_id": game.id,
                "team_id": lakers.id,
                "is_home": True,
                "points": 112,
                "field_goals_made": 42,
                "field_goals_attempted": 88,
                "fast_break_points": 18,
                "points_in_paint": 52,
            }
        )

        assert stats.game_id == game.id
        assert stats.team_id == lakers.id
        assert stats.is_home is True
        assert stats.points == 112
        assert stats.fast_break_points == 18
        assert stats.extra_stats == {}

    def test_get_by_game(
        self, test_db: Session, game: Game, lakers: Team, celtics: Team
    ):
        """Test getting both team stats for a game."""
        service = TeamGameStatsService(test_db)

        service.create_stats(
            {"game_id": game.id, "team_id": lakers.id, "is_home": True, "points": 112}
        )
        service.create_stats(
            {"game_id": game.id, "team_id": celtics.id, "is_home": False, "points": 108}
        )

        stats = service.get_by_game(game.id)

        assert len(stats) == 2
        # Home team should be first (ordered by is_home desc)
        assert stats[0].is_home is True
        assert stats[1].is_home is False

    def test_get_by_team_and_game(
        self, test_db: Session, game: Game, lakers: Team, celtics: Team
    ):
        """Test getting stats for a specific team in a game."""
        service = TeamGameStatsService(test_db)

        service.create_stats(
            {"game_id": game.id, "team_id": lakers.id, "is_home": True, "points": 112}
        )
        service.create_stats(
            {"game_id": game.id, "team_id": celtics.id, "is_home": False, "points": 108}
        )

        lakers_stats = service.get_by_team_and_game(lakers.id, game.id)

        assert lakers_stats is not None
        assert lakers_stats.points == 112
        assert lakers_stats.is_home is True

    def test_get_by_team_and_game_not_found(
        self, test_db: Session, game: Game, lakers: Team
    ):
        """Test get_by_team_and_game returns None when not found."""
        service = TeamGameStatsService(test_db)

        stats = service.get_by_team_and_game(lakers.id, game.id)

        assert stats is None

    def test_get_team_game_history(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
    ):
        """Test getting a team's game history."""
        game_service = GameService(test_db)
        stats_service = TeamGameStatsService(test_db)

        for i in range(3):
            game = game_service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id if i % 2 == 0 else celtics.id,
                    away_team_id=celtics.id if i % 2 == 0 else lakers.id,
                    game_date=datetime(2024, 1, i + 10, 19, 30, tzinfo=UTC),
                    status=GameStatus.FINAL,
                )
            )
            stats_service.create_stats(
                {
                    "game_id": game.id,
                    "team_id": lakers.id,
                    "is_home": i % 2 == 0,
                    "points": 100 + i,
                }
            )

        history, total = stats_service.get_team_game_history(lakers.id)

        assert total == 3
        assert len(history) == 3
        # Verify game context is loaded
        for stat in history:
            assert stat.game is not None
            assert stat.game.home_team is not None
            assert stat.game.away_team is not None

    def test_update_stats(self, test_db: Session, game: Game, lakers: Team):
        """Test updating team game stats."""
        service = TeamGameStatsService(test_db)

        service.create_stats(
            {"game_id": game.id, "team_id": lakers.id, "is_home": True, "points": 112}
        )

        updated = service.update_stats(
            game.id, lakers.id, {"points": 115, "assists": 28}
        )

        assert updated is not None
        assert updated.points == 115
        assert updated.assists == 28

    def test_update_stats_not_found(self, test_db: Session, game: Game, lakers: Team):
        """Test update_stats returns None when not found."""
        service = TeamGameStatsService(test_db)

        updated = service.update_stats(game.id, lakers.id, {"points": 115})

        assert updated is None

    def test_calculate_from_player_stats(
        self,
        test_db: Session,
        game: Game,
        lakers: Team,
        lebron: Player,
        ad: Player,
    ):
        """Test calculating team stats from player stats."""
        player_stats_service = PlayerGameStatsService(test_db)
        team_stats_service = TeamGameStatsService(test_db)

        # Create player stats
        player_stats_service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
                "assists": 8,
                "total_rebounds": 7,
                "field_goals_made": 9,
                "field_goals_attempted": 18,
                "is_starter": True,
            }
        )
        player_stats_service.create_stats(
            {
                "game_id": game.id,
                "player_id": ad.id,
                "team_id": lakers.id,
                "points": 20,
                "assists": 3,
                "total_rebounds": 12,
                "field_goals_made": 8,
                "field_goals_attempted": 15,
                "is_starter": True,
            }
        )

        team_stats = team_stats_service.calculate_from_player_stats(game.id, lakers.id)

        assert team_stats is not None
        assert team_stats.points == 45  # 25 + 20
        assert team_stats.assists == 11  # 8 + 3
        assert team_stats.total_rebounds == 19  # 7 + 12
        assert team_stats.field_goals_made == 17  # 9 + 8
        assert team_stats.field_goals_attempted == 33  # 18 + 15
        assert team_stats.is_home is True
        assert team_stats.bench_points == 0  # Both are starters

    def test_calculate_from_player_stats_with_bench(
        self,
        test_db: Session,
        game: Game,
        lakers: Team,
        lebron: Player,
        ad: Player,
    ):
        """Test calculating team stats correctly calculates bench points."""
        player_stats_service = PlayerGameStatsService(test_db)
        team_stats_service = TeamGameStatsService(test_db)

        # LeBron is starter, AD comes off bench
        player_stats_service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
                "is_starter": True,
            }
        )
        player_stats_service.create_stats(
            {
                "game_id": game.id,
                "player_id": ad.id,
                "team_id": lakers.id,
                "points": 20,
                "is_starter": False,
            }
        )

        team_stats = team_stats_service.calculate_from_player_stats(game.id, lakers.id)

        assert team_stats is not None
        assert team_stats.points == 45
        assert team_stats.bench_points == 20  # Only AD's points

    def test_calculate_from_player_stats_no_players(
        self, test_db: Session, game: Game, lakers: Team
    ):
        """Test calculate_from_player_stats returns None when no player stats."""
        service = TeamGameStatsService(test_db)

        team_stats = service.calculate_from_player_stats(game.id, lakers.id)

        assert team_stats is None

    def test_calculate_from_player_stats_updates_existing(
        self,
        test_db: Session,
        game: Game,
        lakers: Team,
        lebron: Player,
    ):
        """Test calculate_from_player_stats updates existing stats."""
        player_stats_service = PlayerGameStatsService(test_db)
        team_stats_service = TeamGameStatsService(test_db)

        # Create existing team stats with some team-only stats
        team_stats_service.create_stats(
            {
                "game_id": game.id,
                "team_id": lakers.id,
                "is_home": True,
                "points": 100,  # Will be overwritten
                "fast_break_points": 18,  # Should be preserved
                "points_in_paint": 52,  # Should be preserved
            }
        )

        # Create player stats
        player_stats_service.create_stats(
            {
                "game_id": game.id,
                "player_id": lebron.id,
                "team_id": lakers.id,
                "points": 25,
            }
        )

        team_stats = team_stats_service.calculate_from_player_stats(game.id, lakers.id)

        assert team_stats is not None
        assert team_stats.points == 25  # Updated from player stats
        assert team_stats.fast_break_points == 18  # Preserved
        assert team_stats.points_in_paint == 52  # Preserved
