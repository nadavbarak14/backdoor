"""
Player Stats Schema Tests

Tests for src/schemas/player_stats.py covering:
- PlayerSeasonStatsResponse with computed avg_minutes_display
- PlayerCareerStatsResponse with seasons list
- LeagueLeaderEntry validation
- LeagueLeadersResponse structure
- LeagueLeadersFilter defaults and validation
- StatsCategory enum values
"""

import uuid
from datetime import datetime

import pytest

from src.schemas.player_stats import (
    LeagueLeaderEntry,
    LeagueLeadersFilter,
    LeagueLeadersResponse,
    PlayerCareerStatsResponse,
    PlayerSeasonStatsResponse,
    StatsCategory,
    _format_minutes,
)


class TestFormatMinutesHelper:
    """Tests for _format_minutes helper function."""

    def test_format_minutes_exact_minutes(self):
        """_format_minutes should format exact minutes correctly."""
        assert _format_minutes(1800.0) == "30:00"
        assert _format_minutes(2400.0) == "40:00"
        assert _format_minutes(60.0) == "1:00"

    def test_format_minutes_with_seconds(self):
        """_format_minutes should format minutes and seconds correctly."""
        assert _format_minutes(754.0) == "12:34"
        assert _format_minutes(1530.0) == "25:30"
        assert _format_minutes(2142.0) == "35:42"

    def test_format_minutes_zero(self):
        """_format_minutes should handle zero correctly."""
        assert _format_minutes(0.0) == "0:00"

    def test_format_minutes_fractional(self):
        """_format_minutes should handle fractional seconds by truncating."""
        assert _format_minutes(1800.5) == "30:00"
        assert _format_minutes(754.9) == "12:34"


class TestStatsCategoryEnum:
    """Tests for StatsCategory enum."""

    def test_stats_category_values(self):
        """StatsCategory should have expected values."""
        assert StatsCategory.POINTS.value == "points"
        assert StatsCategory.REBOUNDS.value == "rebounds"
        assert StatsCategory.ASSISTS.value == "assists"
        assert StatsCategory.STEALS.value == "steals"
        assert StatsCategory.BLOCKS.value == "blocks"
        assert StatsCategory.FIELD_GOAL_PCT.value == "field_goal_pct"
        assert StatsCategory.THREE_POINT_PCT.value == "three_point_pct"
        assert StatsCategory.FREE_THROW_PCT.value == "free_throw_pct"
        assert StatsCategory.MINUTES.value == "minutes"
        assert StatsCategory.EFFICIENCY.value == "efficiency"


