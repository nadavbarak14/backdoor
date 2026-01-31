# Canonical Entities

## Purpose

Canonical entity dataclasses represent the standardized format for basketball data. All league adapters convert their raw API data to these entities before storage.

## Contents

| File | Entity | Description |
|------|--------|-------------|
| `player.py` | `CanonicalPlayer` | Player with positions, height, nationality |
| `team.py` | `CanonicalTeam` | Team with name, city, country |
| `game.py` | `CanonicalGame` | Game with teams, date, score, status |
| `stats.py` | `CanonicalPlayerStats` | Box score statistics |
| `pbp.py` | `CanonicalPBPEvent` | Play-by-play event |
| `season.py` | `CanonicalSeason` | Season with dates |

## Usage

```python
from src.sync.canonical.entities import (
    CanonicalPlayer,
    CanonicalTeam,
    CanonicalGame,
    CanonicalPlayerStats,
    CanonicalPBPEvent,
    CanonicalSeason,
)
from src.sync.canonical import Position, Height, Nationality

player = CanonicalPlayer(
    external_id="123",
    source="euroleague",
    first_name="LeBron",
    last_name="James",
    positions=[Position.SMALL_FORWARD, Position.POWER_FORWARD],
    height=Height(cm=206),
    birth_date=date(1984, 12, 30),
    nationality=Nationality(code="USA"),
    jersey_number="23",
)

print(player.full_name)  # "LeBron James"
print(player.primary_position)  # Position.SMALL_FORWARD
print(player.height_cm)  # 206
```

## Design Principles

1. **All fields have explicit types** - No `Any` types
2. **Optional fields use `| None`** - Clear null handling
3. **Properties for derived values** - `full_name`, `primary_position`, etc.
4. **Minutes always in seconds** - `minutes_seconds` field avoids format ambiguity
5. **External IDs are strings** - Consistent across all sources

## Dependencies

- Uses types from `src/sync/canonical/types/`
