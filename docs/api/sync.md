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

## Related Documentation

- [Aggregated Stats Model](../models/aggregated-stats.md) - SyncLog model details
- [Stats API](stats.md) - Statistics endpoints
