# Teams API

## Overview

Endpoints for managing basketball teams and their rosters. Teams can be filtered by league, season, country, or searched by name.

## Endpoints

### List Teams

`GET /api/v1/teams`

Retrieve a paginated list of teams with optional filters.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `league_id` | UUID | No | - | Filter by league |
| `season_id` | UUID | No | - | Filter by season participation |
| `country` | string | No | - | Filter by country (exact match) |
| `search` | string | No | - | Search by team name (case-insensitive) |
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 100 | Maximum records to return (1-1000) |

**Response:** `200 OK`

```json
{
    "items": [
        {
            "id": "770e8400-e29b-41d4-a716-446655440000",
            "name": "Los Angeles Lakers",
            "short_name": "LAL",
            "city": "Los Angeles",
            "country": "USA",
            "external_ids": {
                "nba": "1610612747"
            },
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        },
        {
            "id": "770e8400-e29b-41d4-a716-446655440001",
            "name": "Boston Celtics",
            "short_name": "BOS",
            "city": "Boston",
            "country": "USA",
            "external_ids": {
                "nba": "1610612738"
            },
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 30
}
```

**Examples:**

```bash
# List all teams
curl http://localhost:8000/api/v1/teams

# Filter by country
curl "http://localhost:8000/api/v1/teams?country=USA"

# Search by name
curl "http://localhost:8000/api/v1/teams?search=lakers"

# Combined filters with pagination
curl "http://localhost:8000/api/v1/teams?country=USA&search=los&skip=0&limit=10"

# Filter by season
curl "http://localhost:8000/api/v1/teams?season_id=660e8400-e29b-41d4-a716-446655440000"
```

---

### Get Team

`GET /api/v1/teams/{team_id}`

Retrieve a specific team by its ID.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | UUID | Yes | The team's unique identifier |

**Response:** `200 OK`

