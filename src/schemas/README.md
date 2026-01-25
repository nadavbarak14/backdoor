# Schemas

## Purpose

Pydantic models for API request validation and response serialization. Schemas define the contract between the API and its clients, ensuring data integrity and type safety.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for all schemas |
| `base.py` | Shared schema utilities (OrmBase, PaginatedResponse) |
| `league.py` | League and Season request/response schemas |
| `team.py` | Team request/response schemas |
| `player.py` | Player request/response schemas |
| `game.py` | Game, GameStatus, EventType, and BoxScore schemas |
| `stats.py` | PlayerGameStats and TeamGameStats schemas with computed fields |
| `play_by_play.py` | Play-by-play event schemas |
| `player_stats.py` | PlayerSeasonStats, CareerStats, and LeagueLeaders schemas |
| `sync.py` | SyncLog and SyncStatus schemas for data synchronization |
| `analytics.py` | Analytics filter schemas (ClutchFilter, SituationalFilter, OpponentFilter, TimeFilter) |

## Naming Conventions

| Suffix | Purpose | HTTP Methods | Example |
|--------|---------|--------------|---------|
| `Create` | Request body for creation | POST | `PlayerCreate` |
| `Update` | Request body for updates | PUT, PATCH | `PlayerUpdate` |
| `Response` | Single item response | GET, POST | `PlayerResponse` |
| `ListResponse` | List of items with total | GET (list) | `PlayerListResponse` |
| `Filter` | Query parameters | GET (list) | `PlayerFilter` |

## Schema Reference

### Base Utilities (`base.py`)

| Schema | Description |
|--------|-------------|
| `OrmBase` | Base model with `from_attributes=True` for ORM compatibility |
| `PaginatedResponse[T]` | Generic paginated response wrapper |

### League Schemas (`league.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `LeagueCreate` | Create league | name, code, country |
| `LeagueUpdate` | Update league | name?, code?, country? |
| `LeagueResponse` | League output | id, name, code, country, season_count, timestamps |
| `LeagueListResponse` | League list | items, total |
| `SeasonCreate` | Create season | league_id, name, start_date, end_date, is_current? |
| `SeasonUpdate` | Update season | name?, start_date?, end_date?, is_current? |
| `SeasonResponse` | Season output | id, league_id, name, dates, is_current, timestamps |
| `SeasonFilter` | Filter seasons | league_id?, is_current? |

### Team Schemas (`team.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `TeamCreate` | Create team | name, short_name, city, country, external_ids? |
| `TeamUpdate` | Update team | name?, short_name?, city?, country?, external_ids? |
| `TeamResponse` | Team output | id, name, short_name, city, country, external_ids, timestamps |
| `TeamListResponse` | Team list | items, total |
| `TeamFilter` | Filter teams | league_id?, season_id?, country?, search? |
| `TeamRosterPlayerResponse` | Player in roster | id, names, jersey_number?, position? |
| `TeamRosterResponse` | Team roster | team, season_id, season_name, players |

### Player Schemas (`player.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `PlayerCreate` | Create player | first_name, last_name, birth_date?, nationality?, height_cm?, position?, external_ids? |
| `PlayerUpdate` | Update player | first_name?, last_name?, birth_date?, nationality?, height_cm?, position?, external_ids? |
| `PlayerResponse` | Player output | id, names, full_name, birth_date, nationality, height_cm, position, external_ids, timestamps |
| `PlayerListResponse` | Player list | items, total |
| `PlayerFilter` | Filter players | team_id?, season_id?, position?, nationality?, search? |
| `PlayerTeamHistoryResponse` | Team history entry | team_id, team_name, season_id, season_name, jersey_number?, position? |
| `PlayerWithHistoryResponse` | Player + history | all PlayerResponse fields + team_history |

### Game Schemas (`game.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `GameStatus` | Enum | SCHEDULED, LIVE, FINAL, POSTPONED, CANCELLED |
| `EventType` | Enum | SHOT, ASSIST, REBOUND, TURNOVER, STEAL, BLOCK, FOUL, FREE_THROW, SUBSTITUTION, TIMEOUT, JUMP_BALL, VIOLATION, PERIOD_START, PERIOD_END |
| `GameCreate` | Create game | season_id, home_team_id, away_team_id, game_date, status?, venue?, external_ids? |
| `GameUpdate` | Update game | game_date?, status?, home_score?, away_score?, venue?, attendance?, external_ids? |
| `GameResponse` | Game output | id, season_id, team_ids, team_names, game_date, status, scores, venue, attendance, external_ids, timestamps |
| `GameListResponse` | Game list | items, total |
| `GameFilter` | Filter games | season_id?, team_id?, start_date?, end_date?, status? |
| `TeamBoxScoreResponse` | Team box score | team_id, team_name, is_home, all stats with computed percentages |
| `PlayerBoxScoreResponse` | Player box score | player_id, player_name, team_id, is_starter, minutes_display, all stats with computed percentages |
| `GameWithBoxScoreResponse` | Game + box scores | all GameResponse fields + home/away team stats + home/away players |

