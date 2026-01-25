# Viewer Components

Reusable UI components for the internal data viewer.

## Purpose

This folder contains shared components used across multiple pages to ensure:
- Consistent look and feel
- DRY (Don't Repeat Yourself) code
- Easy maintenance and updates

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports |
| `navigation.py` | URL handling and entity linking |
| `filters.py` | Filter widgets (dropdowns, search, date pickers) |
| `tables.py` | Data table formatters and display |
| `stats.py` | Statistics cards and comparison displays |

## Component Details

### navigation.py

Handles URL-based navigation between entities.

```python
from viewer.components.navigation import get_param, make_link, link_to

# Get current query parameter
team_id = get_param("team_id")

# Create a URL with parameters
url = make_link("Teams", team_id="abc-123")

# Create a clickable link (returns markdown)
link = link_to("Lakers", "Teams", team_id="abc-123")
```

**Functions:**
- `get_param(name: str) -> str | None` - Get query parameter from URL
- `set_params(**kwargs)` - Update URL with new parameters
- `make_link(page: str, **params) -> str` - Build URL string
- `link_to(label: str, page: str, **params) -> str` - Markdown link
- `navigate_to(page: str, **params)` - Programmatic navigation

### filters.py

Reusable filter widgets that return selected values.

```python
from viewer.components.filters import season_filter, team_filter, search_box

# In your page:
selected_season = season_filter(seasons)
selected_team = team_filter(teams)
search_term = search_box("Search players...")
```

**Functions:**
- `season_filter(seasons: list[dict]) -> str | None` - Season dropdown
- `league_filter(leagues: list[dict]) -> str | None` - League dropdown
- `team_filter(teams: list[dict]) -> str | None` - Team dropdown
- `search_box(placeholder: str) -> str` - Text search input
- `date_range_filter() -> tuple[date, date]` - Start/end date pickers
- `status_filter() -> str | None` - Game status dropdown

### tables.py

Format data for display in Streamlit dataframes.

```python
from viewer.components.tables import format_team_table

# Convert model dicts to display-ready DataFrame
df = format_team_table(teams)
st.dataframe(df, use_container_width=True)
```

**Functions:**
- `format_league_table(leagues: list[dict]) -> pd.DataFrame`
- `format_season_table(seasons: list[dict]) -> pd.DataFrame`
- `format_team_table(teams: list[dict]) -> pd.DataFrame`
- `format_player_table(players: list[dict]) -> pd.DataFrame`
- `format_game_table(games: list[dict]) -> pd.DataFrame`
- `format_box_score(stats: list[dict]) -> pd.DataFrame`
- `format_game_log(games: list[dict]) -> pd.DataFrame`

### stats.py

Display cards and formatted statistics.

```python
from viewer.components.stats import entity_info_card, stats_row

# Display entity information
entity_info_card("Team Info", {
    "Name": team["name"],
    "Country": team["country"],
    "Arena": team["venue"],
})

# Display stats in columns
stats_row([
    ("Games", 82),
    ("Wins", 52),
    ("Losses", 30),
    ("Win %", "63.4%"),
])
```

**Functions:**
- `entity_info_card(title: str, data: dict)` - Key-value info display
- `stats_row(stats: list[tuple])` - Horizontal stats display
- `metric_card(label: str, value: Any, delta: Any = None)` - Single metric
- `comparison_table(home: dict, away: dict)` - Side-by-side comparison
- `box_score_display(stats: list[dict])` - Full box score table

## Usage Pattern

All components are designed to work with dictionaries (not SQLAlchemy objects):

```python
# In page file:
from viewer.db import get_session
from viewer.components.tables import format_team_table

@st.cache_data(ttl=300)
def load_teams() -> list[dict]:
    with get_session() as session:
        teams = session.query(Team).all()
        return [
            {
                "id": str(t.id),
                "name": t.name,
                "country": t.country,
            }
            for t in teams
        ]

# Then use with component
teams = load_teams()
df = format_team_table(teams)
```

## Dependencies

- `streamlit` - UI framework
- `pandas` - DataFrame operations
- Internal: `viewer.db` for database access
