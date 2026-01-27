"""
Unit tests for query_stats tool.

Tests the query_stats universal tool with mocked database.
"""

from unittest.mock import MagicMock, patch


class TestQueryStatsHelpers:
    """Tests for query_stats helper functions."""

    def test_format_metric_header(self):
        """Test metric header formatting."""
        from src.services.query_stats import _format_metric_header

        assert _format_metric_header("points") == "PTS"
        assert _format_metric_header("rebounds") == "REB"
        assert _format_metric_header("assists") == "AST"
        assert _format_metric_header("fg_pct") == "FG%"
        assert _format_metric_header("three_pct") == "3P%"
        assert _format_metric_header("unknown") == "UNKNOWN"

    def test_get_metric_value_basic(self):
        """Test metric value extraction for basic stats."""
        from src.services.query_stats import _get_metric_value

        # Create mock stats object
        stats = MagicMock()
        stats.avg_points = 15.5
        stats.total_points = 310
        stats.avg_rebounds = 5.2
        stats.games_played = 20

        assert _get_metric_value(stats, "points", "game") == "15.5"
        assert _get_metric_value(stats, "points", "total") == "310"
        assert _get_metric_value(stats, "rebounds", "game") == "5.2"
        assert _get_metric_value(stats, "games", "game") == "20"

    def test_get_metric_value_percentages(self):
        """Test metric value extraction for percentages."""
        from src.services.query_stats import _get_metric_value

        stats = MagicMock()
        stats.field_goal_pct = 0.455
        stats.three_point_pct = 0.38
        stats.free_throw_pct = 0.85

        assert _get_metric_value(stats, "fg_pct", "game") == "45.5%"
        assert _get_metric_value(stats, "three_pct", "game") == "38.0%"
        assert _get_metric_value(stats, "ft_pct", "game") == "85.0%"

    def test_get_metric_value_plus_minus(self):
        """Test metric value extraction for plus/minus."""
        from src.services.query_stats import _get_metric_value

        stats = MagicMock()
        stats.avg_plus_minus = 5.2
        stats.total_plus_minus = 104

        assert _get_metric_value(stats, "plus_minus", "game") == "+5.2"
        assert _get_metric_value(stats, "plus_minus", "total") == "+104"

    def test_get_metric_value_unknown(self):
        """Test metric value extraction for unknown metrics."""
        from src.services.query_stats import _get_metric_value

        stats = MagicMock()
        assert _get_metric_value(stats, "unknown_metric", "game") == "N/A"

    def test_get_metric_value_none(self):
        """Test metric value extraction when value is None."""
        from src.services.query_stats import _get_metric_value

        stats = MagicMock()
        stats.avg_points = None

        assert _get_metric_value(stats, "points", "game") == "N/A"

    def test_truncate_response_under_limit(self):
        """Test truncation when response is under limit."""
        from src.services.query_stats import _truncate_response

        response = "Short response"
        result = _truncate_response(response, 5, 5)
        assert result == "Short response"

    def test_truncate_response_over_limit(self):
        """Test truncation when response exceeds limit."""
        from src.services.query_stats import MAX_RESPONSE_CHARS, _truncate_response

        # Create a long response
        long_response = "Line 1\n" * 500
        result = _truncate_response(long_response, 10, 10)

        assert len(result) <= MAX_RESPONSE_CHARS + 100  # Some buffer for message
        assert "truncated" in result

    def test_truncate_response_partial_shown(self):
        """Test truncation message when showing partial results."""
        from src.services.query_stats import _truncate_response

        response = "Some results"
        result = _truncate_response(response, 5, 10)

        assert "Showing 5 of 10" in result


