# Leagues API

## Overview

Endpoints for managing basketball leagues and their seasons. Leagues are the top-level organizational unit containing seasons, which in turn contain team and player data.

## Endpoints

### List Leagues

`GET /api/v1/leagues`

Retrieve a paginated list of all leagues with their season counts.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Response:** `200 OK`

```json
{
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "National Basketball Association",
            "code": "NBA",
            "country": "USA",
            "season_count": 5,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "EuroLeague",
            "code": "EL",
            "country": "Europe",
            "season_count": 3,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 2
}
```

**Example:**

```bash
# List all leagues
curl http://localhost:8000/api/v1/leagues

# With pagination
curl "http://localhost:8000/api/v1/leagues?skip=0&limit=10"
```

---

### Get League

`GET /api/v1/leagues/{league_id}`

Retrieve a specific league by its ID.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `league_id` | UUID | Yes | The league's unique identifier |

**Response:** `200 OK`

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "National Basketball Association",
    "code": "NBA",
    "country": "USA",
    "season_count": 5,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "League with id 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**

```bash
curl http://localhost:8000/api/v1/leagues/550e8400-e29b-41d4-a716-446655440000
```

---

### List League Seasons

`GET /api/v1/leagues/{league_id}/seasons`

Retrieve all seasons for a specific league.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `league_id` | UUID | Yes | The league's unique identifier |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Response:** `200 OK`

```json
[
    {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "league_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "2023-24",
        "start_date": "2023-10-24",
        "end_date": "2024-06-17",
        "is_current": true,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    },
    {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "league_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "2022-23",
        "start_date": "2022-10-18",
        "end_date": "2023-06-12",
        "is_current": false,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
]
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "League with id 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**

```bash
# List all seasons for a league
curl http://localhost:8000/api/v1/leagues/550e8400-e29b-41d4-a716-446655440000/seasons

# With pagination
curl "http://localhost:8000/api/v1/leagues/550e8400-e29b-41d4-a716-446655440000/seasons?skip=0&limit=5"
```

---

## Response Schemas

### LeagueResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | string | Full league name |
| `code` | string | Short code (e.g., "NBA") |
| `country` | string | Country or region |
| `season_count` | integer | Number of seasons in the league |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### SeasonResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `league_id` | UUID | Parent league ID |
| `name` | string | Season name (e.g., "2023-24") |
| `start_date` | date | Season start date |
| `end_date` | date | Season end date |
| `is_current` | boolean | Whether this is the current active season |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

---

## Error Codes

| Code | Description |
|------|-------------|
| 404 | League not found |
| 422 | Validation error (invalid UUID, invalid query parameters) |

---

## Related Endpoints

- [Teams API](teams.md) - Team management
- [Players API](players.md) - Player management
