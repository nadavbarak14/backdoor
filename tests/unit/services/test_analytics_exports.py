"""
Analytics Exports Tests

Tests to verify that AnalyticsService and analytics schemas are properly
exported from their respective packages.

These tests ensure:
- AnalyticsService is importable from src.services
- All analytics filter schemas are importable from src.schemas
- AnalyticsService has all expected methods
"""

import pytest


class TestAnalyticsServiceExports:
    """Tests for AnalyticsService export from services package."""

    def test_analytics_service_importable(self):
        """Test that AnalyticsService is importable from src.services."""
        from src.services import AnalyticsService

        assert AnalyticsService is not None

    def test_analytics_service_in_all(self):
        """Test that AnalyticsService is in __all__ of services package."""
        from src import services

        assert "AnalyticsService" in services.__all__


class TestAnalyticsSchemasExports:
    """Tests for analytics schemas exports from schemas package."""

    def test_clutch_filter_importable(self):
        """Test that ClutchFilter is importable from src.schemas."""
        from src.schemas import ClutchFilter

        assert ClutchFilter is not None

    def test_situational_filter_importable(self):
        """Test that SituationalFilter is importable from src.schemas."""
        from src.schemas import SituationalFilter

        assert SituationalFilter is not None

    def test_opponent_filter_importable(self):
        """Test that OpponentFilter is importable from src.schemas."""
        from src.schemas import OpponentFilter

        assert OpponentFilter is not None

    def test_time_filter_importable(self):
        """Test that TimeFilter is importable from src.schemas."""
        from src.schemas import TimeFilter

        assert TimeFilter is not None

    def test_all_analytics_schemas_in_all(self):
        """Test that all analytics schemas are in __all__ of schemas package."""
        from src import schemas

        expected_schemas = [
            "ClutchFilter",
            "SituationalFilter",
            "OpponentFilter",
            "TimeFilter",
        ]
        for schema_name in expected_schemas:
            assert schema_name in schemas.__all__, f"{schema_name} not in __all__"


class TestAnalyticsServiceMethods:
    """Tests to verify AnalyticsService has all expected methods."""

    def test_analytics_service_has_all_methods(self):
        """Test that AnalyticsService has all expected public methods."""
        from src.services import AnalyticsService

        expected_methods = [
            # Core clutch methods
            "get_clutch_events",
            # Situational methods
            "get_situational_shots",
            "get_situational_stats",
            # Opponent methods
            "get_games_vs_opponent",
            "get_player_stats_vs_opponent",
            "get_player_home_away_split",
            # On/Off methods
            "get_player_on_off_stats",
            "get_player_on_off_for_season",
            # Lineup methods
            "get_lineup_stats",
            "get_lineup_stats_for_season",
            "get_best_lineups",
            # Time-based methods
            "get_events_by_time",
            "get_player_stats_by_quarter",
            # Helper/utility
            "get_game",
        ]

        for method_name in expected_methods:
            assert hasattr(
                AnalyticsService, method_name
            ), f"AnalyticsService missing method: {method_name}"

    def test_analytics_service_has_internal_methods(self):
        """Test that AnalyticsService has expected internal helper methods."""
        from src.services import AnalyticsService

        expected_internal_methods = [
            "_is_clutch_moment",
            "_get_game_score_at_time",
            "_parse_clock_to_seconds",
            "_event_matches_situational_filter",
            "_get_starters_for_game",
            "_build_on_court_timeline",
            "_is_player_on_at_time",
            "_get_lineup_on_court_intervals",
            "_get_points_for_event",
        ]

        for method_name in expected_internal_methods:
            assert hasattr(
                AnalyticsService, method_name
            ), f"AnalyticsService missing internal method: {method_name}"


class TestAnalyticsSchemasDefaults:
    """Tests to verify analytics schemas have correct default values."""

    def test_clutch_filter_defaults(self):
        """Test ClutchFilter has correct NBA standard defaults."""
        from src.schemas import ClutchFilter

        filter = ClutchFilter()
        assert filter.time_remaining_seconds == 300  # 5 minutes
        assert filter.score_margin == 5
        assert filter.include_overtime is True
        assert filter.min_period == 4

    def test_situational_filter_defaults(self):
        """Test SituationalFilter has correct defaults (all None)."""
        from src.schemas import SituationalFilter

        filter = SituationalFilter()
        assert filter.fast_break is None
        assert filter.second_chance is None
        assert filter.contested is None
        assert filter.shot_type is None

    def test_opponent_filter_defaults(self):
        """Test OpponentFilter has correct defaults."""
        from src.schemas import OpponentFilter

        filter = OpponentFilter()
        assert filter.opponent_team_id is None
        assert filter.home_only is False
        assert filter.away_only is False

    def test_time_filter_defaults(self):
        """Test TimeFilter has correct defaults."""
        from src.schemas import TimeFilter

        filter = TimeFilter()
        assert filter.period is None
        assert filter.periods is None
        assert filter.exclude_garbage_time is False
        assert filter.min_time_remaining is None
        assert filter.max_time_remaining is None


class TestAnalyticsSchemasValidation:
    """Tests for analytics schemas validation."""

    def test_opponent_filter_mutual_exclusion(self):
        """Test OpponentFilter rejects both home_only and away_only True."""
        from pydantic import ValidationError

        from src.schemas import OpponentFilter

        with pytest.raises(ValidationError):
            OpponentFilter(home_only=True, away_only=True)

    def test_time_filter_period_mutual_exclusion(self):
        """Test TimeFilter rejects both period and periods set."""
        from pydantic import ValidationError

        from src.schemas import TimeFilter

        with pytest.raises(ValidationError):
            TimeFilter(period=1, periods=[2, 3])

    def test_time_filter_time_range_validation(self):
        """Test TimeFilter validates min <= max time remaining."""
        from pydantic import ValidationError

        from src.schemas import TimeFilter

        with pytest.raises(ValidationError):
            TimeFilter(min_time_remaining=300, max_time_remaining=100)

    def test_clutch_filter_bounds(self):
        """Test ClutchFilter validates bounds correctly."""
        from pydantic import ValidationError

        from src.schemas import ClutchFilter

        # Valid filter
        filter = ClutchFilter(time_remaining_seconds=600, score_margin=10)
        assert filter.time_remaining_seconds == 600

        # Invalid - exceeds max
        with pytest.raises(ValidationError):
            ClutchFilter(time_remaining_seconds=1000)  # Max is 720
