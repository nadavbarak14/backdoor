# Viewer Unit Tests

## Purpose

Tests for the Internal Data Viewer Streamlit application.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `test_page_imports.py` | Verifies page files can be imported correctly |

## Test Categories

### Import Tests (`test_page_imports.py`)

These tests verify that:
1. All viewer pages have proper `sys.path` setup for Streamlit execution
2. Component modules export expected functions
3. Database session management is importable

This is critical because Streamlit pages are executed via `exec()` in a
different context than normal Python imports.

## Running Tests

```bash
# Run all viewer tests
uv run python -m pytest tests/unit/viewer/ -v

# Run specific test file
uv run python -m pytest tests/unit/viewer/test_page_imports.py -v
```

## Adding New Tests

When adding tests for viewer pages:
1. Mock Streamlit functions (`st.cache_data`, `st.query_params`, etc.)
2. Use `pytest-mock` or `unittest.mock` for Streamlit components
3. Test data loading functions separately from UI rendering
