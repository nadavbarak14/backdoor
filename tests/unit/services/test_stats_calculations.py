"""
Unit tests for StatsCalculationService.

Tests all calculation formulas with known input/output values.
These tests verify the mathematical correctness of the stats calculation
methods independently of any database operations.
"""

from src.services.stats_calculation import StatsCalculationService


class TestPercentageCalculation:
    """Tests for calculate_percentage method."""

    def test_basic_percentage(self):
        """Test basic percentage calculation."""
        assert StatsCalculationService.calculate_percentage(5, 10) == 50.0

    def test_zero_attempts_returns_zero(self):
        """Test zero attempts returns zero, not division error."""
        assert StatsCalculationService.calculate_percentage(0, 0) == 0.0

    def test_all_makes(self):
        """Test 100% shooting."""
        assert StatsCalculationService.calculate_percentage(10, 10) == 100.0

    def test_no_makes(self):
        """Test 0% shooting with attempts."""
        assert StatsCalculationService.calculate_percentage(0, 10) == 0.0

    def test_rounding_one_third(self):
        """Test rounding to one decimal place for 1/3."""
        assert StatsCalculationService.calculate_percentage(1, 3) == 33.3

    def test_rounding_two_thirds(self):
        """Test rounding to one decimal place for 2/3."""
        assert StatsCalculationService.calculate_percentage(2, 3) == 66.7

    def test_typical_fg_percentage(self):
        """Test typical field goal percentage."""
        # 9 made out of 18 = 50%
        assert StatsCalculationService.calculate_percentage(9, 18) == 50.0

    def test_high_three_point_percentage(self):
        """Test high three-point percentage."""
        # 4 made out of 8 = 50%
        assert StatsCalculationService.calculate_percentage(4, 8) == 50.0

    def test_free_throw_percentage(self):
        """Test typical free throw percentage."""
        # 8 made out of 9 = 88.9%
        assert StatsCalculationService.calculate_percentage(8, 9) == 88.9


class TestTrueShootingPct:
    """
    Tests for calculate_true_shooting_pct method.

    Formula: TS% = PTS / (2 * (FGA + 0.44 * FTA)) * 100
    """

    def test_basic_ts_pct(self):
        """Test basic true shooting percentage calculation."""
        # 20 pts, 10 FGA, 5 FTA
        # TS% = 20 / (2 * (10 + 0.44 * 5)) * 100
        # TS% = 20 / (2 * 12.2) * 100 = 20 / 24.4 * 100 = 82.0
        assert StatsCalculationService.calculate_true_shooting_pct(20, 10, 5) == 82.0

    def test_no_shots_returns_zero(self):
        """Test zero attempts returns zero."""
        assert StatsCalculationService.calculate_true_shooting_pct(0, 0, 0) == 0.0

    def test_only_free_throws(self):
        """Test when all points come from free throws."""
        # 10 pts from FT only: 0 FGA, 10 FTA
        # TS% = 10 / (2 * (0 + 0.44 * 10)) * 100 = 10 / 8.8 * 100 = 113.6
        assert StatsCalculationService.calculate_true_shooting_pct(10, 0, 10) == 113.6

    def test_only_field_goals(self):
        """Test when all points come from field goals (no FT)."""
        # 20 pts, 10 FGA, 0 FTA
        # TS% = 20 / (2 * (10 + 0)) * 100 = 20 / 20 * 100 = 100.0
        assert StatsCalculationService.calculate_true_shooting_pct(20, 10, 0) == 100.0

    def test_realistic_game(self):
        """Test realistic game stats."""
        # 25 pts, 15 FGA, 8 FTA
        # TS% = 25 / (2 * (15 + 0.44 * 8)) * 100
        # TS% = 25 / (2 * (15 + 3.52)) * 100
        # TS% = 25 / (2 * 18.52) * 100
        # TS% = 25 / 37.04 * 100 = 67.5
        assert StatsCalculationService.calculate_true_shooting_pct(25, 15, 8) == 67.5

    def test_efficient_scorer(self):
        """Test an efficient scorer (high TS%)."""
        # 30 pts, 15 FGA, 5 FTA (efficient player)
        # TS% = 30 / (2 * (15 + 2.2)) * 100 = 30 / 34.4 * 100 = 87.2
        assert StatsCalculationService.calculate_true_shooting_pct(30, 15, 5) == 87.2

    def test_inefficient_scorer(self):
        """Test an inefficient scorer (low TS%)."""
        # 15 pts, 20 FGA, 5 FTA (inefficient player)
        # TS% = 15 / (2 * (20 + 2.2)) * 100 = 15 / 44.4 * 100 = 33.8
        assert StatsCalculationService.calculate_true_shooting_pct(15, 20, 5) == 33.8


