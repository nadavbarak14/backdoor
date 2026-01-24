# Games API

## Overview

Endpoints for retrieving game information, box scores, and play-by-play data. Games can be filtered by season, team, date range, and status.

## Endpoints

### List Games

`GET /api/v1/games`

Retrieve a paginated list of games with optional filters.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `season_id` | UUID | No | - | Filter by season |
| `team_id` | UUID | No | - | Filter by team (home or away) |
| `start_date` | date | No | - | Filter games on or after this date (YYYY-MM-DD) |
| `end_date` | date | No | - | Filter games on or before this date (YYYY-MM-DD) |
| `status` | string | No | - | Filter by game status (SCHEDULED, LIVE, FINAL, POSTPONED, CANCELLED) |
| `skip` | integer | No | 0 | Number of records to skip |
| `limit` | integer | No | 50 | Maximum records to return (1-500) |

**Response:** `200 OK`

```json
{
    "items": [
        {
            "id": "990e8400-e29b-41d4-a716-446655440000",
            "season_id": "660e8400-e29b-41d4-a716-446655440000",
            "home_team_id": "770e8400-e29b-41d4-a716-446655440000",
            "home_team_name": "Los Angeles Lakers",
            "away_team_id": "770e8400-e29b-41d4-a716-446655440001",
            "away_team_name": "Boston Celtics",
            "game_date": "2024-01-15T19:30:00",
            "status": "FINAL",
            "home_score": 112,
            "away_score": 108,
            "venue": "Crypto.com Arena",
            "attendance": 18997,
            "external_ids": {
                "nba": "0022300567"
            },
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T22:30:00Z"
        }
    ],
    "total": 82
}
```

**Examples:**

```bash
# List all games
curl http://localhost:8000/api/v1/games

# Filter by status
curl "http://localhost:8000/api/v1/games?status=FINAL"

# Filter by team
curl "http://localhost:8000/api/v1/games?team_id=770e8400-e29b-41d4-a716-446655440000"

# Filter by date range
curl "http://localhost:8000/api/v1/games?start_date=2024-01-01&end_date=2024-01-31"

# Filter by season
curl "http://localhost:8000/api/v1/games?season_id=660e8400-e29b-41d4-a716-446655440000"

# Combined filters with pagination
curl "http://localhost:8000/api/v1/games?team_id=770e8400-e29b-41d4-a716-446655440000&status=FINAL&skip=0&limit=10"
```

---

### Get Game with Box Score

`GET /api/v1/games/{game_id}`

Retrieve a specific game by ID, including complete box score data for both teams and all players.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `game_id` | UUID | Yes | The game's unique identifier |

**Response:** `200 OK`

