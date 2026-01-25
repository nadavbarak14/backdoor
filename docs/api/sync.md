# Sync API

API endpoints for data synchronization tracking and monitoring.

## Overview

The Sync API provides visibility into data synchronization operations from external sources (Winner League, Euroleague, etc.). Use these endpoints to monitor sync health, debug issues, and track data import history.

## List Sync Logs

Retrieve sync operation history with optional filters.

```
GET /api/v1/sync/logs
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| source | string | No | - | Filter by data source |
| entity_type | string | No | - | Filter by entity type |
| status | string | No | - | Filter by sync status |
| season_id | UUID | No | - | Filter by season |
| start_date | datetime | No | - | Filter logs started after |
| end_date | datetime | No | - | Filter logs started before |
| page | int | No | 1 | Page number (1-indexed) |
| page_size | int | No | 20 | Items per page (1-100) |

### Sources

| Source | Description |
|--------|-------------|
| winner | Winner League (Israel) |
| euroleague | EuroLeague |

### Entity Types

| Type | Description |
|------|-------------|
| games | Game schedules and results |
| players | Player profiles |
| stats | Player/team game statistics |
| pbp | Play-by-play events |

### Status Values

| Status | Description |
|--------|-------------|
| STARTED | Sync operation in progress |
| COMPLETED | Sync finished successfully |
| FAILED | Sync encountered a fatal error |
| PARTIAL | Sync completed with some records skipped |

### Response

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "source": "winner",
      "entity_type": "games",
      "status": "COMPLETED",
      "season_id": "uuid",
      "season_name": "2023-24",
      "game_id": null,
      "records_processed": 150,
      "records_created": 10,
      "records_updated": 140,
      "records_skipped": 0,
      "error_message": null,
      "error_details": null,
      "started_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:00:45Z",
      "duration_seconds": 45.0
    },
    {
      "id": "uuid",
      "source": "winner",
      "entity_type": "players",
      "status": "FAILED",
      "season_id": "uuid",
      "season_name": "2023-24",
      "records_processed": 50,
      "records_created": 48,
      "records_updated": 0,
      "records_skipped": 0,
      "error_message": "API connection timeout",
      "error_details": {
        "endpoint": "/api/players",
        "timeout": 30,
        "last_player_id": "12345"
      },
      "started_at": "2024-01-15T10:01:00Z",
      "completed_at": "2024-01-15T10:02:30Z",
      "duration_seconds": 90.0
    }
  ],
  "total": 2
}
```

### Response Fields

| Field | Description |
|-------|-------------|
| id | Unique sync log identifier |
| source | External data source |
| entity_type | Type of entity synced |
| status | Current sync status |
| season_id | Season being synced (if applicable) |
| season_name | Human-readable season name |
| game_id | Game being synced (if applicable) |
| records_processed | Total records processed |
| records_created | New records created |
| records_updated | Existing records updated |
| records_skipped | Records skipped (duplicates, invalid) |
| error_message | Human-readable error description |
| error_details | Detailed error info (JSON) |
| started_at | When sync started |
| completed_at | When sync completed (null if running) |
| duration_seconds | Elapsed time (null if running) |

---

## Examples

### Get all sync logs
```bash
curl "http://localhost:8000/api/v1/sync/logs"
```

### Filter by source
```bash
curl "http://localhost:8000/api/v1/sync/logs?source=winner"
```

### Filter by status
```bash
curl "http://localhost:8000/api/v1/sync/logs?status=FAILED"
```

### Filter by entity type
```bash
curl "http://localhost:8000/api/v1/sync/logs?entity_type=games"
```

### Combined filters
```bash
curl "http://localhost:8000/api/v1/sync/logs?source=winner&entity_type=games&status=COMPLETED"
```

### Filter by date range
```bash
curl "http://localhost:8000/api/v1/sync/logs?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z"
```

### Pagination
```bash
curl "http://localhost:8000/api/v1/sync/logs?page=2&page_size=50"
```

---

## Interpreting Sync Results

### Successful Sync
```json
{
  "status": "COMPLETED",
  "records_processed": 100,
  "records_created": 5,
  "records_updated": 95,
  "records_skipped": 0,
  "duration_seconds": 45.2
}
```
- All records processed successfully
- 5 new games found, 95 existing games updated

### Partial Sync
```json
{
  "status": "PARTIAL",
  "records_processed": 100,
  "records_created": 90,
  "records_updated": 5,
  "records_skipped": 5,
  "error_message": "5 records had invalid data"
}
```
- Most records processed
- Some records skipped due to data issues

### Failed Sync
```json
{
  "status": "FAILED",
  "records_processed": 25,
  "error_message": "API connection timeout",
  "error_details": {
    "endpoint": "/api/games",
    "timeout": 30
  }
}
```
- Sync failed after processing 25 records
- Check error_details for debugging info

### Running Sync
```json
{
  "status": "STARTED",
  "records_processed": 0,
  "completed_at": null,
  "duration_seconds": null
}
```
- Sync is currently in progress
- No duration yet

---

## Monitoring Best Practices

1. **Check for FAILED syncs regularly**
   ```bash
   curl "http://localhost:8000/api/v1/sync/logs?status=FAILED&page_size=10"
   ```

2. **Monitor running syncs**
   ```bash
   curl "http://localhost:8000/api/v1/sync/logs?status=STARTED"
   ```

3. **Verify recent completions**
   ```bash
   curl "http://localhost:8000/api/v1/sync/logs?status=COMPLETED&page_size=5"
   ```

4. **Check sync health by source**
   ```bash
   # Check Winner League syncs
   curl "http://localhost:8000/api/v1/sync/logs?source=winner&page_size=10"
   ```

---

## Get Sync Status