### Stats Schemas (`stats.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `PlayerGameStatsResponse` | Per-game player stats | id, game_id, player_id, player_name, team_id, all box score fields + computed percentages + minutes_display |
| `PlayerGameStatsWithGameResponse` | Player stats + game context | all PlayerGameStatsResponse fields + game_date, opponent info, is_home, scores, computed result (W/L) |
| `PlayerGameLogResponse` | Player game log | items, total |
| `TeamGameStatsResponse` | Per-game team stats | game_id, team_id, team_name, is_home, all stats + team-only stats + computed percentages |
| `TeamGameSummaryResponse` | Team game summary | game_id, game_date, opponent info, is_home, scores, venue, computed result (W/L) |
| `TeamGameHistoryResponse` | Team game history | items, total |

### Play-by-Play Schemas (`play_by_play.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `PlayByPlayEventResponse` | Single PBP event | id, game_id, event_number, period, clock, event_type, event_subtype, player info, team info, success, coords, attributes, description, related_event_ids |
| `PlayByPlayResponse` | Game PBP data | game_id, events, total_events |
| `PlayByPlayFilter` | Filter PBP events | period?, event_type?, player_id?, team_id? |

### Player Stats Schemas (`player_stats.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `StatsCategory` | Enum | POINTS, REBOUNDS, ASSISTS, STEALS, BLOCKS, FIELD_GOAL_PCT, THREE_POINT_PCT, FREE_THROW_PCT, MINUTES, EFFICIENCY |
| `PlayerSeasonStatsResponse` | Season stats | id, player/team/season info, totals, averages, percentages (0-100), advanced stats, last_calculated, computed avg_minutes_display |
| `PlayerCareerStatsResponse` | Career stats | player_id, player_name, career totals, career averages, seasons list |
| `LeagueLeaderEntry` | Leader entry | rank, player_id, player_name, team_id, team_name, value, games_played |
| `LeagueLeadersResponse` | Leaders list | category, season_id, season_name, min_games, leaders |
| `LeagueLeadersFilter` | Filter leaders | season_id, category?, limit? (1-100, default 10), min_games? (default 0) |

### Sync Schemas (`sync.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `SyncStatus` | Enum | STARTED, COMPLETED, FAILED, PARTIAL |
| `SyncLogResponse` | Sync log entry | id, source, entity_type, status, season_id?, season_name?, game_id?, record counts, error fields, timestamps, computed duration_seconds |
| `SyncLogListResponse` | Sync log list | items, total |
| `SyncLogFilter` | Filter sync logs | source?, entity_type?, status?, season_id?, start_date?, end_date?, page (default 1), page_size (1-100, default 20) |

### Analytics Schemas (`analytics.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `ClutchFilter` | Configure clutch time criteria | time_remaining_seconds (default 300), score_margin (default 5), include_overtime (default True), min_period (default 4) |
| `SituationalFilter` | Filter PBP events by attributes | fast_break?, second_chance?, contested?, shot_type? |
| `OpponentFilter` | Filter by opponent/home/away | opponent_team_id?, home_only (default False), away_only (default False) |
| `TimeFilter` | Filter by time/period criteria | period?, periods?, exclude_garbage_time (default False), min_time_remaining?, max_time_remaining? |

**ClutchFilter defaults** match NBA standard clutch time definition:
- Last 5 minutes of 4th quarter or overtime
- Score within 5 points

**SituationalFilter shot_type options:** `PULL_UP`, `CATCH_AND_SHOOT`, `POST_UP`

**OpponentFilter note:** `home_only` and `away_only` are mutually exclusive.

**TimeFilter note:** `period` and `periods` are mutually exclusive. Use `periods` for multiple periods (e.g., `[1, 2]` for first half).

## Validation Rules

### String Length Constraints

| Schema | Field | Min | Max |
|--------|-------|-----|-----|
| LeagueCreate | name | 1 | 100 |
| LeagueCreate | code | 1 | 20 |
| LeagueCreate | country | 1 | 100 |
| SeasonCreate | name | 1 | 50 |
| TeamCreate | name | 1 | 100 |
| TeamCreate | short_name | 1 | 20 |
| TeamCreate | city | 1 | 100 |
| TeamCreate | country | 1 | 100 |
| PlayerCreate | first_name | 1 | 100 |
| PlayerCreate | last_name | 1 | 100 |
| PlayerCreate | nationality | - | 100 |
| PlayerCreate | position | - | 20 |
| PlayerFilter | search | 1 | - |
| TeamFilter | search | 1 | - |
| GameCreate | venue | - | 200 |
| GameUpdate | venue | - | 200 |

### Numeric Constraints

| Schema | Field | Min | Max | Description |
|--------|-------|-----|-----|-------------|
| PlayerCreate | height_cm | 100 | 250 | Height in centimeters |
| GameUpdate | home_score | 0 | - | Non-negative score |
| GameUpdate | away_score | 0 | - | Non-negative score |
| GameUpdate | attendance | 0 | - | Non-negative attendance |
| PlayByPlayFilter | period | 1 | - | Period number (1+ for OT) |