class TestQueryStatsResolution:
    """Tests for name resolution helpers."""

    def test_resolve_league_by_name_found(self):
        """Test league resolution when league exists."""
        from src.services.query_stats import _resolve_league_by_name

        mock_db = MagicMock()
        mock_league = MagicMock()
        mock_league.name = "Test League"
        mock_db.scalars.return_value.first.return_value = mock_league

        result = _resolve_league_by_name(mock_db, "Test")
        assert result == mock_league

    def test_resolve_league_by_name_not_found(self):
        """Test league resolution when league doesn't exist."""
        from src.services.query_stats import _resolve_league_by_name

        mock_db = MagicMock()
        mock_db.scalars.return_value.first.return_value = None

        result = _resolve_league_by_name(mock_db, "NonExistent")
        assert result is None

    def test_resolve_team_by_name_found(self):
        """Test team resolution when team exists."""
        from src.services.query_stats import _resolve_team_by_name

        with patch("src.services.query_stats.TeamService") as mock_service_class:
            mock_service = MagicMock()
            mock_team = MagicMock()
            mock_team.name = "Test Team"
            mock_service.get_filtered.return_value = ([mock_team], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = _resolve_team_by_name(mock_db, "Test")
            assert result == mock_team

    def test_resolve_team_by_name_not_found(self):
        """Test team resolution when team doesn't exist."""
        from src.services.query_stats import _resolve_team_by_name

        with patch("src.services.query_stats.TeamService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_filtered.return_value = ([], 0)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = _resolve_team_by_name(mock_db, "NonExistent")
            assert result is None

    def test_resolve_player_by_name_found(self):
        """Test player resolution when player exists."""
        from src.services.query_stats import _resolve_player_by_name

        with patch("src.services.query_stats.PlayerService") as mock_service_class:
            mock_service = MagicMock()
            mock_player = MagicMock()
            mock_player.first_name = "Test"
            mock_player.last_name = "Player"
            mock_service.get_filtered.return_value = ([mock_player], 1)
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = _resolve_player_by_name(mock_db, "Test")
            assert result == mock_player

    def test_resolve_season_current(self):
        """Test season resolution for current season."""
        from src.services.query_stats import _resolve_season

        with patch("src.services.query_stats.SeasonService") as mock_service_class:
            mock_service = MagicMock()
            mock_season = MagicMock()
            mock_season.name = "2024-25"
            mock_service.get_current.return_value = mock_season
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            result = _resolve_season(mock_db, None, None)
            assert result == mock_season

    def test_resolve_season_by_name(self):
        """Test season resolution by name."""
        from src.services.query_stats import _resolve_season

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.name = "2023-24"
        mock_db.scalars.return_value.first.return_value = mock_season

        result = _resolve_season(mock_db, "2023", None)
        assert result == mock_season


class TestQueryStatsTool:
    """Tests for the main query_stats tool.

    Note: We call the underlying function directly (query_stats.func)
    instead of using .invoke() because LangChain validates Session type.
    """

    def test_query_stats_no_db(self):
        """Test query_stats returns error when no db provided."""
        from src.services.query_stats import query_stats

        # Call the underlying function directly
        result = query_stats.func(db=None)
        assert "Error" in result

    def test_query_stats_default_metrics(self):
        """Test query_stats uses default metrics when not specified."""
        from src.services.query_stats import query_stats

        with patch("src.services.query_stats._resolve_season") as mock_resolve:
            mock_resolve.return_value = None

            mock_db = MagicMock()
            result = query_stats.func(db=mock_db)

            assert "No season found" in result

    def test_query_stats_team_not_found(self):
        """Test query_stats returns error when team not found."""
        from src.services.query_stats import query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch("src.services.query_stats._resolve_team_by_name") as mock_team,
        ):
            mock_season.return_value = MagicMock()
            mock_team.return_value = None

            mock_db = MagicMock()
            result = query_stats.func(team_name="NonExistent", db=mock_db)

            assert "not found" in result

    def test_query_stats_league_not_found(self):
        """Test query_stats returns error when league not found."""
        from src.services.query_stats import query_stats

        with patch("src.services.query_stats._resolve_league_by_name") as mock_league:
            mock_league.return_value = None

            mock_db = MagicMock()
            result = query_stats.func(league_name="NonExistent", db=mock_db)

            assert "not found" in result

    def test_query_stats_player_not_found(self):
        """Test query_stats returns error when player not found."""
        from src.services.query_stats import query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch("src.services.query_stats._resolve_player_by_name") as mock_player,
        ):
            mock_season.return_value = MagicMock()
            mock_player.return_value = None

            mock_db = MagicMock()
            result = query_stats.func(player_names=["NonExistent"], db=mock_db)

            assert "not found" in result

    def test_query_stats_limit_enforced(self):
        """Test that limit is enforced to MAX_RESPONSE_ROWS."""
        from src.services.query_stats import MAX_RESPONSE_ROWS, query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch("src.services.query_stats._query_league_stats") as mock_query_league,
        ):
            mock_season.return_value = MagicMock()
            mock_query_league.return_value = "Results"

            mock_db = MagicMock()
            query_stats.func(limit=100, db=mock_db)

            # Verify limit was capped
            call_args = mock_query_league.call_args
            assert call_args[0][5] <= MAX_RESPONSE_ROWS  # limit argument
