# Play-by-Play Events Reference

Complete documentation of play-by-play event types, subtypes, and event linking.

## Event Types

| Type | Description | Has Player | Common Subtypes |
|------|-------------|------------|-----------------|
| `SHOT` | Field goal attempt | Yes | 2PT, 3PT, LAYUP, DUNK, JUMP_SHOT, HOOK |
| `ASSIST` | Assist on made shot | Yes | - |
| `REBOUND` | Rebound | Yes | OFFENSIVE, DEFENSIVE |
| `TURNOVER` | Turnover | Yes | BAD_PASS, LOST_BALL, TRAVEL, OUT_OF_BOUNDS, OFFENSIVE_FOUL |
| `STEAL` | Steal | Yes | - |
| `BLOCK` | Blocked shot | Yes | - |
| `FOUL` | Foul called | Yes | PERSONAL, SHOOTING, OFFENSIVE, TECHNICAL, FLAGRANT |
| `FREE_THROW` | Free throw attempt | Yes | - |
| `SUBSTITUTION` | Player substitution | Yes | - |
| `TIMEOUT` | Timeout called | No | FULL, SHORT, OFFICIAL |
| `JUMP_BALL` | Jump ball | No | - |
| `VIOLATION` | Violation called | Yes | KICKED_BALL, LANE, GOALTENDING, BACKCOURT |
| `PERIOD_START` | Period begins | No | - |
| `PERIOD_END` | Period ends | No | - |

## Event Subtypes

### Shot Subtypes

| Subtype | Description |
|---------|-------------|
| `2PT` | Generic 2-point shot |
| `3PT` | 3-point shot |
| `LAYUP` | Layup attempt |
| `DUNK` | Dunk attempt |
| `JUMP_SHOT` | Jump shot |
| `HOOK` | Hook shot |
| `TIP` | Tip-in attempt |
| `FLOATER` | Floater shot |
| `FADEAWAY` | Fadeaway shot |

### Rebound Subtypes

| Subtype | Description |
|---------|-------------|
| `OFFENSIVE` | Offensive rebound |
| `DEFENSIVE` | Defensive rebound |
| `TEAM` | Team rebound (no specific player) |

### Foul Subtypes

| Subtype | Description |
|---------|-------------|
| `PERSONAL` | Personal foul |
| `SHOOTING` | Shooting foul (free throws awarded) |
| `OFFENSIVE` | Offensive foul |
| `TECHNICAL` | Technical foul |
| `FLAGRANT` | Flagrant foul |
| `LOOSE_BALL` | Loose ball foul |

### Turnover Subtypes

| Subtype | Description |
|---------|-------------|
| `BAD_PASS` | Bad pass turnover |
| `LOST_BALL` | Lost ball |
| `TRAVEL` | Traveling violation |
| `OUT_OF_BOUNDS` | Stepped out of bounds |
| `OFFENSIVE_FOUL` | Offensive foul turnover |
| `DOUBLE_DRIBBLE` | Double dribble violation |
| `SHOT_CLOCK` | Shot clock violation |

---

## Event Linking

Events are linked to show relationships between related plays. The `related_event_ids` field contains UUIDs of events this event is connected to.

### Made Shot with Assist

When a shot is made with an assist:

```json
[
    {
        "id": "evt-001",
        "event_type": "SHOT",
        "event_subtype": "LAYUP",
        "player_name": "LeBron James",
        "success": true,
        "related_event_ids": []
    },
    {
        "id": "evt-002",
        "event_type": "ASSIST",
        "player_name": "Anthony Davis",
        "related_event_ids": ["evt-001"]
    }
]
```

### Missed Shot with Rebound

When a shot is missed and rebounded:

```json
[
    {
        "id": "evt-001",
        "event_type": "SHOT",
        "event_subtype": "3PT",
        "player_name": "Stephen Curry",
        "success": false,
        "related_event_ids": []
    },
    {
        "id": "evt-002",
        "event_type": "REBOUND",
        "event_subtype": "DEFENSIVE",
        "player_name": "LeBron James",
        "related_event_ids": ["evt-001"]
    }
]
```

### Steal and Turnover

When a turnover is caused by a steal:

```json
[
    {
        "id": "evt-001",
        "event_type": "TURNOVER",
        "event_subtype": "BAD_PASS",
        "player_name": "Opponent Player",
        "team_name": "Boston Celtics",
        "related_event_ids": []
    },
    {
        "id": "evt-002",
        "event_type": "STEAL",
        "player_name": "LeBron James",
        "team_name": "Los Angeles Lakers",
        "related_event_ids": ["evt-001"]
    }
]
```

### Block and Missed Shot

When a shot is blocked:

```json
[
    {
        "id": "evt-001",
        "event_type": "SHOT",
        "event_subtype": "LAYUP",
        "player_name": "Jayson Tatum",
        "success": false,
        "related_event_ids": []
    },
    {
        "id": "evt-002",
        "event_type": "BLOCK",
        "player_name": "Anthony Davis",
        "related_event_ids": ["evt-001"]
    },
    {
        "id": "evt-003",
        "event_type": "REBOUND",
        "event_subtype": "DEFENSIVE",
        "player_name": "LeBron James",
        "related_event_ids": ["evt-001"]
    }
]
```

### And-1 Play (Complex Linking)

Made shot with shooting foul and free throw:

```json
[
    {
        "id": "evt-001",
        "event_type": "SHOT",
        "event_subtype": "LAYUP",
        "player_name": "Giannis Antetokounmpo",
        "success": true,
        "description": "Giannis makes layup (14 PTS)",
        "related_event_ids": []
    },
    {
        "id": "evt-002",
        "event_type": "ASSIST",
        "player_name": "Damian Lillard",
        "description": "Lillard assist",
        "related_event_ids": ["evt-001"]
    },
    {
        "id": "evt-003",
        "event_type": "FOUL",
        "event_subtype": "SHOOTING",
        "player_name": "Defender",
        "description": "Shooting foul on Giannis",
        "related_event_ids": ["evt-001"]
    },
    {
        "id": "evt-004",
        "event_type": "FREE_THROW",
        "player_name": "Giannis Antetokounmpo",
        "success": true,
        "description": "Giannis makes FT 1/1",
        "related_event_ids": ["evt-001", "evt-003"]
    }
]
```

---

## Shot Coordinates

Shot events include X/Y coordinates for shot chart visualization.

### Coordinate System

| Field | Range | Description |
|-------|-------|-------------|
| `coord_x` | 0-100 | Horizontal position (baseline to baseline) |
| `coord_y` | 0-50 | Vertical position (sideline to sideline) |

### Court Orientation

- **Origin (0, 25)**: Center of baseline on left side
- **Center court (50, 25)**: Half-court line center
- **Basket position**: Approximately (5.25, 25) on each end
- **3-point line**: Arc at approximately 23.75 feet from basket

### Home Team Orientation

- Home team attacks **left-to-right** in 1st and 3rd periods
- Home team attacks **right-to-left** in 2nd and 4th periods

### Coordinate Examples

```json
// Layup at the rim (left basket)
{
    "coord_x": 5.0,
    "coord_y": 25.0,
    "event_subtype": "LAYUP"
}

// Corner 3 (left corner)
{
    "coord_x": 3.0,
    "coord_y": 3.0,
    "event_subtype": "3PT"
}

// Top of the key 3
{
    "coord_x": 19.0,
    "coord_y": 25.0,
    "event_subtype": "3PT"
}

// Mid-range wing shot
{
    "coord_x": 12.0,
    "coord_y": 35.0,
    "event_subtype": "JUMP_SHOT"
}
```

---

## Attributes JSON

The `attributes` field stores extended event data:

### Shot Attributes

```json
{
    "shot_distance": 7.5,
    "shot_type": "PULL_UP",
    "fast_break": true,
    "second_chance": false,
    "contested": true,
    "points_type": 2
}
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `shot_distance` | float | Distance from basket in feet |
| `shot_type` | string | PULL_UP, CATCH_AND_SHOOT, POST_UP, etc. |
| `fast_break` | bool | Shot on fast break |
| `second_chance` | bool | Shot after offensive rebound |
| `contested` | bool | Defender within 4 feet |
| `points_type` | int | 2 or 3 (redundant with subtype) |

### Foul Attributes

```json
{
    "foul_type": "P2",
    "team_fouls": 4,
    "in_penalty": true,
    "free_throws": 2
}
```

### Substitution Attributes

```json
{
    "player_in_id": "uuid-player-in",
    "player_in_name": "Austin Reaves",
    "player_out_id": "uuid-player-out",
    "player_out_name": "D'Angelo Russell"
}
```

---

## Filtering Play-by-Play

The API supports filtering by multiple criteria:

### Filter by Period

Get 4th quarter events only:
```bash
curl "/api/v1/games/{game_id}/pbp?period=4"
```

### Filter by Event Type

Get all shots:
```bash
curl "/api/v1/games/{game_id}/pbp?event_type=SHOT"
```

### Filter by Player

Get all events involving a specific player:
```bash
curl "/api/v1/games/{game_id}/pbp?player_id={player_id}"
```

### Filter by Team

Get all events for a specific team:
```bash
curl "/api/v1/games/{game_id}/pbp?team_id={team_id}"
```

### Combined Filters

Get 4th quarter shots by a specific player:
```bash
curl "/api/v1/games/{game_id}/pbp?period=4&event_type=SHOT&player_id={player_id}"
```

---

## Related Documentation

- [Game Statistics Reference](game-stats.md) - Box score fields
- [Games API](../api/games.md) - Play-by-play endpoint
- [Models Reference](../../src/models/README.md) - Database schema
