"""
Tests verifying the database is properly populated with data.
"""

import pytest
from sqlalchemy.orm import Session


class TestDataPopulation:
    """Tests verifying data exists in all required tables."""

    def test_leagues_populated(self, real_db: Session):
        """Verify at least one league exists."""
        from src.models.league import League
        assert real_db.query(League).count() >= 1

    def test_seasons_populated(self, real_db: Session):
        """Verify at least one season exists."""
        from src.models.league import Season
        assert real_db.query(Season).count() >= 1

    def test_teams_populated(self, real_db: Session):
        """Verify teams are populated."""
        from src.models.team import Team
        count = real_db.query(Team).count()
        assert count >= 10, f"Expected 10+ teams, found {count}"

    def test_players_populated(self, real_db: Session):
        """Verify players are populated."""
        from src.models.player import Player
        count = real_db.query(Player).count()
        assert count >= 100, f"Expected 100+ players, found {count}"

    def test_games_populated(self, real_db: Session):
        """Verify games are populated."""
        from src.models.game import Game
        count = real_db.query(Game).count()
        assert count >= 50, f"Expected 50+ games, found {count}"

    def test_player_game_stats_populated(self, real_db: Session):
        """Verify player box scores are populated."""
        from src.models.game import PlayerGameStats
        count = real_db.query(PlayerGameStats).count()
        assert count >= 1000, f"Expected 1000+ stats, found {count}"

    def test_team_game_stats_populated(self, real_db: Session):
        """Verify team game stats are populated."""
        from src.models.game import TeamGameStats
        count = real_db.query(TeamGameStats).count()
        assert count >= 100, f"Expected 100+ team stats, found {count}"

    def test_player_season_stats_populated(self, real_db: Session):
        """Verify player season stats are populated."""
        from src.models.stats import PlayerSeasonStats
        count = real_db.query(PlayerSeasonStats).count()
        assert count >= 50, f"Expected 50+ season stats, found {count}"

    def test_play_by_play_populated(self, real_db: Session):
        """Verify play-by-play events are populated."""
        from src.models.play_by_play import PlayByPlayEvent
        count = real_db.query(PlayByPlayEvent).count()
        assert count >= 10000, f"Expected 10000+ PBP events, found {count}"


class TestRelationshipIntegrity:
    """Tests verifying data relationships are correct."""

    def test_games_have_valid_teams(self, real_db: Session):
        """Verify all games reference valid teams."""
        from src.models.game import Game
        from src.models.team import Team

        for game in real_db.query(Game).limit(50).all():
            assert real_db.query(Team).filter(Team.id == game.home_team_id).first()
            assert real_db.query(Team).filter(Team.id == game.away_team_id).first()

    def test_player_stats_have_valid_players(self, real_db: Session):
        """Verify player stats reference valid players."""
        from src.models.game import PlayerGameStats
        from src.models.player import Player

        for stat in real_db.query(PlayerGameStats).limit(100).all():
            assert real_db.query(Player).filter(Player.id == stat.player_id).first()

    def test_seasons_have_valid_leagues(self, real_db: Session):
        """Verify all seasons reference valid leagues."""
        from src.models.league import Season, League

        for season in real_db.query(Season).all():
            assert real_db.query(League).filter(League.id == season.league_id).first()
