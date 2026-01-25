# Field Mappings

This document details how fields from external APIs are mapped to our internal database schema.

## Player Statistics

### Box Score Stats

| Our Field | Winner League | Euroleague | Description |
|-----------|---------------|------------|-------------|
| `player_external_id` | `PlayerId` | `Player_ID` | Unique player identifier |
| `player_name` | `Name` | `Player` | Player display name |
| `team_external_id` | (from parent) | `Team` | Team code |
| `minutes_played` | `Minutes` (parsed) | `Minutes` (parsed) | Time in seconds |
| `is_starter` | `IsStarter` | `IsStarter` | Boolean |
| `points` | `Points` | `Points` | Total points |
| `field_goals_made` | `FGM` | `FieldGoalsMade2 + FieldGoalsMade3` | FG made |
| `field_goals_attempted` | `FGA` | `FieldGoalsAttempted2 + FieldGoalsAttempted3` | FG attempted |
| `two_pointers_made` | `FGM - ThreePM` | `FieldGoalsMade2` | 2PT made |
| `two_pointers_attempted` | `FGA - ThreePA` | `FieldGoalsAttempted2` | 2PT attempted |
| `three_pointers_made` | `ThreePM` | `FieldGoalsMade3` | 3PT made |
| `three_pointers_attempted` | `ThreePA` | `FieldGoalsAttempted3` | 3PT attempted |
| `free_throws_made` | `FTM` | `FreeThrowsMade` | FT made |
| `free_throws_attempted` | `FTA` | `FreeThrowsAttempted` | FT attempted |
| `offensive_rebounds` | `OffReb` | `OffensiveRebounds` | Offensive rebounds |
| `defensive_rebounds` | `DefReb` | `DefensiveRebounds` | Defensive rebounds |
| `total_rebounds` | `Rebounds` | `TotalRebounds` | Total rebounds |
| `assists` | `Assists` | `Assistances` | Assists |
| `turnovers` | `Turnovers` | `Turnovers` | Turnovers |
| `steals` | `Steals` | `Steals` | Steals |
| `blocks` | `Blocks` | `BlocksFavour` | Blocks |
| `personal_fouls` | `Fouls` | `FoulsCommited` | Personal fouls |
| `plus_minus` | `PlusMinus` | `Plusminus` | Plus/minus |
| `efficiency` | `Efficiency` | `Valuation` | Efficiency rating |

### Minutes Parsing

Both sources provide minutes in `MM:SS` format, converted to seconds:

```python
def parse_minutes_to_seconds(minutes_str: str) -> int:
    """Parse '32:15' to 1935 seconds."""
    parts = minutes_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])
```

### Two-Point Calculation

Winner League provides total FG and 3PT separately, so 2PT is calculated:

```python
two_pm = fgm - three_pm
two_pa = fga - three_pa
```

Euroleague provides 2PT and 3PT separately.

## Play-by-Play Events

### Event Types

| Our Event Type | Winner League | Euroleague | Description |
|----------------|---------------|------------|-------------|
| `shot` | `MADE_2PT`, `MISS_2PT`, `MADE_3PT`, `MISS_3PT` | `2FGM`, `2FGA`, `3FGM`, `3FGA` | Field goal attempt |
| `free_throw` | `MADE_FT`, `MISS_FT` | `FTM`, `FTA` | Free throw attempt |
| `rebound` | `REBOUND` | `O`, `D` | Offensive or defensive rebound |
| `assist` | `ASSIST` | `AS` | Assist |
| `turnover` | `TURNOVER` | `TO` | Turnover |
| `steal` | `STEAL` | `ST` | Steal |
| `block` | `BLOCK` | `BLK`, `FV` | Blocked shot |
| `foul` | `FOUL` | `CM` | Personal foul |
| `jump_ball` | `JUMP_BALL` | `TPOFF` | Jump ball / tip-off |
| `timeout` | `TIMEOUT` | - | Team timeout |
| `substitution` | `SUBSTITUTION` | `IN`, `OUT` | Player substitution |

### Event Success

The `success` field indicates whether a shot was made:

| Value | Winner | Euroleague |
|-------|--------|------------|
| `true` | `MADE_*` prefix | `*M` suffix (2FGM, FTM) |
| `false` | `MISS_*` prefix | `*A` suffix (2FGA, FTA) |
| `null` | Other events | Other events |

### Event Coordinates

Shot location coordinates (when available):

| Our Field | Winner | Euroleague |
|-----------|--------|------------|
| `coord_x` | `CoordX` | `COORD_X` |
| `coord_y` | `CoordY` | `COORD_Y` |

Coordinates are in court percentage (0-100) where:
- X: 0 = left baseline, 100 = right baseline
- Y: 0 = near sideline, 100 = far sideline

### Event Linking

Related events are linked by inferring relationships:

```python
# Rules for linking events
1. ASSIST after made SHOT (same team, <2 sec) → links to shot
2. REBOUND after missed SHOT (<3 sec) → links to shot
3. STEAL after TURNOVER (diff team, <2 sec) → links to turnover
4. BLOCK with missed SHOT (same time) → links to shot
5. FREE_THROW after FOUL → links to foul
```

## Teams

| Our Field | Winner | Euroleague |
|-----------|--------|------------|
| `external_id` | `TeamId` | `code` |
| `name` | `TeamName` | `name` |
| `short_name` | `ShortName` | `tv_code` or `code` |

## Games

| Our Field | Winner | Euroleague |
|-----------|--------|------------|
| `external_id` | `GameId` | `{competition}{season}_{gamecode}` |
| `home_team_external_id` | `HomeTeamId` | `hometeam` |
| `away_team_external_id` | `AwayTeamId` | `awayteam` |
| `game_date` | `GameDate` | `date` |
| `status` | `Status` (normalized) | Inferred from scores |
| `home_score` | `HomeScore` | `homescore` |
| `away_score` | `AwayScore` | `awayscore` |

### Game Status

| Our Status | Winner | Euroleague |
|------------|--------|------------|
| `scheduled` | No scores | `home_score = null` |
| `live` | - | `Live = true` |
| `final` | Has scores | Has scores |

### Euroleague Game ID Format

Euroleague games use a composite ID:

```
{competition}{season}_{gamecode}
Example: E2024_15
```

Where:
- `competition`: "E" (Euroleague) or "U" (EuroCup)
- `season`: Year (e.g., 2024)
- `gamecode`: Game number within season

## Seasons

| Our Field | Winner | Euroleague |
|-----------|--------|------------|
| `external_id` | Season string | `{competition}{season}` |
| `name` | From API | `{year}-{year+1} {competition_name}` |
| `start_date` | Inferred from games | October 1 |
| `end_date` | Inferred from games | May 31 |
| `is_current` | Assumed true | From config |

## Player Info

Biographical data from player profiles:

| Our Field | Winner (Scraper) | Euroleague |
|-----------|------------------|------------|
| `external_id` | `player_id` | `code` |
| `first_name` | Parsed from `name` | Parsed from `name` |
| `last_name` | Parsed from `name` | Parsed from `name` |
| `birth_date` | `birth_date` | `birthdate` |
| `height_cm` | `height_cm` | `height` (meters × 100) |
| `position` | `position` | `position` |

### Name Parsing

**Winner**: "FirstName LastName" → split on first space
**Euroleague**: "LASTNAME, FIRSTNAME" → split on comma, swap order

### Height Conversion

Euroleague provides height in meters (e.g., "1.98"), converted to cm:

```python
height_cm = round(float(height_str) * 100)  # "1.98" → 198
```

## Date Formats

| Source | Format | Example |
|--------|--------|---------|
| Winner | ISO 8601 | `2024-01-15T19:30:00` |
| Euroleague | Text | `Oct 03, 2024` |
| Euroleague (alt) | Slash | `03/10/2024` |

### Euroleague Birth Date

Format: "12 March, 1998"

```python
datetime.strptime(date_str, "%d %B, %Y").date()
```

## Related Documentation

- [Sync Architecture](architecture.md)
- [Winner Adapter](../../src/sync/winner/README.md)
- [Euroleague Adapter](../../src/sync/euroleague/README.md)
- [Raw Types](../../src/sync/types.py)
