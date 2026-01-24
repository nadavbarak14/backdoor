# Models

## Purpose

SQLAlchemy ORM models for the Basketball Analytics Platform database. This module provides the declarative base, reusable mixins, and all entity models that represent database tables.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports for Base, mixins, and all entity models |
| `base.py` | DeclarativeBase, UUIDMixin, and TimestampMixin |
| `league.py` | League and Season models |
| `team.py` | Team and TeamSeason models |
| `player.py` | Player and PlayerTeamHistory models |
| `game.py` | Game, PlayerGameStats, and TeamGameStats models |
| `play_by_play.py` | PlayByPlayEvent and PlayByPlayEventLink models |
| `stats.py` | PlayerSeasonStats model for pre-computed season aggregates |
| `sync.py` | SyncLog model for tracking data synchronization operations |

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│     League      │       │     Season      │
├─────────────────┤       ├─────────────────┤
│ id (UUID, PK)   │       │ id (UUID, PK)   │
│ name            │──1:N──│ league_id (FK)  │
│ code (unique)   │       │ name            │
│ country         │       │ start_date      │
│ created_at      │       │ end_date        │
│ updated_at      │       │ is_current      │
└─────────────────┘       │ created_at      │
                          │ updated_at      │
                          └────────┬────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│     TeamSeason      │  │ PlayerTeamHistory   │  │                     │
├─────────────────────┤  ├─────────────────────┤  │                     │
│ team_id (FK, PK)    │  │ id (UUID, PK)       │  │                     │
│ season_id (FK, PK)  │  │ player_id (FK)      │  │                     │
│ created_at          │  │ team_id (FK)        │  │                     │
│ updated_at          │  │ season_id (FK)      │  │                     │
└──────────┬──────────┘  │ jersey_number       │  │                     │
           │             │ position            │  │                     │
           │             │ created_at          │  │                     │
           │             │ updated_at          │  │                     │
           │             └──────────┬──────────┘  │                     │
           │                        │             │                     │
           ▼                        ▼             │                     │
┌─────────────────────┐  ┌─────────────────────┐  │                     │
│       Team          │  │      Player         │  │                     │
├─────────────────────┤  ├─────────────────────┤  │                     │
│ id (UUID, PK)       │  │ id (UUID, PK)       │  │                     │
│ name                │  │ first_name          │  │                     │
│ short_name          │  │ last_name           │  │                     │
│ city                │  │ birth_date          │  │                     │
│ country             │  │ nationality         │  │                     │
│ external_ids (JSON) │  │ height_cm           │  │                     │
│ created_at          │  │ position            │  │                     │
│ updated_at          │  │ external_ids (JSON) │  │                     │
└─────────────────────┘  │ created_at          │  │                     │
                         │ updated_at          │  │                     │
                         └─────────────────────┘  │                     │
```

## Models Reference

### League

Represents a basketball league (e.g., NBA, EuroLeague).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `name` | String(100) | NOT NULL | League full name |
| `code` | String(20) | NOT NULL, UNIQUE | Short code (e.g., "NBA") |
| `country` | String(100) | NOT NULL | Country or region |
| `created_at` | DateTime | NOT NULL, server default | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, auto-update | Last modification |

**Relationships:**
- `seasons`: One-to-many with Season (cascade delete)

```python
from src.models import League