```json
{
    "id": "990e8400-e29b-41d4-a716-446655440000",
    "season_id": "660e8400-e29b-41d4-a716-446655440000",
    "home_team_id": "770e8400-e29b-41d4-a716-446655440000",
    "home_team_name": "Los Angeles Lakers",
    "away_team_id": "770e8400-e29b-41d4-a716-446655440001",
    "away_team_name": "Boston Celtics",
    "game_date": "2024-01-15T19:30:00",
    "status": "FINAL",
    "home_score": 112,
    "away_score": 108,
    "venue": "Crypto.com Arena",
    "attendance": 18997,
    "external_ids": {
        "nba": "0022300567"
    },
    "home_team_stats": {
        "team_id": "770e8400-e29b-41d4-a716-446655440000",
        "team_name": "Los Angeles Lakers",
        "is_home": true,
        "points": 112,
        "field_goals_made": 42,
        "field_goals_attempted": 88,
        "field_goal_pct": 47.7,
        "three_pointers_made": 12,
        "three_pointers_attempted": 32,
        "three_point_pct": 37.5,
        "free_throws_made": 16,
        "free_throws_attempted": 20,
        "free_throw_pct": 80.0,
        "offensive_rebounds": 10,
        "defensive_rebounds": 32,
        "total_rebounds": 42,
        "assists": 25,
        "turnovers": 12,
        "steals": 8,
        "blocks": 5,
        "personal_fouls": 18,
        "fast_break_points": 15,
        "points_in_paint": 48,
        "second_chance_points": 12,
        "bench_points": 28
    },
    "away_team_stats": {
        "team_id": "770e8400-e29b-41d4-a716-446655440001",
        "team_name": "Boston Celtics",
        "is_home": false,
        "points": 108,
        "field_goals_made": 40,
        "field_goals_attempted": 90,
        "field_goal_pct": 44.4,
        "three_pointers_made": 12,
        "three_pointers_attempted": 36,
        "three_point_pct": 33.3,
        "free_throws_made": 16,
        "free_throws_attempted": 18,
        "free_throw_pct": 88.9,
        "offensive_rebounds": 8,
        "defensive_rebounds": 28,
        "total_rebounds": 36,
        "assists": 22,
        "turnovers": 14,
        "steals": 6,
        "blocks": 3,
        "personal_fouls": 20,
        "fast_break_points": 12,
        "points_in_paint": 44,
        "second_chance_points": 10,
        "bench_points": 24
    },
    "home_players": [
        {
            "player_id": "880e8400-e29b-41d4-a716-446655440000",
            "player_name": "LeBron James",
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "is_starter": true,
            "minutes_played": 2100,
            "minutes_display": "35:00",
            "points": 30,
            "field_goals_made": 11,
            "field_goals_attempted": 22,
            "field_goal_pct": 50.0,
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
            "plus_minus": 12
        }
    ],
    "away_players": [
        {
            "player_id": "880e8400-e29b-41d4-a716-446655440002",
            "player_name": "Jayson Tatum",
            "team_id": "770e8400-e29b-41d4-a716-446655440001",
            "is_starter": true,
            "minutes_played": 2040,
            "minutes_display": "34:00",
            "points": 28,
            "field_goals_made": 10,
            "field_goals_attempted": 20,
            "field_goal_pct": 50.0,
            "three_pointers_made": 4,
            "three_pointers_attempted": 10,
            "three_point_pct": 40.0,
            "free_throws_made": 4,
            "free_throws_attempted": 5,
            "free_throw_pct": 80.0,
            "offensive_rebounds": 1,
            "defensive_rebounds": 6,
            "total_rebounds": 7,
            "assists": 5,
            "turnovers": 4,
            "steals": 2,
            "blocks": 0,
            "personal_fouls": 2,
            "plus_minus": -8
        }
    ],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T22:30:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "Game with id 990e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Example:**

```bash
curl http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000
```

---

### Get Play-by-Play

`GET /api/v1/games/{game_id}/pbp`

Retrieve play-by-play events for a game with optional filters.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `game_id` | UUID | Yes | The game's unique identifier |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `period` | integer | No | - | Filter by period number (1-4 for regulation, 5+ for OT) |
| `event_type` | string | No | - | Filter by event type (SHOT, REBOUND, TURNOVER, etc.) |
| `player_id` | UUID | No | - | Filter by player |
| `team_id` | UUID | No | - | Filter by team |

**Response:** `200 OK`

```json
{
    "game_id": "990e8400-e29b-41d4-a716-446655440000",
    "events": [
        {
            "id": "aa0e8400-e29b-41d4-a716-446655440001",
            "game_id": "990e8400-e29b-41d4-a716-446655440000",
            "event_number": 1,
            "period": 1,
            "clock": "12:00",
            "event_type": "JUMP_BALL",
            "event_subtype": null,
            "player_id": null,
            "player_name": null,
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "team_name": "Los Angeles Lakers",
            "success": null,
            "coord_x": null,
            "coord_y": null,
            "attributes": {},
            "description": "Jump ball won by Lakers",
            "related_event_ids": []
        },
        {
            "id": "aa0e8400-e29b-41d4-a716-446655440002",
            "game_id": "990e8400-e29b-41d4-a716-446655440000",
            "event_number": 2,
            "period": 1,
            "clock": "11:45",
            "event_type": "SHOT",
            "event_subtype": "LAYUP",
            "player_id": "880e8400-e29b-41d4-a716-446655440000",
            "player_name": "LeBron James",
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "team_name": "Los Angeles Lakers",
            "success": true,
            "coord_x": 0.5,
            "coord_y": 0.5,
            "attributes": {
                "shot_distance": 2.0,
                "fast_break": true
            },
            "description": "LeBron James makes layup (2 PTS)",
            "related_event_ids": ["aa0e8400-e29b-41d4-a716-446655440003"]
        },
        {
            "id": "aa0e8400-e29b-41d4-a716-446655440003",
            "game_id": "990e8400-e29b-41d4-a716-446655440000",
            "event_number": 3,
            "period": 1,
            "clock": "11:45",
            "event_type": "ASSIST",
            "event_subtype": null,
            "player_id": "880e8400-e29b-41d4-a716-446655440001",
            "player_name": "Anthony Davis",
            "team_id": "770e8400-e29b-41d4-a716-446655440000",
            "team_name": "Los Angeles Lakers",
            "success": null,
            "coord_x": null,
            "coord_y": null,
            "attributes": {},
            "description": "Anthony Davis assist",
            "related_event_ids": ["aa0e8400-e29b-41d4-a716-446655440002"]
        }
    ],
    "total_events": 425
}
```

**Error Response:** `404 Not Found`

```json
{
    "detail": "Game with id 990e8400-e29b-41d4-a716-446655440000 not found"
}
```

**Examples:**

```bash
# Get all play-by-play events
curl http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp

# Filter by period (4th quarter)
curl "http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp?period=4"

# Filter by event type (shots only)
curl "http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp?event_type=SHOT"

# Filter by player
curl "http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp?player_id=880e8400-e29b-41d4-a716-446655440000"

