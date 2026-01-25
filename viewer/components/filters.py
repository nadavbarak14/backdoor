"""
Filter Components

Reusable filter widgets for the viewer pages.

This module provides standardized filter widgets that:
- Accept data as list of dicts
- Return selected value(s)
- Maintain consistent styling

Usage:
    from viewer.components.filters import season_filter, search_box

    selected_season = season_filter(seasons_list)
    search_term = search_box("Search players...")
"""

from datetime import date

import streamlit as st


def season_filter(
    seasons: list[dict],
    key: str = "season_filter",
    label: str = "Season",
    include_all: bool = True,
) -> str | None:
    """
    Display a season dropdown filter.

    Args:
        seasons: List of season dicts with 'id' and 'name' keys.
        key: Unique key for the widget.
        label: Label to display above the dropdown.
        include_all: Whether to include an "All Seasons" option.

    Returns:
        Selected season ID or None if "All" is selected.

    Example:
        >>> seasons = [{"id": "abc", "name": "2023-24"}, ...]
        >>> selected = season_filter(seasons)
    """
    options = ["All Seasons"] if include_all else []
    options.extend([s["name"] for s in seasons])

    id_map = {s["name"]: s["id"] for s in seasons}

    selected = st.selectbox(label, options, key=key)

    if selected == "All Seasons" or selected is None:
        return None
    return id_map.get(selected)


def league_filter(
    leagues: list[dict],
    key: str = "league_filter",
    label: str = "League",
    include_all: bool = True,
) -> str | None:
    """
    Display a league dropdown filter.

    Args:
        leagues: List of league dicts with 'id' and 'name' keys.
        key: Unique key for the widget.
        label: Label to display above the dropdown.
        include_all: Whether to include an "All Leagues" option.

    Returns:
        Selected league ID or None if "All" is selected.

    Example:
        >>> leagues = [{"id": "abc", "name": "EuroLeague"}, ...]
        >>> selected = league_filter(leagues)
    """
    options = ["All Leagues"] if include_all else []
    options.extend([lg["name"] for lg in leagues])

    id_map = {lg["name"]: lg["id"] for lg in leagues}

    selected = st.selectbox(label, options, key=key)

    if selected == "All Leagues" or selected is None:
        return None
    return id_map.get(selected)


def team_filter(
    teams: list[dict],
    key: str = "team_filter",
    label: str = "Team",
    include_all: bool = True,
) -> str | None:
    """
    Display a team dropdown filter.

    Args:
        teams: List of team dicts with 'id' and 'name' keys.
        key: Unique key for the widget.
        label: Label to display above the dropdown.
        include_all: Whether to include an "All Teams" option.

    Returns:
        Selected team ID or None if "All" is selected.

    Example:
        >>> teams = [{"id": "abc", "name": "Lakers"}, ...]
        >>> selected = team_filter(teams)
    """
    options = ["All Teams"] if include_all else []
    options.extend([t["name"] for t in teams])

    id_map = {t["name"]: t["id"] for t in teams}

    selected = st.selectbox(label, options, key=key)

    if selected == "All Teams" or selected is None:
        return None
    return id_map.get(selected)


def position_filter(
    key: str = "position_filter",
    label: str = "Position",
    include_all: bool = True,
) -> str | None:
    """
    Display a position dropdown filter.

    Args:
        key: Unique key for the widget.
        label: Label to display above the dropdown.
        include_all: Whether to include an "All Positions" option.

    Returns:
        Selected position or None if "All" is selected.

    Example:
        >>> selected = position_filter()
    """
    positions = ["Guard", "Forward", "Center", "Guard-Forward", "Forward-Center"]
    options = ["All Positions"] if include_all else []
    options.extend(positions)

    selected = st.selectbox(label, options, key=key)

    if selected == "All Positions" or selected is None:
        return None
    return selected


def nationality_filter(
    nationalities: list[str],
    key: str = "nationality_filter",
    label: str = "Nationality",
    include_all: bool = True,
) -> str | None:
    """
    Display a nationality dropdown filter.

    Args:
        nationalities: List of nationality strings to populate the dropdown.
        key: Unique key for the widget.
        label: Label to display above the dropdown.
        include_all: Whether to include an "All Nationalities" option.

    Returns:
        Selected nationality or None if "All" is selected.

    Example:
        >>> nationalities = ["USA", "Spain", "France", ...]
        >>> selected = nationality_filter(nationalities)
    """
    options = ["All Nationalities"] if include_all else []
    options.extend(nationalities)

    selected = st.selectbox(label, options, key=key)

    if selected == "All Nationalities" or selected is None:
        return None
    return selected


def search_box(
    placeholder: str = "Search...",
    key: str = "search_box",
    label: str | None = None,
) -> str:
    """
    Display a text search input.

    Args:
        placeholder: Placeholder text for empty input.
        key: Unique key for the widget.
        label: Optional label above the input.

    Returns:
        Current search text (may be empty string).

    Example:
        >>> search = search_box("Search players...")
        >>> if search:
        ...     filtered = [p for p in players if search.lower() in p["name"].lower()]
    """
    return st.text_input(
        label or "Search",
        placeholder=placeholder,
        key=key,
        label_visibility="collapsed" if not label else "visible",
    )


def date_range_filter(
    key_prefix: str = "date_range",
    label: str = "Date Range",
    default_start: date | None = None,
    default_end: date | None = None,
) -> tuple[date | None, date | None]:
    """
    Display start and end date pickers.

    Args:
        key_prefix: Prefix for widget keys.
        label: Label to display above the date pickers.
        default_start: Default start date.
        default_end: Default end date.

    Returns:
        Tuple of (start_date, end_date), either may be None.

    Example:
        >>> start, end = date_range_filter()
        >>> if start and end:
        ...     filtered = [g for g in games if start <= g["date"] <= end]
    """
    st.write(label)
    col1, col2 = st.columns(2)

    with col1:
        start = st.date_input(
            "Start",
            value=default_start,
            key=f"{key_prefix}_start",
        )

    with col2:
        end = st.date_input(
            "End",
            value=default_end,
            key=f"{key_prefix}_end",
        )

    return start, end


def status_filter(
    key: str = "status_filter",
    label: str = "Status",
    include_all: bool = True,
) -> str | None:
    """
    Display a game status dropdown filter.

    Args:
        key: Unique key for the widget.
        label: Label to display above the dropdown.
        include_all: Whether to include an "All Statuses" option.

    Returns:
        Selected status or None if "All" is selected.

    Example:
        >>> selected = status_filter()
        >>> if selected:
        ...     filtered = [g for g in games if g["status"] == selected]
    """
    statuses = ["scheduled", "live", "finished", "postponed", "cancelled"]
    options = ["All Statuses"] if include_all else []
    options.extend(statuses)

    selected = st.selectbox(label, options, key=key)

    if selected == "All Statuses" or selected is None:
        return None
    return selected


__all__ = [
    "season_filter",
    "league_filter",
    "team_filter",
    "position_filter",
    "nationality_filter",
    "search_box",
    "date_range_filter",
    "status_filter",
]
