"""
Teams Page

Browse teams with filtering and detailed views.

List view: Filterable table of teams with league, country, and search filters
Detail view: Team info, roster, and recent games

Usage:
    - Access via sidebar navigation
    - Filter by season, league, country, or text search
    - Click team name to view details
    - From detail view, click players to navigate to Player page
    - From detail view, click games to navigate to Game page
"""

import sys
from pathlib import Path

# Add project root to path for Streamlit page imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st  # noqa: E402
from sqlalchemy import or_  # noqa: E402

from src.models.game import Game  # noqa: E402
from src.models.league import League, Season  # noqa: E402
from src.models.player import Player, PlayerTeamHistory  # noqa: E402
from src.models.team import Team, TeamSeason  # noqa: E402
from viewer.components.filters import (  # noqa: E402
    league_filter,
    search_box,
    season_filter,
)
from viewer.components.navigation import (  # noqa: E402
    back_button,
    get_param,
    navigate_to,
)
from viewer.components.stats import entity_info_card, external_ids_display  # noqa: E402
from viewer.db import get_session  # noqa: E402

st.set_page_config(page_title="Teams", page_icon="👥", layout="wide")


# -----------------------------------------------------------------------------
# Data Fetching Functions
# -----------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_all_teams() -> list[dict]:
    """
    Fetch all teams with their basic info.

    Returns:
        List of team dictionaries with id, name, short_name, city, country.
    """
    with get_session() as session:
        teams = session.query(Team).order_by(Team.name).all()
        return [
            {
                "id": str(team.id),
                "name": team.name,
                "short_name": team.short_name,
                "city": team.city,
                "country": team.country,
                "external_ids": team.external_ids,
            }
            for team in teams
        ]


@st.cache_data(ttl=300)
def get_teams_for_season(season_id: str) -> list[dict]:
    """
    Fetch teams participating in a specific season.

    Args:
        season_id: UUID of the season.

    Returns:
        List of team dictionaries for teams in that season.
    """
    with get_session() as session:
        team_seasons = (
            session.query(TeamSeason).filter(TeamSeason.season_id == season_id).all()
        )

        result = []
        for ts in team_seasons:
            team = ts.team
            season = ts.season
            result.append(
                {
                    "id": str(team.id),
                    "name": team.name,
                    "short_name": team.short_name,
                    "city": team.city,
                    "country": team.country,
                    "league_name": season.league.name if season.league else "-",
                    "season_name": season.name,
                }
            )
        return result


@st.cache_data(ttl=300)
def get_all_seasons() -> list[dict]:
    """
    Fetch all seasons ordered by start date (most recent first).

    Returns:
        List of season dictionaries with id, name, and league info.
    """
    with get_session() as session:
        seasons = (
            session.query(Season).join(League).order_by(Season.start_date.desc()).all()
        )
        return [
            {
                "id": str(s.id),
                "name": f"{s.league.name} - {s.name}" if s.league else s.name,
                "league_id": str(s.league_id),
                "league_name": s.league.name if s.league else "-",
                "is_current": s.is_current,
            }
            for s in seasons
        ]


@st.cache_data(ttl=300)
def get_all_leagues() -> list[dict]:
    """
    Fetch all leagues.

    Returns:
        List of league dictionaries with id and name.
    """
    with get_session() as session:
        leagues = session.query(League).order_by(League.name).all()
        return [{"id": str(lg.id), "name": lg.name} for lg in leagues]


@st.cache_data(ttl=300)
def get_all_countries() -> list[str]:
    """
    Fetch distinct countries from teams.

    Returns:
        List of unique country names.
    """
    with get_session() as session:
        countries = session.query(Team.country).distinct().order_by(Team.country).all()
        return [c[0] for c in countries if c[0]]


@st.cache_data(ttl=300)
def get_team_by_id(team_id: str) -> dict | None:
    """
    Fetch a single team by ID.

    Args:
        team_id: UUID of the team.

    Returns:
        Team dictionary or None if not found.
    """
    with get_session() as session:
        team = session.query(Team).filter(Team.id == team_id).first()
        if not team:
            return None
        return {
            "id": str(team.id),
            "name": team.name,
            "short_name": team.short_name,
            "city": team.city,
            "country": team.country,
            "external_ids": team.external_ids,
        }


@st.cache_data(ttl=300)
def get_seasons_for_team(team_id: str) -> list[dict]:
    """
    Fetch all seasons a team has participated in.

    Args:
        team_id: UUID of the team.

    Returns:
        List of season dictionaries ordered by start date (most recent first).
    """
    with get_session() as session:
        team_seasons = (
            session.query(TeamSeason)
            .join(Season)
            .filter(TeamSeason.team_id == team_id)
            .order_by(Season.start_date.desc())
            .all()
        )
        return [
            {
                "id": str(ts.season_id),
                "name": (
                    f"{ts.season.league.name} - {ts.season.name}"
                    if ts.season.league
                    else ts.season.name
                ),
                "is_current": ts.season.is_current,
            }
            for ts in team_seasons
        ]


