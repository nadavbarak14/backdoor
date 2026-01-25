# AnalyticsService

## Overview

AnalyticsService is the orchestration service for advanced basketball analytics in the Basketball Analytics Platform. It composes existing domain services to provide higher-level analysis capabilities including:

- **Clutch Time Analysis**: Filter events by clutch time criteria (NBA standard: last 5 min Q4/OT, within 5 points)
- **Situational Analysis**: Filter shots by game context (fast break, second chance, contested)
- **Opponent Splits**: Player/team performance against specific opponents
- **Home/Away Splits**: Performance breakdown by game location
- **On/Off Court Analysis**: Team performance with/without a player on court
- **Lineup Analysis**: Statistics for player combinations (2-5 man lineups)
- **Time-Based Analysis**: Quarter-by-quarter breakdowns, garbage time exclusion

## Filter Schemas

### ClutchFilter

Configure clutch time criteria. NBA standard defaults are used if not specified.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `time_remaining_seconds` | int | 300 | Max seconds remaining in period (5 min) |
| `score_margin` | int | 5 | Max point difference to qualify |
| `include_overtime` | bool | True | Include overtime periods |
| `min_period` | int | 4 | Minimum period (4 = 4th quarter) |

```python
from src.schemas import ClutchFilter

# NBA standard clutch time
filter = ClutchFilter()  # 300 sec, 5 pts, include OT

# "Super clutch" - stricter criteria
filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)

# Regulation only (no overtime)
filter = ClutchFilter(include_overtime=False)
```

### SituationalFilter

Filter play-by-play events by situational attributes. All fields are optional; only non-None fields are applied.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `fast_break` | bool \| None | None | Filter for fast break opportunities |
| `second_chance` | bool \| None | None | Filter for offensive rebound opportunities |
| `contested` | bool \| None | None | Filter for contested/uncontested shots |
| `shot_type` | str \| None | None | Shot classification: PULL_UP, CATCH_AND_SHOOT, POST_UP |

```python
from src.schemas import SituationalFilter

# Fast break shots only
filter = SituationalFilter(fast_break=True)

# Contested catch-and-shoot attempts
filter = SituationalFilter(contested=True, shot_type="CATCH_AND_SHOOT")

# Uncontested shots, excluding fast breaks
filter = SituationalFilter(fast_break=False, contested=False)
```

### OpponentFilter

Filter by opponent team and/or home/away status.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `opponent_team_id` | UUID \| None | None | Opponent team to filter against |
| `home_only` | bool | False | Only include home games |
| `away_only` | bool | False | Only include away games |

Note: `home_only` and `away_only` are mutually exclusive.

```python
from src.schemas import OpponentFilter

# Games vs specific opponent
filter = OpponentFilter(opponent_team_id=celtics_id)

# Home games only
filter = OpponentFilter(home_only=True)

# Away games vs Celtics
filter = OpponentFilter(opponent_team_id=celtics_id, away_only=True)
```

### TimeFilter

Filter events by time/period criteria.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `period` | int \| None | None | Single period to filter (1-10) |
| `periods` | list[int] \| None | None | Multiple periods to include |
| `exclude_garbage_time` | bool | False | Exclude events when margin > 20 |
| `min_time_remaining` | int \| None | None | Min seconds remaining in period |
| `max_time_remaining` | int \| None | None | Max seconds remaining in period |

Note: `period` and `periods` are mutually exclusive.

```python
from src.schemas import TimeFilter

# 4th quarter only
filter = TimeFilter(period=4)

# First half (Q1 and Q2)
filter = TimeFilter(periods=[1, 2])

# Exclude garbage time (blowout situations)
filter = TimeFilter(exclude_garbage_time=True)

# Last 2 minutes of any period
filter = TimeFilter(max_time_remaining=120)
```

## Method Reference

### Clutch Analysis

#### `get_clutch_events(game_id, clutch_filter?) -> list[PlayByPlayEvent]`

Get play-by-play events that occurred during clutch time.

```python
service = AnalyticsService(db)

# NBA standard clutch events
events = service.get_clutch_events(game_id)

# Custom clutch criteria
filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)
events = service.get_clutch_events(game_id, filter)

# Analyze clutch shooting
made = sum(1 for e in events if e.event_type == "SHOT" and e.success)
attempted = sum(1 for e in events if e.event_type == "SHOT")
print(f"Clutch FG: {made}/{attempted}")
```

### Situational Analysis

#### `get_situational_shots(game_id, player_id?, team_id?, filter?) -> list[PlayByPlayEvent]`

