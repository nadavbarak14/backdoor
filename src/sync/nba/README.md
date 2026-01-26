# NBA Sync Module

## Purpose

Provides data synchronization capabilities for NBA basketball data from the NBA Stats API (stats.nba.com). This module implements the `BaseLeagueAdapter` interface to fetch seasons, teams, game schedules, box scores, and play-by-play data.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Module exports and documentation |
| `adapter.py` | `NBAAdapter` - implements `BaseLeagueAdapter` for NBA data |
| `client.py` | `NBAClient` - wraps nba_api package with rate limiting and retries |
| `config.py` | `NBAConfig` - configuration settings (rate limits, seasons, timeouts) |
| `exceptions.py` | NBA-specific exceptions (`NBAAPIError`, `NBARateLimitError`, etc.) |
| `mapper.py` | `NBAMapper` - transforms NBA API data to `RawTypes` |

## Usage

### Basic Usage

```python
from src.sync.nba import NBAAdapter, NBAClient, NBAMapper, NBAConfig

# Create components with defaults
config = NBAConfig()
client = NBAClient(config)
mapper = NBAMapper()

# Create adapter
adapter = NBAAdapter(client, mapper, config)

# Fetch seasons
seasons = await adapter.get_seasons()
# Returns: [RawSeason(external_id='NBA2023-24', ...), ...]

# Fetch teams
teams = await adapter.get_teams("NBA2023-24")
# Returns: [RawTeam(external_id='1610612737', name='Atlanta Hawks', ...), ...]

# Fetch schedule
games = await adapter.get_schedule("NBA2023-24")
# Returns: [RawGame(external_id='0022300001', ...), ...]

# Fetch box score
boxscore = await adapter.get_game_boxscore("0022300001")
# Returns: RawBoxScore with home_players and away_players

# Fetch play-by-play
pbp = await adapter.get_game_pbp("0022300001")
# Returns: [RawPBPEvent(...), ...]
```

### Custom Configuration

```python
# Custom rate limiting and seasons
config = NBAConfig(
    requests_per_minute=10,  # More conservative rate limit
    request_timeout=60.0,    # Longer timeout
    configured_seasons=["2023-24", "2022-23", "2021-22"],
)

# With proxy (for IP rotation)
config = NBAConfig(
    proxy="http://proxy.example.com:8080"
)
```

### Error Handling

```python
from src.sync.nba.exceptions import (
    NBAAPIError,
    NBARateLimitError,
    NBANotFoundError,
)

try:
    boxscore = await adapter.get_game_boxscore(game_id)
except NBARateLimitError as e:
    # Wait and retry
    await asyncio.sleep(e.retry_after or 60)
except NBANotFoundError as e:
    # Game doesn't exist
    logger.warning(f"Game not found: {e.resource_id}")
except NBAAPIError as e:
    # General API error
    logger.error(f"NBA API error: {e}")
```

## Dependencies

### Internal
- `src.sync.adapters.base` - `BaseLeagueAdapter` interface
- `src.sync.types` - `RawSeason`, `RawTeam`, `RawGame`, `RawBoxScore`, `RawPBPEvent`

### External
- `nba_api>=1.4.1` - NBA Stats API wrapper

## Data Source

### NBA Stats API (stats.nba.com)

The NBA Stats API is an unofficial API that powers the official NBA website. Key characteristics:

- **Pros**: Official data source, comprehensive statistics, real-time updates
- **Cons**: Undocumented, rate-limited, may block aggressive scrapers

### Endpoints Used

| Endpoint | nba_api Class | Purpose |
|----------|---------------|---------|
| `/stats/leaguegamefinder` | `LeagueGameFinder` | Game schedules |
| `/stats/boxscoretraditionalv3` | `BoxScoreTraditionalV3` | Box scores |
| `/stats/playbyplayv3` | `PlayByPlayV3` | Play-by-play |
| Static data | `teams.get_teams()` | Team info |

### Rate Limiting

The NBA Stats API has undocumented rate limits. Recommendations:

- Default: 20 requests/minute (3 seconds between requests)
- Conservative: 10 requests/minute (6 seconds between requests)
- With proxy rotation: Up to 60 requests/minute

## Field Mappings

### Teams (nba_api static → RawTeam)

| NBA Field | RawTeam Field |
|-----------|---------------|
| `id` | `external_id` |
| `full_name` | `name` |
| `abbreviation` | `short_name` |

### Games (LeagueGameFinder → RawGame)

| NBA Field | RawGame Field |
|-----------|---------------|
| `GAME_ID` | `external_id` |
| `TEAM_ID` (home) | `home_team_external_id` |
| `TEAM_ID` (away) | `away_team_external_id` |
| `GAME_DATE` | `game_date` |
| `WL` | `status` (W/L = final) |
| `PTS` | `home_score`/`away_score` |

### Player Stats (BoxScoreTraditionalV3 → RawPlayerStats)

| NBA Field | RawPlayerStats Field |
|-----------|---------------------|
| `playerId` | `player_external_id` |
| `playerName` | `player_name` |
| `teamId` | `team_external_id` |
| `minutes` | `minutes_played` (converted to seconds) |
| `points` | `points` |
| `fieldGoalsMade` | `field_goals_made` |
| `fieldGoalsAttempted` | `field_goals_attempted` |
| `threePointersMade` | `three_pointers_made` |
| `threePointersAttempted` | `three_pointers_attempted` |
| `freeThrowsMade` | `free_throws_made` |
| `freeThrowsAttempted` | `free_throws_attempted` |
| `reboundsOffensive` | `offensive_rebounds` |
| `reboundsDefensive` | `defensive_rebounds` |
| `reboundsTotal` | `total_rebounds` |
| `assists` | `assists` |
| `turnovers` | `turnovers` |
| `steals` | `steals` |
| `blocks` | `blocks` |
| `foulsPersonal` | `personal_fouls` |
| `plusMinusPoints` | `plus_minus` |

### Play-by-Play (PlayByPlayV3 → RawPBPEvent)

| NBA Field | RawPBPEvent Field |
|-----------|------------------|
| `actionNumber` | `event_number` |
| `period` | `period` |
| `clock` | `clock` (converted to MM:SS) |
| `actionType` | `event_type` |
| `playerNameI` | `player_name` |
| `teamId` | `team_external_id` |
| `shotResult` | `success` (MADE/MISSED) |
| `xLegacy` | `coord_x` |
| `yLegacy` | `coord_y` |

## Related Documentation

- [Adding a New Source Guide](../../docs/sync/adding-new-source.md)
- [Field Mappings](../../docs/sync/field-mappings.md)
- [nba_api Documentation](https://github.com/swar/nba_api)