league = League(name="National Basketball Association", code="NBA", country="USA")
```

### Season

Represents a season within a league.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `league_id` | UUID | FK → leagues.id, NOT NULL | Parent league |
| `name` | String(50) | NOT NULL | Season name (e.g., "2023-24") |
| `start_date` | Date | NOT NULL | Season start date |
| `end_date` | Date | NOT NULL | Season end date |
| `is_current` | Boolean | NOT NULL, default=False | Is this the current season? |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Unique Constraint:** `(league_id, name)` - One season name per league

**Relationships:**
- `league`: Many-to-one with League
- `team_seasons`: One-to-many with TeamSeason
- `player_team_histories`: One-to-many with PlayerTeamHistory

### Team

Represents a basketball team.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `name` | String(100) | NOT NULL | Full team name |
| `short_name` | String(20) | NOT NULL | Abbreviated name (e.g., "LAL") |
| `city` | String(100) | NOT NULL | Team's city |
| `country` | String(100) | NOT NULL | Team's country |
| `external_ids` | JSON | default={} | External provider IDs |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Relationships:**
- `team_seasons`: One-to-many with TeamSeason
- `player_team_histories`: One-to-many with PlayerTeamHistory

### TeamSeason

Junction table linking teams to seasons (composite primary key).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `team_id` | UUID | PK, FK → teams.id | Team reference |
| `season_id` | UUID | PK, FK → seasons.id | Season reference |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Note:** Uses composite primary key `(team_id, season_id)`.

### Player

Represents a basketball player.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `first_name` | String(100) | NOT NULL | First name |
| `last_name` | String(100) | NOT NULL | Last name |
| `birth_date` | Date | NULL | Date of birth |
| `nationality` | String(100) | NULL | Player nationality |
| `height_cm` | Integer | NULL | Height in centimeters |
| `position` | String(20) | NULL | Position (PG, SG, SF, PF, C) |
| `external_ids` | JSON | default={} | External provider IDs |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Computed Property:**
- `full_name`: Returns `"{first_name} {last_name}"`

**Relationships:**
- `team_histories`: One-to-many with PlayerTeamHistory

### PlayerTeamHistory

Tracks a player's tenure with a team for a specific season.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `player_id` | UUID | FK → players.id, NOT NULL | Player reference |
| `team_id` | UUID | FK → teams.id, NOT NULL | Team reference |
| `season_id` | UUID | FK → seasons.id, NOT NULL | Season reference |
| `jersey_number` | Integer | NULL | Jersey number for this stint |
| `position` | String(20) | NULL | Position played on this team |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Unique Constraint:** `(player_id, team_id, season_id)` - One entry per player-team-season

### Game

Represents a basketball game between two teams.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `season_id` | UUID | FK → seasons.id, NOT NULL | Season this game belongs to |
| `home_team_id` | UUID | FK → teams.id, NOT NULL | Home team |
| `away_team_id` | UUID | FK → teams.id, NOT NULL | Away team |
| `game_date` | DateTime | NOT NULL, indexed | Game date and time |
| `status` | String(20) | NOT NULL, default="SCHEDULED" | SCHEDULED, LIVE, FINAL, POSTPONED |
| `home_score` | Integer | NULL | Home team final score |
| `away_score` | Integer | NULL | Away team final score |
| `venue` | String(200) | NULL | Arena/venue name |
| `attendance` | Integer | NULL | Number of spectators |
| `external_ids` | JSON | default={} | External provider IDs |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Relationships:**
- `season`: Many-to-one with Season
- `home_team`: Many-to-one with Team
- `away_team`: Many-to-one with Team
- `player_game_stats`: One-to-many with PlayerGameStats
- `team_game_stats`: One-to-many with TeamGameStats
- `play_by_play_events`: One-to-many with PlayByPlayEvent

### PlayerGameStats

Per-player box score statistics for a game.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `game_id` | UUID | FK → games.id, NOT NULL | Game reference |
| `player_id` | UUID | FK → players.id, NOT NULL | Player reference |
| `team_id` | UUID | FK → teams.id, NOT NULL | Team the player played for |
| `minutes_played` | Integer | NOT NULL, default=0 | Playing time in seconds |
| `is_starter` | Boolean | NOT NULL, default=False | In starting lineup |
| `points` | Integer | NOT NULL, default=0 | Points scored |
| `field_goals_made` | Integer | NOT NULL, default=0 | FG made |
| `field_goals_attempted` | Integer | NOT NULL, default=0 | FG attempted |
| `two_pointers_made` | Integer | NOT NULL, default=0 | 2PT made |
| `two_pointers_attempted` | Integer | NOT NULL, default=0 | 2PT attempted |
| `three_pointers_made` | Integer | NOT NULL, default=0 | 3PT made |
| `three_pointers_attempted` | Integer | NOT NULL, default=0 | 3PT attempted |
| `free_throws_made` | Integer | NOT NULL, default=0 | FT made |
| `free_throws_attempted` | Integer | NOT NULL, default=0 | FT attempted |
| `offensive_rebounds` | Integer | NOT NULL, default=0 | Offensive rebounds |
| `defensive_rebounds` | Integer | NOT NULL, default=0 | Defensive rebounds |
| `total_rebounds` | Integer | NOT NULL, default=0 | Total rebounds |
| `assists` | Integer | NOT NULL, default=0 | Assists |
| `turnovers` | Integer | NOT NULL, default=0 | Turnovers |
| `steals` | Integer | NOT NULL, default=0 | Steals |
| `blocks` | Integer | NOT NULL, default=0 | Blocks |
| `personal_fouls` | Integer | NOT NULL, default=0 | Personal fouls |
| `plus_minus` | Integer | NOT NULL, default=0 | Plus/minus |
| `efficiency` | Integer | NOT NULL, default=0 | Efficiency rating |
| `extra_stats` | JSON | default={} | League-specific stats |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Unique Constraint:** `(game_id, player_id)` - One stat line per player per game

### TeamGameStats

Team-level aggregated statistics for a game (composite primary key).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `game_id` | UUID | PK, FK → games.id | Game reference |
| `team_id` | UUID | PK, FK → teams.id | Team reference |
| `is_home` | Boolean | NOT NULL | Is this the home team |
| `points` | Integer | NOT NULL, default=0 | Total points |
| `field_goals_made` | Integer | NOT NULL, default=0 | FG made |
| `field_goals_attempted` | Integer | NOT NULL, default=0 | FG attempted |
| (... all standard stats ...) | | | |
| `fast_break_points` | Integer | NOT NULL, default=0 | Fast break points |
| `points_in_paint` | Integer | NOT NULL, default=0 | Points in the paint |
| `second_chance_points` | Integer | NOT NULL, default=0 | Second chance points |
| `bench_points` | Integer | NOT NULL, default=0 | Bench points |
| `biggest_lead` | Integer | NOT NULL, default=0 | Biggest lead |
| `time_leading` | Integer | NOT NULL, default=0 | Time leading in seconds |
| `extra_stats` | JSON | default={} | League-specific stats |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Note:** Uses composite primary key `(game_id, team_id)`.

### PlayByPlayEvent

Individual play-by-play event in a game.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `game_id` | UUID | FK → games.id, NOT NULL | Game reference |
| `event_number` | Integer | NOT NULL | Sequence in game |
| `period` | Integer | NOT NULL | Period/quarter |
| `clock` | String(20) | NOT NULL | Game clock (e.g., "10:30") |
| `event_type` | String(50) | NOT NULL | SHOT, REBOUND, ASSIST, etc. |
| `event_subtype` | String(50) | NULL | 2PT, 3PT, OFFENSIVE, etc. |
| `player_id` | UUID | FK → players.id, NULL | Player involved |
| `team_id` | UUID | FK → teams.id, NOT NULL | Team involved |
| `success` | Boolean | NULL | For shots: made or missed |
| `coord_x` | Float | NULL | Shot X coordinate |
| `coord_y` | Float | NULL | Shot Y coordinate |
| `attributes` | JSON | default={} | Extended attributes |
| `description` | String(500) | NULL | Human-readable description |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Unique Constraint:** `(game_id, event_number)` - One event number per game

**Relationships:**
- `game`: Many-to-one with Game
- `player`: Many-to-one with Player (nullable)
- `team`: Many-to-one with Team
- `related_events`: Many-to-many via PlayByPlayEventLink (events this links to)
- `linked_from`: Many-to-many via PlayByPlayEventLink (events that link to this)

### PlayByPlayEventLink

Association table linking related play-by-play events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `event_id` | UUID | PK, FK → play_by_play_events.id | Source event |
| `related_event_id` | UUID | PK, FK → play_by_play_events.id | Related event |

**Example (And-1 Play):**
```
Event 1: SHOT (2PT, made, player=Lessort)
Event 2: ASSIST (player=Wilbekin) → links to [1]
Event 3: FOUL (shooting, player=Opponent) → links to [1]
Event 4: FREE_THROW (made, player=Lessort) → links to [1, 3]
```

### PlayerSeasonStats

Pre-computed aggregated player statistics for a season (per team).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `player_id` | UUID | FK → players.id, NOT NULL | Player reference |
| `team_id` | UUID | FK → teams.id, NOT NULL | Team reference |
| `season_id` | UUID | FK → seasons.id, NOT NULL | Season reference |
| `games_played` | Integer | NOT NULL, default=0 | Number of games played |
| `games_started` | Integer | NOT NULL, default=0 | Number of games started |
| `total_minutes` | Integer | NOT NULL, default=0 | Total playing time in seconds |
| `total_points` | Integer | NOT NULL, default=0 | Total points scored |
| `total_field_goals_made` | Integer | NOT NULL, default=0 | Total FG made |
| `total_field_goals_attempted` | Integer | NOT NULL, default=0 | Total FG attempted |
| `total_two_pointers_made` | Integer | NOT NULL, default=0 | Total 2PT made |
| `total_two_pointers_attempted` | Integer | NOT NULL, default=0 | Total 2PT attempted |
| `total_three_pointers_made` | Integer | NOT NULL, default=0 | Total 3PT made |
| `total_three_pointers_attempted` | Integer | NOT NULL, default=0 | Total 3PT attempted |
| `total_free_throws_made` | Integer | NOT NULL, default=0 | Total FT made |
| `total_free_throws_attempted` | Integer | NOT NULL, default=0 | Total FT attempted |
| `total_offensive_rebounds` | Integer | NOT NULL, default=0 | Total offensive rebounds |
| `total_defensive_rebounds` | Integer | NOT NULL, default=0 | Total defensive rebounds |
| `total_rebounds` | Integer | NOT NULL, default=0 | Total rebounds |
| `total_assists` | Integer | NOT NULL, default=0 | Total assists |
| `total_turnovers` | Integer | NOT NULL, default=0 | Total turnovers |
| `total_steals` | Integer | NOT NULL, default=0 | Total steals |
| `total_blocks` | Integer | NOT NULL, default=0 | Total blocks |
| `total_personal_fouls` | Integer | NOT NULL, default=0 | Total personal fouls |
| `total_plus_minus` | Integer | NOT NULL, default=0 | Cumulative plus/minus |
| `avg_minutes` | Float | NOT NULL, default=0.0 | Average minutes per game (seconds) |
| `avg_points` | Float | NOT NULL, default=0.0 | Average points per game |
| `avg_rebounds` | Float | NOT NULL, default=0.0 | Average rebounds per game |
| `avg_assists` | Float | NOT NULL, default=0.0 | Average assists per game |
| `avg_turnovers` | Float | NOT NULL, default=0.0 | Average turnovers per game |
| `avg_steals` | Float | NOT NULL, default=0.0 | Average steals per game |
| `avg_blocks` | Float | NOT NULL, default=0.0 | Average blocks per game |
| `field_goal_pct` | Float | NULL | Field goal percentage (0.0-1.0) |
| `two_point_pct` | Float | NULL | Two-point percentage (0.0-1.0) |
| `three_point_pct` | Float | NULL | Three-point percentage (0.0-1.0) |
| `free_throw_pct` | Float | NULL | Free throw percentage (0.0-1.0) |
| `true_shooting_pct` | Float | NULL | True shooting percentage (TS%) |
| `effective_field_goal_pct` | Float | NULL | Effective field goal pct (eFG%) |
| `assist_turnover_ratio` | Float | NULL | Assist to turnover ratio |
| `last_calculated` | DateTime | NOT NULL, server default | When stats were last computed |
| `created_at` | DateTime | NOT NULL | Creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification |

**Unique Constraint:** `(player_id, team_id, season_id)` - One entry per player-team-season combination

**Note:** If a player is traded mid-season, they will have multiple rows (one per team).

**Relationships:**
- `player`: Many-to-one with Player
- `team`: Many-to-one with Team
- `season`: Many-to-one with Season

### SyncLog

Tracks data synchronization operations from external sources.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, auto-generated | Unique identifier |
| `source` | String(50) | NOT NULL | External data source (e.g., "winner", "euroleague") |
| `entity_type` | String(50) | NOT NULL | Type of entity (e.g., "games", "players", "stats", "pbp") |
| `status` | String(20) | NOT NULL, default="STARTED" | STARTED, COMPLETED, FAILED, PARTIAL |
| `season_id` | UUID | FK → seasons.id, NULL | Optional season context |
| `game_id` | UUID | FK → games.id, NULL | Optional game context |
| `records_processed` | Integer | NOT NULL, default=0 | Total records processed |
| `records_created` | Integer | NOT NULL, default=0 | New records created |
| `records_updated` | Integer | NOT NULL, default=0 | Existing records updated |
| `records_skipped` | Integer | NOT NULL, default=0 | Records skipped |
| `error_message` | Text | NULL | Human-readable error message |
| `error_details` | JSON | NULL | Detailed error information |
| `started_at` | DateTime | NOT NULL, server default | Sync start timestamp |
| `completed_at` | DateTime | NULL | Sync completion timestamp |

**Index:** `(source, entity_type, started_at)` - Efficient lookup of sync history

**Relationships:**
- `season`: Many-to-one with Season (SET NULL on delete)
- `game`: Many-to-one with Game (SET NULL on delete)

## JSON Fields (external_ids)

The `external_ids` field on Team and Player stores external data source identifiers:

```python
# Team external_ids example
team.external_ids = {
    "nba": "1610612747",       # NBA.com team ID
    "espn": "13",              # ESPN team ID
    "basketball_ref": "LAL"    # Basketball Reference code
}

