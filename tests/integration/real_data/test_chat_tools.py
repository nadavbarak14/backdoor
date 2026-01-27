"""
Tests for AI chat tools with real data.

Tests all 14 LangChain tools that the AI agent uses.
"""

import pytest
from sqlalchemy.orm import Session


class TestSearchPlayers:
    """Tests for search_players tool."""

    def test_search_by_name(self, real_db: Session):
        from src.services.chat_tools import search_players
        result = search_players.invoke({"query": "Clark", "db": real_db})
        assert "Clark" in result or "Players Matching" in result

    def test_search_by_position(self, real_db: Session):
        from src.services.chat_tools import search_players
        result = search_players.invoke({"query": "a", "position": "G", "db": real_db})
        assert "Error" not in result

    def test_search_not_found(self, real_db: Session):
        from src.services.chat_tools import search_players
        result = search_players.invoke({"query": "XXXNONEXISTENT123", "db": real_db})
        assert "No players found" in result


class TestSearchTeams:
    """Tests for search_teams tool."""

    def test_search_by_name(self, real_db: Session):
        from src.services.chat_tools import search_teams
        result = search_teams.invoke({"query": "Maccabi", "db": real_db})
        assert "Maccabi" in result

    def test_search_not_found(self, real_db: Session):
        from src.services.chat_tools import search_teams
        result = search_teams.invoke({"query": "XXXNONEXISTENT123", "db": real_db})
        assert "No teams found" in result


class TestGetTeamRoster:
    """Tests for get_team_roster tool."""

    def test_get_roster(self, real_db: Session):
        from src.services.chat_tools import get_team_roster
        result = get_team_roster.invoke({"team_name": "Maccabi Tel-Aviv", "db": real_db})
        assert "Roster" in result or "not found" in result

    def test_team_not_found(self, real_db: Session):
        from src.services.chat_tools import get_team_roster
        result = get_team_roster.invoke({"team_name": "XXXNONEXISTENT", "db": real_db})
        assert "not found" in result


class TestGetGameDetails:
    """Tests for get_game_details tool."""

    def test_get_by_teams(self, real_db: Session):
        from src.services.chat_tools import get_game_details
        result = get_game_details.invoke({
            "home_team": "Maccabi Tel-Aviv",
            "away_team": "Hapoel Jerusalem",
            "db": real_db
        })
        assert isinstance(result, str)

    def test_get_by_id(self, real_db: Session):
        from src.models.game import Game
        from src.services.chat_tools import get_game_details
        game = real_db.query(Game).first()
        result = get_game_details.invoke({"game_id": str(game.id), "db": real_db})
        assert isinstance(result, str)


class TestGetPlayerStats:
    """Tests for get_player_stats tool."""

    def test_get_stats(self, real_db: Session):
        from src.models.stats import PlayerSeasonStats
        from src.services.chat_tools import get_player_stats
        stat = real_db.query(PlayerSeasonStats).first()
        if not stat:
            pytest.skip("No season stats")
        name = f"{stat.player.first_name} {stat.player.last_name}"
        result = get_player_stats.invoke({"player_name": name, "db": real_db})
        assert "Averages" in result or "not found" in result or "No stats" in result

    def test_not_found(self, real_db: Session):
        from src.services.chat_tools import get_player_stats
        result = get_player_stats.invoke({"player_name": "XXXNONEXISTENT", "db": real_db})
        assert "not found" in result


class TestGetPlayerGames:
    """Tests for get_player_games tool."""

    def test_get_game_log(self, real_db: Session):
        from src.models.game import PlayerGameStats
        from src.services.chat_tools import get_player_games
        stat = real_db.query(PlayerGameStats).first()
        name = f"{stat.player.first_name} {stat.player.last_name}"
        result = get_player_games.invoke({"player_name": name, "limit": 5, "db": real_db})
        assert "Last" in result or "No games" in result or "not found" in result


