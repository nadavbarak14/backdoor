"""
Stats Schema Tests

Tests for src/schemas/stats.py covering:
- Percentage calculations (0 attempts = 0.0%)
- minutes_display formatting (1800 -> "30:00", 754 -> "12:34")
- result computation ("W"/"L")
- PlayerGameStatsWithGameResponse context fields
- TeamGameStatsResponse computed percentages
- TeamGameSummaryResponse computed result
"""

import uuid
from datetime import datetime

import pytest

from src.schemas.stats import (
    PlayerGameLogResponse,
    PlayerGameStatsResponse,
    PlayerGameStatsWithGameResponse,
    TeamGameHistoryResponse,
    TeamGameStatsResponse,
    TeamGameSummaryResponse,
    _compute_percentage,
    _format_minutes,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_compute_percentage_normal(self):
        """_compute_percentage should compute correct percentage."""
        assert _compute_percentage(7, 14) == 50.0
        assert _compute_percentage(3, 10) == 30.0
        assert _compute_percentage(42, 88) == 47.7

    def test_compute_percentage_zero_attempts(self):
        """_compute_percentage should return 0.0 for zero attempts."""
        assert _compute_percentage(0, 0) == 0.0

    def test_compute_percentage_zero_made(self):
        """_compute_percentage should return 0.0 for zero made."""
        assert _compute_percentage(0, 10) == 0.0

    def test_compute_percentage_perfect(self):
        """_compute_percentage should return 100.0 for perfect shooting."""
        assert _compute_percentage(10, 10) == 100.0

    def test_format_minutes_exact_minutes(self):
        """_format_minutes should format exact minutes correctly."""
        assert _format_minutes(1800) == "30:00"
        assert _format_minutes(2400) == "40:00"
        assert _format_minutes(60) == "1:00"

    def test_format_minutes_with_seconds(self):
        """_format_minutes should format minutes and seconds correctly."""
        assert _format_minutes(754) == "12:34"
        assert _format_minutes(1530) == "25:30"
        assert _format_minutes(2142) == "35:42"

    def test_format_minutes_zero(self):
        """_format_minutes should handle zero correctly."""
        assert _format_minutes(0) == "0:00"

    def test_format_minutes_single_digit_seconds(self):
        """_format_minutes should pad single-digit seconds with zero."""
        assert _format_minutes(65) == "1:05"
        assert _format_minutes(601) == "10:01"
        assert _format_minutes(3609) == "60:09"


class TestPlayerGameStatsResponse:
    """Tests for PlayerGameStatsResponse schema."""

    @pytest.fixture
    def sample_stats(self):
        """Create sample player game stats."""
        return PlayerGameStatsResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            minutes_played=2040,  # 34 minutes
            is_starter=True,
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            two_pointers_made=6,
            two_pointers_attempted=11,
            three_pointers_made=3,
            three_pointers_attempted=7,
            free_throws_made=4,
            free_throws_attempted=5,
            offensive_rebounds=1,
            defensive_rebounds=7,
            total_rebounds=8,
            assists=10,
            turnovers=3,
            steals=2,
            blocks=1,
            personal_fouls=2,
            plus_minus=15,
            efficiency=32,
            extra_stats={},
        )

    def test_minutes_display_computed(self, sample_stats):
        """PlayerGameStatsResponse should compute minutes_display."""
        assert sample_stats.minutes_display == "34:00"

    def test_field_goal_pct_computed(self, sample_stats):
        """PlayerGameStatsResponse should compute field_goal_pct."""
        assert sample_stats.field_goal_pct == 50.0

    def test_two_point_pct_computed(self, sample_stats):
        """PlayerGameStatsResponse should compute two_point_pct."""
        assert sample_stats.two_point_pct == 54.5

    def test_three_point_pct_computed(self, sample_stats):
        """PlayerGameStatsResponse should compute three_point_pct."""
        assert sample_stats.three_point_pct == 42.9

    def test_free_throw_pct_computed(self, sample_stats):
        """PlayerGameStatsResponse should compute free_throw_pct."""
        assert sample_stats.free_throw_pct == 80.0

    def test_zero_attempts_percentages(self):
        """PlayerGameStatsResponse should handle zero attempts correctly."""
        stats = PlayerGameStatsResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="Bench Player",
            team_id=uuid.uuid4(),
            minutes_played=300,  # 5 minutes
            is_starter=False,
            points=0,
            field_goals_made=0,
            field_goals_attempted=0,
            two_pointers_made=0,
            two_pointers_attempted=0,
            three_pointers_made=0,
            three_pointers_attempted=0,
            free_throws_made=0,
            free_throws_attempted=0,
            offensive_rebounds=0,
            defensive_rebounds=1,
            total_rebounds=1,
            assists=1,
            turnovers=1,
            steals=0,
            blocks=0,
            personal_fouls=1,
            plus_minus=-5,
            efficiency=-4,
            extra_stats={},
        )

        assert stats.field_goal_pct == 0.0
        assert stats.two_point_pct == 0.0
        assert stats.three_point_pct == 0.0
        assert stats.free_throw_pct == 0.0
        assert stats.minutes_display == "5:00"


