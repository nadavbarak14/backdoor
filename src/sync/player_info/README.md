# Player Info Module

## Purpose

This module provides services for aggregating and merging player biographical data from multiple external sources (Winner League, Euroleague, etc.). It handles conflicting data by applying configurable priority rules based on the order of adapters provided.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `service.py` | PlayerInfoService - aggregates player info from multiple adapters |
| `merger.py` | MergedPlayerInfo dataclass and merge_player_info function |
| `README.md` | This documentation file |

## Usage

### Basic Usage

```python
from src.sync.player_info import PlayerInfoService
from src.sync.winner.adapter import WinnerAdapter
from src.sync.euroleague.adapter import EuroleagueAdapter

# Create adapters (requires their respective dependencies)
winner_adapter = WinnerAdapter(client, scraper, mapper)
euroleague_adapter = EuroleagueAdapter(client, direct_client, mapper)

# Create service with adapters ordered by priority (first = highest)
service = PlayerInfoService([winner_adapter, euroleague_adapter])

# Fetch and merge player info from multiple sources
merged = await service.get_player_info({
    "winner": "w123",
    "euroleague": "e456",
})

print(f"Name: {merged.first_name} {merged.last_name}")
print(f"Height: {merged.height_cm}cm")
print(f"Height source: {merged.sources.get('height_cm')}")
```

### Fetching from a Specific Source

```python
# Fetch raw info from a specific source
info = await service.get_player_info_from_source("winner", "w123")
if info:
    print(f"{info.first_name} {info.last_name}")
```

### Searching for Players

```python
# Search across all sources
results = await service.search_player("James")
for player in results:
    print(f"{player.first_name} {player.last_name}")

# Search with team filter
results = await service.search_player("James", team="100")
```

### Updating a Player Model

```python
from src.models.player import Player

# Fetch player from database
player = session.query(Player).get(player_id)

# Get updates from all sources
updates = await service.update_player_from_sources(player)

# Apply updates
for field, value in updates.items():
    setattr(player, field, value)

session.commit()
```

### Using the Merge Function Directly

```python
from src.sync.player_info import merge_player_info
from src.sync.types import RawPlayerInfo

# Merge player info from multiple sources
sources = [
    ("winner", RawPlayerInfo(external_id="w123", first_name="LeBron", last_name="James", height_cm=206)),
    ("euroleague", RawPlayerInfo(external_id="e456", first_name="Lebron", last_name="James", position="SF")),
]
merged = merge_player_info(sources)

print(merged.height_cm)  # 206 (from winner, first source)
print(merged.position)   # "SF" (from euroleague, not in winner)
```

## Merge Priority Rules

When merging player info from multiple sources, the following priority rules apply:

| Field | Priority Rule |
|-------|--------------|
| `first_name` | First source with non-empty value |
| `last_name` | First source with non-empty value |
| `height_cm` | First source with non-null value |
| `birth_date` | First source with non-null value |
| `position` | First source with non-null value |

The adapter order in `PlayerInfoService` determines priority - adapters listed first have higher priority.

## Dependencies

- **Depends on:**
  - `src.sync.adapters.base` - BasePlayerInfoAdapter interface
  - `src.sync.types` - RawPlayerInfo dataclass

- **External libs:**
  - None (uses only Python standard library)

## Related Documentation

- [Sync Module README](../README.md)
- [Base Adapter Documentation](../adapters/README.md)
- [Winner Adapter Documentation](../winner/README.md)
- [Euroleague Adapter Documentation](../euroleague/README.md)
