"""
Sync Page

Real-time data synchronization with progress tracking.

Features:
- View sync history and status
- Start new syncs with live progress display
- Monitor sync progress in real-time via SSE streaming

Usage:
    - Access via sidebar navigation
    - Select season and source to sync
    - Watch real-time progress as games are synced
"""

import sys
from pathlib import Path

# Add project root to path for Streamlit page imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json  # noqa: E402

import httpx  # noqa: E402
import streamlit as st  # noqa: E402

from src.models.league import Season  # noqa: E402
from src.models.sync import SyncLog  # noqa: E402
from viewer.db import get_session  # noqa: E402

st.set_page_config(page_title="Sync", page_icon="🔄", layout="wide")


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

API_BASE_URL = "http://localhost:8000/api/v1"
AVAILABLE_SOURCES = ["winner"]  # Add more as they become available


# -----------------------------------------------------------------------------
# Data Fetching Functions
# -----------------------------------------------------------------------------


@st.cache_data(ttl=60)
def get_sync_logs(limit: int = 20) -> list[dict]:
    """
    Fetch recent sync logs.

    Args:
        limit: Maximum number of logs to return.

    Returns:
        List of sync log dictionaries.
    """
    with get_session() as session:
        logs = (
            session.query(SyncLog)
            .order_by(SyncLog.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(log.id),
                "source": log.source,
                "entity_type": log.entity_type,
                "status": log.status,
                "season_name": log.season.name if log.season else None,
                "records_processed": log.records_processed or 0,
                "records_created": log.records_created or 0,
                "records_skipped": log.records_skipped or 0,
                "error_message": log.error_message,
                "started_at": log.started_at,
                "completed_at": log.completed_at,
                "duration": (
                    (log.completed_at - log.started_at).total_seconds()
                    if log.completed_at and log.started_at
                    else None
                ),
            }
            for log in logs
        ]


@st.cache_data(ttl=300)
def get_seasons() -> list[dict]:
    """
    Fetch all seasons.

    Returns:
        List of season dictionaries.
    """
    with get_session() as session:
        seasons = session.query(Season).order_by(Season.start_date.desc()).all()
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "league": s.league.name if s.league else "Unknown",
            }
            for s in seasons
        ]


# -----------------------------------------------------------------------------
# Sync Functions
# -----------------------------------------------------------------------------


def stream_sync(source: str, season_id: str, include_pbp: bool) -> None:
    """
    Stream sync progress from the API and update UI in real-time.

    Args:
        source: Data source name.
        season_id: External season identifier.
        include_pbp: Whether to include play-by-play data.
    """
    url = f"{API_BASE_URL}/sync/{source}/season/{season_id}/stream"
    params = {"include_pbp": str(include_pbp).lower()}

    # Create placeholders for real-time updates
    status_container = st.container()
    progress_bar = st.progress(0, text="Starting sync...")
    log_container = st.container()

    events_log = []
    current_game = 0
    total_games = 0
    synced_count = 0
    error_count = 0

    try:
        with httpx.Client(timeout=None) as client:  # noqa: SIM117
            with client.stream("POST", url, params=params) as response:
                if response.status_code != 200:
                    st.error(f"Failed to start sync: HTTP {response.status_code}")
                    return

                buffer = ""
                for chunk in response.iter_text():
                    buffer += chunk

                    # Process complete events (double newline separated)
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)

                        # Parse SSE format
                        event_type = None
                        event_data = None

                        for line in event_str.split("\n"):
                            if line.startswith("event: "):
                                event_type = line[7:]
                            elif line.startswith("data: "):
                                try:
                                    event_data = json.loads(line[6:])
                                except json.JSONDecodeError:
                                    continue

                        if not event_data:
                            continue

                        # Process event
                        if event_type == "start":
                            total_games = event_data.get("total", 0)
                            skipped = event_data.get("skipped", 0)
                            with status_container:
                                st.info(
                                    f"🚀 Starting sync: {total_games} games to sync, "
                                    f"{skipped} already synced"
                                )

                        elif event_type == "progress":
                            current_game = event_data.get("current", 0)
                            game_id = event_data.get("game_id", "")
                            if total_games > 0:
                                progress = current_game / total_games
                                progress_bar.progress(
                                    progress,
                                    text=f"Syncing game {current_game}/{total_games}: {game_id}",
                                )

                        elif event_type == "synced":
                            synced_count += 1
                            game_id = event_data.get("game_id", "")
                            events_log.append(f"✅ Synced: {game_id}")

                        elif event_type == "error":
                            error_count += 1
                            game_id = event_data.get("game_id", "")
                            error = event_data.get("error", "Unknown error")
                            events_log.append(f"❌ Error ({game_id}): {error}")

                        elif event_type == "complete":
                            sync_log = event_data.get("sync_log", {})
                            status = sync_log.get("status", "UNKNOWN")
                            progress_bar.progress(1.0, text="Sync complete!")

                            with status_container:
                                if status == "COMPLETED":
                                    st.success(
                                        f"✅ Sync completed! "
                                        f"Created: {sync_log.get('records_created', 0)}, "
                                        f"Skipped: {sync_log.get('records_skipped', 0)}"
                                    )
                                elif status == "FAILED":
                                    st.error(
                                        f"❌ Sync failed: {sync_log.get('error_message', 'Unknown error')}"
                                    )
                                else:
                                    st.warning(
                                        f"⚠️ Sync finished with status: {status}"
                                    )

                        # Update log display (show last 10 events)
                        with log_container:
                            if events_log:
                                st.text("\n".join(events_log[-10:]))

        # Clear cache to show updated data
        get_sync_logs.clear()

    except httpx.ConnectError:
        st.error(
            "❌ Cannot connect to API server. "
            "Make sure the server is running: `uv run uvicorn src.main:app`"
        )
    except Exception as e:
        st.error(f"❌ Sync error: {e}")