class TestPlayerSeasonStatsResponse:
    """Tests for PlayerSeasonStatsResponse schema."""

    @pytest.fixture
    def sample_season_stats(self):
        """Create sample player season stats."""
        return PlayerSeasonStatsResponse(
            id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            team_name="Los Angeles Lakers",
            season_id=uuid.uuid4(),
            season_name="2023-24",
            games_played=72,
            games_started=72,
            total_minutes=187200,
            total_points=1800,
            total_field_goals_made=650,
            total_field_goals_attempted=1340,
            total_two_pointers_made=450,
            total_two_pointers_attempted=850,
            total_three_pointers_made=200,
            total_three_pointers_attempted=490,
            total_free_throws_made=300,
            total_free_throws_attempted=360,
            total_offensive_rebounds=72,
            total_defensive_rebounds=504,
            total_rebounds=576,
            total_assists=540,
            total_turnovers=216,
            total_steals=90,
            total_blocks=36,
            total_personal_fouls=144,
            total_plus_minus=360,
            avg_minutes=2600.0,
            avg_points=25.0,
            avg_rebounds=8.0,
            avg_assists=7.5,
            avg_turnovers=3.0,
            avg_steals=1.25,
            avg_blocks=0.5,
            field_goal_pct=48.5,
            two_point_pct=52.9,
            three_point_pct=40.8,
            free_throw_pct=83.3,
            true_shooting_pct=61.2,
            effective_field_goal_pct=55.9,
            assist_turnover_ratio=2.5,
            last_calculated=datetime.now(),
        )

    def test_avg_minutes_display_computed(self, sample_season_stats):
        """PlayerSeasonStatsResponse should compute avg_minutes_display."""
        assert sample_season_stats.avg_minutes_display == "43:20"

    def test_all_fields_present(self, sample_season_stats):
        """PlayerSeasonStatsResponse should have all expected fields."""
        assert sample_season_stats.player_name == "LeBron James"
        assert sample_season_stats.team_name == "Los Angeles Lakers"
        assert sample_season_stats.season_name == "2023-24"
        assert sample_season_stats.games_played == 72
        assert sample_season_stats.avg_points == 25.0
        assert sample_season_stats.field_goal_pct == 48.5

    def test_optional_percentages_can_be_none(self):
        """PlayerSeasonStatsResponse should accept None for percentage fields."""
        stats = PlayerSeasonStatsResponse(
            id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="Rookie Player",
            team_id=uuid.uuid4(),
            team_name="Test Team",
            season_id=uuid.uuid4(),
            season_name="2023-24",
            games_played=10,
            games_started=0,
            total_minutes=1200,
            total_points=50,
            total_field_goals_made=20,
            total_field_goals_attempted=50,
            total_two_pointers_made=20,
            total_two_pointers_attempted=50,
            total_three_pointers_made=0,
            total_three_pointers_attempted=0,
            total_free_throws_made=10,
            total_free_throws_attempted=12,
            total_offensive_rebounds=5,
            total_defensive_rebounds=15,
            total_rebounds=20,
            total_assists=10,
            total_turnovers=8,
            total_steals=3,
            total_blocks=2,
            total_personal_fouls=15,
            total_plus_minus=-10,
            avg_minutes=120.0,
            avg_points=5.0,
            avg_rebounds=2.0,
            avg_assists=1.0,
            avg_turnovers=0.8,
            avg_steals=0.3,
            avg_blocks=0.2,
            field_goal_pct=None,
            two_point_pct=None,
            three_point_pct=None,
            free_throw_pct=None,
            true_shooting_pct=None,
            effective_field_goal_pct=None,
            assist_turnover_ratio=None,
            last_calculated=datetime.now(),
        )
        assert stats.field_goal_pct is None
        assert stats.three_point_pct is None

    def test_serialization_includes_computed_field(self, sample_season_stats):
        """Serialized output should include computed avg_minutes_display."""
        data = sample_season_stats.model_dump()
        assert "avg_minutes_display" in data
        assert data["avg_minutes_display"] == "43:20"


class TestPlayerCareerStatsResponse:
    """Tests for PlayerCareerStatsResponse schema."""

    @pytest.fixture
    def sample_season_stats(self):
        """Create sample season stats for career response."""
        return PlayerSeasonStatsResponse(
            id=uuid.uuid4(),
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            team_id=uuid.uuid4(),
            team_name="Los Angeles Lakers",
            season_id=uuid.uuid4(),
            season_name="2023-24",
            games_played=72,
            games_started=72,
            total_minutes=187200,
            total_points=1800,
            total_field_goals_made=650,
            total_field_goals_attempted=1340,
            total_two_pointers_made=450,
            total_two_pointers_attempted=850,
            total_three_pointers_made=200,
            total_three_pointers_attempted=490,
            total_free_throws_made=300,
            total_free_throws_attempted=360,
            total_offensive_rebounds=72,
            total_defensive_rebounds=504,
            total_rebounds=576,
            total_assists=540,
            total_turnovers=216,
            total_steals=90,
            total_blocks=36,
            total_personal_fouls=144,
            total_plus_minus=360,
            avg_minutes=2600.0,
            avg_points=25.0,
            avg_rebounds=8.0,
            avg_assists=7.5,
            avg_turnovers=3.0,
            avg_steals=1.25,
            avg_blocks=0.5,
            field_goal_pct=48.5,
            two_point_pct=52.9,
            three_point_pct=40.8,
            free_throw_pct=83.3,
            true_shooting_pct=61.2,
            effective_field_goal_pct=55.9,
            assist_turnover_ratio=2.5,
            last_calculated=datetime.now(),
        )

    def test_career_stats_with_seasons(self, sample_season_stats):
        """PlayerCareerStatsResponse should include list of seasons."""
        career = PlayerCareerStatsResponse(
            player_id=uuid.uuid4(),
            player_name="LeBron James",
            career_games_played=1421,
            career_games_started=1420,
            career_points=38652,
            career_rebounds=10566,
            career_assists=10420,
            career_steals=2219,
            career_blocks=1074,
            career_turnovers=5067,
            career_avg_points=27.2,
            career_avg_rebounds=7.4,
            career_avg_assists=7.3,
            seasons=[sample_season_stats],
        )

        assert career.player_name == "LeBron James"
        assert career.career_games_played == 1421
        assert career.career_avg_points == 27.2
        assert len(career.seasons) == 1
        assert career.seasons[0].season_name == "2023-24"

    def test_career_stats_empty_seasons(self):
        """PlayerCareerStatsResponse should allow empty seasons list."""
        career = PlayerCareerStatsResponse(
            player_id=uuid.uuid4(),
            player_name="New Player",
            career_games_played=0,
            career_games_started=0,
            career_points=0,
            career_rebounds=0,
            career_assists=0,
            career_steals=0,
            career_blocks=0,
            career_turnovers=0,
            career_avg_points=0.0,
            career_avg_rebounds=0.0,
            career_avg_assists=0.0,
            seasons=[],
        )

        assert len(career.seasons) == 0


