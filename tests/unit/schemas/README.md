# Schema Unit Tests

## Purpose

Unit tests for Pydantic schemas in `src/schemas/`. These tests verify request validation, response serialization, and ORM compatibility.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package marker |
| `test_league_schemas.py` | Tests for League and Season schemas |
| `test_team_schemas.py` | Tests for Team schemas |
| `test_player_schemas.py` | Tests for Player schemas |

## Test Coverage

### League Schema Tests (`test_league_schemas.py`)

- `LeagueCreate` validation (required fields, length limits)
- `LeagueUpdate` partial validation
- `SeasonCreate` date validation
- `LeagueResponse` from ORM object
- `SeasonFilter` optional fields

### Team Schema Tests (`test_team_schemas.py`)

- `TeamCreate` with external_ids dict
- `TeamFilter` optional fields
- `TeamResponse` from ORM object
- `TeamRosterResponse` nested structure

### Player Schema Tests (`test_player_schemas.py`)

- `PlayerCreate` height_cm range validation (100-250)
- `PlayerFilter` search field
- `PlayerResponse` full_name included
- `PlayerWithHistoryResponse` nested structure

## Running Tests

```bash
# Run all schema tests
uv run python -m pytest tests/unit/schemas/ -v

# Run specific test file
uv run python -m pytest tests/unit/schemas/test_player_schemas.py -v

# Run with coverage
uv run python -m pytest tests/unit/schemas/ --cov=src/schemas
```

## Test Patterns

### Validation Tests

```python
def test_name_required(self):
    """Schema should require name field."""
    with pytest.raises(ValidationError) as exc_info:
        LeagueCreate(code="NBA", country="USA")
    assert "name" in str(exc_info.value)
```

### ORM Serialization Tests

```python
def test_from_orm_object(self, db_session: Session):
    """Response should serialize from ORM object."""
    player = Player(first_name="LeBron", last_name="James")
    db_session.add(player)
    db_session.commit()

    response = PlayerResponse.model_validate(player)
    assert response.full_name == "LeBron James"
```

## Dependencies

- **Internal**: `src.schemas`, `src.models`
- **External**: `pytest`, `pydantic`, `sqlalchemy`