### Default Values

| Schema | Field | Default |
|--------|-------|---------|
| SeasonCreate | is_current | `False` |
| TeamCreate | external_ids | `None` |
| PlayerCreate | external_ids | `None` |
| PlayerResponse | external_ids | `{}` |
| TeamResponse | external_ids | `{}` |
| LeagueResponse | season_count | `0` |
| GameCreate | status | `GameStatus.SCHEDULED` |
| GameCreate | external_ids | `None` |
| GameResponse | external_ids | `{}` |

### Computed Fields

Stats schemas include computed fields that are automatically calculated:

| Schema | Field | Computation |
|--------|-------|-------------|
| PlayerGameStatsResponse | minutes_display | `f"{mins}:{secs:02d}"` from minutes_played (seconds) |
| PlayerGameStatsResponse | field_goal_pct | `(made / attempted) * 100` (0.0 if no attempts) |
| PlayerGameStatsResponse | two_point_pct | 2-point percentage |
| PlayerGameStatsResponse | three_point_pct | 3-point percentage |
| PlayerGameStatsResponse | free_throw_pct | Free throw percentage |
| PlayerGameStatsWithGameResponse | result | `"W"` if team_score > opponent_score else `"L"` |
| TeamGameStatsResponse | field_goal_pct, two_point_pct, three_point_pct, free_throw_pct | Same as player |
| TeamGameSummaryResponse | result | Same as PlayerGameStatsWithGameResponse |
| PlayerSeasonStatsResponse | avg_minutes_display | `f"{mins}:{secs:02d}"` from avg_minutes (seconds) |
| SyncLogResponse | duration_seconds | `(completed_at - started_at).total_seconds()` (None if still running) |

## Usage Examples

### Request Validation (Create)

```python
from src.schemas import PlayerCreate

# FastAPI automatically validates request body
@router.post("/players", response_model=PlayerResponse)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    service = PlayerService(db)
    return service.create_player(data)

# Valid request
data = PlayerCreate(
    first_name="LeBron",
    last_name="James",
    birth_date=date(1984, 12, 30),
    nationality="USA",
    height_cm=206,
    position="SF",
    external_ids={"nba": "2544"}
)

# Invalid request - raises ValidationError
PlayerCreate(first_name="", last_name="James")  # first_name too short
PlayerCreate(first_name="LeBron", last_name="James", height_cm=300)  # height too large
```

### Request Validation (Update)

```python
from src.schemas import PlayerUpdate

# All fields are optional for partial updates
@router.patch("/players/{player_id}", response_model=PlayerResponse)
def update_player(
    player_id: UUID,
    data: PlayerUpdate,
    db: Session = Depends(get_db)
):
    service = PlayerService(db)
    return service.update_player(player_id, data)

# Only update position
data = PlayerUpdate(position="PF")
```

### Response Serialization

```python
from src.schemas import PlayerResponse, PlayerWithHistoryResponse

# Convert ORM object to response schema
player_orm = service.get_by_id(player_id)
response = PlayerResponse.model_validate(player_orm)

# With nested team history
player_with_history = service.get_with_history(player_id)
response = PlayerWithHistoryResponse(
    id=player.id,
    first_name=player.first_name,
    last_name=player.last_name,
    full_name=player.full_name,
    # ... other fields
    team_history=[
        PlayerTeamHistoryResponse(
            team_id=h.team_id,
            team_name=h.team.name,
            season_id=h.season_id,
            season_name=h.season.name,
            jersey_number=h.jersey_number,
            position=h.position
        )
        for h in player.team_histories
    ]
)
```

### Query Parameter Filtering

```python
from src.schemas import PlayerFilter

@router.get("/players", response_model=PlayerListResponse)
def list_players(
    team_id: UUID | None = Query(None),
    season_id: UUID | None = Query(None),
    position: str | None = Query(None),
    nationality: str | None = Query(None),
    search: str | None = Query(None, min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    filters = PlayerFilter(
        team_id=team_id,
        season_id=season_id,
        position=position,
        nationality=nationality,
        search=search
    )
    service = PlayerService(db)
    players, total = service.get_filtered(filters, skip=skip, limit=limit)
    return PlayerListResponse(
        items=[PlayerResponse.model_validate(p) for p in players],
        total=total
    )
```

### List Response Structure

```python
from src.schemas import PlayerListResponse, PlayerResponse

# Response format for list endpoints
response = PlayerListResponse(
    items=[
        PlayerResponse(id=..., first_name="LeBron", ...),
        PlayerResponse(id=..., first_name="Stephen", ...),
    ],
    total=150  # Total count (not just items in this page)
)

# JSON output
{
    "items": [
        {"id": "...", "first_name": "LeBron", ...},
        {"id": "...", "first_name": "Stephen", ...}
    ],
    "total": 150
}
```

## Dependencies

- **Internal**: None (schemas are independent)
- **External**: `pydantic` v2

## Related Documentation

- [API Documentation](../../docs/api/README.md)
- [Models](../models/README.md)
- [Services](../services/README.md)
