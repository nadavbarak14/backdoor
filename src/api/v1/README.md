# API Version 1

## Purpose

Version 1 of the Basketball Analytics API. Contains all endpoints under `/api/v1/`.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `router.py` | Main router aggregating all endpoints |
| `players.py` | Player endpoints (future) |
| `teams.py` | Team endpoints (future) |
| `games.py` | Game endpoints (future) |
| `stats.py` | Statistics endpoints (future) |

## Endpoints Overview

| Prefix | Resource | Description |
|--------|----------|-------------|
| `/api/v1/players` | Players | Player CRUD and search |
| `/api/v1/teams` | Teams | Team CRUD and rosters |
| `/api/v1/games` | Games | Game schedules and box scores |
| `/api/v1/stats` | Statistics | Aggregated stats and rankings |

## Usage

```python
# In main.py
from fastapi import FastAPI
from src.api.v1.router import router as api_v1_router

app = FastAPI()
app.include_router(api_v1_router)
```

## Versioning Strategy

- Breaking changes require a new version (v2)
- Non-breaking additions can be made to v1
- Old versions remain available for deprecation period

## Dependencies

- **Internal**: `src/schemas/`, `src/services/`
- **External**: `fastapi`

## Related Documentation

- [API Documentation](../../../docs/api/README.md)
- [API Layer Overview](../README.md)
