# Players API

## Overview

Endpoints for searching and retrieving basketball player information. Players can be filtered by team, season, position, nationality, or searched by name. Individual player endpoints include complete team history.

## Endpoints

### List Players

`GET /api/v1/players`

Search and retrieve a paginated list of players with optional filters.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `team_id` | UUID | No | - | Filter by team |
| `season_id` | UUID | No | - | Filter by season participation |
| `position` | string | No | - | Filter by position (PG, SG, SF, PF, C) |
| `nationality` | string | No | - | Filter by nationality (exact match) |
| `search` | string | No | - | Search by player name (case-insensitive) |
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Response:** `200 OK`

```json
{
    "items": [
        {
            "id": "880e8400-e29b-41d4-a716-446655440000",
            "first_name": "LeBron",
            "last_name": "James",
            "full_name": "LeBron James",
            "birth_date": "1984-12-30",
            "nationality": "USA",
            "height_cm": 206,
            "position": "SF",
            "external_ids": {
                "nba": "2544"
            },
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "880e8400-e29b-41d4-a716-446655440001",
            "first_name": "Stephen",
            "last_name": "Curry",
            "full_name": "Stephen Curry",
            "birth_date": "1988-03-14",
            "nationality": "USA",
            "height_cm": 188,
            "position": "PG",
            "external_ids": {
                "nba": "201939"
            },
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 500
}
```

**Examples:**

```bash
# List all players
curl http://localhost:8000/api/v1/players

# Search by name
curl "http://localhost:8000/api/v1/players?search=curry"

# Filter by position
curl "http://localhost:8000/api/v1/players?position=PG"

# Filter by nationality
curl "http://localhost:8000/api/v1/players?nationality=Slovenia"

# Filter by team
curl "http://localhost:8000/api/v1/players?team_id=770e8400-e29b-41d4-a716-446655440000"

# Combined filters with pagination
curl "http://localhost:8000/api/v1/players?position=PG&nationality=USA&skip=0&limit=20"

# Filter by season (players active in that season)
curl "http://localhost:8000/api/v1/players?season_id=660e8400-e29b-41d4-a716-446655440000"
```

---

### Get Player

`GET /api/v1/players/{player_id}`

Retrieve a specific player by ID, including their complete team history.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player_id` | UUID | Yes | The player's unique identifier |

**Response:** `200 OK`

```json
{
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "first_name": "LeBron",
    "last_name": "James",
    "full_name": "LeBron James",
    "birth_date": "1984-12-30",
    "nationality": "USA",
    "height_cm": 206,
    "position": "SF",
    "external_ids": {
        "nba": "2544",
        "espn": "1966"
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "team_history": [
        {
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "team_name": "Los Angeles Lakers",
            "season_id": "660e8400-e29b-41d4-a716-446655440000",
            "season_name": "2023-24",
            "jersey_number": 23,
            "position": "SF"
        },
        {
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "team_name": "Los Angeles Lakers",
            "season_id": "660e8400-e29b-41d4-a716-446655440001",
            "season_name": "2022-23",
            "jersey_number": 6,
            "position": "SF"
        },
        {
            "team_id": "770e8400-e29b-41d4-a716-446655440002",
            "team_name": "Cleveland Cavaliers",
            "season_id": "660e8400-e29b-41d4-a716-446655440010",
            "season_name": "2017-18",
            "jersey_number": 23,
            "position": "SF"
        }
    ]
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "Player with id 880e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**

```bash
curl http://localhost:8000/api/v1/players/880e8400-e29b-41d4-a716-446655440000
```

---

## Response Schemas

### PlayerResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `first_name` | string | Player's first name |
| `last_name` | string | Player's last name |
| `full_name` | string | Computed full name |
| `birth_date` | date | Date of birth (may be null) |
| `nationality` | string | Player's nationality (may be null) |
| `height_cm` | integer | Height in centimeters (may be null) |
| `position` | string | Primary position (may be null) |
| `external_ids` | object | Map of external provider IDs |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### PlayerWithHistoryResponse

Extends PlayerResponse with:

| Field | Type | Description |
|-------|------|-------------|
| `team_history` | array | List of team history entries |

### PlayerTeamHistoryResponse

| Field | Type | Description |
|-------|------|-------------|
| `team_id` | UUID | Team identifier |
| `team_name` | string | Team name |
| `season_id` | UUID | Season identifier |
| `season_name` | string | Season name (e.g., "2023-24") |
| `jersey_number` | integer | Jersey number (may be null) |
| `position` | string | Position played on this team (may be null) |

---

## Filter Behavior

### Search Filter

The `search` parameter performs a case-insensitive partial match on:
- Player `first_name`
- Player `last_name`

```bash
# Matches "Stephen Curry" and "Seth Curry"
curl "http://localhost:8000/api/v1/players?search=curry"

# Matches "LeBron James"
curl "http://localhost:8000/api/v1/players?search=lebron"

# Partial match on first name
curl "http://localhost:8000/api/v1/players?search=steph"
```

### Position Filter

Valid positions:
- `PG` - Point Guard
- `SG` - Shooting Guard
- `SF` - Small Forward
- `PF` - Power Forward
- `C` - Center

```bash
# All point guards
curl "http://localhost:8000/api/v1/players?position=PG"
```

### Team and Season Filters

When filtering by `team_id` or `season_id`, the filter matches players who have a PlayerTeamHistory entry for that team/season.

```bash
# Players who played for a specific team (any season)
curl "http://localhost:8000/api/v1/players?team_id=770e8400-e29b-41d4-a716-446655440000"

# Players active in a specific season
curl "http://localhost:8000/api/v1/players?season_id=660e8400-e29b-41d4-a716-446655440000"

# Players on a specific team in a specific season
curl "http://localhost:8000/api/v1/players?team_id=770e8400-e29b-41d4-a716-446655440000&season_id=660e8400-e29b-41d4-a716-446655440000"
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 404 | Player not found |
| 422 | Validation error (invalid UUID, invalid query parameters) |

---

## Related Endpoints

- [Leagues API](leagues.md) - League management
- [Teams API](teams.md) - Team management