@st.cache_data(ttl=300)
def get_roster_for_team_season(team_id: str, season_id: str) -> list[dict]:
    """
    Fetch roster for a team in a specific season.

    Args:
        team_id: UUID of the team.
        season_id: UUID of the season.

    Returns:
        List of player dictionaries with roster info.
    """
    with get_session() as session:
        histories = (
            session.query(PlayerTeamHistory)
            .join(Player)
            .filter(
                PlayerTeamHistory.team_id == team_id,
                PlayerTeamHistory.season_id == season_id,
            )
            .order_by(Player.last_name, Player.first_name)
            .all()
        )

        return [
            {
                "player_id": str(h.player_id),
                "name": h.player.full_name,
                "jersey_number": h.jersey_number,
                "position": h.position or h.player.position or "-",
                "nationality": h.player.nationality or "-",
            }
            for h in histories
        ]


@st.cache_data(ttl=300)
def get_recent_games_for_team(team_id: str, limit: int = 10) -> list[dict]:
    """
    Fetch recent games for a team.

    Args:
        team_id: UUID of the team.
        limit: Maximum number of games to return.

    Returns:
        List of game dictionaries with scores and opponent info.
    """
    with get_session() as session:
        games = (
            session.query(Game)
            .filter(or_(Game.home_team_id == team_id, Game.away_team_id == team_id))
            .order_by(Game.game_date.desc())
            .limit(limit)
            .all()
        )

        result = []
        for game in games:
            is_home = str(game.home_team_id) == team_id
            opponent = game.away_team if is_home else game.home_team
            team_score = game.home_score if is_home else game.away_score
            opponent_score = game.away_score if is_home else game.home_score

            # Determine W/L
            if team_score is not None and opponent_score is not None:
                if team_score > opponent_score:
                    result_str = "W"
                elif team_score < opponent_score:
                    result_str = "L"
                else:
                    result_str = "T"
            else:
                result_str = "-"

            # Format score
            if team_score is not None and opponent_score is not None:
                score_str = f"{team_score}-{opponent_score}"
            else:
                score_str = "-"

            result.append(
                {
                    "game_id": str(game.id),
                    "date": game.game_date.strftime("%Y-%m-%d"),
                    "opponent_id": str(opponent.id) if opponent else None,
                    "opponent_name": opponent.name if opponent else "Unknown",
                    "score": score_str,
                    "result": result_str,
                    "is_home": is_home,
                    "status": game.status,
                }
            )
        return result


# -----------------------------------------------------------------------------
# Filtering Logic
# -----------------------------------------------------------------------------


def filter_teams(
    teams: list[dict],
    search: str,
    country: str | None,
) -> list[dict]:
    """
    Filter teams by search term and country.

    Args:
        teams: List of team dictionaries.
        search: Text search term (matches name, short_name, city).
        country: Country filter.

    Returns:
        Filtered list of teams.
    """
    result = teams

    # Filter by search term
    if search:
        search_lower = search.lower()
        result = [
            t
            for t in result
            if search_lower in t["name"].lower()
            or search_lower in t.get("short_name", "").lower()
            or search_lower in t.get("city", "").lower()
        ]

    # Filter by country
    if country:
        result = [t for t in result if t.get("country") == country]

    return result


# -----------------------------------------------------------------------------
# View Rendering
# -----------------------------------------------------------------------------


def render_list_view():
    """Render the team list view with filters and table."""
    st.header("👥 Teams")

    # Check if season_id is passed from Leagues page
    initial_season_id = get_param("season_id")

    # Fetch filter data
    all_seasons = get_all_seasons()
    all_leagues = get_all_leagues()
    all_countries = get_all_countries()

    # Filters in columns
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_season = season_filter(all_seasons, key="team_season_filter")
        # If season_id from URL, use it
        if initial_season_id and not selected_season:
            selected_season = initial_season_id

    with col2:
        selected_league = league_filter(all_leagues, key="team_league_filter")

    with col3:
        # Country dropdown
        country_options = ["All Countries"] + all_countries
        selected_country_option = st.selectbox(
            "Country", country_options, key="team_country_filter"
        )
        selected_country = (
            None
            if selected_country_option == "All Countries"
            else selected_country_option
        )

    # Search box
    search = search_box("Search teams by name, code, or city...", key="team_search")

    # Fetch teams based on filters
    if selected_season:
        teams = get_teams_for_season(selected_season)
    else:
        teams = get_all_teams()

    # Apply additional filters
    filtered = filter_teams(teams, search, selected_country)

    # Also filter by league if selected (for all-teams view)
    if selected_league and not selected_season:
        # For all-teams view, we need to filter by teams that have at least one season in the league
        league_season_ids = {
            s["id"] for s in all_seasons if s["league_id"] == selected_league
        }
        # Get teams for these seasons
        teams_in_league = set()
        for sid in league_season_ids:
            season_teams = get_teams_for_season(sid)
            teams_in_league.update(t["id"] for t in season_teams)
        filtered = [t for t in filtered if t["id"] in teams_in_league]

    # Display count
    if search or selected_season or selected_league or selected_country:
        st.caption(f"Showing {len(filtered)} of {len(teams)} teams")
    else:
        st.caption(f"{len(filtered)} teams")

    if not filtered:
        st.info("No teams found matching your filters.")
        return

    # Table header
    st.markdown("Click a team name to view details:")
    cols = st.columns([3, 1, 2, 2])
    cols[0].markdown("**Team**")
    cols[1].markdown("**Code**")
    cols[2].markdown("**City**")
    cols[3].markdown("**Country**")

    # Table rows
    for team in filtered:
        cols = st.columns([3, 1, 2, 2])

        with cols[0]:
            if st.button(team["name"], key=f"team_{team['id']}"):
                navigate_to("2_Teams", team_id=team["id"])

        cols[1].write(team.get("short_name", "-"))
        cols[2].write(team.get("city", "-"))
        cols[3].write(team.get("country", "-"))


def render_detail_view(team_id: str):
    """
    Render the team detail view.

    Args:
        team_id: UUID of the team to display.
    """
    team = get_team_by_id(team_id)

    if not team:
        st.error("Team not found")
        if back_button():
            st.rerun()
        return

    # Back button
    if back_button("← Back to teams"):
        st.rerun()

    # Team header
    st.header(f"👥 {team['name']}")

    # Team info card
    entity_info_card(
        "Team Information",
        {
            "Full Name": team["name"],
            "Code": team["short_name"],
            "City": team["city"],
            "Country": team["country"],
        },
    )

    # External IDs
    external_ids_display(team.get("external_ids"))

    st.divider()

    # Get seasons for this team
    team_seasons = get_seasons_for_team(team_id)

    if not team_seasons:
        st.info("No season data available for this team.")
        return

    # Season selector for roster
    st.subheader("Roster")

    # Find current season or default to first
    current_idx = 0
    for i, s in enumerate(team_seasons):
        if s["is_current"]:
            current_idx = i
            break

    season_names = [s["name"] for s in team_seasons]
    selected_season_name = st.selectbox(
        "Select Season",
        season_names,
        index=current_idx,
        key="roster_season_select",
    )

    # Get selected season ID
    selected_season = next(
        (s for s in team_seasons if s["name"] == selected_season_name), None
    )

    if selected_season:
        roster = get_roster_for_team_season(team_id, selected_season["id"])

        if roster:
            # Roster table header
            cols = st.columns([3, 1, 2, 2])
            cols[0].markdown("**Player**")
            cols[1].markdown("**#**")
            cols[2].markdown("**Position**")
            cols[3].markdown("**Nationality**")

            # Roster rows
            for player in roster:
                cols = st.columns([3, 1, 2, 2])

                with cols[0]:
                    if st.button(player["name"], key=f"player_{player['player_id']}"):
                        navigate_to("3_Players", player_id=player["player_id"])

                cols[1].write(
                    str(player["jersey_number"]) if player["jersey_number"] else "-"
                )
                cols[2].write(player["position"])
                cols[3].write(player["nationality"])
        else:
            st.info("No roster data available for this season.")

    st.divider()

    # Recent games
    st.subheader("Recent Games")

    recent_games = get_recent_games_for_team(team_id)

    if not recent_games:
        st.info("No games found for this team.")
    else:
        # Games table header
        cols = st.columns([2, 3, 2, 1, 1])
        cols[0].markdown("**Date**")
        cols[1].markdown("**Opponent**")
        cols[2].markdown("**Score**")
        cols[3].markdown("**Result**")
        cols[4].markdown("**H/A**")

        # Games rows
        for game in recent_games:
            cols = st.columns([2, 3, 2, 1, 1])

            cols[0].write(game["date"])

            with cols[1]:
                if game["opponent_id"]:
                    if st.button(
                        game["opponent_name"],
                        key=f"opp_{game['game_id']}",
                    ):
                        navigate_to("2_Teams", team_id=game["opponent_id"])
                else:
                    st.write(game["opponent_name"])

            with cols[2]:
                if st.button(game["score"], key=f"game_{game['game_id']}"):
                    navigate_to("4_Games", game_id=game["game_id"])

            # Color-code result
            result = game["result"]
            if result == "W":
                cols[3].markdown(":green[W]")
            elif result == "L":
                cols[3].markdown(":red[L]")
            else:
                cols[3].write(result)

            cols[4].write("H" if game["is_home"] else "A")


# -----------------------------------------------------------------------------
# Main Router
# -----------------------------------------------------------------------------


def main():
    """Main page router based on URL parameters."""
    team_id = get_param("team_id")

    if team_id:
        render_detail_view(team_id)
    else:
        render_list_view()


if __name__ == "__main__":
    main()
