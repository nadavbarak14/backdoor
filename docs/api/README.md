# API Documentation

## Purpose

Comprehensive API reference for the Basketball Analytics Platform REST API.

## Contents

| File | Description |
|------|-------------|
| [README.md](README.md) | This file - API overview |
| [leagues.md](leagues.md) | Leagues API reference |
| [teams.md](teams.md) | Teams API reference |
| [players.md](players.md) | Players API reference |
| [games.md](games.md) | Games, box scores, and play-by-play reference |

## Quick Start

### Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.basketball-analytics.com/api/v1
```

### Running the Server

```bash
# Development with auto-reload
uv run uvicorn src.main:app --reload

# Production
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Versioning

The API is versioned via URL path:
- `/api/v1/...` - Current stable version

### Versioning Policy

- **Breaking changes** require a new API version (e.g., v2)
- **Non-breaking additions** can be added to the current version
- **Deprecation period**: Old versions remain available for minimum 6 months after deprecation notice

## Authentication

*Authentication will be added in a future release.*

## Endpoints Overview

### Leagues

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/leagues` | List all leagues |
| GET | `/api/v1/leagues/{id}` | Get league by ID |
| GET | `/api/v1/leagues/{id}/seasons` | List league seasons |

[Full Leagues API Reference](leagues.md)

### Teams

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/teams` | List/search teams |
| GET | `/api/v1/teams/{id}` | Get team by ID |
| GET | `/api/v1/teams/{id}/roster` | Get team roster |
| GET | `/api/v1/teams/{id}/games` | Get team game history |

[Full Teams API Reference](teams.md)

### Players

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/players` | Search players |
| GET | `/api/v1/players/{id}` | Get player with history |
| GET | `/api/v1/players/{id}/games` | Get player game log |

[Full Players API Reference](players.md)

### Games

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/games` | List games with filters |
| GET | `/api/v1/games/{id}` | Get game with box score |
| GET | `/api/v1/games/{id}/pbp` | Get play-by-play events |

[Full Games API Reference](games.md)

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Common Patterns

### Pagination

All list endpoints support pagination with `skip` and `limit` parameters:

```bash
GET /api/v1/players?skip=0&limit=20
```

Response includes total count:

```json
{
    "items": [...],
    "total": 500
}
```

### Filtering

Most list endpoints support filtering by various parameters:

```bash
# Filter players by position and nationality
GET /api/v1/players?position=PG&nationality=USA

# Search teams by name
GET /api/v1/teams?search=lakers

# Filter by related entities
GET /api/v1/players?team_id=abc-123&season_id=def-456
```

### Error Responses

All errors return a consistent format:

```json
{
    "detail": "Resource not found"
}
```

#### Common Error Codes

| Code | Description |
|------|-------------|
| 404 | Resource not found |
| 422 | Validation error (invalid input) |

#### Validation Error Format

```json
{
    "detail": [
        {
            "loc": ["query", "skip"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer"
        }
    ]
}
```

## Quick Examples

### List All Leagues

```bash
curl http://localhost:8000/api/v1/leagues
```

### Get a Specific Team

```bash
curl http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000
```

### Search Players by Name

```bash
curl "http://localhost:8000/api/v1/players?search=curry"
```

### Get Team Roster for Current Season

```bash
curl http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/roster
```

### Get Player with Team History

```bash
curl http://localhost:8000/api/v1/players/880e8400-e29b-41d4-a716-446655440000
```

### Get Game with Box Score

```bash
curl http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000
```

### Get Play-by-Play Events

```bash
curl "http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp?period=4"
```

### Get Player Game Log

```bash
curl http://localhost:8000/api/v1/players/880e8400-e29b-41d4-a716-446655440000/games
```

### Get Team Game History

```bash
curl http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/games
```

## Using with httpx (Python)

```python
import httpx

# Create client
client = httpx.Client(base_url="http://localhost:8000/api/v1")

# List leagues
response = client.get("/leagues")
leagues = response.json()

# Search players
response = client.get("/players", params={"search": "curry", "position": "PG"})
players = response.json()

# Get team roster
response = client.get(f"/teams/{team_id}/roster")
roster = response.json()
```

## Rate Limiting

*Rate limiting will be added in a future release.*

## Related Documentation

- [Source Code API Layer](../../src/api/README.md)
- [API v1 Implementation](../../src/api/v1/README.md)
- [Game Statistics Reference](../models/game-stats.md)
- [Play-by-Play Reference](../models/play-by-play.md)
- [Schemas](../../src/schemas/README.md)
- [Services](../../src/services/README.md)
