"""
Navigation Components

URL handling and entity linking helpers for the viewer.

This module provides functions for:
- Reading query parameters from the URL
- Building URLs with parameters
- Creating clickable links to entities
- Programmatic navigation

Usage:
    from viewer.components.navigation import get_param, link_to

    # Check if viewing detail
    team_id = get_param("team_id")

    # Create a link to a team
    link = link_to("Lakers", "Teams", team_id="abc-123")
"""

import streamlit as st


def get_param(name: str) -> str | None:
    """
    Get a query parameter from the current URL.

    Args:
        name: The parameter name to retrieve.

    Returns:
        The parameter value as a string, or None if not present.

    Example:
        >>> team_id = get_param("team_id")
        >>> if team_id:
        ...     show_team_detail(team_id)
    """
    params = st.query_params
    return params.get(name)


def set_params(**kwargs) -> None:
    """
    Update URL query parameters.

    Merges the provided parameters with existing ones.
    Pass None as a value to remove a parameter.

    Args:
        **kwargs: Parameter names and values to set.

    Example:
        >>> set_params(team_id="abc-123", season_id="xyz-456")
        >>> set_params(team_id=None)  # Remove team_id
    """
    current = dict(st.query_params)
    for key, value in kwargs.items():
        if value is None:
            current.pop(key, None)
        else:
            current[key] = str(value)
    st.query_params.update(current)


def clear_params() -> None:
    """
    Clear all query parameters from the URL.

    Example:
        >>> clear_params()  # Returns to list view
    """
    st.query_params.clear()


def make_link(page: str, **params) -> str:
    """
    Build a URL path with query parameters.

    Args:
        page: The page name (e.g., "Teams", "Players").
        **params: Query parameters to include.

    Returns:
        URL path string.

    Example:
        >>> url = make_link("Teams", team_id="abc-123")
        >>> # Returns: "/Teams?team_id=abc-123"
    """
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        return f"/{page}?{query}"
    return f"/{page}"


def link_to(label: str, page: str, **params) -> str:
    """
    Create a markdown link to an entity.

    Args:
        label: The display text for the link.
        page: The target page name.
        **params: Query parameters for the link.

    Returns:
        Markdown formatted link string.

    Example:
        >>> link = link_to("Lakers", "Teams", team_id="abc-123")
        >>> st.markdown(link)
    """
    url = make_link(page, **params)
    return f"[{label}]({url})"


def navigate_to(page: str, **params) -> None:
    """
    Navigate programmatically to a page with parameters.

    Updates the query parameters and triggers a rerun to show
    the new page/view.

    Args:
        page: The target page name.
        **params: Query parameters to set.

    Example:
        >>> if st.button("View Team"):
        ...     navigate_to("Teams", team_id=team["id"])
    """
    st.query_params.clear()
    if params:
        st.query_params.update({k: str(v) for k, v in params.items() if v is not None})
    st.switch_page(f"pages/{page}.py")


def back_button(label: str = "← Back to list") -> bool:
    """
    Display a back button that clears query params.

    Args:
        label: Button text to display.

    Returns:
        True if button was clicked.

    Example:
        >>> if back_button():
        ...     st.rerun()
    """
    if st.button(label):
        clear_params()
        return True
    return False


__all__ = [
    "get_param",
    "set_params",
    "clear_params",
    "make_link",
    "link_to",
    "navigate_to",
    "back_button",
]
