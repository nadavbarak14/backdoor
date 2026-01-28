"""
Tests for AI chat tools with real data.

Tests the 4 LangChain tools that the AI agent uses:
- search_players: Search for players by name
- search_teams: Search for teams by name
- search_leagues: Search for leagues by name (tested in test_search_tools.py)
- query_stats: Universal stats query tool
"""

import json

import pytest
from sqlalchemy.orm import Session


class TestSearchPlayers:
    """Tests for search_players tool (returns JSON)."""

    def test_search_by_name(self, real_db: Session):
        from src.services.chat_tools import search_players

        result = search_players.invoke({"query": "Clark", "db": real_db})
        data = json.loads(result)
        assert data["query"] == "Clark"
        assert "players" in data
        # Either found players or empty list
        if data["total"] > 0:
            assert any("Clark" in p["name"] for p in data["players"])

    def test_search_by_position(self, real_db: Session):
        from src.services.chat_tools import search_players

        result = search_players.invoke({"query": "a", "position": "G", "db": real_db})
        data = json.loads(result)
        assert "error" not in data

    def test_search_not_found(self, real_db: Session):
        from src.services.chat_tools import search_players

        result = search_players.invoke({"query": "XXXNONEXISTENT123", "db": real_db})
        data = json.loads(result)
        assert data["total"] == 0
        assert data["players"] == []


class TestSearchTeams:
    """Tests for search_teams tool (returns JSON)."""

    def test_search_by_name(self, real_db: Session):
        from src.services.chat_tools import search_teams

        result = search_teams.invoke({"query": "Maccabi", "db": real_db})
        data = json.loads(result)
        assert data["query"] == "Maccabi"
        if data["total"] > 0:
            assert any("Maccabi" in t["name"] for t in data["teams"])

    def test_search_not_found(self, real_db: Session):
        from src.services.chat_tools import search_teams

        result = search_teams.invoke({"query": "XXXNONEXISTENT123", "db": real_db})
        data = json.loads(result)
        assert data["total"] == 0
        assert data["teams"] == []


