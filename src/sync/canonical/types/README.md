# Canonical Types

## Purpose

Individual type definitions for the canonical data layer. Each file contains a type definition and its associated parse function(s).

## Contents

| File | Type | Parse Function(s) | Description |
|------|------|-------------------|-------------|
| `position.py` | `Position` | `parse_position()`, `parse_positions()` | Basketball positions |
| `height.py` | `Height` | `parse_height()` | Player height in cm |
| `birthdate.py` | - | `parse_birthdate()` | Birthdate as `date` |
| `nationality.py` | `Nationality` | `parse_nationality()` | ISO country codes |
| `event.py` | `EventType`, `ShotType`, etc. | - | Play-by-play events |
| `game_status.py` | `GameStatus` | `parse_game_status()` | Game states |
| `errors.py` | `ValidationError`, `ConversionError` | - | Custom exceptions |

## Design Principles

1. **Parse functions return None on invalid input** - Never raise exceptions
2. **All parsing is case-insensitive**
3. **Enums inherit from `str` for JSON serialization**
4. **Dataclasses are frozen (immutable)**
