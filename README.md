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

For development (includes testing and linting tools):

```bash
pip install -e ".[dev]"
```

For production only:

```bash
pip install -e .
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

### Running Tests

Run all tests:

```bash
pytest
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

### Running the Application

Start the development server:

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
basketball-analytics/
├── CLAUDE.md                 # Development guidelines
├── README.md                 # This file
├── pyproject.toml            # Project configuration
├── docs/                     # Documentation
│   ├── api/                  # API documentation
│   └── models/               # Data model documentation
├── src/                      # Source code
│   ├── api/                  # API routes
│   ├── core/                 # Core configuration
│   ├── models/               # Database models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   └── sync/                 # Data synchronization
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