class TestQueryStats:
    """Tests for query_stats universal tool (uses IDs, not names)."""

    def test_team_stats(self, real_db: Session):
        """Test querying team stats by ID."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%")).first()
        if not team:
            pytest.skip("No Maccabi team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "limit": 5, "db": real_db}
        )
        assert "Maccabi" in result or "No stats" in result

    def test_player_stats(self, real_db: Session):
        """Test querying specific player stats by ID."""
        from src.models.player import Player
        from src.services.query_stats import query_stats

        player = real_db.query(Player).first()
        if not player:
            pytest.skip("No players in database")

        result = query_stats.invoke({"player_ids": [str(player.id)], "db": real_db})
        assert "Player Stats" in result or "No stats" in result

    def test_league_leaders(self, real_db: Session):
        """Test league leaders / leaderboard mode."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke(
            {"metrics": ["points", "assists"], "limit": 5, "db": real_db}
        )
        assert "Leaders" in result or "No stats" in result

    def test_custom_metrics(self, real_db: Session):
        """Test with custom metrics selection."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%")).first()
        if not team:
            pytest.skip("No Maccabi team in database")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "metrics": ["points", "fg_pct", "three_pct"],
                "limit": 3,
                "db": real_db,
            }
        )
        assert "FG%" in result or "No stats" in result

    def test_per_total(self, real_db: Session):
        """Test total stats instead of per-game averages."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%")).first()
        if not team:
            pytest.skip("No Maccabi team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "per": "total", "limit": 3, "db": real_db}
        )
        # Totals should be larger integers
        assert "Maccabi" in result or "No stats" in result

    def test_response_size_limit(self, real_db: Session):
        """Test that response is truncated appropriately."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke(
            {"limit": 50, "db": real_db}  # Requests more than MAX_RESPONSE_ROWS
        )
        # Should be limited to MAX_RESPONSE_ROWS (20)
        lines = [
            line
            for line in result.split("\n")
            if line.startswith("|") and not line.startswith("|-")
        ]
        # Header + up to 20 data rows
        assert len(lines) <= 22

    def test_league_filter(self, real_db: Session):
        """Test filtering by league ID."""
        from src.models.league import League
        from src.services.query_stats import query_stats

        league = real_db.query(League).filter(League.name.ilike("%Winner%")).first()
        if not league:
            pytest.skip("No Winner league in database")

        result = query_stats.invoke(
            {"league_id": str(league.id), "limit": 5, "db": real_db}
        )
        assert isinstance(result, str)

    def test_season_filter(self, real_db: Session):
        """Test filtering by season ID."""
        from src.models.league import Season
        from src.services.query_stats import query_stats

        season = real_db.query(Season).filter(Season.name.ilike("%2024%")).first()
        if not season:
            pytest.skip("No 2024 season in database")

        result = query_stats.invoke(
            {"season_id": str(season.id), "limit": 5, "db": real_db}
        )
        assert isinstance(result, str)

    def test_not_found_errors(self, real_db: Session):
        """Test error handling for non-existent entity IDs."""
        from src.services.query_stats import query_stats

        # Non-existent team (valid UUID format but doesn't exist)
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = query_stats.invoke({"team_id": fake_uuid, "db": real_db})
        assert "not found" in result

        # Non-existent player
        result = query_stats.invoke({"player_ids": [fake_uuid], "db": real_db})
        assert "not found" in result

        # Non-existent league
        result = query_stats.invoke({"league_id": fake_uuid, "db": real_db})
        assert "not found" in result

    def test_time_filter_validation(self, real_db: Session):
        """Test time filter validation."""
        from src.services.query_stats import query_stats

        # Invalid quarter
        result = query_stats.invoke({"quarter": 5, "db": real_db})
        assert "Error" in result

        # Mutually exclusive
        result = query_stats.invoke({"quarter": 4, "quarters": [1, 2], "db": real_db})
        assert "mutually exclusive" in result

    def test_quarter_filter_player(self, real_db: Session):
        """Test quarter filter for a player."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        # Get a player with games
        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {"player_ids": [str(stat.player_id)], "quarter": 4, "db": real_db}
        )
        # Should have Q4 in header and return stats or no stats message
        assert "Q4" in result or "No stats" in result

    def test_last_n_games_player(self, real_db: Session):
        """Test last_n_games filter for a player."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {"player_ids": [str(stat.player_id)], "last_n_games": 3, "db": real_db}
        )
        assert "Last 3 Games" in result or "No stats" in result

    def test_quarter_filter_team(self, real_db: Session):
        """Test quarter filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "quarter": 4, "db": real_db}
        )
        assert "Q4" in result or "No stats" in result or "No games" in result

    def test_clutch_filter_team(self, real_db: Session):
        """Test clutch_only filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "clutch_only": True, "db": real_db}
        )
        assert "Clutch" in result or "No stats" in result or "No games" in result

    def test_first_half_filter(self, real_db: Session):
        """Test quarters filter for first half."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "quarters": [1, 2], "db": real_db}
        )
        assert "1st Half" in result or "No stats" in result or "No games" in result

    def test_time_filter_requires_entity(self, real_db: Session):
        """Test that time filters require player or team."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({"quarter": 4, "db": real_db})
        assert "require specifying" in result


class TestQueryStatsLocationFilters:
    """Tests for query_stats location and opponent filters."""

    def test_home_only_team(self, real_db: Session):
        """Test home_only filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "home_only": True, "db": real_db}
        )
        assert "Home" in result or "No stats" in result or "No games" in result

    def test_away_only_team(self, real_db: Session):
        """Test away_only filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "away_only": True, "db": real_db}
        )
        assert "Away" in result or "No stats" in result or "No games" in result

    def test_home_away_mutually_exclusive(self, real_db: Session):
        """Test that home_only and away_only are mutually exclusive."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke(
            {"home_only": True, "away_only": True, "db": real_db}
        )
        assert "mutually exclusive" in result

    def test_vs_opponent_team(self, real_db: Session):
        """Test opponent_team_id filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        teams = real_db.query(Team).limit(2).all()
        if len(teams) < 2:
            pytest.skip("Need at least 2 teams")

        result = query_stats.invoke(
            {
                "team_id": str(teams[0].id),
                "opponent_team_id": str(teams[1].id),
                "db": real_db,
            }
        )
        assert "vs" in result or "No stats" in result or "No games" in result

    def test_home_only_player(self, real_db: Session):
        """Test home_only filter for a player."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {"player_ids": [str(stat.player_id)], "home_only": True, "db": real_db}
        )
        assert "Home" in result or "No stats" in result


