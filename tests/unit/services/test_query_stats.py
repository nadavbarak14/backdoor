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


class TestGetRecentGames:
    """Tests for _get_recent_games helper."""

    def test_get_recent_games_player(self):
        """Test getting recent games for a player."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        mock_games = [MagicMock(), MagicMock()]
        mock_db.scalars.return_value.all.return_value = mock_games

        result = _get_recent_games(
            mock_db, mock_season, player_id="player-123", last_n_games=5
        )

        assert len(result) == 2
        mock_db.scalars.assert_called_once()

    def test_get_recent_games_team(self):
        """Test getting recent games for a team."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        mock_games = [MagicMock()]
        mock_db.scalars.return_value.all.return_value = mock_games

        result = _get_recent_games(
            mock_db, mock_season, team_id="team-123", last_n_games=3
        )

        assert len(result) == 1

    def test_get_recent_games_no_entity(self):
        """Test getting recent games with no specific entity."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        mock_games = [MagicMock(), MagicMock(), MagicMock()]
        mock_db.scalars.return_value.all.return_value = mock_games

        result = _get_recent_games(mock_db, mock_season)

        assert len(result) == 3


class TestCalcStatsFromGames:
    """Tests for _calc_stats_from_games helper."""

    def test_calc_stats_no_time_filters(self):
        """Test calculating stats without time filters (box scores)."""
        from src.services.query_stats import _calc_stats_from_games

        mock_db = MagicMock()
        mock_game = MagicMock()
        mock_game.id = "game-123"

        mock_pgs = MagicMock()
        mock_pgs.points = 20
        mock_pgs.total_rebounds = 10
        mock_pgs.assists = 5
        mock_pgs.steals = 2
        mock_pgs.blocks = 1
        mock_pgs.turnovers = 3
        mock_pgs.field_goals_made = 8
        mock_pgs.field_goals_attempted = 15
        mock_pgs.three_pointers_made = 2
        mock_pgs.three_pointers_attempted = 5
        mock_pgs.free_throws_made = 2
        mock_pgs.free_throws_attempted = 3
        mock_pgs.plus_minus = 5
        mock_pgs.minutes_played = 1800  # 30 minutes

        mock_db.scalars.return_value.first.return_value = mock_pgs

        result = _calc_stats_from_games(
            mock_db,
            [mock_game],
            player_id="player-123",
        )

        assert result["games"] == 1
        assert result["points"] == 20
        assert result["rebounds"] == 10

    def test_calc_stats_no_games(self):
        """Test calculating stats with no games."""
        from src.services.query_stats import _calc_stats_from_games

        mock_db = MagicMock()

        result = _calc_stats_from_games(mock_db, [])

        assert result["games"] == 0
        assert result["points"] == 0

    def test_calc_stats_with_time_filters(self):
        """Test calculating stats with time filters (uses PBP)."""
        from src.services.query_stats import _calc_stats_from_games

        mock_db = MagicMock()
        mock_game = MagicMock()
        mock_game.id = "game-123"

        with patch("src.services.query_stats.AnalyticsService") as mock_analytics_cls:
            mock_analytics = MagicMock()
            mock_analytics_cls.return_value = mock_analytics

            with patch(
                "src.services.query_stats._calc_pbp_stats_for_game"
            ) as mock_calc_pbp:
                mock_calc_pbp.return_value = {
                    "has_data": True,
                    "points": 8,
                    "rebounds": 3,
                    "assists": 2,
                    "steals": 1,
                    "blocks": 0,
                    "turnovers": 1,
                    "fgm": 3,
                    "fga": 6,
                    "fg3m": 1,
                    "fg3a": 2,
                    "ftm": 1,
                    "fta": 2,
                    "plus_minus": 3,
                    "minutes": 0,
                }

                result = _calc_stats_from_games(
                    mock_db,
                    [mock_game],
                    player_id="player-123",
                    quarter=4,
                )

                assert result["games"] == 1
                assert result["points"] == 8


class TestCalcPbpStatsForGame:
    """Tests for _calc_pbp_stats_for_game helper."""

    def test_calc_pbp_stats_no_events(self):
        """Test calculating PBP stats with no events."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()
        mock_analytics.get_events_by_time.return_value = []

        mock_game = MagicMock()
        mock_game.id = "game-123"

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            quarter=4,
        )

        assert result["has_data"] is False
        assert result["points"] == 0

    def test_calc_pbp_stats_with_shot_events(self):
        """Test calculating PBP stats with shot events."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()

        # Create shot event
        mock_event = MagicMock()
        mock_event.player_id = "player-123"
        mock_event.team_id = "team-123"
        mock_event.event_type = "SHOT"
        mock_event.event_subtype = "2PT"
        mock_event.success = True

        mock_analytics.get_events_by_time.return_value = [mock_event]

        mock_game = MagicMock()
        mock_game.id = "game-123"

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            quarter=4,
        )

        assert result["has_data"] is True
        assert result["points"] == 2
        assert result["fgm"] == 1
        assert result["fga"] == 1

    def test_calc_pbp_stats_with_3pt_shot(self):
        """Test calculating PBP stats with 3-point shot."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()

        mock_event = MagicMock()
        mock_event.player_id = "player-123"
        mock_event.team_id = "team-123"
        mock_event.event_type = "SHOT"
        mock_event.event_subtype = "3PT"
        mock_event.success = True

        mock_analytics.get_events_by_time.return_value = [mock_event]

        mock_game = MagicMock()

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            quarter=4,
        )

        assert result["points"] == 3
        assert result["fg3m"] == 1
        assert result["fg3a"] == 1

    def test_calc_pbp_stats_with_free_throw(self):
        """Test calculating PBP stats with free throw."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()

        mock_event = MagicMock()
        mock_event.player_id = "player-123"
        mock_event.team_id = "team-123"
        mock_event.event_type = "FREE_THROW"
        mock_event.success = True

        mock_analytics.get_events_by_time.return_value = [mock_event]

        mock_game = MagicMock()

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            quarter=4,
        )

        assert result["points"] == 1
        assert result["ftm"] == 1
        assert result["fta"] == 1

    def test_calc_pbp_stats_with_other_events(self):
        """Test calculating PBP stats with rebounds, assists, etc."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()

        events = []
        for event_type in ["REBOUND", "ASSIST", "STEAL", "BLOCK", "TURNOVER"]:
            mock_event = MagicMock()
            mock_event.player_id = "player-123"
            mock_event.team_id = "team-123"
            mock_event.event_type = event_type
            mock_event.success = True
            events.append(mock_event)

        mock_analytics.get_events_by_time.return_value = events

        mock_game = MagicMock()

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            quarter=4,
        )

        assert result["rebounds"] == 1
        assert result["assists"] == 1
        assert result["steals"] == 1
        assert result["blocks"] == 1
        assert result["turnovers"] == 1

    def test_calc_pbp_stats_clutch_mode(self):
        """Test calculating PBP stats in clutch mode."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()
        mock_analytics.get_clutch_events.return_value = []

        mock_game = MagicMock()

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            clutch_only=True,
        )

        mock_analytics.get_clutch_events.assert_called_once()
        assert result["has_data"] is False

    def test_calc_pbp_stats_filter_wrong_player(self):
        """Test that events for wrong player are filtered out."""
        from src.services.query_stats import _calc_pbp_stats_for_game

        mock_analytics = MagicMock()

        mock_event = MagicMock()
        mock_event.player_id = "other-player"  # Different player
        mock_event.team_id = "team-123"
        mock_event.event_type = "SHOT"
        mock_event.success = True

        mock_analytics.get_events_by_time.return_value = [mock_event]

        mock_game = MagicMock()

        result = _calc_pbp_stats_for_game(
            mock_analytics,
            mock_game,
            player_id="player-123",
            quarter=4,
        )

        assert result["has_data"] is False


class TestQueryWithTimeFilters:
    """Tests for _query_with_time_filters function."""

    def test_query_with_time_filters_no_entity(self):
        """Test time filter query with no player/team returns error."""
        from src.services.query_stats import _query_with_time_filters

        mock_db = MagicMock()
        mock_season = MagicMock()

        result = _query_with_time_filters(
            db=mock_db,
            season=mock_season,
            players=[],
            team=None,
            metrics=["points"],
            per="game",
            limit=10,
            quarter=4,
            quarters=None,
            clutch_only=False,
            exclude_garbage_time=False,
            last_n_games=None,
        )

        assert "Error" in result
        assert "require specifying" in result

    def test_query_with_time_filters_player_no_games(self):
        """Test time filter query for player with no games."""
        from src.services.query_stats import _query_with_time_filters

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.name = "2024-25"

        mock_player = MagicMock()
        mock_player.first_name = "Test"
        mock_player.last_name = "Player"
        mock_player.id = "player-123"

        with patch("src.services.query_stats._get_recent_games") as mock_get_games:
            mock_get_games.return_value = []

            result = _query_with_time_filters(
                db=mock_db,
                season=mock_season,
                players=[mock_player],
                team=None,
                metrics=["points"],
                per="game",
                limit=10,
                quarter=4,
                quarters=None,
                clutch_only=False,
                exclude_garbage_time=False,
                last_n_games=5,
            )

            assert "No stats found" in result

    def test_query_with_time_filters_team_no_games(self):
        """Test time filter query for team with no games."""
        from src.services.query_stats import _query_with_time_filters

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.name = "2024-25"

        mock_team = MagicMock()
        mock_team.name = "Test Team"
        mock_team.id = "team-123"

        with patch("src.services.query_stats._get_recent_games") as mock_get_games:
            mock_get_games.return_value = []

            result = _query_with_time_filters(
                db=mock_db,
                season=mock_season,
                players=[],
                team=mock_team,
                metrics=["points"],
                per="game",
                limit=10,
                quarter=4,
                quarters=None,
                clutch_only=False,
                exclude_garbage_time=False,
                last_n_games=None,
            )

            assert "No games found" in result


class TestLocationFilterValidation:
    """Tests for location filter validation functions."""

    def test_validate_location_filters_valid(self):
        """Test validation passes for valid filters."""
        from src.services.query_stats import _validate_location_filters

        assert _validate_location_filters(False, False) is None
        assert _validate_location_filters(True, False) is None
        assert _validate_location_filters(False, True) is None

    def test_validate_location_filters_mutually_exclusive(self):
        """Test validation fails when home_only and away_only both set."""
        from src.services.query_stats import _validate_location_filters

        result = _validate_location_filters(True, True)
        assert "mutually exclusive" in result

    def test_has_location_filters_none(self):
        """Test has_location_filters returns False when no filters active."""
        from src.services.query_stats import _has_location_filters

        assert _has_location_filters(False, False, None) is False

    def test_has_location_filters_home_only(self):
        """Test has_location_filters returns True when home_only is set."""
        from src.services.query_stats import _has_location_filters

        assert _has_location_filters(True, False, None) is True

    def test_has_location_filters_away_only(self):
        """Test has_location_filters returns True when away_only is set."""
        from src.services.query_stats import _has_location_filters

        assert _has_location_filters(False, True, None) is True

    def test_has_location_filters_opponent(self):
        """Test has_location_filters returns True when opponent_team_id is set."""
        from src.services.query_stats import _has_location_filters

        assert _has_location_filters(False, False, "team-123") is True


class TestLocationFilterLabel:
    """Tests for location filter label building."""

    def test_build_time_filter_label_home(self):
        """Test label for home_only."""
        from src.services.query_stats import _build_time_filter_label

        label = _build_time_filter_label(None, None, False, False, None, True, False)
        assert "Home" in label

    def test_build_time_filter_label_away(self):
        """Test label for away_only."""
        from src.services.query_stats import _build_time_filter_label

        label = _build_time_filter_label(None, None, False, False, None, False, True)
        assert "Away" in label

    def test_build_time_filter_label_opponent(self):
        """Test label for opponent."""
        from src.services.query_stats import _build_time_filter_label

        label = _build_time_filter_label(
            None, None, False, False, None, False, False, "Hapoel Jerusalem"
        )
        assert "vs Hapoel Jerusalem" in label

    def test_build_time_filter_label_combined_location(self):
        """Test label with home + opponent."""
        from src.services.query_stats import _build_time_filter_label

        label = _build_time_filter_label(
            None, None, False, False, None, True, False, "Hapoel"
        )
        assert "Home" in label
        assert "vs Hapoel" in label

    def test_build_time_filter_label_quarter_plus_home(self):
        """Test label with quarter and home filters."""
        from src.services.query_stats import _build_time_filter_label

        label = _build_time_filter_label(4, None, False, False, None, True, False)
        assert "Q4" in label
        assert "Home" in label


class TestQueryStatsWithLocationFilters:
    """Tests for query_stats with location filters."""

    def test_query_stats_mutually_exclusive_home_away(self):
        """Test query_stats returns error when home_only and away_only both set."""
        from src.services.query_stats import query_stats

        mock_db = MagicMock()
        result = query_stats.func(home_only=True, away_only=True, db=mock_db)
        assert "Error" in result
        assert "mutually exclusive" in result

    def test_query_stats_opponent_not_found(self):
        """Test query_stats returns error when opponent team not found."""
        from src.services.query_stats import query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch("src.services.query_stats._resolve_team_by_name") as mock_team,
        ):
            mock_season.return_value = MagicMock()
            mock_team.return_value = None  # Opponent not found

            mock_db = MagicMock()
            result = query_stats.func(opponent_team="NonExistent", db=mock_db)

            assert "not found" in result

    def test_query_stats_location_filter_triggers_time_filter_path(self):
        """Test home_only triggers time filter path."""
        from src.services.query_stats import query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch(
                "src.services.query_stats._query_with_time_filters"
            ) as mock_time_filters,
        ):
            mock_season.return_value = MagicMock()
            mock_time_filters.return_value = "Location filtered results"

            mock_db = MagicMock()
            result = query_stats.func(home_only=True, db=mock_db)

            # Should call time filter path due to location filter
            mock_time_filters.assert_called_once()
            assert result == "Location filtered results"

    def test_query_stats_opponent_filter_triggers_time_filter_path(self):
        """Test opponent_team triggers time filter path."""
        from src.services.query_stats import query_stats

        with (
            patch("src.services.query_stats._resolve_season") as mock_season,
            patch("src.services.query_stats._resolve_team_by_name") as mock_team,
            patch(
                "src.services.query_stats._query_with_time_filters"
            ) as mock_time_filters,
        ):
            mock_season.return_value = MagicMock()
            mock_opponent = MagicMock()
            mock_opponent.id = "opponent-123"
            mock_opponent.name = "Hapoel"
            mock_team.return_value = mock_opponent
            mock_time_filters.return_value = "Opponent filtered results"

            mock_db = MagicMock()
            result = query_stats.func(opponent_team="Hapoel", db=mock_db)

            mock_time_filters.assert_called_once()
            assert result == "Opponent filtered results"


class TestGetRecentGamesWithLocationFilters:
    """Tests for _get_recent_games with location filters."""

    def test_get_recent_games_team_home_only(self):
        """Test getting home games only for a team."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        mock_games = [MagicMock()]
        mock_db.scalars.return_value.all.return_value = mock_games

        result = _get_recent_games(
            mock_db, mock_season, team_id="team-123", home_only=True
        )

        assert len(result) == 1
        mock_db.scalars.assert_called_once()

    def test_get_recent_games_team_away_only(self):
        """Test getting away games only for a team."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        mock_games = [MagicMock()]
        mock_db.scalars.return_value.all.return_value = mock_games

        result = _get_recent_games(
            mock_db, mock_season, team_id="team-123", away_only=True
        )

        assert len(result) == 1

    def test_get_recent_games_team_vs_opponent(self):
        """Test getting games against specific opponent for a team."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        mock_games = [MagicMock()]
        mock_db.scalars.return_value.all.return_value = mock_games

        result = _get_recent_games(
            mock_db, mock_season, team_id="team-123", opponent_team_id="opponent-456"
        )

        assert len(result) == 1

    def test_get_recent_games_player_with_location_filters(self):
        """Test getting home games for a player uses post-filtering."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        # Create mock game that is a home game for the player's team
        mock_game = MagicMock()
        mock_game.home_team_id = "team-123"
        mock_game.away_team_id = "team-456"

        # Return tuple of (Game, team_id) as the execute result
        mock_db.execute.return_value.all.return_value = [(mock_game, "team-123")]

        result = _get_recent_games(
            mock_db, mock_season, player_id="player-123", home_only=True
        )

        # Should include the game since it's a home game for the player's team
        assert len(result) == 1
        assert result[0] == mock_game

    def test_get_recent_games_player_home_filter_excludes_away(self):
        """Test player home filter excludes away games."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        # Create mock game that is an away game for the player's team
        mock_game = MagicMock()
        mock_game.home_team_id = "opponent-456"  # Opponent is home
        mock_game.away_team_id = "team-123"  # Player's team is away

        mock_db.execute.return_value.all.return_value = [(mock_game, "team-123")]

        result = _get_recent_games(
            mock_db, mock_season, player_id="player-123", home_only=True
        )

        # Should exclude the game since player's team is away
        assert len(result) == 0

    def test_get_recent_games_player_opponent_filter(self):
        """Test player opponent filter works correctly."""
        from src.services.query_stats import _get_recent_games

        mock_db = MagicMock()
        mock_season = MagicMock()
        mock_season.id = "season-123"

        # Create games - one vs target opponent, one vs different opponent
        game_vs_target = MagicMock()
        game_vs_target.home_team_id = "team-123"
        game_vs_target.away_team_id = "target-opponent"

        game_vs_other = MagicMock()
        game_vs_other.home_team_id = "team-123"
        game_vs_other.away_team_id = "other-opponent"

        mock_db.execute.return_value.all.return_value = [
            (game_vs_target, "team-123"),
            (game_vs_other, "team-123"),
        ]

        result = _get_recent_games(
            mock_db,
            mock_season,
            player_id="player-123",
            opponent_team_id="target-opponent",
        )

        # Should only include game vs target opponent
        assert len(result) == 1
        assert result[0] == game_vs_target
