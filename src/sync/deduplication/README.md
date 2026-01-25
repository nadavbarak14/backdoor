# Deduplication

## Purpose

This module provides functionality for deduplicating players and teams across multiple data sources (Winner League, Euroleague). When the same entity appears in different leagues, their `external_ids` are merged into a single database record.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `normalizer.py` | Name normalization utilities for matching across sources |
| `team_matcher.py` | Team matching and merging across data sources |
| `player.py` | Player deduplication using multi-tier matching strategy |

## Matching Strategies

### Player Deduplication

Players are matched using a multi-tier strategy:

1. **External ID Match** - Exact match by source-specific ID (highest confidence)
2. **Team Roster Match** - Same team, same normalized name
3. **Global Bio Match** - Name + birth_date or height (for transferred players)

```
┌─────────────────────────────────────────────────────────────┐
│                   Player Matching Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  New Player Data ──► Check external_id ──► Found? ──► Return │
│        │                                      │              │
│        │                                      ▼ No           │
│        │              Check team roster ──► Found? ──► Merge │
│        │                                      │              │
│        │                                      ▼ No           │
│        │              Global name+bio  ──► Found? ──► Merge  │
│        │                                      │              │
│        │                                      ▼ No           │
│        └──────────────────────────────────► Create New       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Team Deduplication

Teams are matched by:

1. **External ID** - Exact match for known mappings
2. **Normalized Name** - Case-insensitive, accent-normalized comparison

## Usage

### Name Normalization

```python
from src.sync.deduplication import normalize_name, names_match, parse_full_name

# Normalize a name (lowercase, remove accents, normalize whitespace)
normalized = normalize_name("Luka Dončić")  # "luka doncic"

# Compare two names
if names_match("Dončić", "DONCIC"):
    print("Same player!")

# Parse full name into components
first, last = parse_full_name("Scottie Wilbekin")  # ("Scottie", "Wilbekin")
```

### Team Matching

```python
from src.sync.deduplication import TeamMatcher
from src.sync.types import RawTeam

matcher = TeamMatcher(db_session)

# Find or create a team (handles deduplication automatically)
team = matcher.find_or_create_team(
    source="winner",
    external_id="team-123",
    team_data=RawTeam(
        external_id="team-123",
        name="Maccabi Tel Aviv",
        short_name="MTA"
    )
)

# Later, when importing from Euroleague, same team is matched
team = matcher.find_or_create_team(
    source="euroleague",
    external_id="MAT",
    team_data=RawTeam(
        external_id="MAT",
        name="Maccabi Playtika Tel Aviv",
        short_name="MTA"
    )
)

# Team now has both external_ids
print(team.external_ids)  # {'winner': 'team-123', 'euroleague': 'MAT'}
```

### Player Deduplication

```python
from src.sync.deduplication import PlayerDeduplicator
from src.sync.types import RawPlayerInfo
from datetime import date

dedup = PlayerDeduplicator(db_session)

# Import player from Winner League
player = dedup.find_or_create_player(
    source="winner",
    external_id="player-123",
    player_data=RawPlayerInfo(
        external_id="player-123",
        first_name="Scottie",
        last_name="Wilbekin",
        birth_date=date(1993, 7, 19),
        height_cm=185
    ),
    team_id=maccabi.id
)

# Later, same player from Euroleague (matched by name + birth_date)
player = dedup.find_or_create_player(
    source="euroleague",
    external_id="PWB",
    player_data=RawPlayerInfo(
        external_id="PWB",
        first_name="Scottie",
        last_name="Wilbekin",
        birth_date=date(1993, 7, 19)
    ),
    team_id=maccabi.id
)

# Same player record with merged external_ids
print(player.external_ids)  # {'winner': 'player-123', 'euroleague': 'PWB'}
```

### Finding Potential Duplicates

```python
# Find players that might be duplicates for manual review
duplicates = dedup.find_potential_duplicates()

for p1, p2 in duplicates:
    print(f"Possible duplicate: {p1.full_name} vs {p2.full_name}")
    print(f"  P1 external_ids: {p1.external_ids}")
    print(f"  P2 external_ids: {p2.external_ids}")
```

## Name Normalization Details

The normalizer handles common variations:

| Original | Normalized |
|----------|------------|
| `Luka Dončić` | `luka doncic` |
| `LEBRON JAMES` | `lebron james` |
| `  John   Doe  ` | `john doe` |
| `José García` | `jose garcia` |

## Dependencies

- **Internal**: `src/models/player`, `src/models/team`, `src/sync/types`
- **External**: `unicodedata` (stdlib), `sqlalchemy`

## Related Documentation

- [Sync README](../README.md)
- [Player Model](../../models/README.md)
- [Services](../../services/README.md)
