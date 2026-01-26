# NBA Sync Unit Tests

## Purpose

Unit tests for the NBA sync module that fetches data from the NBA Stats API.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Test module initialization |
| `test_config.py` | Tests for `NBAConfig` settings and methods |
| `test_mapper.py` | Tests for `NBAMapper` data transformation |

## Running Tests

```bash
# Run all NBA sync tests
uv run python -m pytest tests/unit/sync/nba/ -v

# Run specific test file
uv run python -m pytest tests/unit/sync/nba/test_mapper.py -v

# Run with coverage
uv run python -m pytest tests/unit/sync/nba/ --cov=src/sync/nba
```

## Test Coverage

- **Config Tests**: Default values, custom configuration, helper methods
- **Mapper Tests**: Minutes parsing, date parsing, season/team/game mapping, player stats, boxscore, PBP events

## Dependencies

- `pytest` - Test framework
- `src.sync.nba` - Module under test