class TestPlayerGameStatsWithGameResponse:
    """Tests for PlayerGameStatsWithGameResponse schema."""

    @pytest.fixture
    def sample_stats_with_game(self):
        """Create sample player game stats with game context."""
        return PlayerGameStatsWithGameResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            minutes_played=2040,
            is_starter=True,
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            two_pointers_made=6,
            two_pointers_attempted=11,
            three_pointers_made=3,
            three_pointers_attempted=7,
            free_throws_made=4,
            free_throws_attempted=5,
            offensive_rebounds=1,
            defensive_rebounds=7,
            total_rebounds=8,
            assists=10,
            turnovers=3,
            steals=2,
            blocks=1,
            personal_fouls=2,
            plus_minus=15,
            efficiency=32,
            extra_stats={},
            # Game context fields
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=True,
            team_score=112,
            opponent_score=108,
        )

    def test_result_win(self, sample_stats_with_game):
        """PlayerGameStatsWithGameResponse should compute result as 'W' for win."""
        assert sample_stats_with_game.result == "W"

    def test_result_loss(self):
        """PlayerGameStatsWithGameResponse should compute result as 'L' for loss."""
        stats = PlayerGameStatsWithGameResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            minutes_played=2040,
            is_starter=True,
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            two_pointers_made=6,
            two_pointers_attempted=11,
            three_pointers_made=3,
            three_pointers_attempted=7,
            free_throws_made=4,
            free_throws_attempted=5,
            offensive_rebounds=1,
            defensive_rebounds=7,
            total_rebounds=8,
            assists=10,
            turnovers=3,
            steals=2,
            blocks=1,
            personal_fouls=2,
            plus_minus=-10,
            efficiency=28,
            extra_stats={},
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=True,
            team_score=100,
            opponent_score=108,
        )
        assert stats.result == "L"

    def test_game_context_fields(self, sample_stats_with_game):
        """PlayerGameStatsWithGameResponse should include game context."""
        assert sample_stats_with_game.game_date == datetime(2024, 1, 15, 19, 30)
        assert sample_stats_with_game.opponent_team_name == "Boston Celtics"
        assert sample_stats_with_game.is_home is True
        assert sample_stats_with_game.team_score == 112
        assert sample_stats_with_game.opponent_score == 108

    def test_inherits_computed_fields(self, sample_stats_with_game):
        """PlayerGameStatsWithGameResponse should inherit computed fields."""
        assert sample_stats_with_game.minutes_display == "34:00"
        assert sample_stats_with_game.field_goal_pct == 50.0


class TestPlayerGameLogResponse:
    """Tests for PlayerGameLogResponse schema."""

    def test_list_response_structure(self):
        """PlayerGameLogResponse should contain items and total."""
        stats = PlayerGameStatsWithGameResponse(
            id=uuid.uuid4(),
            game_id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            minutes_played=2040,
            is_starter=True,
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            two_pointers_made=6,
            two_pointers_attempted=11,
            three_pointers_made=3,
            three_pointers_attempted=7,
            free_throws_made=4,
            free_throws_attempted=5,
            offensive_rebounds=1,
            defensive_rebounds=7,
            total_rebounds=8,
            assists=10,
            turnovers=3,
            steals=2,
            blocks=1,
            personal_fouls=2,
            plus_minus=15,
            efficiency=32,
            extra_stats={},
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=True,
            team_score=112,
            opponent_score=108,
        )

        response = PlayerGameLogResponse(items=[stats], total=82)

        assert len(response.items) == 1
        assert response.total == 82
        assert response.items[0].result == "W"


