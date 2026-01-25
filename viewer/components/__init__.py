"""
Viewer Components Package

Reusable UI components for the internal data viewer.

This package provides:
    - navigation: URL handling and entity linking
    - filters: Filter widgets (dropdowns, search, date pickers)
    - tables: Data table formatters
    - stats: Statistics cards and displays

Usage:
    from viewer.components.navigation import get_param, link_to
    from viewer.components.filters import season_filter, search_box
    from viewer.components.tables import format_team_table
    from viewer.components.stats import entity_info_card
"""

from viewer.components.filters import (
    date_range_filter,
    league_filter,
    nationality_filter,
    position_filter,
    search_box,
    season_filter,
    status_filter,
    team_filter,
)
from viewer.components.navigation import (
    get_param,
    link_to,
    make_link,
    navigate_to,
    set_params,
)
from viewer.components.stats import (
    comparison_table,
    entity_info_card,
    external_ids_display,
    game_header,
    metric_card,
    quarter_scores_table,
    stats_row,
)
from viewer.components.tables import (
    format_box_score,
    format_career_history,
    format_game_log,
    format_game_table,
    format_league_table,
    format_player_table,
    format_roster_table,
    format_season_table,
    format_team_table,
)

__all__ = [
    # navigation
    "get_param",
    "set_params",
    "make_link",
    "link_to",
    "navigate_to",
    # filters
    "season_filter",
    "league_filter",
    "team_filter",
    "position_filter",
    "nationality_filter",
    "search_box",
    "date_range_filter",
    "status_filter",
    # tables
    "format_league_table",
    "format_season_table",
    "format_team_table",
    "format_player_table",
    "format_game_table",
    "format_roster_table",
    "format_box_score",
    "format_game_log",
    "format_career_history",
    # stats
    "entity_info_card",
    "external_ids_display",
    "stats_row",
    "metric_card",
    "comparison_table",
    "game_header",
    "quarter_scores_table",
]
