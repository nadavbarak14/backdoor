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

### Get Player Game Log

`GET /api/v1/players/{player_id}/games`

Retrieve a player's game-by-game statistics with opponent information and win/loss results.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `player_id` | UUID | Yes | The player's unique identifier |

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
            "id": "bb0e8400-e29b-41d4-a716-446655440000",
            "game_id": "990e8400-e29b-41d4-a716-446655440000",
            "player_id": "880e8400-e29b-41d4-a716-446655440000",
            "player_name": "LeBron James",
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "minutes_played": 2100,
            "minutes_display": "35:00",
            "is_starter": true,
            "points": 30,
            "field_goals_made": 11,
            "field_goals_attempted": 22,
            "field_goal_pct": 50.0,
            "two_pointers_made": 8,
            "two_pointers_attempted": 14,
            "two_point_pct": 57.1,
            "three_pointers_made": 3,
            "three_pointers_attempted": 8,
            "three_point_pct": 37.5,
            "free_throws_made": 5,
            "free_throws_attempted": 6,
            "free_throw_pct": 83.3,
            "offensive_rebounds": 2,
            "defensive_rebounds": 8,
            "total_rebounds": 10,
            "assists": 8,
            "turnovers": 3,
            "steals": 2,
            "blocks": 1,
            "personal_fouls": 2,
            "plus_minus": 12,
            "efficiency": 38,
            "extra_stats": {},
            "game_date": "2024-01-15T19:30:00",
            "opponent_team_id": "770e8400-e29b-41d4-a716-446655440001",
            "opponent_team_name": "Boston Celtics",
            "is_home": true,
            "team_score": 112,
            "opponent_score": 108,
            "result": "W"
        },
        {
            "id": "bb0e8400-e29b-41d4-a716-446655440001",
            "game_id": "990e8400-e29b-41d4-a716-446655440001",
            "player_id": "880e8400-e29b-41d4-a716-446655440000",
            "player_name": "LeBron James",
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "minutes_played": 1980,
            "minutes_display": "33:00",
            "is_starter": true,
            "points": 25,
            "field_goals_made": 9,
            "field_goals_attempted": 20,
            "field_goal_pct": 45.0,
            "two_pointers_made": 6,
            "two_pointers_attempted": 12,
            "two_point_pct": 50.0,
            "three_pointers_made": 3,
            "three_pointers_attempted": 8,
            "three_point_pct": 37.5,
            "free_throws_made": 4,
            "free_throws_attempted": 5,
            "free_throw_pct": 80.0,
            "offensive_rebounds": 1,
            "defensive_rebounds": 6,
            "total_rebounds": 7,
            "assists": 6,
            "turnovers": 4,
            "steals": 1,
            "blocks": 0,
            "personal_fouls": 3,
            "plus_minus": -10,
            "efficiency": 22,
            "extra_stats": {},
            "game_date": "2024-01-20T19:30:00",
            "opponent_team_id": "770e8400-e29b-41d4-a716-446655440001",
            "opponent_team_name": "Boston Celtics",
            "is_home": false,
            "team_score": 105,
            "opponent_score": 115,
            "result": "L"
        }
    ],
    "total": 45
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "Player with id 880e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Examples:**

```bash
# Get player game log
curl http://localhost:8000/api/v1/players/880e8400-e29b-41d4-a716-446655440000/games

# Filter by season
curl "http://localhost:8000/api/v1/players/880e8400-e29b-41d4-a716-446655440000/games?season_id=660e8400-e29b-41d4-a716-446655440000"

# With pagination
curl "http://localhost:8000/api/v1/players/880e8400-e29b-41d4-a716-446655440000/games?skip=0&limit=10"
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

### PlayerGameStatsWithGameResponse

Extends PlayerGameStatsResponse with game context:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Stats entry identifier |
| `game_id` | UUID | Game identifier |
| `player_id` | UUID | Player identifier |
| `player_name` | string | Player full name |
| `team_id` | UUID | Team identifier |
| `minutes_played` | integer | Playing time in seconds |
| `minutes_display` | string | Formatted time "MM:SS" |
| `is_starter` | boolean | In starting lineup |
| `points` | integer | Points scored |
| `field_goals_made` | integer | FG made |
| `field_goals_attempted` | integer | FG attempted |
| `field_goal_pct` | float | FG percentage (computed) |
| `two_pointers_made` | integer | 2PT made |
| `two_pointers_attempted` | integer | 2PT attempted |
| `two_point_pct` | float | 2PT percentage (computed) |
| `three_pointers_made` | integer | 3PT made |
| `three_pointers_attempted` | integer | 3PT attempted |
| `three_point_pct` | float | 3PT percentage (computed) |
| `free_throws_made` | integer | FT made |
| `free_throws_attempted` | integer | FT attempted |
| `free_throw_pct` | float | FT percentage (computed) |
| `offensive_rebounds` | integer | Offensive rebounds |
| `defensive_rebounds` | integer | Defensive rebounds |
| `total_rebounds` | integer | Total rebounds |
| `assists` | integer | Assists |
| `turnovers` | integer | Turnovers |
| `steals` | integer | Steals |
| `blocks` | integer | Blocks |
| `personal_fouls` | integer | Personal fouls |
| `plus_minus` | integer | Plus/minus |
| `efficiency` | integer | Efficiency rating |
| `extra_stats` | object | League-specific stats |
| `game_date` | datetime | Date and time of game |
| `opponent_team_id` | UUID | Opponent team identifier |
| `opponent_team_name` | string | Opponent team name |
| `is_home` | boolean | Was this a home game |
| `team_score` | integer | Player's team final score |
| `opponent_score` | integer | Opponent final score |
| `result` | string | "W" for win, "L" for loss (computed) |

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
- [Games API](games.md) - Game details and box scores
