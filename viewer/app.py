"""
Basketball Analytics - Internal Data Viewer

Home dashboard displaying data overview and navigation.

This is the main entry point for the Streamlit viewer app.
Run with: uv run streamlit run viewer/app.py
"""

import streamlit as st
from sqlalchemy import func

from src.models import Game, League, Player, Season, SyncLog, Team
from viewer.db import get_session

st.set_page_config(
    page_title="Basketball Analytics",
    page_icon="🏀",
    layout="wide",
)


@st.cache_data(ttl=300)
def get_entity_counts() -> dict[str, int]:
    """
    Get counts of all major entities in the database.

    Returns:
        Dictionary with entity names as keys and counts as values.
    """
    with get_session() as session:
        return {
            "leagues": session.query(func.count(League.id)).scalar() or 0,
            "seasons": session.query(func.count(Season.id)).scalar() or 0,
            "teams": session.query(func.count(Team.id)).scalar() or 0,
            "players": session.query(func.count(Player.id)).scalar() or 0,
            "games": session.query(func.count(Game.id)).scalar() or 0,
        }


@st.cache_data(ttl=60)
def get_recent_syncs() -> list[dict]:
    """
    Get recent sync operations.

    Returns:
        List of recent sync log entries as dictionaries.
    """
    with get_session() as session:
        logs = (
            session.query(SyncLog).order_by(SyncLog.started_at.desc()).limit(10).all()
        )
        return [
            {
                "source": log.source,
                "entity_type": log.entity_type,
                "status": log.status,
                "records_processed": log.records_processed,
                "records_created": log.records_created,
                "started_at": (
                    log.started_at.strftime("%Y-%m-%d %H:%M") if log.started_at else "-"
                ),
                "completed_at": (
                    log.completed_at.strftime("%Y-%m-%d %H:%M")
                    if log.completed_at
                    else "-"
                ),
            }
            for log in logs
        ]


@st.cache_data(ttl=300)
def get_last_sync_time() -> str | None:
    """
    Get the timestamp of the most recent completed sync.

    Returns:
        Formatted timestamp string or None if no syncs exist.
    """
    with get_session() as session:
        last_sync = (
            session.query(SyncLog)
            .filter(SyncLog.status == "COMPLETED")
            .order_by(SyncLog.completed_at.desc())
            .first()
        )
        if last_sync and last_sync.completed_at:
            return last_sync.completed_at.strftime("%Y-%m-%d %H:%M:%S")
        return None


def main():
    """Render the home dashboard."""
    st.title("🏀 Basketball Analytics")
    st.markdown("Internal data viewer for browsing synced basketball data.")

    # Data freshness indicator
    last_sync = get_last_sync_time()
    if last_sync:
        st.caption(f"Last sync: {last_sync}")
    else:
        st.caption("No sync data available")

    st.divider()

    # Entity counts
    st.subheader("Data Overview")

    counts = get_entity_counts()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Leagues", counts["leagues"])
    with col2:
        st.metric("Seasons", counts["seasons"])
    with col3:
        st.metric("Teams", counts["teams"])
    with col4:
        st.metric("Players", counts["players"])
    with col5:
        st.metric("Games", counts["games"])

    st.divider()

    # Quick navigation
    st.subheader("Quick Navigation")

    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)

    with nav_col1:
        st.page_link("pages/1_Leagues.py", label="📋 Leagues", use_container_width=True)
    with nav_col2:
        st.page_link("pages/2_Teams.py", label="👥 Teams", use_container_width=True)
    with nav_col3:
        st.page_link("pages/3_Players.py", label="🏃 Players", use_container_width=True)
    with nav_col4:
        st.page_link("pages/4_Games.py", label="🎮 Games", use_container_width=True)

    st.divider()

    # Recent sync activity
    st.subheader("Recent Sync Activity")

    syncs = get_recent_syncs()

    if syncs:
        # Create a simple table
        import pandas as pd

        df = pd.DataFrame(syncs)
        df.columns = [
            "Source",
            "Entity",
            "Status",
            "Processed",
            "Created",
            "Started",
            "Completed",
        ]

        # Color code status
        status_colors = {
            "COMPLETED": "color: green",
            "FAILED": "color: red",
            "STARTED": "color: orange",
        }

        def style_status(val):
            return status_colors.get(val, "")

        styled_df = df.style.map(style_status, subset=["Status"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("No sync activity recorded yet.")

    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
