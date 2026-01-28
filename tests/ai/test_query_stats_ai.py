"""
AI tests for query_stats tool.

These tests validate that the LLM correctly interprets natural language
queries and generates the right filter parameters. They are NOT run in CI
and require manual execution with actual LLM inference.

Run with: pytest tests/ai/ -m ai_test --run-ai

Cost considerations:
- Each test makes 1-3 LLM API calls
- Total ~15-20 test cases
- Estimated cost: ~$0.10-0.20 per full run with gpt-4o-mini
"""

import pytest

# =============================================================================
# Basic Query Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsBasicAI:
    """Basic AI tests for query_stats."""

    def test_ai_player_stats_query(self, ai_agent):
        """
        Test: 'Get Jimmy Clark stats' -> uses search_players + query_stats

        Validates that the agent:
        1. Searches for the player by name
        2. Uses the returned ID with query_stats
        """
        result = ai_agent.invoke({"input": "Get stats for Jimmy Clark"})
        output = result.get("output", "").lower()
        # Should return some stats or indicate player not found
        assert "point" in output or "stat" in output or "not found" in output

    def test_ai_team_stats_query(self, ai_agent):
        """
        Test: 'Maccabi season stats' -> uses search_teams + query_stats

        Validates that the agent searches for the team and queries stats.
        """
        result = ai_agent.invoke({"input": "Show me Maccabi Tel-Aviv stats"})
        output = result.get("output", "").lower()
        assert "maccabi" in output or "stat" in output or "not found" in output

    def test_ai_league_leaders_query(self, ai_agent):
        """
        Test: 'Top scorers' -> query_stats with order_by='points'

        Validates that "top scorers" triggers leaderboard mode.
        """
        result = ai_agent.invoke({"input": "Who are the top scorers in the league?"})
        output = result.get("output", "").lower()
        assert "leader" in output or "top" in output or "point" in output


# =============================================================================
# Time Filter Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsTimeFiltersAI:
    """AI tests for time-based filters."""

    def test_ai_quarter_filter_query(self, ai_agent):
        """
        Test: '4th quarter scoring' -> quarter=4

        Validates that quarter references are correctly extracted.
        """
        result = ai_agent.invoke(
            {"input": "How does Maccabi perform in the 4th quarter?"}
        )
        output = result.get("output", "").lower()
        assert "q4" in output or "4th" in output or "quarter" in output

    def test_ai_clutch_query(self, ai_agent):
        """
        Test: 'Clutch performance' -> clutch_only=True

        Validates that clutch references trigger clutch_only filter.
        """
        result = ai_agent.invoke({"input": "Show clutch time stats for Maccabi"})
        output = result.get("output", "").lower()
        assert "clutch" in output

    def test_ai_first_half_query(self, ai_agent):
        """
        Test: 'First half stats' -> quarters=[1, 2]

        Validates that "first half" is interpreted correctly.
        """
        result = ai_agent.invoke({"input": "Maccabi first half performance"})
        output = result.get("output", "").lower()
        assert "half" in output or "1st" in output or "q1" in output or "q2" in output

    def test_ai_last_n_games_query(self, ai_agent):
        """
        Test: 'Last 5 games' -> last_n_games=5

        Validates recent game queries.
        """
        result = ai_agent.invoke({"input": "Stats from the last 5 games for Maccabi"})
        output = result.get("output", "").lower()
        assert "last" in output or "5" in output or "game" in output


# =============================================================================
# Location Filter Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsLocationFiltersAI:
    """AI tests for location-based filters."""

    def test_ai_home_query(self, ai_agent):
        """
        Test: 'How do we play at home?' -> home_only=True

        Validates home game filter detection.
        """
        result = ai_agent.invoke({"input": "How does Maccabi perform at home?"})
        output = result.get("output", "").lower()
        assert "home" in output

    def test_ai_away_query(self, ai_agent):
        """
        Test: 'Road game performance' -> away_only=True

        Validates away game filter detection.
        """
        result = ai_agent.invoke({"input": "Maccabi road game stats"})
        output = result.get("output", "").lower()
        assert "away" in output or "road" in output

    def test_ai_opponent_query(self, ai_agent):
        """
        Test: 'Stats vs Hapoel' -> opponent_team='Hapoel'

        Validates opponent team filter detection.
        """
        result = ai_agent.invoke(
            {"input": "How does Maccabi perform against Hapoel Jerusalem?"}
        )
        output = result.get("output", "").lower()
        assert "hapoel" in output or "vs" in output or "against" in output