class TestTeamGameStatsResponse:
    """Tests for TeamGameStatsResponse schema."""

    @pytest.fixture
    def sample_team_stats(self):
        """Create sample team game stats."""
        return TeamGameStatsResponse(
            game_id=uuid.uuid4(),
            team_id=uuid.uuid4(),
            team_name="Los Angeles Lakers",
            is_home=True,
            points=112,
            field_goals_made=42,
            field_goals_attempted=88,
            two_pointers_made=30,
            two_pointers_attempted=58,
            three_pointers_made=12,
            three_pointers_attempted=30,
            free_throws_made=16,
            free_throws_attempted=20,
            offensive_rebounds=10,
            defensive_rebounds=35,
            total_rebounds=45,
            assists=25,
            turnovers=12,
            steals=8,
            blocks=5,
            personal_fouls=18,
            fast_break_points=14,
            points_in_paint=48,
            second_chance_points=12,
            bench_points=35,
            biggest_lead=18,
            time_leading=1800,  # 30 minutes
            extra_stats={},
        )

    def test_field_goal_pct_computed(self, sample_team_stats):
        """TeamGameStatsResponse should compute field_goal_pct."""
        assert sample_team_stats.field_goal_pct == 47.7

    def test_two_point_pct_computed(self, sample_team_stats):
        """TeamGameStatsResponse should compute two_point_pct."""
        assert sample_team_stats.two_point_pct == 51.7

    def test_three_point_pct_computed(self, sample_team_stats):
        """TeamGameStatsResponse should compute three_point_pct."""
        assert sample_team_stats.three_point_pct == 40.0

    def test_free_throw_pct_computed(self, sample_team_stats):
        """TeamGameStatsResponse should compute free_throw_pct."""
        assert sample_team_stats.free_throw_pct == 80.0

    def test_team_only_stats(self, sample_team_stats):
        """TeamGameStatsResponse should include team-only stats."""
        assert sample_team_stats.fast_break_points == 14
        assert sample_team_stats.points_in_paint == 48
        assert sample_team_stats.second_chance_points == 12
        assert sample_team_stats.bench_points == 35
        assert sample_team_stats.biggest_lead == 18
        assert sample_team_stats.time_leading == 1800

    def test_zero_attempts_percentages(self):
        """TeamGameStatsResponse should handle zero attempts correctly."""
        stats = TeamGameStatsResponse(
            game_id=uuid.uuid4(),
            team_id=uuid.uuid4(),
            team_name="Test Team",
            is_home=True,
            points=0,
            field_goals_made=0,
            field_goals_attempted=0,
            two_pointers_made=0,
            two_pointers_attempted=0,
            three_pointers_made=0,
            three_pointers_attempted=0,
            free_throws_made=0,
            free_throws_attempted=0,
            offensive_rebounds=0,
            defensive_rebounds=0,
            total_rebounds=0,
            assists=0,
            turnovers=0,
            steals=0,
            blocks=0,
            personal_fouls=0,
            fast_break_points=0,
            points_in_paint=0,
            second_chance_points=0,
            bench_points=0,
            biggest_lead=0,
            time_leading=0,
            extra_stats={},
        )

        assert stats.field_goal_pct == 0.0
        assert stats.two_point_pct == 0.0
        assert stats.three_point_pct == 0.0
        assert stats.free_throw_pct == 0.0


class TestTeamGameSummaryResponse:
    """Tests for TeamGameSummaryResponse schema."""

    def test_result_win(self):
        """TeamGameSummaryResponse should compute result as 'W' for win."""
        summary = TeamGameSummaryResponse(
            game_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=True,
            team_score=112,
            opponent_score=108,
            venue="Crypto.com Arena",
        )
        assert summary.result == "W"

    def test_result_loss(self):
        """TeamGameSummaryResponse should compute result as 'L' for loss."""
        summary = TeamGameSummaryResponse(
            game_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=False,
            team_score=100,
            opponent_score=108,
            venue="TD Garden",
        )
        assert summary.result == "L"

    def test_away_game(self):
        """TeamGameSummaryResponse should correctly represent away game."""
        summary = TeamGameSummaryResponse(
            game_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=False,
            team_score=115,
            opponent_score=110,
            venue="TD Garden",
        )
        assert summary.is_home is False
        assert summary.result == "W"

    def test_venue_nullable(self):
        """TeamGameSummaryResponse should allow null venue."""
        summary = TeamGameSummaryResponse(
            game_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=True,
            team_score=112,
            opponent_score=108,
            venue=None,
        )
        assert summary.venue is None


class TestTeamGameHistoryResponse:
    """Tests for TeamGameHistoryResponse schema."""

    def test_list_response_structure(self):
        """TeamGameHistoryResponse should contain items and total."""
        summary = TeamGameSummaryResponse(
            game_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
            opponent_team_id=uuid.uuid4(),
            opponent_team_name="Boston Celtics",
            is_home=True,
            team_score=112,
            opponent_score=108,
            venue="Crypto.com Arena",
        )

        response = TeamGameHistoryResponse(items=[summary], total=82)

        assert len(response.items) == 1
        assert response.total == 82
        assert response.items[0].result == "W"


class TestImports:
    """Tests for module imports."""

    def test_import_from_stats_module(self):
        """Should be able to import from stats schema module."""
        from src.schemas.stats import (
            PlayerGameLogResponse,
            PlayerGameStatsResponse,
            PlayerGameStatsWithGameResponse,
            TeamGameHistoryResponse,
            TeamGameStatsResponse,
            TeamGameSummaryResponse,
        )

        assert PlayerGameStatsResponse is not None
        assert PlayerGameStatsWithGameResponse is not None
        assert PlayerGameLogResponse is not None
        assert TeamGameStatsResponse is not None
        assert TeamGameSummaryResponse is not None
        assert TeamGameHistoryResponse is not None

    def test_import_from_schemas_package(self):
        """Should be able to import from schemas package."""
        from src.schemas import (
            PlayerGameStatsResponse,
            TeamGameStatsResponse,
        )

        assert PlayerGameStatsResponse is not None
        assert TeamGameStatsResponse is not None
