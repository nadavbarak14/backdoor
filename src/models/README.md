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
