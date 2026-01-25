# Viewer Pages

Streamlit multipage app pages for browsing basketball data.

## Purpose

Each page provides list and detail views for a specific entity type, with navigation links to related entities.

## Contents

| File | Entity | Description |
|------|--------|-------------|
| `1_Leagues.py` | League, Season | Browse leagues and their seasons |
| `2_Teams.py` | Team, TeamSeason | Browse teams, rosters, recent games |
| `3_Players.py` | Player | Browse players, career history, game logs |
| `4_Games.py` | Game | Browse games, box scores, play-by-play |

## Page Naming Convention

Streamlit uses file prefixes for sidebar ordering:
- `1_Leagues.py` appears first
- `2_Teams.py` appears second
- etc.

The number prefix is stripped from the display name.

## Common Page Structure

Each page follows this pattern:

```python
"""
[Entity] Page

Browse [entities] with filtering and detailed views.
"""

import streamlit as st
from viewer.db import get_session
from viewer.components.navigation import get_param, link_to
from viewer.components.filters import search_box
from viewer.components.tables import format_entity_table

st.set_page_config(page_title="[Entity]", page_icon="[icon]")

# Check for detail view
entity_id = get_param("entity_id")

if entity_id:
    show_detail_view(entity_id)
else:
    show_list_view()


def show_list_view():
    """Display filterable list of entities."""
    st.header("[Entities]")

    # Filters
    search = search_box("Search...")

    # Load and filter data
    entities = load_entities()
    if search:
        entities = [e for e in entities if search.lower() in e["name"].lower()]

    # Display table
    df = format_entity_table(entities)
    st.dataframe(df)


def show_detail_view(entity_id: str):
    """Display detailed view of single entity."""
    entity = load_entity(entity_id)

    if not entity:
        st.error("Entity not found")
        return

    # Back button
    if st.button("← Back to list"):
        st.query_params.clear()
        st.rerun()

    # Entity info
    st.header(entity["name"])

    # Related data...
```

## Page Specifications

### 1_Leagues.py

**List View:**
- All leagues with season counts
- Search by name

**Detail View:**
- League info (name, country, code)
- Seasons table with links to Teams page

**Links to:** Teams (via season)

---

### 2_Teams.py

**List View:**
- All teams with filters:
  - Season dropdown
  - League dropdown
  - Country dropdown
  - Search by name

**Detail View:**
- Team info (name, code, venue, external IDs)
- Current season roster (links to Players)
- Recent games (links to Games)
- Season stats summary

**Links to:** Players, Games, Leagues

---

### 3_Players.py

**List View:**
- All players with filters:
  - Season dropdown
  - Team dropdown
  - Position dropdown
  - Nationality dropdown
  - Search by name

**Detail View:**
- Player info (name, position, height, nationality, DOB)
- Career history by season (links to Teams)
- Season stats table
- Game log for selected season (links to Games)

**Links to:** Teams, Games

---

### 4_Games.py

**List View:**
- All games with filters:
  - Season dropdown
  - Team dropdown
  - Date range
  - Status dropdown

**Detail View:**
- Game header (date, venue, final score)
- Quarter/period scores
- Team stats comparison (side-by-side)
- Box scores for both teams (links to Players)
- Play-by-play (collapsible, by quarter)

**Links to:** Teams, Players

## URL Parameters

Each page responds to query parameters:

| Page | List Params | Detail Param |
|------|-------------|--------------|
| Leagues | - | `league_id` |
| Teams | `season_id`, `league_id` | `team_id` |
| Players | `season_id`, `team_id`, `position` | `player_id` |
| Games | `season_id`, `team_id`, `status` | `game_id` |

## Data Loading Pattern

```python
@st.cache_data(ttl=300)
def load_entities(filter_key: str = "") -> list[dict]:
    """
    Load entities from database.

    Args:
        filter_key: Cache key differentiator for filtered queries

    Returns:
        List of entity dictionaries
    """
    with get_session() as session:
        query = session.query(Entity)
        # Apply filters...
        return [entity_to_dict(e) for e in query.all()]
```

## Dependencies

- `streamlit` - UI framework
- `viewer.db` - Database sessions
- `viewer.components.*` - Reusable UI components
- `src.models.*` - SQLAlchemy models