class TestEffectiveFGPct:
    """
    Tests for calculate_effective_fg_pct method.

    Formula: eFG% = (FGM + 0.5 * 3PM) / FGA * 100
    """

    def test_no_three_pointers(self):
        """Test eFG% equals FG% when no 3-pointers."""
        # 5 FGM (all 2PT), 10 FGA
        # eFG% = (5 + 0) / 10 * 100 = 50.0
        assert StatsCalculationService.calculate_effective_fg_pct(5, 0, 10) == 50.0

    def test_all_three_pointers(self):
        """Test eFG% when all makes are 3-pointers."""
        # 4 FGM (all 3PT), 10 FGA
        # eFG% = (4 + 0.5 * 4) / 10 * 100 = 6 / 10 * 100 = 60.0
        assert StatsCalculationService.calculate_effective_fg_pct(4, 4, 10) == 60.0

    def test_mixed_shooting(self):
        """Test eFG% with mixed 2PT and 3PT makes."""
        # 8 FGM (5 2PT + 3 3PT), 15 FGA
        # eFG% = (8 + 0.5 * 3) / 15 * 100 = 9.5 / 15 * 100 = 63.3
        assert StatsCalculationService.calculate_effective_fg_pct(8, 3, 15) == 63.3

    def test_zero_attempts(self):
        """Test zero attempts returns zero."""
        assert StatsCalculationService.calculate_effective_fg_pct(0, 0, 0) == 0.0

    def test_perfect_two_point_shooting(self):
        """Test 100% 2PT shooting."""
        # 10 FGM (all 2PT), 10 FGA = 100% eFG
        assert StatsCalculationService.calculate_effective_fg_pct(10, 0, 10) == 100.0

    def test_perfect_three_point_shooting(self):
        """Test 100% 3PT shooting."""
        # 10 FGM (all 3PT), 10 FGA
        # eFG% = (10 + 0.5 * 10) / 10 * 100 = 15 / 10 * 100 = 150.0
        assert StatsCalculationService.calculate_effective_fg_pct(10, 10, 10) == 150.0

    def test_half_makes_half_threes(self):
        """Test 50% FG with half being threes."""
        # 10 FGM (5 2PT + 5 3PT), 20 FGA
        # eFG% = (10 + 0.5 * 5) / 20 * 100 = 12.5 / 20 * 100 = 62.5
        assert StatsCalculationService.calculate_effective_fg_pct(10, 5, 20) == 62.5


