# Aggregated Statistics Reference

Documentation for the aggregated statistics system including PlayerSeasonStats calculations, formulas, and sync tracking.

## Overview

The aggregated statistics system provides:
- **Pre-computed season stats** for efficient querying
- **Advanced metrics** (TS%, eFG%, AST/TO)
- **League leader functionality**
- **Sync operation tracking** for data imports

## Data Models

### PlayerSeasonStats

Stores aggregated statistics for a player on a specific team during a specific season.

```python
PlayerSeasonStats:
  - player_id, team_id, season_id (unique together)
  - games_played, games_started
  - Totals: total_minutes, total_points, total_rebounds, etc.
  - Averages: avg_points, avg_rebounds, avg_assists, etc.
  - Percentages: fg_pct, 3pt_pct, ft_pct (stored as 0.0-1.0)
  - Advanced: true_shooting_pct, effective_fg_pct, assist_turnover_ratio
  - last_calculated: timestamp of last recalculation
```

**Key Design Decisions:**
- Percentages stored as decimals (0.0-1.0) internally, converted to 0-100 in API responses
- One record per player/team/season combination (traded players have multiple records per season)
- Minutes stored in seconds for precision

### SyncLog

Tracks data synchronization operations for monitoring and debugging.

```python
SyncLog:
  - id: UUID
  - source: str (e.g., "winner", "euroleague")
  - entity_type: str (e.g., "games", "players", "stats", "pbp")
  - status: STARTED | COMPLETED | FAILED | PARTIAL
  - season_id: Optional UUID (for season-specific syncs)
  - game_id: Optional UUID (for game-specific syncs)
  - records_processed, records_created, records_updated, records_skipped
  - error_message: Optional error description
  - error_details: Optional JSON with detailed error info
  - started_at, completed_at: timestamps
```

## How Stats Are Calculated

PlayerSeasonStats are computed from PlayerGameStats by:

1. **Aggregating totals** - Sum all game stats for player+team+season
2. **Computing averages** - Divide totals by games_played
3. **Computing percentages** - Calculate shooting percentages
4. **Computing advanced stats** - TS%, eFG%, AST/TO

### Calculation Flow

```
PlayerGameStats (per-game data)
          ↓
StatsCalculationService.calculate_player_season_stats()
          ↓
PlayerSeasonStats (aggregated season data)
```

## Basic Percentages

### Field Goal Percentage (FG%)

```
FG% = (FGM / FGA) × 100
```

**Example:** 8 made out of 18 attempts
- FG% = (8 / 18) × 100 = 44.4%

### Three-Point Percentage (3P%)

```
3P% = (3PM / 3PA) × 100
```

**Example:** 3 made out of 8 attempts
- 3P% = (3 / 8) × 100 = 37.5%

### Free Throw Percentage (FT%)

```
FT% = (FTM / FTA) × 100
```

**Example:** 6 made out of 7 attempts
- FT% = (6 / 7) × 100 = 85.7%

## Advanced Statistics

### True Shooting Percentage (TS%)

Measures scoring efficiency accounting for 3-pointers and free throws.

```
TS% = PTS / (2 × (FGA + 0.44 × FTA)) × 100
```

**Why 0.44?** This coefficient approximates the possession cost of free throws, accounting for:
- And-1 plays (1 FTA after a made basket)
- Technical free throws
- 3-shot fouls

**Example:** 25 points on 15 FGA and 8 FTA
```
TS% = 25 / (2 × (15 + 0.44 × 8)) × 100
TS% = 25 / (2 × 18.52) × 100
TS% = 25 / 37.04 × 100
TS% = 67.5%
```

**Interpretation:**
- League average: ~55-57%
- Elite scorers: 60%+
- Exceptional: 65%+

### Effective Field Goal Percentage (eFG%)

Adjusts FG% to account for 3-pointers being worth 50% more than 2-pointers.

```
eFG% = (FGM + 0.5 × 3PM) / FGA × 100
```

A made 3-pointer is treated as 1.5 made field goals.

**Example:** 8 FGM (including 3 threes) on 15 FGA
```
eFG% = (8 + 0.5 × 3) / 15 × 100
eFG% = 9.5 / 15 × 100
eFG% = 63.3%
```

**Interpretation:**
- Higher than FG% indicates good 3-point shooting
- More useful than FG% for comparing players with different shot profiles

### Assist-to-Turnover Ratio (AST/TO)

Measures ball security and playmaking efficiency.

```
AST/TO = AST / TO
```

**Example:** 7 assists and 2 turnovers
```
AST/TO = 7 / 2 = 3.5
```

**Interpretation:**
- 2.0+: Good ball handler
- 3.0+: Excellent
- 4.0+: Elite playmaker

**Edge Cases:**
- If turnovers = 0, returns assists as float
- If both = 0, returns 0.0

## Mid-Season Trades

When a player is traded during the season:

1. **Separate records per team** - Each team gets its own PlayerSeasonStats entry
2. **Career stats aggregate all entries** - The /stats endpoint combines all records
3. **Season stats show both teams** - The /stats/{season_id} endpoint returns multiple entries

**Example API Response (traded player):**
```json
GET /api/v1/players/{id}/stats/{season_id}

[
  {
    "team_name": "Maccabi Tel Aviv",
    "games_played": 20,
    "avg_points": 15.3,
    ...
  },
  {
    "team_name": "Hapoel Jerusalem",
    "games_played": 12,
    "avg_points": 17.8,
    ...
  }
]
```

## Recalculation

Stats can be recalculated:

### Per Player
```python
service = StatsCalculationService(db)
count = service.recalculate_for_player(player_id)
```

### Per Season
```python
service = StatsCalculationService(db)
count = service.recalculate_all_for_season(season_id)
```

### Single Player-Team-Season
```python
service = StatsCalculationService(db)
stats = service.calculate_player_season_stats(player_id, team_id, season_id)
```

## Sync Statuses

| Status | Description |
|--------|-------------|
| STARTED | Sync operation has begun |
| COMPLETED | Sync finished successfully |
| FAILED | Sync encountered a fatal error |
| PARTIAL | Sync completed with some records skipped |

## Related Documentation

- [Stats API](../api/stats.md) - API endpoints for stats
- [Sync API](../api/sync.md) - API endpoints for sync logs
- [Game Stats](game-stats.md) - Per-game statistics model