class TestQueryStatsAdvancedModes:
    """Tests for query_stats advanced modes (lineup, discovery, leaderboard)."""

    def test_two_player_lineup(self, real_db: Session):
        """Test lineup mode with 2 players."""
        from src.models.player import Player
        from src.services.query_stats import query_stats

        players = real_db.query(Player).limit(2).all()
        if len(players) < 2:
            pytest.skip("Need at least 2 players")

        result = query_stats.invoke(
            {"player_ids": [str(p.id) for p in players], "db": real_db}
        )
        # Lineup mode is triggered when 2+ players provided
        assert (
            "Lineup" in result
            or "together" in result
            or "No games" in result
            or "Error" in result
        )

    def test_lineup_discovery(self, real_db: Session):
        """Test lineup discovery mode for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "discover_lineups": True,
                "lineup_size": 2,
                "min_minutes": 1.0,
                "db": real_db,
            }
        )
        assert "Lineup" in result or "No lineups" in result or "No games" in result

    def test_leaderboard_mode(self, real_db: Session):
        """Test leaderboard mode with order_by."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke(
            {
                "order_by": "points",
                "min_games": 1,
                "limit": 5,
                "db": real_db,
            }
        )
        assert "Leaderboard" in result or "No stats" in result

    def test_leaderboard_ascending(self, real_db: Session):
        """Test leaderboard with ascending order."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke(
            {
                "order_by": "points",
                "order": "asc",
                "min_games": 1,
                "limit": 5,
                "db": real_db,
            }
        )
        assert "ascending" in result or "Leaderboard" in result or "No stats" in result

    def test_leaderboard_validation(self, real_db: Session):
        """Test leaderboard parameter validation."""
        from src.services.query_stats import query_stats

        # Invalid order_by
        result = query_stats.invoke({"order_by": "invalid_stat", "db": real_db})
        assert "Error" in result

        # Invalid order
        result = query_stats.invoke(
            {"order_by": "points", "order": "bad", "db": real_db}
        )
        assert "Error" in result

        # Invalid min_games
        result = query_stats.invoke(
            {"order_by": "points", "min_games": 0, "db": real_db}
        )
        assert "Error" in result


class TestQueryStatsComposition:
    """Tests for composing multiple filters."""

    def test_quarter_plus_home(self, real_db: Session):
        """Test combining quarter and home_only filters."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "quarter": 4,
                "home_only": True,
                "db": real_db,
            }
        )
        # Should show both filters in label
        assert ("Q4" in result and "Home" in result) or "No" in result

    def test_clutch_plus_last_n(self, real_db: Session):
        """Test combining clutch_only and last_n_games filters."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {
                "player_ids": [str(stat.player_id)],
                "clutch_only": True,
                "last_n_games": 5,
                "db": real_db,
            }
        )
        assert ("Clutch" in result and "Last 5" in result) or "No stats" in result

    def test_multiple_filters_combined(self, real_db: Session):
        """Test combining multiple filter types."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "quarters": [3, 4],  # 2nd half
                "home_only": True,
                "last_n_games": 10,
                "db": real_db,
            }
        )
        assert isinstance(result, str)