```json
{
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "name": "Los Angeles Lakers",
    "short_name": "LAL",
    "city": "Los Angeles",
    "country": "USA",
    "external_ids": {
        "nba": "1610612747",
        "espn": "13"
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "Team with id 770e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**

```bash
curl http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000
```

---

### Get Team Roster

`GET /api/v1/teams/{team_id}/roster`

Retrieve the roster for a team in a specific season. If no season is specified, returns the roster for the current season.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | UUID | Yes | The team's unique identifier |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `season_id` | UUID | No | Current season | Season to get roster for |

**Response:** `200 OK`

```json
{
    "team": {
        "id": "770e8400-e29b-41d4-a716-446655440000",
        "name": "Los Angeles Lakers",
        "short_name": "LAL",
        "city": "Los Angeles",
        "country": "USA",
        "external_ids": {
            "nba": "1610612747"
        },
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    },
    "season_id": "660e8400-e29b-41d4-a716-446655440000",
    "season_name": "2023-24",
    "players": [
        {
            "id": "880e8400-e29b-41d4-a716-446655440000",
            "first_name": "LeBron",
            "last_name": "James",
            "full_name": "LeBron James",
            "jersey_number": 23,
            "position": "SF"
        },
        {
            "id": "880e8400-e29b-41d4-a716-446655440001",
            "first_name": "Anthony",
            "last_name": "Davis",
            "full_name": "Anthony Davis",
            "jersey_number": 3,
            "position": "PF"
        }
    ]
}
```

**Error Responses:**

`404 Not Found` - Team not found:
```json
{
    "detail": "Team with id 770e8400-e29b-41d4-a716-446655440000 not found"
}
```

`404 Not Found` - No current season (when season_id not provided):
```json
{
    "detail": "No current season found. Please specify a season_id."
}
```

`404 Not Found` - Season not found:
```json
{
    "detail": "Season with id 660e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Examples:**

```bash
# Get roster for current season
curl http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/roster

# Get roster for specific season
curl "http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/roster?season_id=660e8400-e29b-41d4-a716-446655440000"
```

---

### Get Team Game History

`GET /api/v1/teams/{team_id}/games`

Retrieve a team's game history with win/loss results and opponent information.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | UUID | Yes | The team's unique identifier |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `season_id` | UUID | No | - | Filter by season |
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 50 | Maximum records to return (1-500) |

**Response:** `200 OK`

```json
{
    "items": [
        {
            "game_id": "990e8400-e29b-41d4-a716-446655440002",
            "game_date": "2024-01-25T19:30:00",
            "opponent_team_id": "770e8400-e29b-41d4-a716-446655440003",
            "opponent_team_name": "Golden State Warriors",
            "is_home": true,
            "team_score": 120,
            "opponent_score": 118,
            "venue": "Crypto.com Arena",
            "result": "W"
        },
        {
            "game_id": "990e8400-e29b-41d4-a716-446655440001",
            "game_date": "2024-01-20T19:30:00",
            "opponent_team_id": "770e8400-e29b-41d4-a716-446655440001",
            "opponent_team_name": "Boston Celtics",
            "is_home": false,
            "team_score": 105,
            "opponent_score": 115,
            "venue": "TD Garden",
            "result": "L"
        },
        {
            "game_id": "990e8400-e29b-41d4-a716-446655440000",
            "game_date": "2024-01-15T19:30:00",
            "opponent_team_id": "770e8400-e29b-41d4-a716-446655440001",
            "opponent_team_name": "Boston Celtics",
            "is_home": true,
            "team_score": 112,
            "opponent_score": 108,
            "venue": "Crypto.com Arena",
            "result": "W"
        }
    ],
    "total": 45
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "Team with id 770e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Examples:**

```bash
# Get team game history
curl http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/games

# Filter by season
curl "http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/games?season_id=660e8400-e29b-41d4-a716-446655440000"

# With pagination
curl "http://localhost:8000/api/v1/teams/770e8400-e29b-41d4-a716-446655440000/games?skip=0&limit=10"
```

---

## Response Schemas

### TeamResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | string | Full team name |
| `short_name` | string | Abbreviated name (e.g., "LAL") |
| `city` | string | Team's city |
| `country` | string | Team's country |
| `external_ids` | object | Map of external provider IDs |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### TeamRosterResponse

| Field | Type | Description |
|-------|------|-------------|
| `team` | TeamResponse | Team details |
| `season_id` | UUID | Season identifier |
| `season_name` | string | Season name (e.g., "2023-24") |
| `players` | array | List of players on the roster |

### TeamRosterPlayerResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Player's unique identifier |
| `first_name` | string | Player's first name |
| `last_name` | string | Player's last name |
| `full_name` | string | Player's full name |
| `jersey_number` | integer | Jersey number (may be null) |
| `position` | string | Position on this team (may be null) |

### TeamGameSummaryResponse

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | UUID | Game identifier |
| `game_date` | datetime | Date and time of game |
| `opponent_team_id` | UUID | Opponent team identifier |
| `opponent_team_name` | string | Opponent team name |
| `is_home` | boolean | Was this a home game |
| `team_score` | integer | Team's final score |
| `opponent_score` | integer | Opponent's final score |
| `venue` | string | Arena/venue name |
| `result` | string | "W" for win, "L" for loss (computed) |

---

## Filter Behavior

### Search Filter

The `search` parameter performs a case-insensitive partial match on:
- Team `name`
- Team `short_name`

```bash
# Matches "Los Angeles Lakers" and "Los Angeles Clippers"
curl "http://localhost:8000/api/v1/teams?search=los%20angeles"

# Matches teams with "LAL" in short_name
curl "http://localhost:8000/api/v1/teams?search=lal"
```

### Season Filter

When filtering by `season_id`, only teams that participated in that season are returned (teams with a TeamSeason entry for that season).

---

## Error Codes

| Code | Description |
|------|-------------|
| 404 | Team not found |
| 404 | Season not found |
| 404 | No current season found |
| 422 | Validation error (invalid UUID, invalid query parameters) |

---

## Related Endpoints

- [Leagues API](leagues.md) - League management
- [Players API](players.md) - Player management
- [Games API](games.md) - Game details and box scores
