# API Documentation

## Purpose

Comprehensive API reference for the Basketball Analytics Platform REST API.

## Contents

| File | Description |
|------|-------------|
| `README.md` | This file - API overview |
| `endpoints.md` | Full endpoint reference (future) |
| `schemas.md` | Request/response schemas (future) |
| `errors.md` | Error codes and handling (future) |
| `authentication.md` | Auth guide (future) |

## Quick Start

### Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.basketball-analytics.com/api/v1
```

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Versioning

The API is versioned via URL path:
- `/api/v1/...` - Current stable version

## Authentication

*Authentication will be added in a future release.*

## Common Patterns

### Pagination

```http
GET /api/v1/players?skip=0&limit=20
```

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 500,
  "page": 1,
  "page_size": 20,
  "pages": 25
}
```

### Filtering

```http
GET /api/v1/players?team_id=abc-123&position=PG
```

### Error Responses

All errors return consistent format:
```json
{
  "detail": "Player not found"
}
```

## Endpoints Overview

| Resource | Endpoint | Description |
|----------|----------|-------------|
| Players | `/api/v1/players` | Player CRUD |
| Teams | `/api/v1/teams` | Team CRUD |
| Games | `/api/v1/games` | Game data |
| Stats | `/api/v1/stats` | Statistics |

## Related Documentation

- [Source Code API Layer](../../src/api/README.md)
- [Schemas](../../src/schemas/README.md)