# Player external_ids example
player.external_ids = {
    "nba": "2544",             # NBA.com player ID
    "espn": "1966",            # ESPN player ID
}
```

## Usage Examples

### Creating a Complete Hierarchy

```python
from datetime import date
from src.models import League, Season, Team, Player, PlayerTeamHistory

# Create league
nba = League(name="NBA", code="NBA", country="USA")
db.add(nba)
db.commit()

# Create season
season = Season(
    league_id=nba.id,
    name="2023-24",
    start_date=date(2023, 10, 24),
    end_date=date(2024, 6, 17),
    is_current=True
)
db.add(season)
db.commit()

# Create team
lakers = Team(
    name="Los Angeles Lakers",
    short_name="LAL",
    city="Los Angeles",
    country="USA",
    external_ids={"nba": "1610612747"}
)
db.add(lakers)
db.commit()

# Create player
lebron = Player(
    first_name="LeBron",
    last_name="James",
    birth_date=date(1984, 12, 30),
    nationality="USA",
    height_cm=206,
    position="SF",
    external_ids={"nba": "2544"}
)
db.add(lebron)
db.commit()

# Add player to team for season
history = PlayerTeamHistory(
    player_id=lebron.id,
    team_id=lakers.id,
    season_id=season.id,
    jersey_number=23,
    position="SF"
)
db.add(history)
db.commit()
```

### Querying with Relationships

```python
# Get player with all team history (eager loaded)
from sqlalchemy.orm import joinedload

player = db.query(Player).options(
    joinedload(Player.team_histories)
    .joinedload(PlayerTeamHistory.team),
    joinedload(Player.team_histories)
    .joinedload(PlayerTeamHistory.season)
).filter(Player.id == player_id).first()

for history in player.team_histories:
    print(f"{history.team.name} ({history.season.name})")
```

## Dependencies

### Internal Dependencies
- `src.core.database` - Engine and session management

### External Libraries
- `sqlalchemy` - ORM and database toolkit

## Related Documentation

- [Database Connection](../core/README.md)
- [Schemas](../schemas/README.md)
- [Services](../services/README.md)
- [Architecture](../../docs/architecture.md)
