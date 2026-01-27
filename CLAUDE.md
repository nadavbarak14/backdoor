# Basketball Analytics Platform - Development Guidelines

## Documentation Requirements (MANDATORY)

### Every Folder Must Have Documentation
Each directory in the project MUST contain a `README.md` explaining:
- Purpose of the folder/module
- What files it contains and their responsibilities
- How to use the components
- Dependencies on other modules

### API Documentation (CRITICAL)
API documentation is **highest priority**. Every endpoint MUST have:

1. **OpenAPI/Swagger docs** - Auto-generated via FastAPI
2. **Docstrings on every route** with:
   - Description of what the endpoint does
   - All parameters with types and descriptions
   - All possible response codes and their meanings
   - Example request/response bodies
3. **Dedicated API docs** in `docs/api/` with:
   - Full endpoint reference
   - Authentication requirements
   - Rate limiting info
   - Error code reference
   - Example usage with curl/httpx

### Code Documentation Standards

#### Functions and Methods
```python
def get_player_stats(player_id: str, season_id: str | None = None) -> PlayerStats:
    """
    Retrieve player statistics for a specific season or career totals.

    Args:
        player_id: UUID of the player
        season_id: Optional UUID of season. If None, returns career stats.

    Returns:
        PlayerStats object containing totals, averages, and percentages.

    Raises:
        PlayerNotFoundError: If player_id doesn't exist
        SeasonNotFoundError: If season_id is provided but doesn't exist

    Example:
        >>> stats = get_player_stats("abc-123", "season-456")
        >>> print(stats.avg_points)
        15.4
    """
```

#### Classes
```python
class PlayerGameStats(Base):
    """
    Per-game statistics for a player.

    Stores all box score data for a single player in a single game.
    Stats are stored as integers where applicable (minutes as seconds).

    Attributes:
        game_id: Foreign key to Game
        player_id: Foreign key to Player
        team_id: Foreign key to Team (player's team for this game)
        minutes_played: Playing time in seconds
        points: Total points scored
        ...

    Relationships:
        game: The Game this stat line belongs to
        player: The Player who recorded these stats
        team: The Team the player played for

    Example:
        >>> stat = PlayerGameStats(game_id=game.id, player_id=player.id, points=25)
    """
```

#### Modules
Every Python file must start with a module docstring:
```python
"""
Player Service Module

Provides business logic for player-related operations including:
- Player search and retrieval
- Team history tracking
- Stats aggregation

This service sits between the API layer and the data models,
handling all player-related business logic.

Usage:
    from src.services.player_service import PlayerService

    service = PlayerService(db_session)
    player = service.get_by_id("abc-123")
"""
```

### Folder README Template
```markdown
# [Folder Name]

## Purpose
[What this module/folder is responsible for]

## Contents
| File | Description |
|------|-------------|
| file1.py | Does X |
| file2.py | Does Y |

## Usage
[How to use components from this folder]

## Dependencies
- Depends on: [list internal dependencies]
- External libs: [list external packages used]

## Related Documentation
- [Link to related docs]
```

## Project Structure

The project follows a **component-based layered architecture** where code is organized by technical component (models, schemas, services, api). Each component folder contains all related files for that layer.

```
basketball-analytics/
├── CLAUDE.md                 # This file - development guidelines
├── README.md                 # Project overview and setup
├── alembic/                  # Database migrations
│   └── README.md
├── docs/
│   ├── README.md             # Documentation overview
│   ├── architecture.md       # System architecture
│   ├── api/                  # API documentation (CRITICAL)
│   │   └── README.md
│   └── models/               # Data model documentation
│       └── README.md
├── src/
│   ├── README.md             # Source code overview (REQUIRED)
│   ├── core/                 # Core infrastructure (config, database)
│   │   └── README.md
│   ├── models/               # SQLAlchemy ORM models
│   │   └── README.md
│   ├── schemas/              # Pydantic request/response schemas
│   │   └── README.md
│   ├── services/             # Business logic layer
│   │   └── README.md
│   ├── api/                  # FastAPI routers
│   │   ├── README.md
│   │   └── v1/               # API version 1
│   │       └── README.md
│   └── sync/                 # External data synchronization
│       └── README.md
└── tests/
    ├── README.md
    ├── unit/                 # Unit tests by component
    │   └── README.md
    └── integration/          # Integration tests
        └── README.md
```

## Component-Based Architecture (MANDATORY)

### Every Folder Must Have a README.md

**This is non-negotiable.** Every directory in the project MUST contain a `README.md` that explains:

1. **Purpose** - What this folder is responsible for
2. **Contents** - Table listing each file and its responsibility
3. **Usage** - Code examples showing how to use components
4. **Dependencies** - What this component depends on (internal and external)

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Core** | `src/core/` | Configuration, database connection, shared exceptions |
| **Models** | `src/models/` | SQLAlchemy ORM models (database tables) |
| **Schemas** | `src/schemas/` | Pydantic models for API validation |
| **Services** | `src/services/` | Business logic, orchestrates data access |
| **API** | `src/api/` | FastAPI routers, HTTP request handling |
| **Sync** | `src/sync/` | External API integrations, data import |

### Component Structure

Each component folder follows this pattern:

```
src/<component>/
├── README.md           # Component documentation (REQUIRED)
├── __init__.py         # Public exports
├── base.py             # Base classes/utilities (if applicable)
├── player.py           # Player-related code
├── team.py             # Team-related code
├── game.py             # Game-related code
└── stats.py            # Statistics-related code
```

### Import Rules & Data Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌────────┐
│   API   │ ──▶ │ Services │ ──▶ │  Models  │ ──▶ │  Core  │
│ (routes)│     │ (logic)  │     │  (ORM)   │     │ (db)   │
└─────────┘     └──────────┘     └──────────┘     └────────┘
     │               │
     ▼               ▼
┌─────────┐     ┌──────────┐
│ Schemas │     │   Sync   │
│(validate)│    │(external)│
└─────────┘     └──────────┘
```

```python
# ✅ CORRECT import direction (outer layers import inner layers)
from src.core.config import settings              # Core is available everywhere
from src.core.database import get_db              # Core is available everywhere
from src.models.base import Base, UUIDMixin       # Models available to services
from src.models.player import Player              # Models available to services
from src.schemas.player import PlayerCreate       # Schemas available to API
from src.services.player import PlayerService     # Services available to API

# ❌ WRONG import direction (inner layers should not import outer layers)
from src.api.v1.players import router             # Models should NOT import from API
from src.services.player import PlayerService     # Models should NOT import services
```

### Adding a New Entity (e.g., "Season")

When adding a new entity to the system:

1. **Model** (`src/models/season.py`): Create SQLAlchemy model
2. **Schema** (`src/schemas/season.py`): Create Pydantic schemas
3. **Service** (`src/services/season.py`): Create business logic
4. **Router** (`src/api/v1/seasons.py`): Create API endpoints
5. **Migration**: Run `uv run alembic revision --autogenerate -m "Add season"`
6. **Tests**: Add unit and integration tests
7. **Docs**: Update README.md in each affected folder

## Git Workflow (MANDATORY)

**NEVER push directly to main.** All changes must go through pull requests.

### For Every Ticket

1. **Create a feature branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/<ticket-number>-<short-description>
   ```
   Example: `feature/1.3-core-configuration`

2. **Make commits on the feature branch:**
   ```bash
   git add <specific-files>
   git commit -m "feat: descriptive message

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
   ```

3. **Push the branch and create a PR:**
   ```bash
   git push -u origin feature/<branch-name>
   gh pr create --title "feat: <ticket> <description>" --body "..."
   ```

4. **Wait for CI to pass, then merge:**
   ```bash
   # Check CI status
   gh pr checks

   # Once CI passes, merge
   gh pr merge --squash --delete-branch
   ```

### Branch Protection

The `main` branch has protection rules:
- Requires pull request before merging
- Requires CI (test) to pass before merging
- Enforced for administrators (no bypass)

### Commit Message Format

```
<type>: <short description>

<optional body>

Closes #<issue-number>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## When Completing Any Ticket

Before marking a ticket as complete, verify:

- [ ] All new functions have docstrings with Args, Returns, Raises, Example
- [ ] All new classes have class-level docstrings
- [ ] Module docstring exists at top of new files
- [ ] README.md updated in affected folders
- [ ] API endpoints have full OpenAPI documentation
- [ ] Any new API endpoints documented in docs/api/
- [ ] Examples provided where applicable
- [ ] Type hints on all function signatures
- [ ] Changes are on a feature branch (not main)
- [ ] PR created with descriptive title and body

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Database | SQLite (upgradeable to PostgreSQL) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Testing | pytest |
| HTTP Client | httpx |
| Package Manager | uv |

## Development Commands

This project uses `uv` as the package manager. All commands should be run with `uv run`.

### Setup

```bash
# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
uv run python -m pytest

# Run specific test file
uv run python -m pytest tests/unit/core/test_database.py

# Run with verbose output
uv run python -m pytest -v

# Run with coverage
uv run python -m pytest --cov=src
```

### Linting

```bash
# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check . --fix

# Format code
uv run black .
```

### Common Issues

- If virtual environment is corrupted, delete `.venv` and recreate: `rm -rf .venv && uv venv && uv pip install -e ".[dev]"`
- Always use `uv run python -m pytest` not just `pytest` or `uv run pytest`

## Database Workflow (Multi-Branch Development)

When working on sync features across multiple branches, use the template database workflow to avoid conflicts.

### File Locations

| File | Purpose |
|------|---------|
| `data/template.db` | Shared template database (gitignored) |
| `basketball.db` | Working database for current branch (gitignored) |
| `DB_TEMPLATE_PATH` | Environment variable pointing to template |

### Commands

```bash
# Check database status
python scripts/db_manage.py status

# Copy template to working database (use when starting a new branch)
python scripts/db_manage.py copy-template

# Update template from working database (use after syncing new data)
python scripts/db_manage.py update-template
```

### Workflow

1. **Starting a new feature branch:**
   ```bash
   git checkout -b feature/my-sync-feature
   python scripts/db_manage.py copy-template
   ```

2. **After syncing new data others should have:**
   ```bash
   python scripts/db_manage.py update-template
   ```

3. **Switching branches (if different data needed):**
   ```bash
   python scripts/db_manage.py copy-template
   ```

See `docs/development/database-workflow.md` for full documentation.