Get current sync status for all configured sources.

```
GET /api/v1/sync/status
```

### Response

```json
{
  "sources": [
    {
      "name": "winner",
      "enabled": true,
      "auto_sync_enabled": false,
      "sync_interval_minutes": 60,
      "running_syncs": 0,
      "latest_season_sync": {
        "id": "uuid",
        "status": "COMPLETED",
        "started_at": "2024-01-15T10:00:00Z",
        "records_processed": 150,
        "records_created": 10
      },
      "latest_game_sync": null
    }
  ],
  "total_running_syncs": 0
}
```

### Response Fields

| Field | Description |
|-------|-------------|
| sources | List of configured data sources |
| sources[].name | Source identifier |
| sources[].enabled | Whether source is active |
| sources[].auto_sync_enabled | Whether scheduled syncs are enabled |
| sources[].sync_interval_minutes | Interval between auto syncs |
| sources[].running_syncs | Number of syncs currently in progress |
| sources[].latest_season_sync | Most recent season sync info |
| sources[].latest_game_sync | Most recent individual game sync info |
| total_running_syncs | Total syncs in progress across all sources |

### Example

```bash
curl http://localhost:8000/api/v1/sync/status
```

---

## Sync Season

Trigger sync for all games in a season.

```
POST /api/v1/sync/{source}/season/{season_id}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| source | string | Data source name (e.g., "winner", "euroleague") |
| season_id | string | External season identifier (e.g., "2024-25") |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_pbp | boolean | true | Whether to sync play-by-play data |

### Response

Returns a `SyncLogResponse` with sync operation results.

```json
{
  "id": "uuid",
  "source": "winner",
  "entity_type": "season",
  "status": "COMPLETED",
  "season_id": "uuid",
  "season_name": "2024-25",
  "records_processed": 150,
  "records_created": 10,
  "records_updated": 0,
  "records_skipped": 140,
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:05:30Z"
}
```

### Example

```bash
# Sync Winner League 2024-25 season with PBP
curl -X POST "http://localhost:8000/api/v1/sync/winner/season/2024-25"

# Sync without PBP (faster)
curl -X POST "http://localhost:8000/api/v1/sync/winner/season/2024-25?include_pbp=false"
```

### Notes

- Only syncs games with "final" status
- Skips games that have already been synced
- Creates Team, Player, Game, PlayerGameStats, TeamGameStats records
- If include_pbp=true, also creates PlayByPlayEvent records

---

## Sync Game

Trigger sync for a single game.

```
POST /api/v1/sync/{source}/game/{game_id}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| source | string | Data source name |
| game_id | string | External game identifier |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| include_pbp | boolean | true | Whether to sync play-by-play data |

### Response

Returns a `SyncLogResponse` with sync operation results.

```json
{
  "id": "uuid",
  "source": "winner",
  "entity_type": "game",
  "status": "COMPLETED",
  "game_id": "uuid",
  "records_processed": 1,
  "records_created": 1,
  "records_updated": 0,
  "records_skipped": 0,
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:00:05Z"
}
```

### Example

```bash
# Sync a specific game
curl -X POST "http://localhost:8000/api/v1/sync/winner/game/12345"
```

### Notes

- If game is already synced, returns immediately with `records_skipped: 1`
- Syncs box score and optionally PBP in one operation

---

## Sync Teams

Sync team rosters for a season.

```
POST /api/v1/sync/{source}/teams/{season_id}
```

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| source | string | Data source name |
| season_id | string | External season identifier |

### Response

Returns a `SyncLogResponse` with sync operation results.

```json
{
  "id": "uuid",
  "source": "winner",
  "entity_type": "teams",
  "status": "COMPLETED",
  "season_id": "uuid",
  "season_name": "2024-25",
  "records_processed": 12,
  "records_created": 2,
  "records_updated": 10,
  "records_skipped": 0,
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:00:15Z"
}
```

### Example

```bash
curl -X POST "http://localhost:8000/api/v1/sync/winner/teams/2024-25"
```

### Notes

- Creates or updates Team and TeamSeason records
- Uses deduplication to match existing teams

---

## Error Responses

### 400 Bad Request

Returned when source is invalid or not enabled:

```json
{
  "detail": "Unknown source: invalid_source"
}
```

```json
{
  "detail": "Source euroleague is not enabled"
}
```

### 500 Internal Server Error

Returned when sync fails unexpectedly:

```json
{
  "detail": "Sync failed: Connection timeout"
}
```

---

## Sync Workflow Examples

### Initial Season Sync

```bash
# 1. Sync teams first (optional, season sync does this too)
curl -X POST "http://localhost:8000/api/v1/sync/winner/teams/2024-25"

# 2. Sync all games for the season
curl -X POST "http://localhost:8000/api/v1/sync/winner/season/2024-25"

# 3. Check sync status
curl "http://localhost:8000/api/v1/sync/status"

# 4. View sync logs
curl "http://localhost:8000/api/v1/sync/logs?source=winner&status=COMPLETED"
```

### Incremental Sync

```bash
# Sync only new games (already synced games are skipped)
curl -X POST "http://localhost:8000/api/v1/sync/winner/season/2024-25"
```

### Sync Single Game

```bash
# Sync a specific game that might have been missed
curl -X POST "http://localhost:8000/api/v1/sync/winner/game/12345"
```

## Related Documentation

- [Sync Architecture](../sync/architecture.md) - Detailed sync architecture
- [Deduplication](../sync/deduplication.md) - Player/team deduplication strategy
- [Field Mappings](../sync/field-mappings.md) - API field mappings
- [Aggregated Stats Model](../models/aggregated-stats.md) - SyncLog model details
- [Stats API](stats.md) - Statistics endpoints
