# Entity Syncers

## Purpose

This folder contains syncer classes that handle importing individual entity types from external data sources (raw data) into the database. Each syncer leverages the deduplication infrastructure to avoid creating duplicate records.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports (PlayerSyncer, TeamSyncer, GameSyncer) |
| `player.py` | PlayerSyncer - syncs player data using PlayerDeduplicator |
| `team.py` | TeamSyncer - syncs team and roster data using TeamMatcher |
| `game.py` | GameSyncer - syncs games, box scores, and play-by-play data |

## Usage

### Basic Setup

```python
from sqlalchemy.orm import Session
from src.sync.entities import PlayerSyncer, TeamSyncer, GameSyncer
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher

# Initialize deduplication services
player_deduplicator = PlayerDeduplicator(db_session)
team_matcher = TeamMatcher(db_session)

# Initialize syncers
player_syncer = PlayerSyncer(db_session, player_deduplicator)
team_syncer = TeamSyncer(db_session, team_matcher, player_deduplicator)
game_syncer = GameSyncer(db_session, team_matcher, player_deduplicator)
```

### Syncing Players

```python
from src.sync.types import RawPlayerInfo

# Sync a player from full player info
player = player_syncer.sync_player(
    raw=RawPlayerInfo(
        external_id="p123",
        first_name="Scottie",
        last_name="Wilbekin",
        birth_date=date(1993, 7, 19),
        height_cm=183,
        position="PG"
    ),
    team_id=team.id,
    source="winner"
)

# Sync from box score stats (minimal info)
player = player_syncer.sync_player_from_stats(
    raw=raw_player_stats,
    team_id=team.id,
    source="winner"
)
```

### Syncing Teams

```python
from src.sync.types import RawTeam

# Sync a team
team = team_syncer.sync_team(
    raw=RawTeam(
        external_id="t123",
        name="Maccabi Tel Aviv",
        short_name="MTA"
    ),
    source="winner"
)

# Sync with season-specific record
team, team_season = team_syncer.sync_team_season(
    raw=raw_team,
    season_id=season.id,
    source="winner"
)

# Sync roster from box score
players = team_syncer.sync_roster(
    players=boxscore.home_players,
    team=team,
    season=season,
    source="winner"
)
```

### Syncing Games

```python
from src.sync.types import RawGame, RawBoxScore

# Sync a game
game = game_syncer.sync_game(
    raw=raw_game,
    season_id=season.id,
    source="winner"
)

# Sync box score (creates PlayerGameStats and TeamGameStats)
player_stats, team_stats = game_syncer.sync_boxscore(
    raw=raw_boxscore,
    game=game,
    source="winner"
)

# Sync play-by-play
pbp_events = game_syncer.sync_pbp(
    events=raw_pbp_events,
    game=game,
    source="winner"
)
```

## Architecture

```
External API Response
       ↓
  Raw Data Types (RawGame, RawPlayerStats, etc.)
       ↓
  Entity Syncers (GameSyncer, TeamSyncer, PlayerSyncer)
       ↓
  Deduplication Layer (PlayerDeduplicator, TeamMatcher)
       ↓
  Database Models (Game, Player, Team, PlayerGameStats)
```

## Dependencies

### Internal Dependencies
- `src.sync.deduplication` - PlayerDeduplicator, TeamMatcher
- `src.sync.types` - Raw data types
- `src.models` - Database models

### External Libraries
- SQLAlchemy - ORM and database operations

## Syncer Responsibilities

### PlayerSyncer
- Converts RawPlayerInfo to Player entities
- Handles name parsing from RawPlayerStats
- Delegates deduplication to PlayerDeduplicator

### TeamSyncer
- Converts RawTeam to Team entities
- Creates/updates TeamSeason records
- Syncs team rosters via PlayerTeamHistory
- Delegates deduplication to TeamMatcher

### GameSyncer
- Creates Game records with team references
- Creates PlayerGameStats from box score data
- Aggregates TeamGameStats from player stats
- Creates PlayByPlayEvent records with links
- Handles re-syncing by deleting old data first

## Related Documentation
- [Deduplication](../deduplication/README.md)
- [Types](../types.py)
- [Models](../../models/README.md)