class TestQueryStatsSituationalFilters:
    """Tests for situational filters (fast_break, contested, shot_type)."""

    def test_fast_break_filter(self, real_db: Session):
        """Test fast_break filter for a player."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {"player_ids": [str(stat.player_id)], "fast_break": True, "db": real_db}
        )
        assert "Fast Break" in result or "No stats" in result

    def test_contested_filter(self, real_db: Session):
        """Test contested filter for a player."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {"player_ids": [str(stat.player_id)], "contested": True, "db": real_db}
        )
        assert "Contested" in result or "No stats" in result

    def test_shot_type_filter(self, real_db: Session):
        """Test shot_type filter for a player."""
        from src.models.game import PlayerGameStats
        from src.services.query_stats import query_stats

        stat = real_db.query(PlayerGameStats).first()
        if not stat:
            pytest.skip("No player game stats")

        result = query_stats.invoke(
            {"player_ids": [str(stat.player_id)], "shot_type": "PULL_UP", "db": real_db}
        )
        assert "Pull Up" in result or "No stats" in result

    def test_invalid_shot_type(self, real_db: Session):
        """Test invalid shot_type returns error."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({"shot_type": "INVALID", "db": real_db})
        assert "Error" in result

    def test_situational_with_team(self, real_db: Session):
        """Test situational filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "fast_break": True, "db": real_db}
        )
        assert "Fast Break" in result or "No stats" in result or "No games" in result


class TestQueryStatsScheduleFilters:
    """Tests for schedule filters (back_to_back, min_rest_days)."""

    def test_back_to_back_filter(self, real_db: Session):
        """Test back_to_back filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "back_to_back": True, "db": real_db}
        )
        assert "Back-to-Back" in result or "No stats" in result or "No games" in result

    def test_non_back_to_back_filter(self, real_db: Session):
        """Test back_to_back=False filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "back_to_back": False, "db": real_db}
        )
        assert "Non-B2B" in result or "No stats" in result or "No games" in result

    def test_min_rest_days_filter(self, real_db: Session):
        """Test min_rest_days filter for a team."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).filter(Team.name.ilike("%Maccabi%Tel%")).first()
        if not team:
            pytest.skip("No Maccabi Tel-Aviv team in database")

        result = query_stats.invoke(
            {"team_id": str(team.id), "min_rest_days": 2, "db": real_db}
        )
        assert (
            "Min 2 Rest Days" in result or "No stats" in result or "No games" in result
        )

    def test_schedule_validation(self, real_db: Session):
        """Test schedule filter validation."""
        from src.services.query_stats import query_stats

        # Negative min_rest_days
        result = query_stats.invoke({"min_rest_days": -1, "db": real_db})
        assert "Error" in result

        # Conflicting params
        result = query_stats.invoke(
            {"back_to_back": True, "min_rest_days": 3, "db": real_db}
        )
        assert "conflicts" in result


class TestQueryStatsEdgeCases:
    """Tests for edge cases and error handling."""

    def test_no_season_found(self, real_db: Session):
        """Test error when no season can be resolved."""
        from src.services.query_stats import query_stats

        # Using a fake league_id that doesn't exist
        fake_uuid = "00000000-0000-0000-0000-000000000001"
        result = query_stats.invoke({"league_id": fake_uuid, "db": real_db})
        assert "not found" in result or "Error" in result

    def test_no_db_provided(self):
        """Test error when no db session provided."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({})
        assert "Error" in result
        assert "Database session" in result

    def test_discover_lineups_requires_team(self, real_db: Session):
        """Test that discover_lineups requires team_id."""
        from src.services.query_stats import query_stats

        result = query_stats.invoke({"discover_lineups": True, "db": real_db})
        assert "Error" in result
        assert "team_id" in result

    def test_lineup_size_validation(self, real_db: Session):
        """Test lineup_size validation in discover mode."""
        from src.models.team import Team
        from src.services.query_stats import query_stats

        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams in database")

        # Invalid lineup_size
        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "discover_lineups": True,
                "lineup_size": 6,
                "db": real_db,
            }
        )
        assert "Error" in result
        assert "lineup_size" in result
