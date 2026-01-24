# Alembic Migrations

## Purpose

This directory contains database migration scripts for the Basketball Analytics Platform. Alembic manages version-controlled schema migrations, allowing the database schema to evolve alongside the application code.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `env.py` | Migration environment configuration - connects to database and loads model metadata |
| `script.py.mako` | Template for generating new migration files |
| `versions/` | Directory containing migration scripts (ordered by timestamp) |

## Migration Workflow

### Creating a New Migration

After making changes to SQLAlchemy models in `src/models/`, generate a migration:

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "Add players table"

# Create empty migration for manual edits
uv run alembic revision -m "Add custom index"
```

**Important:** After generating a migration, always review the generated file in `alembic/versions/` to ensure the operations are correct.

### Applying Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Apply next migration only
uv run alembic upgrade +1

# Apply to specific revision
uv run alembic upgrade abc123
```

### Rolling Back Migrations

```bash
# Rollback one migration
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade abc123

# Rollback all migrations (back to empty database)
uv run alembic downgrade base
```

### Viewing Migration Status

```bash
# Show current revision
uv run alembic current

# Show migration history
uv run alembic history

# Show pending migrations
uv run alembic history --indicate-current
```

## Adding New Models

When you add a new SQLAlchemy model:

1. Create the model in `src/models/` inheriting from `Base`
2. Import the model in `alembic/env.py` so it's registered with metadata
3. Run `uv run alembic revision --autogenerate -m "Add <model> table"`
4. Review the generated migration
5. Apply with `uv run alembic upgrade head`

Example model import in `env.py`:
```python
# Import all models for autogenerate detection
from src.models.player import Player
from src.models.team import Team
```

## Best Practices

### Migration Naming

Use descriptive messages that explain what the migration does:
- ✅ `"Add players table"`
- ✅ `"Add index on game_date column"`
- ✅ `"Add foreign key from stats to players"`
- ❌ `"update"`
- ❌ `"fix"`

### Migration Content

1. **Keep migrations small and focused** - One logical change per migration
2. **Always test downgrade** - Ensure migrations can be rolled back
3. **Use batch operations for SQLite** - The env.py is configured for this
4. **Avoid data migrations in schema migrations** - Create separate migrations for data changes

### Before Committing

1. Run `uv run alembic upgrade head` to verify migrations apply cleanly
2. Run `uv run alembic downgrade base` to verify rollback works
3. Run tests to ensure application still works with new schema

## Troubleshooting

### "Target database is not up to date"

The database schema doesn't match the expected revision. Run:
```bash
uv run alembic upgrade head
```

### "Can't locate revision"

A migration file may be missing or corrupted. Check `alembic/versions/` for the expected file.

### "Multiple head revisions"

Multiple branches exist. Merge them:
```bash
uv run alembic merge heads -m "Merge migrations"
```

## Dependencies

- SQLAlchemy 2.0+
- Alembic 1.13+
- Application settings from `src.core.config`
- Base metadata from `src.models.base`

## Related Documentation

- [SQLAlchemy ORM Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Project Models](../src/models/README.md)