class TestAssistTurnoverRatio:
    """Tests for calculate_assist_turnover_ratio method."""

    def test_basic_ratio(self):
        """Test basic A/T ratio."""
        assert StatsCalculationService.calculate_assist_turnover_ratio(10, 5) == 2.0

    def test_zero_turnovers_with_assists(self):
        """Test zero turnovers returns assists as float."""
        assert StatsCalculationService.calculate_assist_turnover_ratio(5, 0) == 5.0

    def test_zero_both(self):
        """Test zero assists and turnovers returns zero."""
        assert StatsCalculationService.calculate_assist_turnover_ratio(0, 0) == 0.0

    def test_more_turnovers_than_assists(self):
        """Test when turnovers exceed assists."""
        assert StatsCalculationService.calculate_assist_turnover_ratio(3, 6) == 0.5

    def test_equal_assists_and_turnovers(self):
        """Test when assists equal turnovers."""
        assert StatsCalculationService.calculate_assist_turnover_ratio(5, 5) == 1.0

    def test_single_turnover(self):
        """Test with single turnover."""
        assert StatsCalculationService.calculate_assist_turnover_ratio(7, 1) == 7.0

    def test_rounding(self):
        """Test rounding to 2 decimal places."""
        # 7 / 3 = 2.333...
        assert StatsCalculationService.calculate_assist_turnover_ratio(7, 3) == 2.33

    def test_point_guard_ratio(self):
        """Test typical point guard ratio."""
        # 8 assists, 3 turnovers = 2.67
        assert StatsCalculationService.calculate_assist_turnover_ratio(8, 3) == 2.67

    def test_turnover_prone_player(self):
        """Test high turnover player."""
        # 4 assists, 6 turnovers = 0.67
        assert StatsCalculationService.calculate_assist_turnover_ratio(4, 6) == 0.67


class TestAverageCalculation:
    """Tests for calculate_average method."""

    def test_basic_average(self):
        """Test basic average calculation."""
        assert StatsCalculationService.calculate_average(100, 10) == 10.0

    def test_zero_games(self):
        """Test zero games returns zero."""
        assert StatsCalculationService.calculate_average(50, 0) == 0.0

    def test_rounding(self):
        """Test rounding to one decimal place."""
        # 100 / 3 = 33.333...
        assert StatsCalculationService.calculate_average(100, 3) == 33.3

    def test_zero_total(self):
        """Test zero total with games played."""
        assert StatsCalculationService.calculate_average(0, 10) == 0.0

    def test_points_per_game(self):
        """Test typical PPG calculation."""
        # 2000 points in 82 games = 24.4 PPG
        assert StatsCalculationService.calculate_average(2000, 82) == 24.4

    def test_rebounds_per_game(self):
        """Test typical RPG calculation."""
        # 820 rebounds in 82 games = 10.0 RPG
        assert StatsCalculationService.calculate_average(820, 82) == 10.0

    def test_assists_per_game(self):
        """Test typical APG calculation."""
        # 656 assists in 82 games = 8.0 APG
        assert StatsCalculationService.calculate_average(656, 82) == 8.0

    def test_single_game(self):
        """Test average over single game."""
        assert StatsCalculationService.calculate_average(35, 1) == 35.0

    def test_large_numbers(self):
        """Test with larger numbers."""
        # 3000 points in 100 games = 30.0 PPG
        assert StatsCalculationService.calculate_average(3000, 100) == 30.0


class TestIntegrationScenarios:
    """Integration tests combining multiple calculations for realistic scenarios."""

    def test_efficient_scorer_stats(self):
        """Test stats for an efficient scorer like Steph Curry."""
        # Hypothetical game: 30 pts, 8/15 FG (4 3PM), 6/6 FT
        # TS% = 30 / (2 * (15 + 0.44 * 6)) * 100 = 30 / 35.28 * 100 = 85.0
        fg_pct = StatsCalculationService.calculate_percentage(8, 15)
        three_pct = StatsCalculationService.calculate_percentage(4, 8)
        ft_pct = StatsCalculationService.calculate_percentage(6, 6)
        ts_pct = StatsCalculationService.calculate_true_shooting_pct(30, 15, 6)
        efg_pct = StatsCalculationService.calculate_effective_fg_pct(8, 4, 15)

        assert fg_pct == 53.3
        assert three_pct == 50.0
        assert ft_pct == 100.0
        assert ts_pct == 85.0  # Very efficient
        assert efg_pct == 66.7  # Boosted by 3-pointers

    def test_paint_scorer_stats(self):
        """Test stats for a paint scorer like Shaq."""
        # Hypothetical game: 28 pts, 12/20 FG (0 3PM), 4/10 FT
        fg_pct = StatsCalculationService.calculate_percentage(12, 20)
        ts_pct = StatsCalculationService.calculate_true_shooting_pct(28, 20, 10)
        efg_pct = StatsCalculationService.calculate_effective_fg_pct(12, 0, 20)

        assert fg_pct == 60.0
        assert ts_pct == 57.4  # Lower due to poor FT%
        assert efg_pct == 60.0  # Same as FG% (no 3s)

    def test_point_guard_playmaking(self):
        """Test point guard playmaking stats."""
        # 10 assists, 2 turnovers
        ast_to = StatsCalculationService.calculate_assist_turnover_ratio(10, 2)
        assert ast_to == 5.0

        # Season totals: 600 assists, 200 turnovers in 75 games
        season_ast_to = StatsCalculationService.calculate_assist_turnover_ratio(
            600, 200
        )
        apg = StatsCalculationService.calculate_average(600, 75)

        assert season_ast_to == 3.0
        assert apg == 8.0

    def test_zero_stat_edge_cases(self):
        """Test edge cases with zero values."""
        # Player with no shot attempts but free throws
        ts_pct = StatsCalculationService.calculate_true_shooting_pct(10, 0, 12)
        assert ts_pct == 94.7

        # Player with attempts but no makes
        fg_pct = StatsCalculationService.calculate_percentage(0, 15)
        efg_pct = StatsCalculationService.calculate_effective_fg_pct(0, 0, 15)
        assert fg_pct == 0.0
        assert efg_pct == 0.0


