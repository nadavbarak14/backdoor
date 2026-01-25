"""
Leagues Page

Browse leagues and their seasons.

List view: All leagues with season counts and search filter
Detail view: League info card + seasons table with navigation to Teams

Usage:
    - Access via sidebar navigation
    - Click league name to view details
    - From detail view, click season to navigate to Teams filtered by that season
"""

import sys
from pathlib import Path

# Add project root to path for Streamlit page imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st  # noqa: E402
from sqlalchemy import func  # noqa: E402

from src.models.game import Game  # noqa: E402
from src.models.league import League, Season  # noqa: E402
from src.models.team import TeamSeason  # noqa: E402
from viewer.components.navigation import (  # noqa: E402
    back_button,
    get_param,
    navigate_to,
)
from viewer.db import get_session  # noqa: E402

st.set_page_config(page_title="Leagues", page_icon="📋", layout="wide")


@st.cache_data(ttl=300)
def get_all_leagues() -> list[dict]:
    """
    Fetch all leagues with their season counts.

    Returns:
        List of league dictionaries with id, name, country, code, season_count.
    """
    with get_session() as session:
        leagues = session.query(League).all()
        return [
            {
                "id": str(league.id),
                "name": league.name,
                "country": league.country,
                "code": league.code,
                "season_count": len(league.seasons),
            }
            for league in leagues
        ]


@st.cache_data(ttl=300)
def get_league_by_id(league_id: str) -> dict | None:
    """
    Fetch a single league by ID.

    Args:
        league_id: UUID of the league.

    Returns:
        League dictionary or None if not found.
    """
    with get_session() as session:
        league = session.query(League).filter(League.id == league_id).first()
        if not league:
            return None
        return {
            "id": str(league.id),
            "name": league.name,
            "country": league.country,
            "code": league.code,
        }


@st.cache_data(ttl=300)
def get_seasons_for_league(league_id: str) -> list[dict]:
    """
    Fetch all seasons for a league with team and game counts.

    Args:
        league_id: UUID of the league.

    Returns:
        List of season dictionaries with counts.
    """
    with get_session() as session:
        seasons = (
            session.query(Season)
            .filter(Season.league_id == league_id)
            .order_by(Season.start_date.desc())
            .all()
        )

        result = []
        for season in seasons:
            # Count teams in this season
            team_count = (
                session.query(func.count(TeamSeason.id))
                .filter(TeamSeason.season_id == season.id)
                .scalar()
                or 0
            )

            # Count games in this season
            game_count = (
                session.query(func.count(Game.id))
                .filter(Game.season_id == season.id)
                .scalar()
                or 0
            )

            result.append(
                {
                    "id": str(season.id),
                    "name": season.name,
                    "start_date": (
                        season.start_date.strftime("%Y-%m-%d")
                        if season.start_date
                        else "-"
                    ),
                    "end_date": (
                        season.end_date.strftime("%Y-%m-%d") if season.end_date else "-"
                    ),
                    "is_current": season.is_current,
                    "team_count": team_count,
                    "game_count": game_count,
                }
            )

        return result


def filter_leagues(leagues: list[dict], search: str) -> list[dict]:
    """
    Filter leagues by search term.

    Args:
        leagues: List of league dictionaries.
        search: Search term to filter by (matches name, country, or code).

    Returns:
        Filtered list of leagues.
    """
    if not search:
        return leagues

    search_lower = search.lower()
    return [
        league
        for league in leagues
        if search_lower in league["name"].lower()
        or search_lower in league["country"].lower()
        or search_lower in league["code"].lower()
    ]


def render_list_view():
    """Render the league list view with search and table."""
    st.header("📋 Leagues")

    # Search filter
    search = st.text_input(
        "Search leagues",
        placeholder="Search by name, country, or code...",
        label_visibility="collapsed",
    )

    # Fetch and filter data
    leagues = get_all_leagues()
    filtered = filter_leagues(leagues, search)

    # Display count
    if search:
        st.caption(f"Showing {len(filtered)} of {len(leagues)} leagues")
    else:
        st.caption(f"{len(leagues)} leagues")

    if not filtered:
        st.info("No leagues found matching your search.")
        return

    # Add league names as clickable links
    st.markdown("Click a league name to view details:")

    # Display as interactive dataframe
    for league in filtered:
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        with col1:
            if st.button(league["name"], key=f"league_{league['id']}"):
                navigate_to("1_Leagues", league_id=league["id"])
        with col2:
            st.write(league["country"])
        with col3:
            st.write(league["code"])
        with col4:
            st.write(f"{league['season_count']} seasons")


def render_detail_view(league_id: str):
    """
    Render the league detail view.

    Args:
        league_id: UUID of the league to display.
    """
    league = get_league_by_id(league_id)

    if not league:
        st.error("League not found")
        if back_button():
            st.rerun()
        return

    # Back button
    if back_button("← Back to leagues"):
        st.rerun()

    # League header
    st.header(f"📋 {league['name']}")

    # League info card
    st.subheader("League Information")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Country", league["country"])
    with col2:
        st.metric("Code", league["code"])
    with col3:
        seasons = get_seasons_for_league(league_id)
        st.metric("Seasons", len(seasons))

    st.divider()

    # Seasons table
    st.subheader("Seasons")

    if not seasons:
        st.info("No seasons found for this league.")
        return

    st.markdown("Click a season to view teams:")

    # Table header
    cols = st.columns([2, 2, 2, 1, 1, 1])
    cols[0].markdown("**Season**")
    cols[1].markdown("**Start**")
    cols[2].markdown("**End**")
    cols[3].markdown("**Teams**")
    cols[4].markdown("**Games**")
    cols[5].markdown("**Current**")

    # Table rows
    for season in seasons:
        cols = st.columns([2, 2, 2, 1, 1, 1])

        with cols[0]:
            if st.button(season["name"], key=f"season_{season['id']}"):
                navigate_to("2_Teams", season_id=season["id"])

        cols[1].write(season["start_date"])
        cols[2].write(season["end_date"])
        cols[3].write(str(season["team_count"]))
        cols[4].write(str(season["game_count"]))
        cols[5].write("✓" if season["is_current"] else "")


def main():
    """Main page router based on URL parameters."""
    league_id = get_param("league_id")

    if league_id:
        render_detail_view(league_id)
    else:
        render_list_view()


if __name__ == "__main__":
    main()
