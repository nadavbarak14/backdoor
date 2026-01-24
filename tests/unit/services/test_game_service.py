"""
Unit tests for GameService.

Tests game business logic including filtering, box score loading,
external ID lookup, and score updates.
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import PlayerGameStats, TeamGameStats
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.game import GameCreate, GameFilter, GameStatus, GameUpdate
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.player import PlayerService
from src.services.team import TeamService


class TestGameService:
    """Tests for GameService operations."""

    @pytest.fixture
    def nba_league(self, test_db: Session) -> League:
        """Create an NBA league for testing."""
        service = LeagueService(test_db)
        return service.create_league(
            LeagueCreate(
                name="NBA",
                code="NBA",
                country="USA",
            )
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
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                position="SF",
            )
        )

    @pytest.fixture
    def tatum(self, test_db: Session) -> Player:
        """Create Jayson Tatum for testing."""
        service = PlayerService(test_db)
        return service.create_player(
            PlayerCreate(
                first_name="Jayson",
                last_name="Tatum",
                position="SF",
            )
        )

    def test_create_game(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test creating a game from Pydantic schema."""
        service = GameService(test_db)
        game_date = datetime(2024, 1, 15, 19, 30, tzinfo=UTC)
        data = GameCreate(
            season_id=nba_season.id,
            home_team_id=lakers.id,
            away_team_id=celtics.id,
            game_date=game_date,
            venue="Crypto.com Arena",
            external_ids={"winner": "123"},
        )

        game = service.create_game(data)

        assert game.id is not None
        assert game.season_id == nba_season.id
        assert game.home_team_id == lakers.id
        assert game.away_team_id == celtics.id
        assert game.status == "SCHEDULED"
        assert game.venue == "Crypto.com Arena"
        assert game.external_ids == {"winner": "123"}

    def test_create_game_without_external_ids(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test creating a game without external_ids defaults to empty dict."""
        service = GameService(test_db)
        data = GameCreate(
            season_id=nba_season.id,
            home_team_id=lakers.id,
            away_team_id=celtics.id,
            game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
        )

        game = service.create_game(data)

        assert game.external_ids == {}

    def test_update_game(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test updating a game from Pydantic schema."""
        service = GameService(test_db)
        game = service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )

        updated = service.update_game(
            game.id,
            GameUpdate(
                status=GameStatus.FINAL,
                home_score=112,
                away_score=108,
                attendance=18997,
            ),
        )

        assert updated is not None
        assert updated.status == "FINAL"
        assert updated.home_score == 112
        assert updated.away_score == 108
        assert updated.attendance == 18997

    def test_update_score(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test updating game score and status."""
        service = GameService(test_db)
        game = service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )

        updated = service.update_score(
            game.id,
            home_score=115,
            away_score=105,
            status=GameStatus.FINAL,
        )

        assert updated is not None
        assert updated.home_score == 115
        assert updated.away_score == 105
        assert updated.status == "FINAL"

    def test_get_by_external_id_found(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test finding a game by external ID."""
        service = GameService(test_db)
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                external_ids={"winner": "12345", "nba": "0022300567"},
            )
        )

        result = service.get_by_external_id("winner", "12345")

        assert result is not None
        assert result.home_team.name == "Los Angeles Lakers"
        assert result.away_team.name == "Boston Celtics"

    def test_get_by_external_id_not_found(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test get_by_external_id returns None for non-existent ID."""
        service = GameService(test_db)
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                external_ids={"winner": "12345"},
            )
        )

        result = service.get_by_external_id("winner", "99999")

        assert result is None

    def test_get_filtered_by_season(
        self, test_db: Session, nba_league: League, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test filtering games by season."""
        service = GameService(test_db)
        season_service = SeasonService(test_db)

        other_season = season_service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )

        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )
        service.create_game(
            GameCreate(
                season_id=other_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2023, 1, 15, 19, 30, tzinfo=UTC),
            )
        )

        games, total = service.get_filtered(GameFilter(season_id=nba_season.id))

        assert total == 1
        assert len(games) == 1
        assert games[0].season_id == nba_season.id

    def test_get_filtered_by_team(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test filtering games by team (home or away)."""
        service = GameService(test_db)
        team_service = TeamService(test_db)

        warriors = team_service.create_team(
            TeamCreate(
                name="Golden State Warriors",
                short_name="GSW",
                city="San Francisco",
                country="USA",
            )
        )

        # Lakers vs Celtics
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )
        # Warriors vs Celtics (Lakers not in this game)
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=warriors.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 16, 19, 30, tzinfo=UTC),
            )
        )

        games, total = service.get_filtered(GameFilter(team_id=lakers.id))

        assert total == 1
        assert len(games) == 1

    def test_get_filtered_by_date_range(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test filtering games by date range."""
        service = GameService(test_db)

        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 10, 19, 30, tzinfo=UTC),
            )
        )
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 20, 19, 30, tzinfo=UTC),
            )
        )
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 30, 19, 30, tzinfo=UTC),
            )
        )

        games, total = service.get_filtered(
            GameFilter(start_date=date(2024, 1, 15), end_date=date(2024, 1, 25))
        )

        assert total == 1
        assert len(games) == 1

    def test_get_filtered_by_status(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test filtering games by status."""
        service = GameService(test_db)

        game1 = service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 20, 19, 30, tzinfo=UTC),
                status=GameStatus.SCHEDULED,
            )
        )

        games, total = service.get_filtered(GameFilter(status=GameStatus.FINAL))

        assert total == 1
        assert len(games) == 1
        assert games[0].id == game1.id

    def test_get_filtered_pagination(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test filtered results respect pagination."""
        service = GameService(test_db)

        for i in range(5):
            service.create_game(
                GameCreate(
                    season_id=nba_season.id,
                    home_team_id=lakers.id,
                    away_team_id=celtics.id,
                    game_date=datetime(2024, 1, i + 1, 19, 30, tzinfo=UTC),
                )
            )

        games, total = service.get_filtered(GameFilter(), skip=2, limit=2)

        assert total == 5
        assert len(games) == 2

    def test_get_by_team(
        self, test_db: Session, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test getting games for a specific team."""
        service = GameService(test_db)
        team_service = TeamService(test_db)

        warriors = team_service.create_team(
            TeamCreate(
                name="Golden State Warriors",
                short_name="GSW",
                city="San Francisco",
                country="USA",
            )
        )

        # Lakers home game
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )
        # Lakers away game
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=warriors.id,
                away_team_id=lakers.id,
                game_date=datetime(2024, 1, 16, 19, 30, tzinfo=UTC),
            )
        )
        # Game without Lakers
        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=warriors.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 17, 19, 30, tzinfo=UTC),
            )
        )

        games, total = service.get_by_team(lakers.id)

        assert total == 2
        assert len(games) == 2

    def test_get_by_team_with_season_filter(
        self, test_db: Session, nba_league: League, nba_season: Season, lakers: Team, celtics: Team
    ):
        """Test getting games for a team filtered by season."""
        service = GameService(test_db)
        season_service = SeasonService(test_db)

        old_season = season_service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )

        service.create_game(
            GameCreate(
                season_id=nba_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
            )
        )
        service.create_game(
            GameCreate(
                season_id=old_season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2023, 1, 15, 19, 30, tzinfo=UTC),
            )
        )

        games, total = service.get_by_team(lakers.id, season_id=nba_season.id)

        assert total == 1
        assert len(games) == 1
        assert games[0].season_id == nba_season.id

    def test_get_with_box_score(
        self,
        test_db: Session,
        nba_season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
        tatum: Player,
    ):
        """Test getting a game with all box score data loaded."""
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

        # Add player stats
        lebron_stats = PlayerGameStats(
            game_id=game.id,
            player_id=lebron.id,
            team_id=lakers.id,
            points=25,
            assists=8,
            total_rebounds=7,
        )
        tatum_stats = PlayerGameStats(
            game_id=game.id,
            player_id=tatum.id,
            team_id=celtics.id,
            points=30,
            assists=5,
            total_rebounds=9,
        )
        test_db.add_all([lebron_stats, tatum_stats])

        # Add team stats
        lakers_stats = TeamGameStats(
            game_id=game.id,
            team_id=lakers.id,
            is_home=True,
            points=112,
        )
        celtics_stats = TeamGameStats(
            game_id=game.id,
            team_id=celtics.id,
            is_home=False,
            points=108,
        )
        test_db.add_all([lakers_stats, celtics_stats])
        test_db.commit()

        result = service.get_with_box_score(game.id)

        assert result is not None
        assert result.home_team.name == "Los Angeles Lakers"
        assert result.away_team.name == "Boston Celtics"
        assert len(result.player_game_stats) == 2
        assert len(result.team_game_stats) == 2

    def test_get_with_box_score_not_found(self, test_db: Session):
        """Test get_with_box_score returns None for non-existent game."""
        service = GameService(test_db)
        fake_id = uuid.uuid4()

        result = service.get_with_box_score(fake_id)

        assert result is None
