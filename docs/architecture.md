# Basketball Analytics Platform - Architecture

## Vision
A unified basketball analytics platform aggregating data from multiple leagues (Winner, Euroleague) into a single data model for AI-powered analytics, coaching, and scouting.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL DATA SOURCES                        │
│    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐       │
│    │ Winner API  │    │ Euroleague   │    │  Future Sources │       │
│    └──────┬──────┘    └──────┬───────┘    └────────┬────────┘       │
└───────────┼──────────────────┼─────────────────────┼────────────────┘
            │                  │                     │
            ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SYNC LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     Sync Manager                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│     │   Winner    │    │ Euroleague  │    │   Future    │          │
│     │   Adapter   │    │   Adapter   │    │   Adapter   │          │
│     └─────────────┘    └─────────────┘    └─────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     SQLite Database                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│   │
│  │  │ Leagues │ │  Teams  │ │ Players │ │  Games  │ │  Stats  ││   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘│   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐  │
│  │   Player    │ │    Game     │ │    Stats    │ │   Analytics  │  │
│  │   Service   │ │   Service   │ │   Service   │ │   Service    │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     FastAPI REST API                          │   │
│  │   /leagues   /teams   /players   /games   /stats   /sync     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CONSUMERS                                    │
│    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐       │
│    │   React     │    │   AI/ML      │    │  Coaching Tools │       │
│    │  Frontend   │    │   Services   │    │                 │       │
│    │ (TypeScript)│    └──────────────┘    └─────────────────┘       │
│    └─────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Database | SQLite (upgradeable to PostgreSQL) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Testing | pytest |
| HTTP Client | httpx |

### Frontend
| Layer | Technology |
|-------|------------|
| Framework | React 18 |
| Language | TypeScript |
| Build Tool | Vite |
| Data Fetching | TanStack Query |
| Routing | React Router |
| Styling | Tailwind CSS |
| Icons | Lucide React |

> **Note:** Starting with SQLite for simplicity. Schema designed to be compatible with PostgreSQL migration later. JSONB fields will use JSON type in SQLite.

---

## Data Flows

**Sync Flow:**
```
External API → Adapter → Mapper → Unified Schema → Deduplication → Database
```

**Query Flow:**
```
API Request → Router → Service → Database → Serialization → Response
```

**Stats Calculation:**
```
New Game Synced → Stats Service → Update Aggregated Tables
```

---

# EPICS

---

## EPIC 1: Project Foundation

### Goal
Set up project infrastructure, development environment, and core utilities.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| Project Config | pyproject.toml, dependencies, linting | None |
| Core Config | Environment settings (Pydantic) | None |
| Database Connection | SQLAlchemy engine, session management (SQLite) | Core Config |
| Base Models | Common model mixins (UUID, timestamps) | Database |
| Alembic Setup | Migration configuration | Database |

### API
None (infrastructure only)

---

## EPIC 2: Data Layer - Core Entities

### Goal
Implement database models for leagues, seasons, teams, and players with cross-league support.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| League Model | League table with code identifier | Base Models |
| Season Model | Seasons linked to leagues | League Model |
| Team Model | Teams with JSONB external_ids | Base Models |
| TeamSeason Model | Team participation in seasons | Team, Season |
| Player Model | Players with JSONB external_ids | Base Models |
| PlayerTeamHistory | Roster tracking across seasons | Player, Team, Season |

### Data Model
```
League (id, name, code, country)
    └── Season (id, league_id, name, start_date, end_date, is_current)
            └── TeamSeason (team_id, season_id)

Team (id, name, short_name, city, country, external_ids: JSON)
    └── PlayerTeamHistory (player_id, team_id, season_id, jersey_number, position)

Player (id, first_name, last_name, birth_date, nationality, height_cm, position, external_ids: JSON)
```

> **Note:** `external_ids` stores cross-league mappings as JSON: `{"winner": "123", "euroleague": "ABC"}`

### API
```
GET  /api/v1/leagues                    List all leagues
GET  /api/v1/leagues/{id}               Get league by ID
GET  /api/v1/leagues/{id}/seasons       List seasons for league

GET  /api/v1/teams                      List teams (filterable by league, season)
GET  /api/v1/teams/{id}                 Get team by ID
GET  /api/v1/teams/{id}/roster          Get current team roster

GET  /api/v1/players                    Search players (filterable)
GET  /api/v1/players/{id}               Get player by ID
```

---

## EPIC 3: Data Layer - Game Data

### Goal
Implement game-related models including games, box scores, and play-by-play events.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| Game Model | Games with teams, date, scores | Team, Season |
| PlayerGameStats | Per-player box score stats | Game, Player, Team |
| TeamGameStats | Per-team aggregated stats | Game, Team |
| PlayByPlayEvent | Event-level data with JSONB attributes | Game, Player, Team |

### Data Model
```
Game (id, season_id, home_team_id, away_team_id, game_date, status, scores, venue, external_ids)
    ├── PlayerGameStats (game_id, player_id, team_id, minutes, points, rebounds, assists, ...)
    ├── TeamGameStats (game_id, team_id, is_home, points, fast_break_points, ...)
    └── PlayByPlayEvent (game_id, period, clock, event_type, player_id, success, coords, attributes)
```

### API
```
GET  /api/v1/games                      List games (filterable by date, team, season)
GET  /api/v1/games/{id}                 Get game with box score
GET  /api/v1/games/{id}/pbp             Get play-by-play events

GET  /api/v1/players/{id}/games         Get player game log
GET  /api/v1/teams/{id}/games           Get team game history
```

---

## EPIC 4: Data Layer - Aggregated Stats

### Goal
Implement pre-computed statistics for efficient querying and sync tracking.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| PlayerSeasonStats | Aggregated season stats (totals, averages, percentages) | Player, Team, Season, PlayerGameStats |
| SyncLog | Track sync operations and history | None |
| Stats Calculation Service | Compute aggregations from game stats | PlayerGameStats |

### Data Model
```
PlayerSeasonStats (player_id, team_id, season_id, games_played, totals, averages, percentages)

SyncLog (id, source, entity_type, status, records_processed, error_message, timestamps)
```

### API
```
GET  /api/v1/players/{id}/stats              Get player career stats
GET  /api/v1/players/{id}/stats/{season_id}  Get player season stats
GET  /api/v1/stats/leaders                   Get league leaders

GET  /api/v1/sync/logs                       Get sync history
```

---

## EPIC 5: Sync Layer

### Goal
Implement data synchronization from external APIs with adapters and deduplication.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| Base Adapter | Abstract interface for data sources | None |
| Sync Manager | Orchestration, error handling, logging | Base Adapter, SyncLog |
| Deduplication Service | Match players across leagues | Player Model |
| Winner Adapter | API client + mapper for Winner league | Base Adapter |
| Euroleague Adapter | API client + mapper for Euroleague | Base Adapter |

### Adapter Structure (per source)
```
adapter/
├── client.py      # HTTP client, API communication
├── mapper.py      # Transform to unified schema
└── sync.py        # Orchestrate sync for this source
```

### API
```
POST /api/v1/sync/{source}              Trigger manual sync (source: winner, euroleague)
GET  /api/v1/sync/status                Get current sync status
GET  /api/v1/sync/logs                  Get sync history (from EPIC 4)
```

---

## EPIC 6: Service Layer

### Goal
Implement business logic services that sit between API and data layers.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| Player Service | Search, CRUD, team history, stats retrieval | Player, PlayerTeamHistory, PlayerSeasonStats |
| Game Service | Query games, box scores, PBP | Game, PlayerGameStats, TeamGameStats, PBP |
| Stats Service | Calculate aggregations, rankings, leaders | PlayerGameStats, PlayerSeasonStats |
| Analytics Service | Player comparison, AI data prep, flexible queries | All data models |

### Service → Model Mapping
```
PlayerService  → Player, PlayerTeamHistory, PlayerSeasonStats
GameService    → Game, PlayerGameStats, TeamGameStats, PlayByPlayEvent
StatsService   → PlayerGameStats, PlayerSeasonStats
AnalyticsService → All (cross-cutting queries)
```

### API
Services are consumed by API layer, not exposed directly.

---

## EPIC 7: Testing Infrastructure

### Goal
Set up comprehensive testing with fixtures, test database, and coverage.

### Components
| Component | Description | Dependencies |
|-----------|-------------|--------------|
| Test Database Config | In-memory SQLite for tests | Core Config |
| Pytest Conftest | Session fixtures, test client, factories | Test DB |
| JSON Test Fixtures | Sample API responses (Winner, Euroleague) | None |
| Coverage Config | pytest-cov setup, thresholds | Pytest |

### Test Structure
```
tests/
├── conftest.py           # Shared fixtures
├── fixtures/
│   ├── winner/           # Winner API sample responses
│   └── euroleague/       # Euroleague API sample responses
├── unit/                 # Model, mapper, service tests
└── integration/          # API endpoint tests
```

### API
None (testing infrastructure)

---

## Epic Hierarchy & Dependencies

```
EPIC 1: Project Foundation
    │
    ├──────────────────────────┐
    │                          │
    ▼                          ▼
EPIC 2: Core Entities      EPIC 7: Testing
    │
    ▼
EPIC 3: Game Data
    │
    ▼
EPIC 4: Aggregated Stats
    │
    ├──────────────────────────┐
    │                          │
    ▼                          ▼
EPIC 5: Sync Layer         EPIC 6: Service Layer
```

---

## Implementation Order

1. **EPIC 1** - Project Foundation (prerequisite for all)
2. **EPIC 7** - Testing Infrastructure (parallel with EPIC 1)
3. **EPIC 2** - Core Entities
4. **EPIC 3** - Game Data
5. **EPIC 4** - Aggregated Stats
6. **EPIC 5** - Sync Layer
7. **EPIC 6** - Service Layer

---

## Documentation Requirements

> **See `CLAUDE.md` for complete documentation standards**

### Every Epic Must Include:
- README.md in every new folder
- Docstrings on all classes and functions
- API endpoints fully documented in OpenAPI
- Dedicated docs in `docs/` folder

### API Documentation (CRITICAL)
- `docs/api/` contains full endpoint reference
- Every endpoint has example requests/responses
- All query parameters documented
- Error codes explained