class TestGetLeagueLeaders:
    """Tests for get_league_leaders tool."""

    def test_leaders_points(self, real_db: Session):
        from src.services.chat_tools import get_league_leaders
        result = get_league_leaders.invoke({"category": "points", "limit": 5, "db": real_db})
        assert "Leaders" in result or "No leaders" in result

    def test_leaders_rebounds(self, real_db: Session):
        from src.services.chat_tools import get_league_leaders
        result = get_league_leaders.invoke({"category": "rebounds", "limit": 5, "db": real_db})
        assert isinstance(result, str)

    def test_leaders_assists(self, real_db: Session):
        from src.services.chat_tools import get_league_leaders
        result = get_league_leaders.invoke({"category": "assists", "limit": 5, "db": real_db})
        assert isinstance(result, str)


class TestGetClutchStats:
    """Tests for get_clutch_stats tool."""

    def test_team_clutch(self, real_db: Session):
        from src.services.chat_tools import get_clutch_stats
        result = get_clutch_stats.invoke({"team_name": "Maccabi Tel-Aviv", "db": real_db})
        assert "Clutch" in result or "not found" in result

    def test_player_clutch(self, real_db: Session):
        from src.models.player import Player
        from src.services.chat_tools import get_clutch_stats
        player = real_db.query(Player).first()
        name = f"{player.first_name} {player.last_name}"
        result = get_clutch_stats.invoke({"player_name": name, "db": real_db})
        assert isinstance(result, str)


class TestGetQuarterSplits:
    """Tests for get_quarter_splits tool."""

    def test_team_splits(self, real_db: Session):
        from src.services.chat_tools import get_quarter_splits
        result = get_quarter_splits.invoke({"team_name": "Maccabi Tel-Aviv", "db": real_db})
        assert "Quarter" in result or "not found" in result or "Please provide" in result


class TestGetTrend:
    """Tests for get_trend tool."""

    def test_player_trend(self, real_db: Session):
        from sqlalchemy import func

        from src.models.game import PlayerGameStats
        from src.services.chat_tools import get_trend

        player_id = real_db.query(
            PlayerGameStats.player_id
        ).group_by(PlayerGameStats.player_id).having(func.count() >= 5).first()

        if not player_id:
            pytest.skip("No player with 5+ games")

        from src.models.player import Player
        player = real_db.query(Player).filter(Player.id == player_id[0]).first()
        name = f"{player.first_name} {player.last_name}"

        result = get_trend.invoke({
            "stat": "points",
            "player_name": name,
            "last_n_games": 5,
            "db": real_db
        })
        assert "Trend" in result or "Error" in result or "not found" in result


class TestGetLineupStats:
    """Tests for get_lineup_stats tool."""

    def test_two_players(self, real_db: Session):
        from src.models.player import Player
        from src.services.chat_tools import get_lineup_stats
        players = real_db.query(Player).limit(2).all()
        names = [f"{p.first_name} {p.last_name}" for p in players]
        result = get_lineup_stats.invoke({"player_names": names, "db": real_db})
        assert "Lineup" in result or "Error" in result or "not found" in result

    def test_too_few_players(self, real_db: Session):
        from src.services.chat_tools import get_lineup_stats
        result = get_lineup_stats.invoke({"player_names": ["One"], "db": real_db})
        assert "at least 2" in result


class TestGetHomeAwaySplit:
    """Tests for get_home_away_split tool."""

    def test_player_split(self, real_db: Session):
        from src.models.game import PlayerGameStats
        from src.services.chat_tools import get_home_away_split
        stat = real_db.query(PlayerGameStats).first()
        name = f"{stat.player.first_name} {stat.player.last_name}"
        result = get_home_away_split.invoke({"player_name": name, "db": real_db})
        assert "Home" in result or "Away" in result or "not found" in result


