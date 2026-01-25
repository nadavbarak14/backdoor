# Stats API

API endpoints for player statistics and league leaders.

## Player Career Stats

Retrieve a player's career statistics including all season stats.

```
GET /api/v1/players/{player_id}/stats
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| player_id | UUID | The player's unique identifier |

### Response

```json
{
  "player_id": "550e8400-e29b-41d4-a716-446655440000",
  "player_name": "Scottie Wilbekin",
  "career_games_played": 150,
  "career_games_started": 145,
  "career_points": 2175,
  "career_rebounds": 450,
  "career_assists": 675,
  "career_steals": 150,
  "career_blocks": 30,
  "career_turnovers": 225,
  "career_avg_points": 14.5,
  "career_avg_rebounds": 3.0,
  "career_avg_assists": 4.5,
  "seasons": [
    {
      "id": "uuid",
      "player_id": "uuid",
      "player_name": "Scottie Wilbekin",
      "team_id": "uuid",
      "team_name": "Maccabi Tel Aviv",
      "season_id": "uuid",
      "season_name": "2023-24",
      "games_played": 30,
      "games_started": 30,
      "total_minutes": 54000,
      "total_points": 495,
      "avg_points": 16.5,
      "avg_rebounds": 3.2,
      "avg_assists": 5.1,
      "field_goal_pct": 45.2,
      "three_point_pct": 38.5,
      "true_shooting_pct": 58.3,
      "last_calculated": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Error Responses

| Code | Description |
|------|-------------|
| 404 | Player not found |

### Example

```bash
curl "http://localhost:8000/api/v1/players/550e8400-e29b-41d4-a716-446655440000/stats"
```

---

## Player Season Stats

Retrieve a player's statistics for a specific season.

```
GET /api/v1/players/{player_id}/stats/{season_id}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| player_id | UUID | The player's unique identifier |
| season_id | UUID | The season's unique identifier |

### Response

Returns a list (array) because players traded mid-season will have multiple entries.

```json
[
  {
    "id": "uuid",
    "player_id": "uuid",
    "player_name": "Scottie Wilbekin",
    "team_id": "uuid",
    "team_name": "Maccabi Tel Aviv",
    "season_id": "uuid",
    "season_name": "2023-24",
    "games_played": 20,
    "games_started": 20,
    "total_minutes": 36000,
    "total_points": 330,
    "total_field_goals_made": 120,
    "total_field_goals_attempted": 265,
    "total_three_pointers_made": 50,
    "total_three_pointers_attempted": 125,
    "total_free_throws_made": 40,
    "total_free_throws_attempted": 48,
    "total_rebounds": 64,
    "total_assists": 100,
    "total_turnovers": 40,
    "avg_minutes": 1800.0,
    "avg_minutes_display": "30:00",
    "avg_points": 16.5,
    "avg_rebounds": 3.2,
    "avg_assists": 5.0,
    "avg_turnovers": 2.0,
    "avg_steals": 1.2,
    "avg_blocks": 0.3,
    "field_goal_pct": 45.3,
    "two_point_pct": 52.1,
    "three_point_pct": 40.0,
    "free_throw_pct": 83.3,
    "true_shooting_pct": 58.5,
    "effective_field_goal_pct": 54.7,
    "assist_turnover_ratio": 2.5,
    "last_calculated": "2024-01-15T10:00:00Z"
  }
]
```

**Traded Player Response:**
```json
[
  {"team_name": "Maccabi Tel Aviv", "games_played": 20, "avg_points": 15.3},
  {"team_name": "Fenerbahce", "games_played": 15, "avg_points": 17.8}
]
```

### Error Responses

| Code | Description |
|------|-------------|
| 404 | Player not found or no stats for season |

### Example

```bash
curl "http://localhost:8000/api/v1/players/{player_id}/stats/{season_id}"
```

---

## League Leaders

Retrieve league leaders for a statistical category.

```
GET /api/v1/stats/leaders
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| season_id | UUID | Yes | - | The season to query |
| category | string | No | points | Statistical category |
| limit | int | No | 10 | Max leaders to return (1-100) |
| min_games | int | No | 1 | Min games for qualification |

### Available Categories

| Category | Description |
|----------|-------------|
| points | Points per game |
| rebounds | Rebounds per game |
| assists | Assists per game |
| steals | Steals per game |
| blocks | Blocks per game |
| field_goal_pct | Field goal percentage |
| three_point_pct | Three-point percentage |
| free_throw_pct | Free throw percentage |
| minutes | Minutes per game |
| efficiency | True shooting percentage |

### Response

```json
{
  "category": "points",
  "season_id": "uuid",
  "season_name": "2023-24",
  "min_games": 10,
  "leaders": [
    {
      "rank": 1,
      "player_id": "uuid",
      "player_name": "Scottie Wilbekin",
      "team_id": "uuid",
      "team_name": "Maccabi Tel Aviv",
      "value": 18.5,
      "games_played": 30
    },
    {
      "rank": 2,
      "player_id": "uuid",
      "player_name": "Wade Baldwin",
      "team_id": "uuid",
      "team_name": "Hapoel Jerusalem",
      "value": 16.2,
      "games_played": 28
    }
  ]
}
```

### Error Responses

| Code | Description |
|------|-------------|
| 400 | Invalid category |
| 404 | Season not found |
| 422 | Missing required parameter (season_id) |

### Examples

**Get scoring leaders:**
```bash
curl "http://localhost:8000/api/v1/stats/leaders?season_id={uuid}&category=points&min_games=10"
```

**Get top 20 assist leaders:**
```bash
curl "http://localhost:8000/api/v1/stats/leaders?season_id={uuid}&category=assists&limit=20"
```

**Get 3-point percentage leaders (min 15 games):**
```bash
curl "http://localhost:8000/api/v1/stats/leaders?season_id={uuid}&category=three_point_pct&min_games=15"
```

---

## Understanding the Statistics

### Percentages

All percentages in responses are on a 0-100 scale:
- `field_goal_pct: 45.3` means 45.3% FG

### Minutes

- `avg_minutes`: Average minutes per game in seconds (e.g., 1800.0 = 30:00)
- `avg_minutes_display`: Formatted string (e.g., "30:00")
- `total_minutes`: Total playing time in seconds

### Advanced Stats

See [Aggregated Stats Documentation](../models/aggregated-stats.md) for formula details.

## Related Documentation

- [Aggregated Stats Model](../models/aggregated-stats.md) - Calculation formulas
- [Players API](players.md) - Other player endpoints
- [Sync API](sync.md) - Sync operation tracking