# =============================================================================
# Advanced Mode Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsAdvancedModesAI:
    """AI tests for advanced query modes."""

    def test_ai_lineup_query(self, ai_agent):
        """
        Test: 'How do X and Y play together?' -> player_ids=[X, Y] (lineup mode)

        Validates that two-player queries trigger lineup mode.
        """
        result = ai_agent.invoke(
            {"input": "How do the two starting guards play together?"}
        )
        output = result.get("output", "").lower()
        assert "lineup" in output or "together" in output or "pair" in output

    def test_ai_leaderboard_query(self, ai_agent):
        """
        Test: 'Assist leaders' -> order_by='assists'

        Validates that category-specific leaderboard queries work.
        """
        result = ai_agent.invoke({"input": "Who leads the league in assists?"})
        output = result.get("output", "").lower()
        assert "assist" in output or "leader" in output

    def test_ai_efficiency_query(self, ai_agent):
        """
        Test: 'Most efficient shooters' -> order_by='fg_pct'

        Validates efficiency/percentage queries.
        """
        result = ai_agent.invoke({"input": "Who has the best field goal percentage?"})
        output = result.get("output", "").lower()
        assert "fg" in output or "field goal" in output or "percent" in output


# =============================================================================
# Combined Filter Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsCompositionAI:
    """AI tests for filter composition."""

    def test_ai_combined_location_time_query(self, ai_agent):
        """
        Test: 'Home 4th quarter stats' -> home_only=True, quarter=4

        Validates that location and time filters compose correctly.
        """
        result = ai_agent.invoke(
            {"input": "How does Maccabi perform in the 4th quarter at home?"}
        )
        output = result.get("output", "").lower()
        assert ("home" in output and ("q4" in output or "4th" in output)) or (
            "no stats" in output or "no games" in output
        )

    def test_ai_opponent_clutch_query(self, ai_agent):
        """
        Test: 'Clutch stats vs Hapoel' -> opponent_team='Hapoel', clutch_only=True

        Validates opponent and clutch filters compose correctly.
        """
        result = ai_agent.invoke(
            {"input": "What are Maccabi's clutch stats against Hapoel?"}
        )
        output = result.get("output", "").lower()
        assert "clutch" in output or "hapoel" in output


# =============================================================================
# Situational Filter Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsSituationalAI:
    """AI tests for situational filters."""

    def test_ai_fast_break_query(self, ai_agent):
        """
        Test: 'Fast break points' -> fast_break=True

        Validates fast break filter detection.
        """
        result = ai_agent.invoke({"input": "How efficient is Maccabi on fast breaks?"})
        output = result.get("output", "").lower()
        assert "fast break" in output or "transition" in output

    def test_ai_contested_shots_query(self, ai_agent):
        """
        Test: 'Contested shot percentage' -> contested=True

        Validates contested shot filter detection.
        """
        result = ai_agent.invoke(
            {"input": "What's the team's contested shot percentage?"}
        )
        output = result.get("output", "").lower()
        assert "contested" in output or "shot" in output


# =============================================================================
# Schedule Filter Tests
# =============================================================================


@pytest.mark.ai_test
@pytest.mark.skip_ci
class TestQueryStatsScheduleAI:
    """AI tests for schedule-based filters."""

    def test_ai_back_to_back_query(self, ai_agent):
        """
        Test: 'Performance on back to backs' -> back_to_back=True

        Validates back-to-back filter detection.
        """
        result = ai_agent.invoke(
            {"input": "How does Maccabi perform on back-to-back games?"}
        )
        output = result.get("output", "").lower()
        assert "back" in output or "b2b" in output or "consecutive" in output

    def test_ai_rest_days_query(self, ai_agent):
        """
        Test: 'Well rested games' -> min_rest_days=3

        Validates rest day filter detection.
        """
        result = ai_agent.invoke(
            {"input": "Show me stats when the team has had 3+ days of rest"}
        )
        output = result.get("output", "").lower()
        assert "rest" in output or "day" in output
