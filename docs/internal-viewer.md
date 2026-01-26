# Internal Data Viewer - Usage Guide

The Internal Data Viewer is a Streamlit-based web application for browsing and exploring synced basketball data. This guide explains how to use each page and common workflows.

## Getting Started

### Starting the Viewer

```bash
# Install viewer dependencies (if not already installed)
uv pip install -e ".[viewer]"

# Start the viewer
uv run streamlit run viewer/app.py
```

The viewer opens at `http://localhost:8501`.

### Home Dashboard

The home page displays:

- **Data Overview**: Counts of leagues, seasons, teams, players, and games
- **Quick Navigation**: Links to all entity pages
- **Recent Sync Activity**: Latest sync operations with status

Use the **Refresh Data** button to clear cache and reload fresh data.

---

## Pages

### Leagues Page

**Purpose**: Browse all basketball leagues and their seasons.

#### List View

| Column | Description |
|--------|-------------|
| League Name | Clickable - opens league detail |
| Country | Country of the league |
| Code | Short code identifier |
| Seasons | Number of seasons synced |

**Filters**:
- Text search (searches league name)

#### Detail View

Shows:
- League information (name, country, code, external IDs)
- Seasons table with team/game counts
- Click a season to navigate to Teams filtered by that season

**Navigation**:
- Click season row → Teams page filtered by season

---

### Teams Page

**Purpose**: Browse teams with rosters and recent games.

#### List View

| Column | Description |
|--------|-------------|
| Team Name | Clickable - opens team detail |
| Code | Short code identifier |
| City | Team's city |
| Country | Team's country |

**Filters**:
- **Season**: Filter to teams in a specific season
- **League**: Filter to teams in a specific league
- **Country**: Filter by country
- **Search**: Text search by name, code, or city

#### Detail View

Shows:
- Team information (name, code, city, country, external IDs)
- **Roster**: Players for the selected season (dropdown to change season)
  - Click player name → Player detail
- **Recent Games**: Last 10 games
  - Click opponent → Team detail
  - Click score → Game detail

**Navigation**:
- Click player name → Players page with player detail
- Click opponent team → Teams page with team detail
- Click game score → Games page with game detail

---

### Players Page

**Purpose**: Browse players with career history and game logs.

#### List View

| Column | Description |
|--------|-------------|
| Player Name | Clickable - opens player detail |
| Team | Current/season team |
| Position | Player position |
| Nationality | Player's nationality |
| Height | Height in cm |

**Filters**:
- **Season**: Filter to players active in a season
- **Team**: Filter to players on a specific team
- **Position**: Filter by position (Guard, Forward, Center, etc.)
- **Nationality**: Filter by nationality
- **Search**: Text search by name

#### Detail View

Shows:
- Player information (name, position, height, nationality, DOB, age, external IDs)
- **Career History**: Season-by-season stats
  - Season, Team (clickable), GP, PPG, RPG, APG
- **Game Log**: Game-by-game performance
  - Select season from dropdown
  - Date (clickable), Opponent (clickable), Result, MIN, PTS, REB, AST, +/-

**Navigation**:
- Click team name → Teams page with team detail
- Click game date → Games page with game detail
- Click opponent → Teams page with team detail

---

### Games Page

**Purpose**: Browse games with box scores and play-by-play.

#### List View

| Column | Description |
|--------|-------------|
| Date | Game date |
| Home | Home team (clickable) |
| Score | Final score (clickable - opens game detail) |
| Away | Away team (clickable) |
| Status | Game status (color-coded) |

**Status Colors**:
- :green[Green] - Finished/Final
- :red[Red] - Live
- :blue[Blue] - Scheduled

**Filters**:
- **Season**: Filter to games in a season
- **Team**: Filter to games involving a team
- **Start Date / End Date**: Date range filter
- **Status**: Filter by game status

#### Detail View

Shows:
- **Game Header**: Large score display with team names, date, venue
- **Team Stats Comparison**: Side-by-side stats (FG%, 3P%, rebounds, etc.)
- **Box Score**:
  - Toggle between home/away team
  - Starters and bench sections
  - Full stats: MIN, PTS, FG, 3PT, FT, REB, AST, STL, BLK, TO, +/-
  - Player names are clickable
- **Play-by-Play** (collapsible):
  - Filter by quarter/period
  - Shows clock, team, player, action type, description

**Navigation**:
- Click team name → Teams page with team detail
- Click player name → Players page with player detail

---

## Common Workflows

### Finding a Specific Player's Stats

1. Go to **Players** page
2. Use search box to find player by name
3. Click player name to open detail view
4. View career history table for season averages
5. Select a season in Game Log section for game-by-game stats

### Viewing a Team's Roster

1. Go to **Teams** page
2. Filter by season (optional) or search for team
3. Click team name to open detail view
4. View roster section - use dropdown to change seasons
5. Click any player to see their full profile

### Analyzing a Game

1. Go to **Games** page
2. Filter by team and/or date range
3. Click the score to open game detail
4. View team stats comparison for overall performance
5. Switch between teams in box score to see individual stats
6. Expand Play-by-Play for detailed event log

### Exploring a League's Data

1. Go to **Leagues** page
2. Click a league to see its seasons
3. Click a season row to navigate to Teams filtered by that season
4. Browse teams, then drill into rosters and games

### Checking Data Quality

1. Start at **Home Dashboard**
2. Review entity counts - are numbers reasonable?
3. Check Recent Sync Activity for any FAILED syncs
4. Browse specific entities to verify data completeness

---

## URL Parameters

The viewer uses URL parameters for bookmarkable/shareable links:

| Page | Parameter | Example |
|------|-----------|---------|
| Leagues | `league_id` | `/Leagues?league_id=abc-123` |
| Teams | `team_id` | `/Teams?team_id=abc-123` |
| Teams | `season_id` | `/Teams?season_id=abc-123` |
| Players | `player_id` | `/Players?player_id=abc-123` |
| Games | `game_id` | `/Games?game_id=abc-123` |

Copy the URL to share a specific view with others.

---

## Keyboard Shortcuts

Streamlit provides these keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| `R` | Rerun the app |
| `C` | Clear cache and rerun |

---

## Troubleshooting

### No Data Displayed

1. Check Home Dashboard sync activity - are syncs completing?
2. Verify database connection in terminal output
3. Try the Refresh Data button to clear cache

### Slow Loading

1. First load fetches from database - subsequent loads use cache
2. Complex pages (Games with box scores) may take longer
3. Check terminal for any database query issues

### Navigation Not Working

1. Check browser console for JavaScript errors
2. Try refreshing the page
3. Clear browser cache if needed

---

## Related Documentation

- [Viewer README](../viewer/README.md) - Technical architecture
- [Pages README](../viewer/pages/README.md) - Page implementation details
- [Components README](../viewer/components/README.md) - Reusable components
