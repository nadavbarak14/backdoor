"""
AI tests for query_stats tool.

These tests validate that the LLM correctly interprets natural language
queries and generates the right filter parameters. They are NOT run in CI
and require manual execution with actual LLM inference.

Run with: pytest tests/ai/ -m ai_test --run-ai
"""

import pytest


@pytest.mark.ai_test
@pytest.mark.skip_ci
def test_ai_opponent_query():
    """
    Test: 'Stats vs Hapoel' -> opponent_team='Hapoel'

    This test validates that when a user asks about stats against
    a specific opponent, the LLM correctly extracts the opponent_team
    parameter.

    Expected behavior:
    - Input: "Show me stats vs Hapoel"
    - Output should include: opponent_team="Hapoel" (or similar)
    """
    # This test requires LLM inference and is skipped in CI
    # Manual execution: pytest tests/ai/test_query_stats_ai.py -m ai_test --run-ai
    pass


@pytest.mark.ai_test
@pytest.mark.skip_ci
def test_ai_home_away_query():
    """
    Test: 'How do we play at home?' -> home_only=True

    This test validates that when a user asks about home game
    performance, the LLM correctly sets home_only=True.

    Expected behavior:
    - Input: "How do we perform at home?"
    - Output should include: home_only=True
    """
    # This test requires LLM inference and is skipped in CI
    # Manual execution: pytest tests/ai/test_query_stats_ai.py -m ai_test --run-ai
    pass


@pytest.mark.ai_test
@pytest.mark.skip_ci
def test_ai_away_query():
    """
    Test: 'Road game performance' -> away_only=True

    This test validates that when a user asks about away game
    performance, the LLM correctly sets away_only=True.

    Expected behavior:
    - Input: "What are our stats on the road?"
    - Output should include: away_only=True
    """
    pass


@pytest.mark.ai_test
@pytest.mark.skip_ci
def test_ai_combined_location_time_query():
    """
    Test: 'Home 4th quarter stats' -> home_only=True, quarter=4

    This test validates that location and time filters compose correctly.

    Expected behavior:
    - Input: "How do we perform in the 4th quarter at home?"
    - Output should include: home_only=True, quarter=4
    """
    pass


@pytest.mark.ai_test
@pytest.mark.skip_ci
def test_ai_opponent_clutch_query():
    """
    Test: 'Clutch stats vs Hapoel' -> opponent_team='Hapoel', clutch_only=True

    This test validates that opponent and clutch filters compose correctly.

    Expected behavior:
    - Input: "What are our clutch stats against Hapoel?"
    - Output should include: opponent_team="Hapoel", clutch_only=True
    """
    pass