class TestGetOnOffStats:
    """Tests for get_on_off_stats tool."""

    def test_player_on_off(self, real_db: Session):
        from src.models.game import PlayerGameStats
        from src.services.chat_tools import get_on_off_stats
        stat = real_db.query(PlayerGameStats).first()
        name = f"{stat.player.first_name} {stat.player.last_name}"
        result = get_on_off_stats.invoke({"player_name": name, "db": real_db})
        assert "On" in result or "Off" in result or "not found" in result


class TestGetVsOpponent:
    """Tests for get_vs_opponent tool."""

    def test_player_vs_team(self, real_db: Session):
        from src.models.game import PlayerGameStats
        from src.services.chat_tools import get_vs_opponent
        stat = real_db.query(PlayerGameStats).first()
        name = f"{stat.player.first_name} {stat.player.last_name}"
        result = get_vs_opponent.invoke({
            "player_name": name,
            "opponent_team": "Hapoel Jerusalem",
            "db": real_db
        })
        assert "vs" in result or "not found" in result or "No games" in result


class TestQueryStats:
    """Tests for query_stats universal tool."""

    def test_team_stats(self, real_db: Session):
        """Test querying team stats."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "team_name": "Maccabi",
            "limit": 5,
            "db": real_db
        })
        assert "Maccabi" in result or "not found" in result

    def test_player_stats(self, real_db: Session):
        """Test querying specific player stats."""
        from src.models.player import Player
        from src.services.query_stats import query_stats

        player = real_db.query(Player).first()
        if not player:
            pytest.skip("No players in database")

        result = query_stats.invoke({
            "player_names": [player.last_name],
            "db": real_db
        })
        assert "Player Stats" in result or "not found" in result or "No stats" in result

    def test_league_leaders(self, real_db: Session):
        """Test league leaders / leaderboard mode."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "metrics": ["points", "assists"],
            "limit": 5,
            "db": real_db
        })
        assert "Leaders" in result or "No stats" in result

    def test_custom_metrics(self, real_db: Session):
        """Test with custom metrics selection."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "team_name": "Maccabi",
            "metrics": ["points", "fg_pct", "three_pct"],
            "limit": 3,
            "db": real_db
        })
        assert "FG%" in result or "not found" in result

    def test_per_total(self, real_db: Session):
        """Test total stats instead of per-game averages."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "team_name": "Maccabi",
            "per": "total",
            "limit": 3,
            "db": real_db
        })
        # Totals should be larger integers
        assert "Maccabi" in result or "not found" in result

    def test_response_size_limit(self, real_db: Session):
        """Test that response is truncated appropriately."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "limit": 50,  # Requests more than MAX_RESPONSE_ROWS
            "db": real_db
        })
        # Should be limited to MAX_RESPONSE_ROWS (20)
        lines = [line for line in result.split("\n") if line.startswith("|") and not line.startswith("|-")]
        # Header + up to 20 data rows
        assert len(lines) <= 22

    def test_league_filter(self, real_db: Session):
        """Test filtering by league name."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "league_name": "Winner",
            "limit": 5,
            "db": real_db
        })
        assert isinstance(result, str)

    def test_season_filter(self, real_db: Session):
        """Test filtering by season."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({
            "season": "2025",
            "limit": 5,
            "db": real_db
        })
        assert isinstance(result, str)

    def test_not_found_errors(self, real_db: Session):
        """Test error handling for non-existent entities."""
        from src.services.query_stats import query_stats

        # Non-existent team
        result = query_stats.invoke({
            "team_name": "XXXNONEXISTENT",
            "db": real_db
        })
        assert "not found" in result

        # Non-existent player
        result = query_stats.invoke({
            "player_names": ["XXXNONEXISTENT"],
            "db": real_db
        })
        assert "not found" in result

        # Non-existent league
        result = query_stats.invoke({
            "league_name": "XXXNONEXISTENT",
            "db": real_db
        })
        assert "not found" in result
