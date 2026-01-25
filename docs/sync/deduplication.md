# Player Deduplication

## Overview

When syncing data from multiple sources (Winner League, Euroleague), the same player may appear in both. The deduplication system ensures we create a single `Player` record with merged `external_ids`.

## Strategy: Multi-Tier Matching

We use a hierarchical matching strategy with three tiers:

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

### Tier 1: External ID Match (Highest Confidence)

Check if we already have this player from this source:

```python
# Look for existing player with this source's external_id
stmt = select(Player).where(
    Player.external_ids[source].as_string() == external_id
)
player = db.scalars(stmt).first()
```

If found, return the existing player immediately.

### Tier 2: Team Roster Match

If no external_id match, look for a player on the same team with matching name:

```python
# Get players currently on this team
team_players = get_players_on_team(team_id)

for player in team_players:
    if names_match(player.full_name, new_player_name):
        # Found! Merge external_ids
        player.external_ids[source] = external_id
        return player
```

**Why team-based matching?**
- Same name on the same team is almost certainly the same player
- Avoids false positives from common names across different teams
- Fast lookup with indexed team relationship

### Tier 3: Global Biographical Match

For players who may have transferred teams, match by name + biographical data:

```python
# Search all players with matching normalized name
candidates = find_players_by_normalized_name(first_name, last_name)

for player in candidates:
    if match_biographical_data(player, new_player_data):
        # Found! Merge external_ids
        player.external_ids[source] = external_id
        return player
```

Biographical matching criteria:
- **Birth date** - Exact match (most reliable)
- **Height** - Within 2cm tolerance (accounts for measurement differences)

### Create New Player

If no match found at any tier, create a new player record:

```python
player = Player(
    first_name=first_name,
    last_name=last_name,
    birth_date=birth_date,
    height_cm=height_cm,
    external_ids={source: external_id}
)
db.add(player)
```

## Name Normalization

Names are normalized before comparison to handle variations:

```python
def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison.

    - Lowercase
    - Remove accents (Dončić → Doncic)
    - Normalize whitespace
    """
    # Remove accents using unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ASCII", "ignore").decode("ASCII")

    # Lowercase and normalize whitespace
    return " ".join(ascii_name.lower().split())
```

### Examples

| Original | Normalized |
|----------|------------|
| `Luka Dončić` | `luka doncic` |
| `LEBRON JAMES` | `lebron james` |
| `José García` | `jose garcia` |
| `  John   Doe  ` | `john doe` |

## External IDs Storage

Players store external IDs as a JSONB column:

```python
class Player(Base):
    external_ids = Column(JSON, default=dict, nullable=False)
    # Example: {"winner": "p123", "euroleague": "PWB"}
```

### Merging External IDs

When a match is found, the new source's ID is added:

```python
def merge_external_id(player: Player, source: str, external_id: str) -> None:
    """Add a new external ID to an existing player."""
    if player.external_ids is None:
        player.external_ids = {}
    player.external_ids[source] = external_id
    flag_modified(player, "external_ids")
```

### Querying by External ID

```python
# Find player by any source's external ID
def get_by_external_id(source: str, external_id: str) -> Player | None:
    stmt = select(Player).where(
        Player.external_ids[source].as_string() == external_id
    )
    return db.scalars(stmt).first()
```

## Team Deduplication

Teams are deduplicated similarly:

### Matching Strategy

1. **External ID** - Exact match for known source
2. **Normalized Name** - Case-insensitive, accent-normalized comparison

```python
class TeamMatcher:
    def find_or_create_team(
        self, source: str, external_id: str, team_data: RawTeam
    ) -> Team:
        # Check external_id first
        team = self.get_by_external_id(source, external_id)
        if team:
            return team

        # Check by normalized name
        team = self.find_by_normalized_name(team_data.name)
        if team:
            team.external_ids[source] = external_id
            return team

        # Create new team
        return self.create_team(source, external_id, team_data)
```

### Cross-League Example

```python
# Winner sync creates team
team = matcher.find_or_create_team(
    source="winner",
    external_id="team-123",
    team_data=RawTeam(name="Maccabi Tel Aviv")
)
# team.external_ids = {"winner": "team-123"}

# Later, Euroleague sync finds same team by name
team = matcher.find_or_create_team(
    source="euroleague",
    external_id="MAT",
    team_data=RawTeam(name="Maccabi Playtika Tel Aviv")
)
# team.external_ids = {"winner": "team-123", "euroleague": "MAT"}
```

## Edge Cases

### Player Traded Mid-Season

Players can have multiple team entries within a season:

```python
# PlayerTeamHistory tracks team affiliations
PlayerTeamHistory(player_id=player.id, team_id=team1.id, season_id=season.id)
PlayerTeamHistory(player_id=player.id, team_id=team2.id, season_id=season.id)
```

The deduplication system handles this by checking all team rosters.

### Name Transliteration

Hebrew/Cyrillic names may be transliterated differently:

| Winner | Euroleague | Normalized |
|--------|------------|------------|
| `Gal Mekel` | `GAL MEKEL` | `gal mekel` |
| `Scottie Wilbekin` | `WILBEKIN, SCOTTIE` | `scottie wilbekin` |

The normalizer handles case differences. Name order is handled by parsing both "First Last" and "LAST, FIRST" formats.

### Same Name, Different Player

Rare on the same team, but handled by biographical data matching. If two players have the same name on the same team:
- Birth date comparison will distinguish them
- If no birth date available, they may need manual review

### Finding Potential Duplicates

For manual review of possible duplicate records:

```python
def find_potential_duplicates(self) -> list[tuple[Player, Player]]:
    """Find player pairs that might be duplicates."""
    duplicates = []

    # Find players with similar normalized names
    # but different external_id sources
    ...

    return duplicates
```

## Usage Example

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
# player.external_ids = {"winner": "player-123"}

# Later, import same player from Euroleague
# Matched by team roster + normalized name
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
# Same player record, now with merged external_ids:
# player.external_ids = {"winner": "player-123", "euroleague": "PWB"}
```

## Related Documentation

- [Sync Architecture](architecture.md)
- [Deduplication Source Code](../../src/sync/deduplication/README.md)
- [Player Model](../../src/models/README.md)
