"""
Tests for services with real data.
"""

from sqlalchemy.orm import Session


class TestLeagueService:
    """Tests for LeagueService."""

    def test_get_all_with_counts(self, real_db: Session):
        from src.services.league import LeagueService
        service = LeagueService(real_db)
        leagues = service.get_all_with_season_counts()
        assert len(leagues) >= 1
        league, count = leagues[0]
        assert league.id is not None


class TestTeamService:
    """Tests for TeamService."""

    def test_get_all(self, real_db: Session):
        from src.services.team import TeamService
        service = TeamService(real_db)
        teams = service.get_all()
        assert len(teams) >= 10


class TestPlayerService:
    """Tests for PlayerService."""

    def test_get_all(self, real_db: Session):
        from src.services.player import PlayerService
        service = PlayerService(real_db)
        players = service.get_all()
        assert len(players) >= 100


class TestGameService:
    """Tests for GameService."""

    def test_get_all(self, real_db: Session):
        from src.services.game import GameService
        service = GameService(real_db)
        games = service.get_all()
        assert len(games) >= 50

    def test_get_with_box_score(self, real_db: Session):
        from src.models.game import Game
        from src.services.game import GameService
        service = GameService(real_db)
        game = real_db.query(Game).first()
        result = service.get_with_box_score(game.id)
        assert result is not None


class TestPlayerGameStatsService:
    """Tests for PlayerGameStatsService."""

    def test_get_by_game(self, real_db: Session):
        from src.models.game import Game
        from src.services.stats import PlayerGameStatsService
        service = PlayerGameStatsService(real_db)
        game = real_db.query(Game).first()
        stats = service.get_by_game(game.id)
        assert len(stats) >= 1


class TestAnalyticsService:
    """Tests for AnalyticsService."""

    def test_get_clutch_stats(self, real_db: Session):
        from src.models.league import Season
        from src.models.team import Team
        from src.schemas.analytics import ClutchFilter
        from src.services.analytics import AnalyticsService

        team = real_db.query(Team).first()
        season = real_db.query(Season).first()
        service = AnalyticsService(real_db)

        stats = service.get_clutch_stats_for_season(
            season_id=season.id,
            team_id=team.id,
            clutch_filter=ClutchFilter()
        )
        assert hasattr(stats, 'games_in_clutch')

    def test_get_player_home_away_split(self, real_db: Session):
        from src.models.league import Season
        from src.models.player import Player
        from src.services.analytics import AnalyticsService

        player = real_db.query(Player).first()
        season = real_db.query(Season).first()
        service = AnalyticsService(real_db)

        split = service.get_player_home_away_split(player.id, season.id)
        assert "home" in split
        assert "away" in split
