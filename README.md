# Basketball Analytics Platform

A Python-based platform for syncing and analyzing basketball statistics. Built with FastAPI, SQLAlchemy, and modern Python tooling.

## Features

- RESTful API for basketball statistics
- Data synchronization from external sources
- Player, team, and game statistics tracking
- Flexible query and aggregation capabilities

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Database | SQLite (upgradeable to PostgreSQL) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Testing | pytest |
| HTTP Client | httpx |

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/nadavbarak14/backdoor.git
cd backdoor
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

**Development (includes testing and linting tools):**

```bash
uv pip install -e ".[dev]"
```

**Production only:**

```bash
uv pip install -e .
```

**With internal viewer:**

```bash
uv pip install -e ".[viewer]"
```

**All dependencies:**

```bash
uv pip install -e ".[dev,viewer]"
```

## Development

### Code Quality Tools

This project uses `ruff` for linting and `black` for code formatting.

**Run linter:**

```bash
ruff check .
```

**Run formatter check:**

```bash
black --check .
```

**Auto-fix linting issues:**

```bash
ruff check . --fix
```

**Auto-format code:**

```bash
black .
```

### Database Migrations

This project uses Alembic for database migrations.

```bash
# Apply all migrations
uv run alembic upgrade head

# Create a new migration from model changes
uv run alembic revision --autogenerate -m "Description of changes"

# Rollback one migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

See `alembic/README.md` for detailed migration documentation.

### Running Tests

Run all tests:

```bash
uv run python -m pytest
```

Run tests with coverage:

```bash
pytest --cov=src --cov-report=html
```

Run specific test file:

```bash
pytest tests/test_example.py
```

Run tests matching a pattern:

```bash
pytest -k "test_player"
```

## Running the Application

### Backend API

Start the FastAPI development server:

```bash
uv run uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Internal Data Viewer

The project includes a Streamlit-based internal viewer for browsing synced data.

**Install viewer dependencies:**

```bash
uv pip install -e ".[viewer]"
```

**Start the viewer:**

```bash
uv run streamlit run viewer/app.py
```

The viewer will be available at `http://localhost:8501`.

Features:
- Browse leagues, teams, players, and games
- View entity relationships and statistics
- Monitor sync activity

See `viewer/README.md` for detailed documentation.

## Project Structure

```
basketball-analytics/
├── CLAUDE.md                 # Development guidelines
├── README.md                 # This file
├── pyproject.toml            # Project configuration
├── alembic/                  # Database migrations
├── docs/                     # Documentation
│   ├── api/                  # API documentation
│   ├── models/               # Data model documentation
│   └── sync/                 # Sync layer documentation
├── src/                      # Source code
│   ├── api/                  # API routes
│   ├── core/                 # Core configuration
│   ├── models/               # Database models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   └── sync/                 # Data synchronization
├── viewer/                   # Internal data viewer (Streamlit)
│   ├── app.py                # Home dashboard
│   ├── db.py                 # Database session management
│   ├── pages/                # Viewer pages
│   └── components/           # Reusable UI components
└── tests/                    # Test files
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes following the guidelines in `CLAUDE.md`
3. Ensure all tests pass and linting checks succeed
4. Create a pull request

### Branch Protection

The `main` branch is protected and requires:
- Pull request reviews before merging
- CI checks to pass before merging

## License

MIT License - see LICENSE file for details.