Get shot events filtered by situational attributes.

```python
# All fast break shots in a game
filter = SituationalFilter(fast_break=True)
shots = service.get_situational_shots(game_id, filter=filter)

# Player's contested shots
filter = SituationalFilter(contested=True)
shots = service.get_situational_shots(
    game_id, player_id=player_id, filter=filter
)
```

#### `get_situational_stats(game_ids, player_id, filter?) -> dict`

Aggregate shooting stats for situational shots across multiple games.

Returns: `{"made": int, "attempted": int, "pct": float}`

```python
filter = SituationalFilter(fast_break=True)
stats = service.get_situational_stats(
    game_ids=[g.id for g in season_games],
    player_id=player_id,
    filter=filter
)
print(f"Fast break: {stats['made']}/{stats['attempted']} ({stats['pct']:.1%})")
```

### Opponent Analysis

#### `get_games_vs_opponent(team_id, opponent_id, season_id?) -> list[Game]`

Get all games between two teams.

```python
# Lakers vs Celtics this season
games = service.get_games_vs_opponent(
    team_id=lakers_id,
    opponent_id=celtics_id,
    season_id=season_id
)
print(f"Head-to-head: {len(games)} games")
```

#### `get_player_stats_vs_opponent(player_id, opponent_id, season_id?) -> list[PlayerGameStats]`

Get player's game stats against a specific opponent.

```python
stats = service.get_player_stats_vs_opponent(
    player_id=lebron_id,
    opponent_id=celtics_id
)
avg_pts = sum(s.points for s in stats) / len(stats) if stats else 0
print(f"LeBron vs Celtics: {avg_pts:.1f} PPG over {len(stats)} games")
```

#### `get_player_home_away_split(player_id, season_id) -> dict`

Get player's home vs away performance split.

Returns:
```python
{
    "home": {
        "games": int,
        "points": int,
        "rebounds": int,
        "assists": int,
        "avg_points": float,
        "avg_rebounds": float,
        "avg_assists": float
    },
    "away": {...}  # Same structure
}
```

```python
split = service.get_player_home_away_split(player_id, season_id)
print(f"Home: {split['home']['avg_points']:.1f} PPG ({split['home']['games']} G)")
print(f"Away: {split['away']['avg_points']:.1f} PPG ({split['away']['games']} G)")
```

### On/Off Court Analysis

#### `get_player_on_off_stats(player_id, game_id) -> dict`

Calculate player on/off court stats for a single game.

Returns:
```python
{
    "on": {
        "team_pts": int,
        "opp_pts": int,
        "plus_minus": int,
        "minutes": float
    },
    "off": {...}  # Same structure
}
```

```python
on_off = service.get_player_on_off_stats(player_id, game_id)
print(f"On court: {on_off['on']['team_pts']}-{on_off['on']['opp_pts']} "
      f"(+{on_off['on']['plus_minus']}) in {on_off['on']['minutes']} min")
```

#### `get_player_on_off_for_season(player_id, season_id) -> dict`

Aggregate on/off stats across entire season.

Returns same structure as single game, plus `games` count.

```python
season = service.get_player_on_off_for_season(player_id, season_id)
print(f"Season on-court: +{season['on']['plus_minus']} in {season['on']['games']} games")
```

### Lineup Analysis

#### `get_lineup_stats(player_ids, game_id) -> dict`

Calculate stats when ALL specified players are on court together.

Returns: `{"team_pts": int, "opp_pts": int, "plus_minus": int, "minutes": float}`

```python
# Two-man combo
stats = service.get_lineup_stats([lebron_id, ad_id], game_id)
print(f"LeBron+AD: +{stats['plus_minus']} in {stats['minutes']} min")

# Five-man lineup
stats = service.get_lineup_stats(
    [pg_id, sg_id, sf_id, pf_id, c_id],
    game_id
)
```

#### `get_lineup_stats_for_season(player_ids, season_id) -> dict`

Aggregate lineup stats across all season games.

Returns same structure plus `games` count.

```python
stats = service.get_lineup_stats_for_season([lebron_id, ad_id], season_id)
print(f"Season: +{stats['plus_minus']} in {stats['minutes']} min ({stats['games']} G)")
```

#### `get_best_lineups(team_id, game_id, lineup_size=5, min_minutes=2.0) -> list[dict]`

Get best performing lineups sorted by plus/minus.

Returns list of:
```python
{
    "player_ids": list[UUID],
    "team_pts": int,
    "opp_pts": int,
    "plus_minus": int,
    "minutes": float
}
```

