# Tests

## Purpose

This directory contains all automated tests for the Basketball Analytics Platform. Tests are organized by type and module to ensure comprehensive coverage of the codebase.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package marker for the test suite |
| `conftest.py` | Shared pytest fixtures (database sessions, test client) |
| `test_placeholder.py` | Placeholder test to verify pytest runs |

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run with coverage and fail if below threshold
pytest --cov=src --cov-fail-under=80
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/test_placeholder.py

# Run tests matching a pattern
pytest -k "test_health"

# Run only fast tests (exclude slow/integration)
pytest -m "not slow and not integration"

# Run integration tests only
pytest -m integration
```

### Test Output Options

```bash
# Show print statements
pytest -s

# Show local variables in tracebacks
pytest -l

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

## Fixtures

The following fixtures are available in `conftest.py`:

### `test_db`

| Property | Value |
|----------|-------|
| Scope | function |
| Purpose | In-memory SQLite session with auto-rollback |

Provides an isolated database session for each test. All database changes are automatically rolled back after the test completes.

```python
def test_create_player(test_db):
    """Example test using test_db fixture."""
    from src.models.player import Player

    player = Player(name="Test Player")
    test_db.add(player)
    test_db.commit()

    assert test_db.query(Player).count() == 1
    # Changes are automatically rolled back after test
```

### `client`

| Property | Value |
|----------|-------|
| Scope | function |
| Purpose | FastAPI TestClient with test database |

Provides a test client that uses the test database. Useful for testing API endpoints.

```python
def test_health_endpoint(client):
    """Example test using client fixture."""
    response = client.get("/health")
    assert response.status_code == 200
```

### `test_engine`

| Property | Value |
|----------|-------|
| Scope | function |
| Purpose | SQLAlchemy engine for in-memory SQLite |

Low-level fixture providing the database engine. Usually you should use `test_db` instead.

## Test Organization

Tests should be organized as follows:

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── README.md            # This file
├── test_placeholder.py  # Placeholder test
├── unit/                # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_models.py
│   └── test_services.py
├── integration/         # Integration tests (slower, full stack)
│   ├── __init__.py
│   └── test_api.py
└── e2e/                 # End-to-end tests
    ├── __init__.py
    └── test_workflows.py
```

## Markers

Custom pytest markers are defined in `pyproject.toml`:

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.slow` | Marks tests as slow (exclude with `-m "not slow"`) |
| `@pytest.mark.integration` | Marks tests as integration tests |

Example usage:

```python
import pytest

@pytest.mark.slow
def test_large_data_import(test_db):
    """This test processes a lot of data."""
    pass

@pytest.mark.integration
def test_full_sync_workflow(client):
    """This test requires external services."""
    pass
```

## Writing New Tests

### Test File Naming

- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`
- E2E tests: `test_<workflow>_e2e.py`

### Test Function Naming

```python
def test_<action>_<expected_result>():
    """Test that <action> results in <expected_result>."""
    pass

# Examples
def test_create_player_returns_player_id():
def test_get_nonexistent_player_raises_not_found():
def test_update_stats_increments_points():
```

### Test Structure (Arrange-Act-Assert)

```python
def test_player_creation(test_db):
    """Test that creating a player persists correctly."""
    # Arrange
    player_data = {"name": "Test Player", "team_id": "abc-123"}

    # Act
    player = Player(**player_data)
    test_db.add(player)
    test_db.commit()

    # Assert
    saved_player = test_db.query(Player).first()
    assert saved_player.name == "Test Player"
```

## Coverage Requirements

- Target coverage: **80%**
- Coverage reporting is enabled in CI
- Note: `--cov-fail-under=80` will be enforced once source code is added
- Check coverage locally:

```bash
# Generate terminal report
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Dependencies

- **Internal:** Uses `src.core.database` for Base and `src.main` for FastAPI app
- **External Libraries:**
  - `pytest>=7.4.0` - Test framework
  - `pytest-cov>=4.1.0` - Coverage reporting
  - `pytest-asyncio>=0.23.0` - Async test support

## Related Documentation

- [Project README](/README.md)
- [API Documentation](/docs/api/README.md)
- [Architecture](/docs/architecture.md)