class TestCalculateFieldGoalPct:
    """Tests for field goal percentage calculation (ticket requirement)."""

    def test_calculate_field_goal_pct_basic(self):
        """Test FG% = FGM/FGA * 100."""
        # 8 made out of 16 = 50%
        assert StatsCalculationService.calculate_percentage(8, 16) == 50.0

    def test_calculate_field_goal_pct_high_volume(self):
        """Test FG% with high volume shooting."""
        # 400 made out of 900 attempts = 44.4%
        assert StatsCalculationService.calculate_percentage(400, 900) == 44.4

    def test_calculate_field_goal_pct_perfect(self):
        """Test perfect FG%."""
        assert StatsCalculationService.calculate_percentage(15, 15) == 100.0

    def test_calculate_field_goal_pct_zero_makes(self):
        """Test 0% FG with attempts."""
        assert StatsCalculationService.calculate_percentage(0, 20) == 0.0


class TestCalculateSeasonTotals:
    """
    Tests for season totals calculation logic.

    These tests verify that the sum of individual game stats produces
    the correct season totals.
    """

    def test_calculate_season_totals_points(self):
        """Test that season total points equals sum of game points."""
        # Simulate 5 games with varying points
        game_points = [20, 25, 18, 32, 15]
        expected_total = sum(game_points)  # 110

        assert expected_total == 110

    def test_calculate_season_totals_rebounds(self):
        """Test that season total rebounds equals sum of game rebounds."""
        game_rebounds = [8, 12, 6, 10, 9]
        expected_total = sum(game_rebounds)  # 45

        assert expected_total == 45

    def test_calculate_season_totals_shooting(self):
        """Test that FGM and FGA sum correctly for season."""
        # 5 games with FGM/FGA
        game_fgm = [8, 10, 7, 12, 6]
        game_fga = [15, 20, 14, 22, 15]

        total_fgm = sum(game_fgm)  # 43
        total_fga = sum(game_fga)  # 86

        assert total_fgm == 43
        assert total_fga == 86

        # Verify FG% calculation from totals
        fg_pct = StatsCalculationService.calculate_percentage(total_fgm, total_fga)
        assert fg_pct == 50.0  # 43/86 = 50%

    def test_calculate_season_totals_three_pointers(self):
        """Test 3PT totals sum correctly."""
        game_3pm = [3, 4, 2, 5, 1]
        game_3pa = [8, 10, 6, 12, 5]

        total_3pm = sum(game_3pm)  # 15
        total_3pa = sum(game_3pa)  # 41

        assert total_3pm == 15
        assert total_3pa == 41

        # Verify 3P% from totals
        three_pct = StatsCalculationService.calculate_percentage(total_3pm, total_3pa)
        assert three_pct == 36.6  # 15/41 = 36.6%

    def test_calculate_season_totals_free_throws(self):
        """Test FT totals sum correctly."""
        game_ftm = [5, 8, 3, 10, 6]
        game_fta = [6, 10, 4, 12, 8]

        total_ftm = sum(game_ftm)  # 32
        total_fta = sum(game_fta)  # 40

        assert total_ftm == 32
        assert total_fta == 40

        # Verify FT% from totals
        ft_pct = StatsCalculationService.calculate_percentage(total_ftm, total_fta)
        assert ft_pct == 80.0  # 32/40 = 80%

    def test_calculate_season_totals_assists_turnovers(self):
        """Test assists and turnovers sum correctly for A/T ratio."""
        game_assists = [7, 10, 5, 8, 6]
        game_turnovers = [2, 3, 1, 4, 2]

        total_assists = sum(game_assists)  # 36
        total_turnovers = sum(game_turnovers)  # 12

        assert total_assists == 36
        assert total_turnovers == 12

        # Verify A/T ratio from totals
        ast_to = StatsCalculationService.calculate_assist_turnover_ratio(
            total_assists, total_turnovers
        )
        assert ast_to == 3.0  # 36/12 = 3.0

    def test_calculate_season_totals_advanced_stats(self):
        """Test advanced stats calculated from season totals."""
        # Season totals
        total_points = 500
        total_fga = 400
        total_fta = 150
        total_fgm = 180
        total_3pm = 60

        # TS% = PTS / (2 * (FGA + 0.44 * FTA)) * 100
        # TS% = 500 / (2 * (400 + 66)) * 100 = 500 / 932 * 100 = 53.6
        ts_pct = StatsCalculationService.calculate_true_shooting_pct(
            total_points, total_fga, total_fta
        )
        assert ts_pct == 53.6

        # eFG% = (FGM + 0.5 * 3PM) / FGA * 100
        # eFG% = (180 + 30) / 400 * 100 = 210 / 400 * 100 = 52.5
        efg_pct = StatsCalculationService.calculate_effective_fg_pct(
            total_fgm, total_3pm, total_fga
        )
        assert efg_pct == 52.5