```python
# Best 5-man lineups
lineups = service.get_best_lineups(team_id, game_id, lineup_size=5)
for i, lineup in enumerate(lineups[:3]):
    print(f"#{i+1}: +{lineup['plus_minus']} in {lineup['minutes']} min")

# Best 2-man combos
duos = service.get_best_lineups(team_id, game_id, lineup_size=2, min_minutes=5.0)
```

### Time-Based Analysis

#### `get_events_by_time(game_id, time_filter, event_type?) -> list[PlayByPlayEvent]`

Get events filtered by time/period criteria.

```python
from src.schemas.game import EventType

# 4th quarter shots
filter = TimeFilter(period=4)
q4_shots = service.get_events_by_time(game_id, filter, EventType.SHOT)

# Competitive time only (no garbage time)
filter = TimeFilter(exclude_garbage_time=True)
competitive = service.get_events_by_time(game_id, filter)
```

#### `get_player_stats_by_quarter(player_id, game_id) -> dict`

Get player stats broken down by quarter.

Returns:
```python
{
    1: {"points": int, "fgm": int, "fga": int, "fg3m": int, "fg3a": int,
        "ftm": int, "fta": int, "rebounds": int, "assists": int,
        "steals": int, "blocks": int, "turnovers": int},
    2: {...},
    3: {...},
    4: {...},
    "OT": {...}  # Only present if overtime occurred
}
```

```python
quarters = service.get_player_stats_by_quarter(player_id, game_id)
for q, stats in quarters.items():
    print(f"Q{q}: {stats['points']} pts ({stats['fgm']}/{stats['fga']} FG)")
```

## Examples

### Complete Clutch Analysis

```python
from src.services import AnalyticsService
from src.schemas import ClutchFilter

service = AnalyticsService(db)

# Get clutch events
events = service.get_clutch_events(game_id)

# Analyze by player
player_clutch = {}
for event in events:
    if event.player_id and event.event_type == "SHOT":
        if event.player_id not in player_clutch:
            player_clutch[event.player_id] = {"made": 0, "attempted": 0}
        player_clutch[event.player_id]["attempted"] += 1
        if event.success:
            player_clutch[event.player_id]["made"] += 1

for player_id, stats in player_clutch.items():
    pct = stats["made"] / stats["attempted"] if stats["attempted"] else 0
    print(f"Player {player_id}: {stats['made']}/{stats['attempted']} ({pct:.1%})")
```

### Season-Long Opponent Analysis

```python
from src.services import AnalyticsService

service = AnalyticsService(db)

# Get all games vs division rivals
rivals = [celtics_id, nets_id, sixers_id, raptors_id]
rival_stats = {}

for rival_id in rivals:
    stats = service.get_player_stats_vs_opponent(
        player_id=player_id,
        opponent_id=rival_id,
        season_id=season_id
    )
    if stats:
        avg_pts = sum(s.points for s in stats) / len(stats)
        rival_stats[rival_id] = {"games": len(stats), "ppg": avg_pts}

print("Division rival performance:")
for rival_id, data in rival_stats.items():
    print(f"  vs {rival_id}: {data['ppg']:.1f} PPG ({data['games']} G)")
```

### Finding Best Lineup Combinations

```python
from src.services import AnalyticsService

service = AnalyticsService(db)

# Find best 2-man combos that played 10+ minutes
for game_id in season_games[:10]:
    duos = service.get_best_lineups(
        team_id=team_id,
        game_id=game_id,
        lineup_size=2,
        min_minutes=10.0
    )
    if duos:
        best = duos[0]
        print(f"Game {game_id}: Best duo +{best['plus_minus']} ({best['minutes']} min)")
```

## Related API Endpoints

The following API endpoints (when implemented) would use AnalyticsService:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/games/{id}/clutch-events` | GET | Get clutch time events |
| `/api/v1/players/{id}/situational-stats` | GET | Player situational shooting |
| `/api/v1/players/{id}/splits/home-away` | GET | Home/away performance split |
| `/api/v1/players/{id}/splits/opponent/{opp_id}` | GET | Stats vs specific opponent |
| `/api/v1/players/{id}/on-off` | GET | On/off court analysis |
| `/api/v1/teams/{id}/lineups` | GET | Best lineup combinations |

## Related Documentation

- [src/services/README.md](../../src/services/README.md) - Full service reference
- [src/schemas/analytics.py](../../src/schemas/analytics.py) - Filter schema source
- [src/services/analytics.py](../../src/services/analytics.py) - Service source
