# Game Statistics Reference

Complete documentation of all statistics fields used in player and team box scores.

## Player Statistics

### Basic Stats

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `minutes_played` | int | Playing time in seconds | Raw value stored |
| `minutes_display` | str | Formatted time "MM:SS" | Computed from `minutes_played` |
| `is_starter` | bool | In starting lineup | True for starters |
| `points` | int | Total points scored | `2PT*2 + 3PT*3 + FT` |

### Field Goals

| Field | Type | Description | Calculation |
|-------|------|-------------|-------------|
| `field_goals_made` | int | Total made field goals | `2PT_made + 3PT_made` |
| `field_goals_attempted` | int | Total field goal attempts | `2PT_att + 3PT_att` |
| `field_goal_pct` | float | Field goal percentage | `FGM / FGA * 100` |
| `two_pointers_made` | int | Made 2-point shots | Raw value |
| `two_pointers_attempted` | int | 2-point shot attempts | Raw value |
| `two_point_pct` | float | 2-point percentage | `2PM / 2PA * 100` |
| `three_pointers_made` | int | Made 3-point shots | Raw value |
| `three_pointers_attempted` | int | 3-point shot attempts | Raw value |
| `three_point_pct` | float | 3-point percentage | `3PM / 3PA * 100` |

### Free Throws

| Field | Type | Description | Calculation |
|-------|------|-------------|-------------|
| `free_throws_made` | int | Made free throws | Raw value |
| `free_throws_attempted` | int | Free throw attempts | Raw value |
| `free_throw_pct` | float | Free throw percentage | `FTM / FTA * 100` |

### Rebounds

| Field | Type | Description | Calculation |
|-------|------|-------------|-------------|
| `offensive_rebounds` | int | Rebounds on offense | Raw value |
| `defensive_rebounds` | int | Rebounds on defense | Raw value |
| `total_rebounds` | int | Total rebounds | `OREB + DREB` |

### Other Stats

| Field | Type | Description | Notes |
|-------|------|-------------|-------|
| `assists` | int | Passes leading to scores | Raw value |
| `turnovers` | int | Ball possessions lost | Raw value |
| `steals` | int | Turnovers forced | Raw value |
| `blocks` | int | Shots blocked | Raw value |
| `personal_fouls` | int | Fouls committed | Raw value |
| `plus_minus` | int | Point differential while on court | Team score diff |

### Efficiency Ratings

| Field | Type | Description | Calculation |
|-------|------|-------------|-------------|
| `efficiency` | int | Performance Index Rating (PIR) | See formula below |

#### PIR (Performance Index Rating)

Used in European leagues (EuroLeague, etc.):

```
PIR = (PTS + REB + AST + STL + BLK + Fouls Drawn)
    - (FGA - FGM) - (FTA - FTM) - TO - Fouls Committed
```

Simplified:
```
PIR = PTS + REB + AST + STL + BLK
    - Missed FG - Missed FT - TO - PF
```

**Example:**
```
LeBron James: 30 PTS, 10 REB, 8 AST, 2 STL, 1 BLK
             11-22 FG (11 missed), 5-6 FT (1 missed)
             3 TO, 2 PF

PIR = 30 + 10 + 8 + 2 + 1 - 11 - 1 - 3 - 2 = 34
```

---

## Team Statistics

Team statistics include all player statistics aggregated, plus team-specific metrics.

### Team-Only Statistics

| Field | Type | Description |
|-------|------|-------------|
| `fast_break_points` | int | Points scored on fast breaks |
| `points_in_paint` | int | Points scored inside the paint |
| `second_chance_points` | int | Points scored after offensive rebounds |
| `bench_points` | int | Points scored by non-starters |
| `biggest_lead` | int | Maximum point differential during game |
| `time_leading` | int | Seconds spent in the lead |

### Fast Break Points

Points scored on possessions that start with a defensive rebound or steal and result in a shot attempt within a few seconds (typically 7-10 seconds depending on league rules).

### Points in Paint

Points scored within the painted area near the basket. This includes:
- Layups
- Dunks
- Post-up shots
- Floaters in the lane

### Second Chance Points

Points scored after an offensive rebound. When a team misses a shot but gets the rebound on offense, any subsequent points on that possession are counted as second chance points.

### Bench Points

Points scored by players who were not in the starting lineup. Useful for evaluating depth and bench contribution.

---

## Percentage Calculations

All percentages are computed and returned in the API responses. They are calculated as:

```python
def compute_percentage(made: int, attempted: int) -> float:
    """
    Compute shooting percentage.

    Returns 0.0 if no attempts (avoid division by zero).
    Result is rounded to 1 decimal place.
    """
    if attempted == 0:
        return 0.0
    return round((made / attempted) * 100, 1)
```

**Examples:**
- `11 FGM / 22 FGA = 50.0%`
- `3 3PM / 8 3PA = 37.5%`
- `0 FGM / 0 FGA = 0.0%` (no attempts)

---

## Minutes Display Format

Minutes are stored in seconds for precision, then formatted for display:

```python
def format_minutes(seconds: int) -> str:
    """
    Format seconds into MM:SS display string.
    """
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"
```

**Examples:**
- `2100 seconds = "35:00"`
- `1842 seconds = "30:42"`
- `420 seconds = "7:00"`

---

## Extra Stats (JSON Field)

The `extra_stats` field stores league-specific statistics not part of the standard schema:

```json
{
    "fouls_drawn": 5,
    "charges_taken": 1,
    "dunks": 2,
    "double_double": true,
    "triple_double": false
}
```

This field allows flexibility for different leagues with varying stat tracking.

---

## Box Score Display Order

When returning player box scores:

1. **Starters first**: Players with `is_starter=True` appear before bench players
2. **Sorted by points**: Within each group, players are sorted by points (descending)

```python
players.sort(key=lambda p: (not p.is_starter, -p.points))
```

---

## Related Documentation

- [Play-by-Play Reference](play-by-play.md) - Event types and linking
- [Games API](../api/games.md) - Box score endpoints
- [Models Reference](../../src/models/README.md) - Database schema
