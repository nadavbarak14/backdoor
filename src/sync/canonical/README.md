# Canonical Types

## Purpose

This package provides the "layer of truth" for normalized data types. All league adapters (Winner, Euroleague, NBA, etc.) convert their raw scraped data to these validated types before storage.

## Philosophy

From Issue #201:
> "All persisted data must be normalized through our domain models, not raw scraped values."

Key principles:
1. **Parse functions return None on failure** - No exceptions for invalid data
2. **Comprehensive mappings** - Support all known formats from all leagues
3. **Case-insensitive** - All parsing is case-insensitive
4. **Multi-language** - Support English, Hebrew, and abbreviations

## Contents

| File | Description |
|------|-------------|
| `position.py` | Position enum with parse functions for various formats |
| `height.py` | Height dataclass with parsing for cm, meters, feet/inches |
| `birthdate.py` | Birthdate parsing for ISO, European, US, and text formats |
| `nationality.py` | Nationality with ISO 3166-1 alpha-3 codes |
| `event.py` | EventType and subtypes (ShotType, ReboundType, etc.) |
| `game_status.py` | GameStatus enum with parse function |
| `errors.py` | Custom exceptions (ValidationError, ConversionError) |

## Usage

```python
from src.sync.canonical import (
    Position, parse_position, parse_positions,
    Height, parse_height,
    Nationality, parse_nationality,
    EventType, GameStatus,
)

# Position parsing
position = parse_position("Point Guard")  # Position.POINT_GUARD
position = parse_position("גארד")  # Position.GUARD (Hebrew)
position = parse_position("invalid")  # None

# Multi-position parsing
positions = parse_positions("G/F")  # [Position.GUARD, Position.FORWARD]
positions = parse_positions("PG, SG")  # [Position.POINT_GUARD, Position.SHOOTING_GUARD]

# Height parsing
height = parse_height(198)  # Height(cm=198)
height = parse_height("6'8\"")  # Height(cm=203)
height = parse_height(1.98)  # Height(cm=198) (meters)
height = parse_height(100)  # None (out of range)

# Nationality parsing
nat = parse_nationality("Israel")  # Nationality(code="ISR")
nat = parse_nationality("ישראל")  # Nationality(code="ISR")
nat = parse_nationality("ISR")  # Nationality(code="ISR")
```

## Supported Formats

### Positions
- Standard: `PG`, `SG`, `SF`, `PF`, `C`, `G`, `F`
- Full names: `Point Guard`, `Shooting Guard`, etc.
- Euroleague: `Guard (Point)`, `Forward (Small)`
- Hebrew: `גארד`, `פורוורד`, `סנטר`
- Combos: `G/F`, `G-F`, `F-C`

### Heights
- Integer cm: `198`
- String cm: `"198"`, `"198 cm"`
- Meters: `1.98`, `"1.98m"`
- Feet/inches: `"6'8"`, `"6-8"`, `"6ft 8in"`

### Birthdates
- ISO: `"1995-05-15"`
- European: `"15/05/1995"`, `"15-05-1995"`
- US: `"05/15/1995"`
- Text: `"May 15, 1995"`, `"15 May 1995"`

### Nationalities
- ISO codes: `"ISR"`, `"USA"`, `"ESP"`
- English names: `"Israel"`, `"United States"`
- Hebrew names: `"ישראל"`
- Demonyms: `"Israeli"`, `"American"`

## Dependencies

- Internal: None (standalone package)
- External: `pycountry` (for nationality lookups)

## Related Documentation

- [Data Storage Philosophy](../../../docs/architecture.md#data-storage-philosophy)
- [Sync Layer](../README.md)
