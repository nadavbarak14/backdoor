# Real Data Integration Tests

Integration tests that verify all tools work correctly with the real database.

## Purpose

These tests ensure:
1. Database is properly populated with data
2. All API endpoints work with real data
3. All 14 AI chat tools function correctly
4. Services return valid results

## Contents

| File | Description |
|------|-------------|
| conftest.py | Fixtures for real database connection |
| test_data_population.py | Verify data exists in all tables |
| test_api.py | API endpoint tests |
| test_chat_tools.py | All 14 LangChain chat tools |
| test_services.py | Service layer tests |
| test_query_stats_accuracy.py | Comprehensive query_stats data accuracy tests (50 tests) |

## Usage

```bash
# Run all real data tests
uv run python -m pytest tests/integration/real_data/ -v

# Run specific test file
uv run python -m pytest tests/integration/real_data/test_chat_tools.py -v
```

## Requirements

These tests require `basketball.db` to exist in the project root with synced data.

## Dependencies

- Real database: `basketball.db`
- All src modules: models, services, schemas, api
