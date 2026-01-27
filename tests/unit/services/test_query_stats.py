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


class TestQueryHandlers:
    """Tests for query handler functions."""

    def test_query_player_stats_no_results(self):
        """Test _query_player_stats when no stats found."""
        from src.services.query_stats import _query_player_stats

        with patch(
            "src.services.query_stats.PlayerSeasonStatsService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_player_season.return_value = []
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            mock_player = MagicMock()
            mock_player.id = "123"
            mock_player.first_name = "Test"
            mock_player.last_name = "Player"
            mock_season = MagicMock()
            mock_season.id = "456"
            mock_season.name = "2024-25"

            result = _query_player_stats(
                mock_db, [mock_player], mock_season, ["points"], "game", 10
            )

            assert "No stats found" in result

    def test_query_player_stats_with_results(self):
        """Test _query_player_stats with valid stats."""
        from src.services.query_stats import _query_player_stats

        with patch(
            "src.services.query_stats.PlayerSeasonStatsService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_stats = MagicMock()
            mock_stats.team = MagicMock()
            mock_stats.team.short_name = "TST"
            mock_stats.avg_points = 15.5
            mock_service.get_player_season.return_value = [mock_stats]
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            mock_player = MagicMock()
            mock_player.id = "123"
            mock_player.first_name = "Test"
            mock_player.last_name = "Player"
            mock_season = MagicMock()
            mock_season.id = "456"
            mock_season.name = "2024-25"

            result = _query_player_stats(
                mock_db, [mock_player], mock_season, ["points"], "game", 10
            )

            assert "Player Stats" in result
            assert "Test Player" in result
            assert "TST" in result

    def test_query_team_stats_no_results(self):
        """Test _query_team_stats when no stats found."""
        from src.services.query_stats import _query_team_stats

        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = []

        mock_team = MagicMock()
        mock_team.id = "123"
        mock_team.name = "Test Team"
        mock_season = MagicMock()
        mock_season.id = "456"
        mock_season.name = "2024-25"

        result = _query_team_stats(
            mock_db, mock_team, mock_season, ["points"], "game", 10
        )

        assert "No stats found" in result

    def test_query_team_stats_with_results(self):
        """Test _query_team_stats with valid stats."""
        from src.services.query_stats import _query_team_stats

        mock_db = MagicMock()
        mock_stats = MagicMock()
        mock_stats.player = MagicMock()
        mock_stats.player.first_name = "Test"
        mock_stats.player.last_name = "Player"
        mock_stats.avg_points = 15.5
        mock_db.scalars.return_value.all.return_value = [mock_stats]

        mock_team = MagicMock()
        mock_team.id = "123"
        mock_team.name = "Test Team"
        mock_season = MagicMock()
        mock_season.id = "456"
        mock_season.name = "2024-25"

        result = _query_team_stats(
            mock_db, mock_team, mock_season, ["points"], "game", 10
        )

        assert "Test Team" in result
        assert "2024-25" in result

    def test_query_league_stats_no_results(self):
        """Test _query_league_stats when no stats found."""
        from src.services.query_stats import _query_league_stats

        with patch(
            "src.services.query_stats.PlayerSeasonStatsService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_league_leaders.return_value = []
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            mock_season = MagicMock()
            mock_season.id = "456"
            mock_season.name = "2024-25"

            result = _query_league_stats(
                mock_db, None, mock_season, ["points"], "game", 10
            )

            assert "No stats found" in result

    def test_query_league_stats_with_results(self):
        """Test _query_league_stats with valid stats."""
        from src.services.query_stats import _query_league_stats

        with patch(
            "src.services.query_stats.PlayerSeasonStatsService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_stats = MagicMock()
            mock_stats.player = MagicMock()
            mock_stats.player.first_name = "Test"
            mock_stats.player.last_name = "Player"
            mock_stats.team = MagicMock()
            mock_stats.team.short_name = "TST"
            mock_stats.avg_points = 15.5
            mock_service.get_league_leaders.return_value = [mock_stats]
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            mock_season = MagicMock()
            mock_season.id = "456"
            mock_season.name = "2024-25"

            result = _query_league_stats(
                mock_db, None, mock_season, ["points"], "game", 10
            )

            assert "Leaders" in result
            assert "Test Player" in result

    def test_query_league_stats_with_league(self):
        """Test _query_league_stats with league specified."""
        from src.services.query_stats import _query_league_stats

        with patch(
            "src.services.query_stats.PlayerSeasonStatsService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_stats = MagicMock()
            mock_stats.player = MagicMock()
            mock_stats.player.first_name = "Test"
            mock_stats.player.last_name = "Player"
            mock_stats.team = MagicMock()
            mock_stats.team.short_name = "TST"
            mock_stats.avg_points = 15.5
            mock_service.get_league_leaders.return_value = [mock_stats]
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            mock_league = MagicMock()
            mock_league.name = "Test League"
            mock_season = MagicMock()
            mock_season.id = "456"
            mock_season.name = "2024-25"

            result = _query_league_stats(
                mock_db, mock_league, mock_season, ["points"], "game", 10
            )

            assert "Test League" in result

    def test_query_league_stats_fallback_sort(self):
        """Test _query_league_stats falls back to avg_points on invalid category."""
        from src.services.query_stats import _query_league_stats

        with patch(
            "src.services.query_stats.PlayerSeasonStatsService"
        ) as mock_service_class:
            mock_service = MagicMock()
            # First call raises ValueError, second call succeeds
            mock_stats = MagicMock()
            mock_stats.player = MagicMock()
            mock_stats.player.first_name = "Test"
            mock_stats.player.last_name = "Player"
            mock_stats.team = MagicMock()
            mock_stats.team.short_name = "TST"
            mock_stats.avg_points = 15.5
            mock_service.get_league_leaders.side_effect = [
                ValueError("Invalid"),
                [mock_stats],
            ]
            mock_service_class.return_value = mock_service

            mock_db = MagicMock()
            mock_season = MagicMock()
            mock_season.id = "456"
            mock_season.name = "2024-25"

            result = _query_league_stats(
                mock_db, None, mock_season, ["unknown_metric"], "game", 10
            )

            assert "Leaders" in result


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


class TestTimeFilterValidation:
    """Tests for time filter validation functions."""

    def test_validate_time_filters_valid(self):
        """Test validation passes for valid filters."""
        from src.services.query_stats import _validate_time_filters

        assert _validate_time_filters(None, None) is None
        assert _validate_time_filters(1, None) is None
        assert _validate_time_filters(4, None) is None
        assert _validate_time_filters(None, [1, 2]) is None

    def test_validate_time_filters_mutually_exclusive(self):
        """Test validation fails when quarter and quarters both set."""
        from src.services.query_stats import _validate_time_filters

        result = _validate_time_filters(1, [1, 2])
        assert "mutually exclusive" in result

    def test_validate_time_filters_invalid_quarter(self):
        """Test validation fails for invalid quarter values."""
        from src.services.query_stats import _validate_time_filters

        assert "between 1 and 4" in _validate_time_filters(0, None)
        assert "between 1 and 4" in _validate_time_filters(5, None)

    def test_validate_time_filters_invalid_quarters(self):
        """Test validation fails for invalid quarters list values."""
        from src.services.query_stats import _validate_time_filters

        assert "Quarter 0" in _validate_time_filters(None, [0, 1])
        assert "Quarter 5" in _validate_time_filters(None, [1, 5])

    def test_has_time_filters_none(self):
        """Test has_time_filters returns False when no filters active."""
        from src.services.query_stats import _has_time_filters

        assert _has_time_filters(None, None, False, False) is False

    def test_has_time_filters_quarter(self):
        """Test has_time_filters returns True when quarter is set."""
        from src.services.query_stats import _has_time_filters

        assert _has_time_filters(4, None, False, False) is True

    def test_has_time_filters_quarters(self):
        """Test has_time_filters returns True when quarters is set."""
        from src.services.query_stats import _has_time_filters

        assert _has_time_filters(None, [1, 2], False, False) is True

    def test_has_time_filters_clutch(self):
        """Test has_time_filters returns True when clutch_only is True."""
        from src.services.query_stats import _has_time_filters

        assert _has_time_filters(None, None, True, False) is True

    def test_has_time_filters_garbage_time(self):
        """Test has_time_filters returns True when exclude_garbage_time is True."""
        from src.services.query_stats import _has_time_filters

        assert _has_time_filters(None, None, False, True) is True


class TestTimeFilterLabel:
    """Tests for time filter label building."""

    def test_build_time_filter_label_empty(self):
        """Test empty label when no filters."""
        from src.services.query_stats import _build_time_filter_label

        assert _build_time_filter_label(None, None, False, False, None) == ""

    def test_build_time_filter_label_quarter(self):
        """Test label for single quarter."""
        from src.services.query_stats import _build_time_filter_label

        assert "Q4" in _build_time_filter_label(4, None, False, False, None)

    def test_build_time_filter_label_first_half(self):
        """Test label for first half."""
        from src.services.query_stats import _build_time_filter_label

        assert "1st Half" in _build_time_filter_label(None, [1, 2], False, False, None)

    def test_build_time_filter_label_second_half(self):
        """Test label for second half."""
        from src.services.query_stats import _build_time_filter_label

        assert "2nd Half" in _build_time_filter_label(None, [3, 4], False, False, None)

    def test_build_time_filter_label_clutch(self):
        """Test label for clutch."""
        from src.services.query_stats import _build_time_filter_label

        assert "Clutch" in _build_time_filter_label(None, None, True, False, None)

    def test_build_time_filter_label_last_n(self):
        """Test label for last_n_games."""
        from src.services.query_stats import _build_time_filter_label

        assert "Last 5 Games" in _build_time_filter_label(None, None, False, False, 5)

    def test_build_time_filter_label_combined(self):
        """Test label with multiple filters."""
        from src.services.query_stats import _build_time_filter_label

        label = _build_time_filter_label(4, None, True, False, 5)
        assert "Q4" in label
        assert "Clutch" in label
        assert "Last 5 Games" in label


class TestGameStatsFormatting:
    """Tests for game stats value formatting."""

    def test_format_game_stats_value_no_games(self):
        """Test formatting when no games."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 0, "points": 0}
        assert _format_game_stats_value(totals, "points", "game") == "N/A"

    def test_format_game_stats_value_games(self):
        """Test formatting games count."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 10}
        assert _format_game_stats_value(totals, "games", "game") == "10"

    def test_format_game_stats_value_points_avg(self):
        """Test formatting points per game."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 10, "points": 150}
        assert _format_game_stats_value(totals, "points", "game") == "15.0"

    def test_format_game_stats_value_points_total(self):
        """Test formatting total points."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 10, "points": 150}
        assert _format_game_stats_value(totals, "points", "total") == "150"

    def test_format_game_stats_value_fg_pct(self):
        """Test formatting field goal percentage."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 10, "fgm": 45, "fga": 100}
        assert _format_game_stats_value(totals, "fg_pct", "game") == "45.0%"

    def test_format_game_stats_value_plus_minus_avg(self):
        """Test formatting plus/minus per game."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 10, "plus_minus": 50}
        assert _format_game_stats_value(totals, "plus_minus", "game") == "+5.0"

    def test_format_game_stats_value_plus_minus_total(self):
        """Test formatting total plus/minus."""
        from src.services.query_stats import _format_game_stats_value

        totals = {"games": 10, "plus_minus": 50}
        assert _format_game_stats_value(totals, "plus_minus", "total") == "+50"


class TestQueryStatsWithTimeFilters:
    """Tests for query_stats with time filters."""

    def test_query_stats_invalid_quarter(self):
        """Test query_stats returns error for invalid quarter."""
        from src.services.query_stats import query_stats

        mock_db = MagicMock()
        result = query_stats.func(quarter=5, db=mock_db)
        assert "Error" in result
        assert "between 1 and 4" in result

    def test_query_stats_mutually_exclusive_quarters(self):
        """Test query_stats returns error when quarter and quarters both set."""
        from src.services.query_stats import query_stats

        mock_db = MagicMock()
        result = query_stats.func(quarter=4, quarters=[1, 2], db=mock_db)
        assert "Error" in result
        assert "mutually exclusive" in result

    def test_query_stats_time_filter_requires_entity(self):
        """Test time filters require player or team (not league-wide)."""
        from src.services.query_stats import query_stats

        with patch("src.services.query_stats._resolve_season") as mock_season:
            mock_season.return_value = MagicMock()

            mock_db = MagicMock()
            result = query_stats.func(quarter=4, db=mock_db)

            assert "Error" in result
            assert "require specifying" in result

    def test_query_stats_last_n_games_triggers_time_filter(self):
        """Test last_n_games triggers time filter path."""
        from src.services.query_stats import query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch(
                "src.services.query_stats._query_with_time_filters"
            ) as mock_time_filters,
        ):
            mock_season.return_value = MagicMock()
            mock_time_filters.return_value = "Time filtered results"

            mock_db = MagicMock()
            result = query_stats.func(last_n_games=5, db=mock_db)

            # Should call time filter path, not league stats
            mock_time_filters.assert_called_once()
            assert result == "Time filtered results"
