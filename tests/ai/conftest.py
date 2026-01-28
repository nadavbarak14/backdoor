"""
AI test configuration and fixtures.

This module configures the AI testing infrastructure:
- Adds --run-ai CLI option to enable AI tests
- Skips AI tests by default in CI and normal runs
- Provides the ai_agent fixture for LLM-based testing

Usage:
    # Run all tests (AI tests skipped)
    pytest

    # Run AI tests only
    pytest tests/ai/ -m ai_test --run-ai

    # Run all tests including AI
    pytest --run-ai
"""

import pytest


def pytest_addoption(parser):
    """Add --run-ai CLI option."""
    parser.addoption(
        "--run-ai",
        action="store_true",
        default=False,
        help="Run AI tests that require LLM inference",
    )


def pytest_collection_modifyitems(config, items):
    """Skip AI tests unless --run-ai is provided."""
    if config.getoption("--run-ai"):
        # --run-ai given: don't skip AI tests
        return

    skip_ai = pytest.mark.skip(reason="AI tests skipped (use --run-ai to enable)")
    for item in items:
        if "ai_test" in item.keywords:
            item.add_marker(skip_ai)


@pytest.fixture
def ai_agent(real_db):
    """
    Create an agent with LLM for testing.

    This fixture sets up a LangChain agent with:
    - The query_stats tool
    - Search tools (search_players, search_teams, etc.)
    - A small/fast LLM model for inference

    Note: This fixture requires the LangChain and OpenAI packages,
    plus valid API credentials.

    Args:
        real_db: The real database session fixture.

    Yields:
        Agent executor ready for testing.

    Example:
        >>> def test_query(ai_agent):
        ...     result = ai_agent.invoke({"input": "Get stats for Maccabi"})
        ...     assert "points" in result["output"].lower()
    """
    # Import here to avoid import errors when AI tests are skipped
    try:
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        from src.services.query_stats import query_stats
        from src.services.search_tools import SEARCH_TOOLS
    except ImportError as e:
        pytest.skip(f"AI test dependencies not installed: {e}")

    # Create LLM (using a smaller model for testing)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Create tools with db injection
    def make_tool_with_db(tool):
        """Wrap tool to inject db parameter."""
        original_func = tool.func

        def wrapped(**kwargs):
            kwargs["db"] = real_db
            return original_func(**kwargs)

        # Create new tool with same metadata
        from langchain_core.tools import StructuredTool

        return StructuredTool(
            name=tool.name,
            description=tool.description,
            func=wrapped,
            args_schema=tool.args_schema,
        )

    # Wrap query_stats to inject db
    def query_stats_with_db(**kwargs):
        kwargs["db"] = real_db
        return query_stats.func(**kwargs)

    from langchain_core.tools import StructuredTool

    query_stats_tool = StructuredTool(
        name=query_stats.name,
        description=query_stats.description,
        func=query_stats_with_db,
        args_schema=query_stats.args_schema,
    )

    # Collect all tools
    tools = [query_stats_tool] + [make_tool_with_db(t) for t in SEARCH_TOOLS]

    # Create agent prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a basketball analytics assistant. You help users query
basketball statistics using the available tools.

When the user asks about stats, use the search tools to find entity IDs first,
then use query_stats with those IDs to get the statistics.

For example:
1. "Get Maccabi stats" -> search_teams("Maccabi") -> query_stats(team_id=...)
2. "Clark's points" -> search_players("Clark") -> query_stats(player_ids=[...])
""",
            ),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # Create and return agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor
