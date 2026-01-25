# Services

## Purpose

Business logic layer for the Basketball Analytics Platform. Services encapsulate all business rules, validation, and data orchestration. They sit between the API layer and data models, providing a clean separation of concerns.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for all services |
| `base.py` | Generic BaseService with reusable CRUD operations |
| `league.py` | LeagueService and SeasonService |
| `team.py` | TeamService with roster and filtering |
| `player.py` | PlayerService with team history and filtering |
| `game.py` | GameService with box score loading and filtering |
| `stats.py` | PlayerGameStatsService and TeamGameStatsService |
| `play_by_play.py` | PlayByPlayService with event linking and shot charts |
| `stats_calculation.py` | StatsCalculationService for aggregated season stats |
| `player_stats.py` | PlayerSeasonStatsService for season stats queries |
| `sync_service.py` | SyncLogService for tracking sync operations |
| `analytics.py` | AnalyticsService for advanced analytics (clutch, situational, lineup) |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│   (HTTP handling, request/response, authentication)      │
└───────────────────────┬─────────────────────────────────┘
                        │ Depends(get_db) → Session
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                           │
│   (Business logic, validation, data orchestration)       │
│                                                          │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ LeagueService │  │  TeamService  │  │PlayerService │ │
│  └───────────────┘  └───────────────┘  └──────────────┘ │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ SeasonService │  │  GameService  │  │PlayByPlay-   │ │
│  └───────────────┘  └───────────────┘  │    Service   │ │
│  ┌────────────────────────┐            └──────────────┘ │
│  │ PlayerGameStatsService │  ... extends BaseService[T] │
│  │ TeamGameStatsService   │                             │
│  └────────────────────────┘                             │
└───────────────────────┬─────────────────────────────────┘
                        │ SQLAlchemy ORM
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                             │
│         (SQLAlchemy models, database)                    │
└─────────────────────────────────────────────────────────┘
```

## Service Reference

### BaseService[ModelT]

Generic base class providing common CRUD operations for any model.

```python
from src.services.base import BaseService
from src.models import Player

class PlayerService(BaseService[Player]):
    def __init__(self, db: Session):
        super().__init__(db, Player)
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_id` | `(id: UUID) -> ModelT \| None` | Get entity by primary key |
| `get_all` | `(skip=0, limit=100) -> list[ModelT]` | Paginated list of all entities |
| `count` | `() -> int` | Total count of entities |
| `create` | `(data: dict) -> ModelT` | Create new entity from dict |
| `update` | `(id: UUID, data: dict) -> ModelT \| None` | Update entity, returns None if not found |
| `delete` | `(id: UUID) -> bool` | Delete entity, returns success status |

### LeagueService

Extends BaseService with league-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_code` | `(code: str) -> League \| None` | Find league by unique code (e.g., "NBA") |
| `get_with_season_count` | `(league_id: UUID) -> tuple[League \| None, int]` | Get league with season count |
| `get_all_with_season_counts` | `(skip=0, limit=100) -> list[tuple[League, int]]` | All leagues with counts |
| `create_league` | `(data: LeagueCreate) -> League` | Create from Pydantic schema |
| `update_league` | `(league_id: UUID, data: LeagueUpdate) -> League \| None` | Update from schema |

### SeasonService

Extends BaseService with season-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_league` | `(league_id: UUID, skip=0, limit=100) -> list[Season]` | All seasons for a league |
| `get_current` | `(league_id: UUID \| None = None) -> Season \| None` | Get current active season |
| `create_season` | `(data: SeasonCreate) -> Season` | Create with is_current handling |
| `set_current` | `(season_id: UUID) -> Season \| None` | Mark season as current (unsets others) |
| `update_season` | `(season_id: UUID, data: SeasonUpdate) -> Season \| None` | Update from schema |

**Note:** When creating or updating a season with `is_current=True`, other seasons in the same league are automatically set to `is_current=False`.

### TeamService

Extends BaseService with team-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_filtered` | `(filter_params: TeamFilter, skip=0, limit=100) -> tuple[list[Team], int]` | Filtered teams with total |
| `get_by_external_id` | `(source: str, external_id: str) -> Team \| None` | Find by external provider ID |
| `get_roster` | `(team_id: UUID, season_id: UUID) -> list[PlayerTeamHistory]` | Team roster for season |
| `create_team` | `(data: TeamCreate) -> Team` | Create from Pydantic schema |
| `update_team` | `(team_id: UUID, data: TeamUpdate) -> Team \| None` | Update from schema |
| `add_to_season` | `(team_id: UUID, season_id: UUID) -> TeamSeason \| None` | Associate team with season |

### PlayerService

Extends BaseService with player-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_with_history` | `(player_id: UUID) -> Player \| None` | Player with team_histories eager loaded |
| `get_filtered` | `(filter_params: PlayerFilter, skip=0, limit=100) -> tuple[list[Player], int]` | Filtered players with total |
| `get_by_external_id` | `(source: str, external_id: str) -> Player \| None` | Find by external provider ID |
| `create_player` | `(data: PlayerCreate) -> Player` | Create from Pydantic schema |
| `update_player` | `(player_id: UUID, data: PlayerUpdate) -> Player \| None` | Update from schema |
| `add_to_team` | `(player_id, team_id, season_id, jersey_number?, position?) -> PlayerTeamHistory \| None` | Add player to team roster |
| `get_team_history` | `(player_id: UUID) -> list[PlayerTeamHistory]` | All team history entries |

### GameService

Extends BaseService with game-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_with_box_score` | `(game_id: UUID) -> Game \| None` | Game with all stats eager loaded |
| `get_filtered` | `(filter_params: GameFilter, skip=0, limit=50) -> tuple[list[Game], int]` | Filtered games with total |
| `get_by_team` | `(team_id: UUID, season_id?: UUID, skip=0, limit=50) -> tuple[list[Game], int]` | Games for a team |
| `get_by_external_id` | `(source: str, external_id: str) -> Game \| None` | Find by external provider ID |
| `create_game` | `(data: GameCreate) -> Game` | Create from Pydantic schema |
| `update_game` | `(game_id: UUID, data: GameUpdate) -> Game \| None` | Update from schema |
| `update_score` | `(game_id: UUID, home_score: int, away_score: int, status?) -> Game \| None` | Update score and status |

### PlayerGameStatsService

Extends BaseService with player game statistics operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_game` | `(game_id: UUID) -> list[PlayerGameStats]` | All player stats for a game |
| `get_by_game_and_team` | `(game_id: UUID, team_id: UUID) -> list[PlayerGameStats]` | Player stats for one team in game |
| `get_player_game_log` | `(player_id: UUID, season_id?: UUID, skip=0, limit=50) -> tuple[list, int]` | Player's game log with context |
| `get_by_player_and_game` | `(player_id: UUID, game_id: UUID) -> PlayerGameStats \| None` | Stats for specific player/game |
| `create_stats` | `(data: dict) -> PlayerGameStats` | Create stats entry |
| `bulk_create` | `(stats_list: list[dict]) -> list[PlayerGameStats]` | Bulk create for sync efficiency |
| `update_stats` | `(game_id: UUID, player_id: UUID, data: dict) -> PlayerGameStats \| None` | Update stats |

### TeamGameStatsService

Service for team game statistics (uses composite primary key, not BaseService).

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_game` | `(game_id: UUID) -> list[TeamGameStats]` | Both team stats for a game |
| `get_by_team_and_game` | `(team_id: UUID, game_id: UUID) -> TeamGameStats \| None` | Stats for specific team/game |
| `get_team_game_history` | `(team_id: UUID, season_id?: UUID, skip=0, limit=50) -> tuple[list, int]` | Team's game history |
| `create_stats` | `(data: dict) -> TeamGameStats` | Create team stats entry |
| `update_stats` | `(game_id: UUID, team_id: UUID, data: dict) -> TeamGameStats \| None` | Update stats |
| `calculate_from_player_stats` | `(game_id: UUID, team_id: UUID) -> TeamGameStats \| None` | Aggregate team stats from players |

### PlayByPlayService

Extends BaseService with play-by-play event operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_game` | `(game_id: UUID, filter_params?: PlayByPlayFilter) -> list[PlayByPlayEvent]` | Events for a game |
| `get_with_related` | `(event_id: UUID) -> PlayByPlayEvent \| None` | Event with linked events loaded |
| `create_event` | `(data: dict) -> PlayByPlayEvent` | Create single event |
| `update_event` | `(event_id: UUID, data: dict) -> PlayByPlayEvent \| None` | Update event |
| `link_events` | `(event_id: UUID, related_event_ids: list[UUID]) -> None` | Link events together |
| `unlink_events` | `(event_id: UUID, related_event_ids: list[UUID]) -> None` | Remove event links |
| `get_related_events` | `(event_id: UUID) -> list[PlayByPlayEvent]` | Events this event links to |
| `get_events_linking_to` | `(event_id: UUID) -> list[PlayByPlayEvent]` | Events that link to this event |
| `bulk_create_with_links` | `(events: list[dict], links: list[tuple]) -> list[PlayByPlayEvent]` | Bulk create with relationships |
| `get_shot_chart_data` | `(game_id: UUID, team_id?: UUID, player_id?: UUID) -> list[PlayByPlayEvent]` | Shot events with coordinates |
| `get_events_by_type` | `(game_id: UUID, event_type: str, event_subtype?: str) -> list[PlayByPlayEvent]` | Events of specific type |
| `count_by_game` | `(game_id: UUID) -> int` | Total events in game |
| `delete_by_game` | `(game_id: UUID) -> int` | Delete all events for game |

### StatsCalculationService

Calculates aggregated statistics from game-level data.

| Method | Signature | Description |
|--------|-----------|-------------|
| `calculate_player_season_stats` | `(player_id, team_id, season_id) -> PlayerSeasonStats \| None` | Calculate season stats for player/team |
| `recalculate_all_for_season` | `(season_id: UUID) -> int` | Recalculate stats for all players in season |
| `recalculate_for_player` | `(player_id: UUID) -> int` | Recalculate all season stats for player |
| `calculate_percentage` | `(made: int, attempted: int) -> float` | Static: shooting percentage |
| `calculate_true_shooting_pct` | `(points, fga, fta) -> float` | Static: TS% formula |
| `calculate_effective_fg_pct` | `(fgm, three_pm, fga) -> float` | Static: eFG% formula |
| `calculate_assist_turnover_ratio` | `(assists, turnovers) -> float` | Static: AST/TO ratio |
| `calculate_average` | `(total: int, games: int) -> float` | Static: per-game average |

**Formulas:**
- **TS%**: `PTS / (2 * (FGA + 0.44 * FTA)) * 100`
- **eFG%**: `(FGM + 0.5 * 3PM) / FGA * 100`
- **AST/TO**: `AST / TO` (returns assists if 0 turnovers)

### PlayerSeasonStatsService

Extends BaseService with player season statistics operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_player_season` | `(player_id, season_id) -> list[PlayerSeasonStats]` | Stats for player in season (multi-team) |
| `get_player_career` | `(player_id: UUID) -> list[PlayerSeasonStats]` | All career season stats |
| `get_league_leaders` | `(season_id, category, limit=10, min_games=1) -> list[PlayerSeasonStats]` | League leaders by category |
| `get_team_season_stats` | `(team_id, season_id) -> list[PlayerSeasonStats]` | All player stats for team |

**Leader Categories:** `points`, `rebounds`, `assists`, `steals`, `blocks`, `field_goal_pct`, `three_point_pct`, `free_throw_pct`, `true_shooting_pct`, `efficiency`, `effective_field_goal_pct`

### SyncLogService

Extends BaseService with sync operation tracking.

| Method | Signature | Description |
|--------|-----------|-------------|
| `start_sync` | `(source, entity_type, season_id?, game_id?) -> SyncLog` | Start sync with STARTED status |
| `complete_sync` | `(sync_id, processed, created, updated, skipped=0) -> SyncLog \| None` | Mark as COMPLETED |
| `partial_sync` | `(sync_id, processed, created, updated, skipped, error_msg?) -> SyncLog \| None` | Mark as PARTIAL |
| `fail_sync` | `(sync_id, error_message, error_details?) -> SyncLog \| None` | Mark as FAILED |
| `get_latest_by_source` | `(source, entity_type) -> SyncLog \| None` | Most recent sync |
| `get_latest_successful` | `(source, entity_type, season_id?) -> SyncLog \| None` | Most recent successful sync |
| `get_filtered` | `(filter_params: SyncLogFilter) -> tuple[list[SyncLog], int]` | Filter sync logs |
| `get_running_syncs` | `(source?: str) -> list[SyncLog]` | Currently running syncs |

### AnalyticsService

Orchestration service for advanced basketball analytics. Composes existing services for clutch time, situational analysis, opponent splits, lineup analysis, and on/off court statistics.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_clutch_events` | `(game_id: UUID, clutch_filter?: ClutchFilter) -> list[PlayByPlayEvent]` | Get PBP events during clutch time |
| `get_situational_shots` | `(game_id: UUID, player_id?: UUID, team_id?: UUID, filter?: SituationalFilter) -> list[PlayByPlayEvent]` | Get shots filtered by situational attributes |
| `get_situational_stats` | `(game_ids: list[UUID], player_id: UUID, filter?: SituationalFilter) -> dict` | Aggregate shooting stats for situational filter |
| `get_games_vs_opponent` | `(team_id: UUID, opponent_id: UUID, season_id?: UUID) -> list[Game]` | Get games between two teams |
| `get_player_stats_vs_opponent` | `(player_id: UUID, opponent_id: UUID, season_id?: UUID) -> list[PlayerGameStats]` | Player stats against specific opponent |
| `get_player_home_away_split` | `(player_id: UUID, season_id: UUID) -> dict` | Home vs away performance split |
| `get_player_on_off_stats` | `(player_id: UUID, game_id: UUID) -> dict` | On/off court stats for single game |
| `get_player_on_off_for_season` | `(player_id: UUID, season_id: UUID) -> dict` | On/off stats aggregated for season |
| `get_lineup_stats` | `(player_ids: list[UUID], game_id: UUID) -> dict` | Stats when all players on court together |
| `get_lineup_stats_for_season` | `(player_ids: list[UUID], season_id: UUID) -> dict` | Lineup stats aggregated for season |
| `get_best_lineups` | `(team_id: UUID, game_id: UUID, lineup_size?: int, min_minutes?: float) -> list[dict]` | Best performing lineups by plus/minus |
| `get_events_by_time` | `(game_id: UUID, time_filter: TimeFilter, event_type?: EventType) -> list[PlayByPlayEvent]` | Events filtered by time/period criteria |
| `get_player_stats_by_quarter` | `(player_id: UUID, game_id: UUID) -> dict` | Player stats broken down by quarter |

**Internal/Helper Methods:**

| Method | Description |
|--------|-------------|
| `_is_clutch_moment` | Check if a specific game moment qualifies as clutch |
| `_get_game_score_at_time` | Calculate running score at a specific point in game |
| `_parse_clock_to_seconds` | Convert clock string (MM:SS) to seconds |
| `_event_matches_situational_filter` | Check if event matches situational criteria |
| `_get_starters_for_game` | Get starting lineup player IDs |
| `_build_on_court_timeline` | Build timeline of on/off court stints |
| `_is_player_on_at_time` | Check if player was on court at specific time |
| `_get_lineup_on_court_intervals` | Get time intervals when all players on court together |

## Filter Parameters

### TeamFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `league_id` | UUID \| None | Filter by teams in seasons of this league |
| `season_id` | UUID \| None | Filter by teams in this specific season |
| `country` | str \| None | Exact match on team country |
| `search` | str \| None | Case-insensitive search in name or short_name |

**Search behavior:** Matches if search term appears anywhere in `name` OR `short_name`.

```python
# Example: Find all USA teams with "Lakers" in name
filters = TeamFilter(country="USA", search="Lakers")
teams, total = team_service.get_filtered(filters)
```

### PlayerFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `team_id` | UUID \| None | Filter by players on this team (any season) |
| `season_id` | UUID \| None | Filter by players active in this season |
| `position` | str \| None | Exact match on player position |
| `nationality` | str \| None | Exact match on player nationality |
| `search` | str \| None | Case-insensitive search in first_name or last_name |

**Search behavior:** Matches if search term appears anywhere in `first_name` OR `last_name`.

```python
# Example: Find all point guards from USA
filters = PlayerFilter(position="PG", nationality="USA")
players, total = player_service.get_filtered(filters)

# Example: Search for players with "curry" in name
filters = PlayerFilter(search="curry")
players, total = player_service.get_filtered(filters)
```

### GameFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `season_id` | UUID \| None | Filter by games in this season |
| `team_id` | UUID \| None | Filter by team (home or away) |
| `start_date` | date \| None | Filter games on or after this date |
| `end_date` | date \| None | Filter games on or before this date |
| `status` | GameStatus \| None | Filter by game status (SCHEDULED, LIVE, FINAL, etc.) |

```python
# Example: Get all completed Lakers games in January 2024
from datetime import date
from src.schemas.game import GameFilter, GameStatus

filters = GameFilter(
    team_id=lakers_uuid,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    status=GameStatus.FINAL
)
games, total = game_service.get_filtered(filters)
```

### PlayByPlayFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | int \| None | Filter by period number (1-4, 5+ for OT) |
| `event_type` | str \| None | Filter by event type (SHOT, REBOUND, etc.) |
| `player_id` | UUID \| None | Filter by player UUID |
| `team_id` | UUID \| None | Filter by team UUID |

```python
# Example: Get all 4th quarter shots by a specific player
from src.schemas.play_by_play import PlayByPlayFilter

filters = PlayByPlayFilter(
    period=4,
    event_type="SHOT",
    player_id=curry_uuid
)
events = play_by_play_service.get_by_game(game_id, filters)
```

## Usage Examples

### Basic CRUD Operations

```python
from src.services import LeagueService
from src.schemas import LeagueCreate, LeagueUpdate

service = LeagueService(db)

# Create
league = service.create_league(
    LeagueCreate(name="NBA", code="NBA", country="USA")
)

# Read
league = service.get_by_id(league_id)
all_leagues = service.get_all(skip=0, limit=10)
total = service.count()

# Update
updated = service.update_league(
    league_id,
    LeagueUpdate(name="National Basketball Association")
)

# Delete
success = service.delete(league_id)
```

### Using in API Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import get_db
from src.services import PlayerService
from src.schemas import PlayerFilter, PlayerListResponse, PlayerResponse

router = APIRouter()

@router.get("/players", response_model=PlayerListResponse)
def list_players(
    position: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = PlayerService(db)
    filters = PlayerFilter(position=position, search=search)
    players, total = service.get_filtered(filters, skip=skip, limit=limit)

    return PlayerListResponse(
        items=[PlayerResponse.model_validate(p) for p in players],
        total=total
    )

@router.get("/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: UUID, db: Session = Depends(get_db)):
    service = PlayerService(db)
    player = service.get_by_id(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found"
        )

    return PlayerResponse.model_validate(player)
```

### Working with External IDs

```python
from src.services import PlayerService, TeamService

player_service = PlayerService(db)
team_service = TeamService(db)

# Find entities by external provider ID
lebron = player_service.get_by_external_id("nba", "2544")
lakers = team_service.get_by_external_id("nba", "1610612747")

# Useful for data synchronization from external APIs
if lebron is None:
    lebron = player_service.create_player(
        PlayerCreate(
            first_name="LeBron",
            last_name="James",
            external_ids={"nba": "2544"}
        )
    )
```

### Managing Team Rosters

```python
from src.services import PlayerService, TeamService

player_service = PlayerService(db)
team_service = TeamService(db)

# Add player to team for a season
player_service.add_to_team(
    player_id=lebron.id,
    team_id=lakers.id,
    season_id=current_season.id,
    jersey_number=23,
    position="SF"
)

# Get team roster
roster = team_service.get_roster(lakers.id, current_season.id)
for entry in roster:
    print(f"#{entry.jersey_number} {entry.player.full_name} ({entry.position})")

# Get player's team history
history = player_service.get_team_history(lebron.id)
for entry in history:
    print(f"{entry.season.name}: {entry.team.name}")
```

### Calculating Aggregated Stats

```python
from src.services import StatsCalculationService, PlayerSeasonStatsService

calc_service = StatsCalculationService(db)
stats_service = PlayerSeasonStatsService(db)

# Calculate season stats for a player
stats = calc_service.calculate_player_season_stats(
    player_id=lebron.id,
    team_id=lakers.id,
    season_id=current_season.id
)
if stats:
    print(f"PPG: {stats.avg_points}, TS%: {stats.true_shooting_pct}")

# Recalculate all stats for a season (e.g., after sync)
count = calc_service.recalculate_all_for_season(current_season.id)
print(f"Recalculated {count} player-team stats")

# Get league leaders
leaders = stats_service.get_league_leaders(
    season_id=current_season.id,
    category="points",
    limit=10,
    min_games=20
)
for i, leader in enumerate(leaders, 1):
    print(f"{i}. {leader.player.first_name}: {leader.avg_points} PPG")

# Use static calculation methods directly
ts_pct = StatsCalculationService.calculate_true_shooting_pct(
    points=30, fga=18, fta=8
)
print(f"True Shooting: {ts_pct}%")
```

### Tracking Sync Operations

```python
from src.services import SyncLogService

sync_service = SyncLogService(db)

# Start a sync operation
sync = sync_service.start_sync(
    source="winner",
    entity_type="games",
    season_id=current_season.id
)

try:
    # ... perform sync operations ...
    records_created = 50
    records_updated = 10

    # Mark as completed
    sync_service.complete_sync(
        sync_id=sync.id,
        records_processed=60,
        records_created=records_created,
        records_updated=records_updated,
        records_skipped=0
    )
except Exception as e:
    # Mark as failed
    sync_service.fail_sync(
        sync_id=sync.id,
        error_message=str(e),
        error_details={"traceback": "..."}
    )

# Check for running syncs before starting new one
running = sync_service.get_running_syncs(source="winner")
if running:
    print(f"Warning: {len(running)} syncs already in progress")

# Get last successful sync for incremental updates
last_sync = sync_service.get_latest_successful("winner", "games")
if last_sync:
    print(f"Last sync: {last_sync.completed_at}")
```

### Advanced Analytics with AnalyticsService

```python
from src.services import AnalyticsService
from src.schemas import ClutchFilter, SituationalFilter, TimeFilter

analytics = AnalyticsService(db)

# Clutch Analysis - NBA standard (last 5 min Q4/OT, within 5 pts)
clutch_events = analytics.get_clutch_events(game_id)

# "Super clutch" (last 2 min, within 3 pts)
filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)
super_clutch = analytics.get_clutch_events(game_id, filter)

# Situational Filtering - fast break shots
filter = SituationalFilter(fast_break=True)
fast_break_shots = analytics.get_situational_shots(
    game_id, player_id=lebron_id, filter=filter
)

# Aggregate fast break stats across multiple games
stats = analytics.get_situational_stats(
    game_ids=[game1.id, game2.id],
    player_id=lebron_id,
    filter=SituationalFilter(fast_break=True)
)
print(f"Fast break FG%: {stats['pct']:.1%}")

# Opponent Splits - games vs specific opponent
games = analytics.get_games_vs_opponent(
    team_id=lakers_id, opponent_id=celtics_id, season_id=season_id
)

# Player stats vs specific opponent
stats = analytics.get_player_stats_vs_opponent(
    player_id=lebron_id, opponent_id=celtics_id
)
avg_pts = sum(s.points for s in stats) / len(stats) if stats else 0

# Home/Away Split
split = analytics.get_player_home_away_split(lebron_id, season_id)
print(f"Home PPG: {split['home']['avg_points']:.1f}")
print(f"Away PPG: {split['away']['avg_points']:.1f}")

# On/Off Court Analysis - single game
on_off = analytics.get_player_on_off_stats(lebron_id, game_id)
print(f"On court: +{on_off['on']['plus_minus']} in {on_off['on']['minutes']} min")
print(f"Off court: +{on_off['off']['plus_minus']} in {on_off['off']['minutes']} min")

# On/Off for entire season
season_on_off = analytics.get_player_on_off_for_season(lebron_id, season_id)
print(f"Season on: +{season_on_off['on']['plus_minus']} in {season_on_off['on']['games']} games")

# Lineup Analysis - 2-man combo
stats = analytics.get_lineup_stats([lebron_id, ad_id], game_id)
print(f"LeBron+AD: +{stats['plus_minus']} in {stats['minutes']} min")

# Best 5-man lineups in a game
lineups = analytics.get_best_lineups(
    team_id=lakers_id, game_id=game_id, lineup_size=5, min_minutes=2.0
)
for i, lineup in enumerate(lineups[:3]):
    print(f"#{i+1}: +{lineup['plus_minus']} in {lineup['minutes']} min")

# Lineup stats for season
season_lineup = analytics.get_lineup_stats_for_season(
    [lebron_id, ad_id], season_id
)
print(f"Season: +{season_lineup['plus_minus']} in {season_lineup['games']} games")

# Time-Based Filtering - 4th quarter only
time_filter = TimeFilter(period=4)
q4_events = analytics.get_events_by_time(game_id, time_filter)

# Exclude garbage time (margin > 20)
time_filter = TimeFilter(exclude_garbage_time=True)
competitive_events = analytics.get_events_by_time(game_id, time_filter)

# Player stats by quarter
quarter_stats = analytics.get_player_stats_by_quarter(lebron_id, game_id)
for q, stats in quarter_stats.items():
    print(f"Q{q}: {stats['points']} pts, {stats['fgm']}/{stats['fga']} FG")
```

## Design Principles

1. **Single Responsibility**: Each service handles one entity/domain
2. **No HTTP Logic**: Services don't know about HTTP (no status codes, headers, etc.)
3. **Transaction Boundaries**: Services manage their own database transactions
4. **Testability**: Services can be tested with mock database sessions
5. **Generic Base**: Common CRUD operations in BaseService reduce duplication
6. **Type Safety**: Full type hints with generics for IDE support

## Dependencies

- **Internal**: `src/core/`, `src/models/`, `src/schemas/`
- **External**: `sqlalchemy`

## Related Documentation

- [Models](../models/README.md) - Database models
- [Schemas](../schemas/README.md) - Request/response validation
- [API Layer](../api/README.md) - HTTP endpoint definitions
