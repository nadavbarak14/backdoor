"""
Stats Display Components

Components for displaying statistics, info cards, and comparisons.

This module provides styled displays for:
- Entity information cards
- Statistics rows and metrics
- Side-by-side comparisons

Usage:
    from viewer.components.stats import entity_info_card, stats_row

    entity_info_card("Team Info", {"Name": "Lakers", "Arena": "Crypto.com"})
    stats_row([("Games", 82), ("Wins", 52), ("Win %", "63.4%")])
"""

import streamlit as st


def entity_info_card(title: str, data: dict[str, str | int | None]) -> None:
    """
    Display an entity information card with key-value pairs.

    Args:
        title: Card title.
        data: Dictionary of field names to values.

    Example:
        >>> entity_info_card("Player Info", {
        ...     "Name": "LeBron James",
        ...     "Position": "Forward",
        ...     "Height": "206 cm",
        ... })
    """
    st.subheader(title)

    for key, value in data.items():
        display_value = value if value is not None else "-"
        st.markdown(f"**{key}:** {display_value}")


def stats_row(stats: list[tuple[str, str | int | float]]) -> None:
    """
    Display statistics in a horizontal row of columns.

    Args:
        stats: List of (label, value) tuples.

    Example:
        >>> stats_row([
        ...     ("Games", 82),
        ...     ("Points", 2150),
        ...     ("PPG", 26.2),
        ... ])
    """
    if not stats:
        return

    cols = st.columns(len(stats))

    for col, (label, value) in zip(cols, stats, strict=True):
        with col:
            st.metric(label, value)


def metric_card(
    label: str,
    value: str | int | float,
    delta: str | int | float | None = None,
    delta_color: str = "normal",
) -> None:
    """
    Display a single metric card.

    Args:
        label: Metric label.
        value: Main value to display.
        delta: Optional change indicator.
        delta_color: Color for delta ("normal", "inverse", "off").

    Example:
        >>> metric_card("Win Rate", "63.4%", "+5.2%")
    """
    st.metric(label, value, delta=delta, delta_color=delta_color)


def comparison_table(
    home: dict[str, str | int | float],
    away: dict[str, str | int | float],
    home_label: str = "Home",
    away_label: str = "Away",
) -> None:
    """
    Display side-by-side comparison of two sets of stats.

    Args:
        home: Stats for the home/left side.
        away: Stats for the away/right side.
        home_label: Label for home column.
        away_label: Label for away column.

    Example:
        >>> comparison_table(
        ...     {"Points": 105, "FG%": "48.2%"},
        ...     {"Points": 98, "FG%": "44.1%"},
        ...     "Lakers", "Celtics"
        ... )
    """
    # Get all stat keys
    all_keys = list(home.keys())

    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown(f"**{home_label}**")
    with col2:
        st.markdown("**Stat**")
    with col3:
        st.markdown(f"**{away_label}**")

    for key in all_keys:
        col1, col2, col3 = st.columns([2, 1, 2])

        home_val = home.get(key, "-")
        away_val = away.get(key, "-")

        with col1:
            st.write(home_val)
        with col2:
            st.write(key)
        with col3:
            st.write(away_val)


def quarter_scores_table(quarters: list[dict]) -> None:
    """
    Display quarter/period scores in a table.

    Args:
        quarters: List of dicts with 'period', 'home_score', 'away_score'.

    Example:
        >>> quarter_scores_table([
        ...     {"period": "Q1", "home_score": 28, "away_score": 25},
        ...     {"period": "Q2", "home_score": 30, "away_score": 22},
        ... ])
    """
    if not quarters:
        st.info("No quarter scores available")
        return

    import pandas as pd

    df = pd.DataFrame(quarters)

    # Pivot for display
    st.dataframe(df, use_container_width=True, hide_index=True)


def game_header(
    home_team: str,
    away_team: str,
    home_score: int | None,
    away_score: int | None,
    status: str,
    date: str | None = None,
    venue: str | None = None,
) -> None:
    """
    Display a prominent game header with scores.

    Args:
        home_team: Home team name.
        away_team: Away team name.
        home_score: Home team score (None if not started).
        away_score: Away team score (None if not started).
        status: Game status.
        date: Optional game date.
        venue: Optional venue name.

    Example:
        >>> game_header("Lakers", "Celtics", 105, 98, "finished",
        ...             date="2024-01-15", venue="Crypto.com Arena")
    """
    # Date and venue
    if date or venue:
        info_parts = []
        if date:
            info_parts.append(date)
        if venue:
            info_parts.append(venue)
        st.caption(" | ".join(info_parts))

    # Score display
    col1, col2, col3 = st.columns([2, 1, 2])

    with col1:
        st.markdown(f"### {home_team}")
        if home_score is not None:
            st.markdown(f"# {home_score}")
        else:
            st.markdown("# -")

    with col2:
        st.markdown("### ")
        st.markdown(f"**{status.upper()}**")

    with col3:
        st.markdown(f"### {away_team}")
        if away_score is not None:
            st.markdown(f"# {away_score}")
        else:
            st.markdown("# -")


def external_ids_display(external_ids: dict[str, str] | None) -> None:
    """
    Display external IDs in a formatted way.

    Args:
        external_ids: Dictionary of source to external ID.

    Example:
        >>> external_ids_display({"winner": "12345", "euroleague": "PLA123"})
    """
    if not external_ids:
        st.caption("No external IDs")
        return

    st.markdown("**External IDs:**")
    for source, ext_id in external_ids.items():
        st.caption(f"  {source}: `{ext_id}`")


__all__ = [
    "entity_info_card",
    "stats_row",
    "metric_card",
    "comparison_table",
    "quarter_scores_table",
    "game_header",
    "external_ids_display",
]