class TestLeagueLeaderEntry:
    """Tests for LeagueLeaderEntry schema."""

    def test_leader_entry_creation(self):
        """LeagueLeaderEntry should be created with all fields."""
        entry = LeagueLeaderEntry(
            rank=1,
            player_id=uuid.uuid4(),
            player_name="Joel Embiid",
            team_id=uuid.uuid4(),
            team_name="Philadelphia 76ers",
            value=33.1,
            games_played=66,
        )

        assert entry.rank == 1
        assert entry.player_name == "Joel Embiid"
        assert entry.value == 33.1
        assert entry.games_played == 66

    def test_rank_must_be_positive(self):
        """LeagueLeaderEntry rank must be at least 1."""
        with pytest.raises(ValueError):
            LeagueLeaderEntry(
                rank=0,
                player_id=uuid.uuid4(),
                player_name="Test Player",
                team_id=uuid.uuid4(),
                team_name="Test Team",
                value=10.0,
                games_played=50,
            )


class TestLeagueLeadersResponse:
    """Tests for LeagueLeadersResponse schema."""

    def test_league_leaders_response(self):
        """LeagueLeadersResponse should contain category and leaders list."""
        leader1 = LeagueLeaderEntry(
            rank=1,
            player_id=uuid.uuid4(),
            player_name="Joel Embiid",
            team_id=uuid.uuid4(),
            team_name="Philadelphia 76ers",
            value=33.1,
            games_played=66,
        )
        leader2 = LeagueLeaderEntry(
            rank=2,
            player_id=uuid.uuid4(),
            player_name="Luka Doncic",
            team_id=uuid.uuid4(),
            team_name="Dallas Mavericks",
            value=32.4,
            games_played=70,
        )

        response = LeagueLeadersResponse(
            category=StatsCategory.POINTS,
            season_id=uuid.uuid4(),
            season_name="2023-24",
            min_games=58,
            leaders=[leader1, leader2],
        )

        assert response.category == StatsCategory.POINTS
        assert response.season_name == "2023-24"
        assert response.min_games == 58
        assert len(response.leaders) == 2
        assert response.leaders[0].rank == 1


class TestLeagueLeadersFilter:
    """Tests for LeagueLeadersFilter schema."""

    def test_filter_defaults(self):
        """LeagueLeadersFilter should have correct defaults."""
        filter = LeagueLeadersFilter(season_id=uuid.uuid4())

        assert filter.category == StatsCategory.POINTS
        assert filter.limit == 10
        assert filter.min_games == 0

    def test_filter_custom_values(self):
        """LeagueLeadersFilter should accept custom values."""
        filter = LeagueLeadersFilter(
            season_id=uuid.uuid4(),
            category=StatsCategory.ASSISTS,
            limit=25,
            min_games=58,
        )

        assert filter.category == StatsCategory.ASSISTS
        assert filter.limit == 25
        assert filter.min_games == 58

    def test_filter_limit_validation(self):
        """LeagueLeadersFilter limit should be between 1 and 100."""
        # Valid limits
        LeagueLeadersFilter(season_id=uuid.uuid4(), limit=1)
        LeagueLeadersFilter(season_id=uuid.uuid4(), limit=100)

        # Invalid limits
        with pytest.raises(ValueError):
            LeagueLeadersFilter(season_id=uuid.uuid4(), limit=0)
        with pytest.raises(ValueError):
            LeagueLeadersFilter(season_id=uuid.uuid4(), limit=101)

    def test_filter_min_games_validation(self):
        """LeagueLeadersFilter min_games cannot be negative."""
        LeagueLeadersFilter(season_id=uuid.uuid4(), min_games=0)

        with pytest.raises(ValueError):
            LeagueLeadersFilter(season_id=uuid.uuid4(), min_games=-1)