# Filter by team
curl "http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp?team_id=770e8400-e29b-41d4-a716-446655440000"

# Combined filters (4th quarter shots by a player)
curl "http://localhost:8000/api/v1/games/990e8400-e29b-41d4-a716-446655440000/pbp?period=4&event_type=SHOT&player_id=880e8400-e29b-41d4-a716-446655440000"
```

---

## Response Schemas

### GameResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `season_id` | UUID | Season this game belongs to |
| `home_team_id` | UUID | Home team identifier |
| `home_team_name` | string | Home team name |
| `away_team_id` | UUID | Away team identifier |
| `away_team_name` | string | Away team name |
| `game_date` | datetime | Game date and time |
| `status` | string | Game status (SCHEDULED, LIVE, FINAL, POSTPONED, CANCELLED) |
| `home_score` | integer | Home team score (null if not started) |
| `away_score` | integer | Away team score (null if not started) |
| `venue` | string | Arena name (may be null) |
| `attendance` | integer | Number of spectators (may be null) |
| `external_ids` | object | Map of external provider IDs |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### TeamBoxScoreResponse

| Field | Type | Description |
|-------|------|-------------|
| `team_id` | UUID | Team identifier |
| `team_name` | string | Team name |
| `is_home` | boolean | Is this the home team |
| `points` | integer | Total points |
| `field_goals_made` | integer | Field goals made |
| `field_goals_attempted` | integer | Field goals attempted |
| `field_goal_pct` | float | Field goal percentage (computed) |
| `three_pointers_made` | integer | 3-pointers made |
| `three_pointers_attempted` | integer | 3-pointers attempted |
| `three_point_pct` | float | 3-point percentage (computed) |
| `free_throws_made` | integer | Free throws made |
| `free_throws_attempted` | integer | Free throws attempted |
| `free_throw_pct` | float | Free throw percentage (computed) |
| `offensive_rebounds` | integer | Offensive rebounds |
| `defensive_rebounds` | integer | Defensive rebounds |
| `total_rebounds` | integer | Total rebounds |
| `assists` | integer | Assists |
| `turnovers` | integer | Turnovers |
| `steals` | integer | Steals |
| `blocks` | integer | Blocks |
| `personal_fouls` | integer | Personal fouls |
| `fast_break_points` | integer | Points on fast breaks |
| `points_in_paint` | integer | Points scored in the paint |
| `second_chance_points` | integer | Points after offensive rebounds |
| `bench_points` | integer | Points by non-starters |

### PlayerBoxScoreResponse

| Field | Type | Description |
|-------|------|-------------|
| `player_id` | UUID | Player identifier |
| `player_name` | string | Player full name |
| `team_id` | UUID | Team identifier |
| `is_starter` | boolean | In starting lineup |
| `minutes_played` | integer | Playing time in seconds |
| `minutes_display` | string | Formatted time "MM:SS" |
| `points` | integer | Points scored |
| `field_goals_made` | integer | FG made |
| `field_goals_attempted` | integer | FG attempted |
| `field_goal_pct` | float | FG percentage (computed) |
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
| `plus_minus` | integer | Plus/minus rating |

### PlayByPlayEventResponse

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Event identifier |
| `game_id` | UUID | Game identifier |
| `event_number` | integer | Sequence number in game |
| `period` | integer | Period number (1-4, 5+ for OT) |
| `clock` | string | Game clock (e.g., "10:30") |
| `event_type` | string | Event type (SHOT, REBOUND, etc.) |
| `event_subtype` | string | Subtype (3PT, OFFENSIVE, etc.) |
| `player_id` | UUID | Player involved (may be null) |
| `player_name` | string | Player name (may be null) |
| `team_id` | UUID | Team involved |
| `team_name` | string | Team name |
| `success` | boolean | For shots: made or missed (may be null) |
| `coord_x` | float | Shot X coordinate (may be null) |
| `coord_y` | float | Shot Y coordinate (may be null) |
| `attributes` | object | Extended event attributes |
| `description` | string | Human-readable description |
| `related_event_ids` | array | IDs of linked events |

---

## Game Status Values

| Status | Description |
|--------|-------------|
| `SCHEDULED` | Game is scheduled but not started |
| `LIVE` | Game is currently in progress |
| `FINAL` | Game has completed |
| `POSTPONED` | Game has been postponed |
| `CANCELLED` | Game has been cancelled |

---

## Error Codes

| Code | Description |
|------|-------------|
| 404 | Game not found |
| 422 | Validation error (invalid UUID, invalid query parameters) |

---

## Related Documentation

- [Game Statistics Reference](../models/game-stats.md) - Detailed stat field documentation
- [Play-by-Play Reference](../models/play-by-play.md) - Event types and linking
- [Players API](players.md) - Player game log endpoint
- [Teams API](teams.md) - Team game history endpoint
