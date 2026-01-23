# Core Module

## Purpose

The core module contains fundamental application infrastructure that other modules depend on. This includes configuration management, database setup, and shared utilities.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Exports `settings`, `Settings`, and `get_settings` |
| `config.py` | Pydantic Settings class with all application configuration |

## Usage

### Importing Settings

```python
# Recommended: Import the singleton instance
from src.core import settings

print(settings.PROJECT_NAME)  # "Basketball Analytics"
print(settings.DATABASE_URL)  # "sqlite:///./basketball.db"
```

### All Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PROJECT_NAME` | str | "Basketball Analytics" | Application display name |
| `DEBUG` | bool | False | Enable debug mode |
| `DATABASE_URL` | str | "sqlite:///./basketball.db" | Database connection string |
| `TEST_DATABASE_URL` | str | "sqlite:///:memory:" | Test database connection |
| `API_PREFIX` | str | "/api/v1" | API route prefix |

### Environment Variables

Settings can be overridden via environment variables or a `.env` file:

```bash
# Set via environment
export DEBUG=true
export DATABASE_URL="postgresql://user:pass@localhost/basketball"

# Or create a .env file in project root
echo "DEBUG=true" >> .env
```

### For Testing

```python
from src.core.config import Settings

# Create settings with custom values
test_settings = Settings(
    DEBUG=True,
    DATABASE_URL="sqlite:///:memory:"
)
```

### Dependency Injection (FastAPI)

```python
from fastapi import Depends
from src.core import Settings, get_settings

def get_db_url(settings: Settings = Depends(get_settings)) -> str:
    return settings.DATABASE_URL
```

## Dependencies

- **Depends on:** None (this is a foundational module)
- **External libs:** `pydantic-settings>=2.1.0`

## Related Documentation

- [Architecture Overview](../../docs/architecture.md)
- [Environment Example](../../.env.example)
