# Internal Data Viewer

Streamlit-based internal tool for browsing synced basketball data.

## Purpose

This viewer provides a web interface for:
- Browsing all synced entities (leagues, teams, players, games)
- Navigating relationships between entities
- Viewing historical data and statistics
- Debugging sync issues and data quality

**Note:** This is an internal tool, not a production-facing application.

## Quick Start

```bash
# Install viewer dependencies
uv pip install -e ".[viewer]"

# Run the viewer
uv run streamlit run viewer/app.py
```

The app will open at `http://localhost:8501`

## Project Structure

```
viewer/
├── README.md               # This file
├── app.py                  # Home dashboard (entry point)
├── db.py                   # Database session management
├── pages/                  # Streamlit multipage app pages
│   ├── README.md           # Pages documentation
│   ├── 1_Leagues.py        # Leagues list + detail view
│   ├── 2_Teams.py          # Teams list + detail + roster
│   ├── 3_Players.py        # Players list + career history
│   └── 4_Games.py          # Games list + box scores
└── components/             # Reusable UI components
    ├── README.md           # Components documentation
    ├── __init__.py         # Public exports
    ├── navigation.py       # URL/linking helpers
    ├── filters.py          # Filter widgets (dropdowns, search)
    ├── tables.py           # Data table formatters
    └── stats.py            # Stats display cards
```

## Architecture

### Page Structure

Each page follows the **list/detail pattern**:

```
┌─────────────────────────────────────────────────────────┐
│  Page (e.g., Teams)                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  URL: /Teams                    URL: /Teams?team_id=X   │
│  ┌─────────────────────┐        ┌─────────────────────┐ │
│  │     LIST VIEW       │        │    DETAIL VIEW      │ │
│  │                     │        │                     │ │
│  │  - Filters          │  ───►  │  - Entity info      │ │
│  │  - Searchable table │  click │  - Related data     │ │
│  │  - Clickable rows   │        │  - Links to others  │ │
│  └─────────────────────┘        └─────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Navigation Flow

```
Home Dashboard
    │
    ├── Leagues ─────► League Detail ─────► Seasons
    │                                           │
    │                                           ▼
    ├── Teams ◄────────────────────────── Team Detail ◄───┐
    │       │                                  │          │
    │       │                                  ▼          │
    │       │                              Roster ────────┤
    │       │                                  │          │
    │       ▼                                  ▼          │
    ├── Players ──────► Player Detail ◄────────┘          │
    │                        │                            │
    │                        ▼                            │
    │                   Game Log ─────────────────────────┤
    │                        │                            │
    │                        ▼                            │
    └── Games ────────► Game Detail                       │
                             │                            │
                             └── Box Score ───────────────┘
```

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                        PAGES                            │
│   (1_Leagues.py, 2_Teams.py, 3_Players.py, 4_Games.py)  │
├─────────────────────────────────────────────────────────┤
│                      COMPONENTS                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │  navigation  │ │   filters    │ │     tables       │ │
│  │              │ │              │ │                  │ │
│  │ - get_param  │ │ - season     │ │ - format_league  │ │
│  │ - make_link  │ │ - league     │ │ - format_team    │ │
│  │ - link_to    │ │ - team       │ │ - format_player  │ │
│  │              │ │ - search     │ │ - format_game    │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│  ┌──────────────────────────────────────────────────────┤
│  │                      stats                           │
│  │                                                      │
│  │  - entity_info_card    - box_score_table             │
│  │  - season_stats_card   - quarter_scores              │
│  └──────────────────────────────────────────────────────┤
├─────────────────────────────────────────────────────────┤
│                        db.py                            │
│                  (Session management)                   │
├─────────────────────────────────────────────────────────┤
│                    src/models/*                         │
│                  (SQLAlchemy models)                    │
└─────────────────────────────────────────────────────────┘
```

## URL Pattern

All navigation uses query parameters for bookmarkable/shareable URLs:

| Page | List URL | Detail URL |
|------|----------|------------|
| Leagues | `/Leagues` | `/Leagues?league_id=<uuid>` |
| Teams | `/Teams` | `/Teams?team_id=<uuid>` |
| Players | `/Players` | `/Players?player_id=<uuid>` |
| Games | `/Games` | `/Games?game_id=<uuid>` |

Filter state is also preserved in URL:
- `/Teams?season_id=<uuid>` - Teams filtered by season
- `/Players?team_id=<uuid>` - Players filtered by team
- `/Games?team_id=<uuid>&status=finished` - Finished games for a team

## Data Loading

### Caching Strategy

```python
@st.cache_data(ttl=300)  # 5-minute cache
def get_teams(session_key: str) -> list[dict]:
    """Load and cache team data."""
    with get_session() as session:
        teams = session.query(Team).all()
        return [team_to_dict(t) for t in teams]
```

- Use `@st.cache_data` for database queries
- Convert SQLAlchemy objects to dicts before caching
- 5-minute TTL balances freshness with performance

### Session Management

```python
from viewer.db import get_session

with get_session() as session:
    teams = session.query(Team).all()
    # session auto-closes after block
```

## Adding a New Page

1. Create `pages/N_EntityName.py` (N = order number)
2. Implement list view with filters
3. Implement detail view with query param check
4. Add navigation links to/from related entities
5. Update this README

## Development Guidelines

- Follow patterns established in existing pages
- Use components from `viewer/components/`
- Keep pages focused on display, not business logic
- All entity names should be clickable links
- Preserve filter state in URL parameters
