# AI Tests

This directory contains AI tests that require LLM inference and are **NOT run in CI**.

## Purpose

AI tests validate that the LLM correctly interprets natural language queries and generates the right tool parameters. Unlike unit tests which mock the LLM, these tests use actual LLM inference.

## Running AI Tests

```bash
# Run all AI tests
pytest tests/ai/ -m ai_test --run-ai

# Run specific test class
pytest tests/ai/test_query_stats_ai.py::TestQueryStatsBasicAI --run-ai

# Run with verbose output
pytest tests/ai/ -m ai_test --run-ai -v
```

## Cost Considerations

- Each test makes 1-3 LLM API calls
- Total ~15-20 test cases
- Estimated cost: ~$0.10-0.20 per full run with gpt-4o-mini
- Uses `gpt-4o-mini` by default (cheap and fast)

## Requirements

1. **LangChain packages**: `langchain`, `langchain-openai`
2. **OpenAI API key**: Set `OPENAI_API_KEY` environment variable
3. **Real database**: Tests use the `real_db` fixture with actual data

## Test Structure

| Test Class | Description |
|------------|-------------|
| `TestQueryStatsBasicAI` | Basic player, team, and leaderboard queries |
| `TestQueryStatsTimeFiltersAI` | Quarter, clutch, and recent game queries |
| `TestQueryStatsLocationFiltersAI` | Home, away, and opponent queries |
| `TestQueryStatsAdvancedModesAI` | Lineup and leaderboard mode queries |
| `TestQueryStatsCompositionAI` | Combined filter queries |
| `TestQueryStatsSituationalAI` | Fast break and contested shot queries |
| `TestQueryStatsScheduleAI` | Back-to-back and rest day queries |

## Adding New Tests

```python
@pytest.mark.ai_test
@pytest.mark.skip_ci
def test_ai_new_query(self, ai_agent):
    """
    Test: 'Natural language query' -> expected tool parameters
    """
    result = ai_agent.invoke({"input": "Your natural language query"})
    output = result.get("output", "").lower()
    assert "expected" in output
```

## Why These Aren't in CI

1. **Cost**: LLM API calls cost money
2. **Non-determinism**: LLM outputs vary between runs
3. **Speed**: API calls add latency
4. **External dependency**: Requires API access

## Interpreting Results

- **Pass**: The LLM generated appropriate tool calls
- **Fail**: Check if the assertion is too strict or if the LLM misinterpreted the query
- **Skip**: Normal when running without `--run-ai` flag