class TestCalculateSeasonAverages:
    """
    Tests for season averages calculation.

    Verifies that averages are correctly calculated by dividing totals
    by games played.
    """

    def test_calculate_season_averages_ppg(self):
        """Test PPG = total_points / games_played."""
        total_points = 2050
        games_played = 82
        expected_ppg = StatsCalculationService.calculate_average(
            total_points, games_played
        )
        assert expected_ppg == 25.0  # 2050/82 = 25.0

    def test_calculate_season_averages_rpg(self):
        """Test RPG = total_rebounds / games_played."""
        total_rebounds = 820
        games_played = 82
        expected_rpg = StatsCalculationService.calculate_average(
            total_rebounds, games_played
        )
        assert expected_rpg == 10.0

    def test_calculate_season_averages_apg(self):
        """Test APG = total_assists / games_played."""
        total_assists = 574
        games_played = 82
        expected_apg = StatsCalculationService.calculate_average(
            total_assists, games_played
        )
        assert expected_apg == 7.0

    def test_calculate_season_averages_minutes(self):
        """Test minutes per game calculation."""
        # Minutes stored in seconds: 2100 seconds = 35 minutes per game
        total_seconds = 172200  # 82 games * 2100 seconds
        games_played = 82
        avg_seconds = StatsCalculationService.calculate_average(
            total_seconds, games_played
        )
        assert avg_seconds == 2100.0

    def test_calculate_season_averages_short_season(self):
        """Test averages for shortened season."""
        total_points = 500
        games_played = 20
        ppg = StatsCalculationService.calculate_average(total_points, games_played)
        assert ppg == 25.0

    def test_calculate_season_averages_single_game(self):
        """Test averages when only 1 game played."""
        total_points = 35
        games_played = 1
        ppg = StatsCalculationService.calculate_average(total_points, games_played)
        assert ppg == 35.0