# -----------------------------------------------------------------------------
# UI Components
# -----------------------------------------------------------------------------


def render_sync_history() -> None:
    """Render the sync history table."""
    st.subheader("📋 Recent Sync History")

    logs = get_sync_logs()

    if not logs:
        st.info("No sync history yet. Start a sync above!")
        return

    # Format for display
    for log in logs:
        status_icon = {
            "COMPLETED": "✅",
            "FAILED": "❌",
            "STARTED": "🔄",
            "PARTIAL": "⚠️",
        }.get(log["status"], "❓")

        duration_str = f"{log['duration']:.1f}s" if log["duration"] else "In progress"

        with st.expander(
            f"{status_icon} {log['source']} / {log['season_name'] or log['entity_type']} "
            f"- {log['started_at'].strftime('%Y-%m-%d %H:%M')}"
        ):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Status", log["status"])
            with col2:
                st.metric("Created", log["records_created"])
            with col3:
                st.metric("Skipped", log["records_skipped"])
            with col4:
                st.metric("Duration", duration_str)

            if log["error_message"]:
                st.error(f"Error: {log['error_message']}")


def render_sync_form() -> None:
    """Render the sync form with source and season selection."""
    st.subheader("🔄 Start New Sync")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        source = st.selectbox(
            "Data Source",
            options=AVAILABLE_SOURCES,
            format_func=lambda x: x.title(),
            key="sync_source",
        )

    with col2:
        # Allow manual entry of season ID for new seasons
        season_input = st.text_input(
            "Season ID",
            value="2024-25",
            help="Enter the season identifier (e.g., '2024-25')",
            key="sync_season",
        )

    with col3:
        include_pbp = st.checkbox(
            "Include PBP",
            value=False,
            help="Include play-by-play data (slower)",
            key="sync_pbp",
        )

    if st.button("🚀 Start Sync", type="primary", use_container_width=True):
        if not season_input:
            st.warning("Please enter a season ID")
        else:
            st.divider()
            stream_sync(source, season_input, include_pbp)


def render_status_check() -> None:
    """Render API status check."""
    st.subheader("🔌 API Status")

    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{API_BASE_URL}/sync/status")
            if response.status_code == 200:
                data = response.json()
                st.success("✅ API server is running")

                for source in data.get("sources", []):
                    status = "🟢 Enabled" if source["enabled"] else "🔴 Disabled"
                    st.write(f"**{source['name'].title()}**: {status}")
            else:
                st.warning(f"API returned status {response.status_code}")
    except httpx.ConnectError:
        st.error(
            "❌ Cannot connect to API server.\n\n"
            "Start it with: `uv run uvicorn src.main:app --reload`"
        )
    except Exception as e:
        st.error(f"Error checking API: {e}")


# -----------------------------------------------------------------------------
# Main Page
# -----------------------------------------------------------------------------


def main() -> None:
    """Main page entry point."""
    st.title("🔄 Data Sync")
    st.write("Synchronize data from external sources with real-time progress tracking.")

    # API status in sidebar
    with st.sidebar:
        render_status_check()

    # Main content
    tab1, tab2 = st.tabs(["Start Sync", "History"])

    with tab1:
        render_sync_form()

    with tab2:
        if st.button("🔄 Refresh", key="refresh_history"):
            get_sync_logs.clear()
        render_sync_history()


if __name__ == "__main__":
    main()
