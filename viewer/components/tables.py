"""
Table Formatting Components

Functions to format entity data for display in Streamlit dataframes.

This module provides consistent table formatting for all entities,
handling column selection, ordering, and display formatting.

Usage:
    from viewer.components.tables import format_team_table

    teams = load_teams()
    df = format_team_table(teams)
    st.dataframe(df, use_container_width=True)
"""

import pandas as pd


def format_league_table(leagues: list[dict]) -> pd.DataFrame:
    """
    Format league data for table display.

    Args:
        leagues: List of league dictionaries.

    Returns:
        DataFrame with formatted columns.

    Expected dict keys: id, name, country, code, season_count
    """
    if not leagues:
        return pd.DataFrame(columns=["Name", "Country", "Code", "Seasons"])

    df = pd.DataFrame(leagues)

    # Select and rename columns
    columns = {
        "name": "Name",
        "country": "Country",
        "code": "Code",
        "season_count": "Seasons",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_season_table(seasons: list[dict]) -> pd.DataFrame:
    """
    Format season data for table display.

    Args:
        seasons: List of season dictionaries.

    Returns:
        DataFrame with formatted columns.

    Expected dict keys: id, name, start_date, end_date, team_count, game_count
    """
    if not seasons:
        return pd.DataFrame(columns=["Season", "Start", "End", "Teams", "Games"])

    df = pd.DataFrame(seasons)

    columns = {
        "name": "Season",
        "start_date": "Start",
        "end_date": "End",
        "team_count": "Teams",
        "game_count": "Games",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_team_table(teams: list[dict]) -> pd.DataFrame:
    """
    Format team data for table display.

    Args:
        teams: List of team dictionaries.

    Returns:
        DataFrame with formatted columns.

    Expected dict keys: id, name, code, country, league_name
    """
    if not teams:
        return pd.DataFrame(columns=["Name", "Code", "Country", "League"])

    df = pd.DataFrame(teams)

    columns = {
        "name": "Name",
        "code": "Code",
        "country": "Country",
        "league_name": "League",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_player_table(players: list[dict]) -> pd.DataFrame:
    """
    Format player data for table display.

    Args:
        players: List of player dictionaries.

    Returns:
        DataFrame with formatted columns.

    Expected dict keys: id, name, position, nationality, height_cm, team_name
    """
    if not players:
        return pd.DataFrame(
            columns=["Name", "Position", "Team", "Nationality", "Height"]
        )

    df = pd.DataFrame(players)

    # Format height
    if "height_cm" in df.columns:
        df["height_display"] = df["height_cm"].apply(
            lambda x: f"{x} cm" if pd.notna(x) and x else "-"
        )
    else:
        df["height_display"] = "-"

    columns = {
        "name": "Name",
        "position": "Position",
        "team_name": "Team",
        "nationality": "Nationality",
        "height_display": "Height",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_game_table(games: list[dict]) -> pd.DataFrame:
    """
    Format game data for table display.

    Args:
        games: List of game dictionaries.

    Returns:
        DataFrame with formatted columns.

    Expected dict keys: id, date, home_team_name, away_team_name,
                       home_score, away_score, status
    """
    if not games:
        return pd.DataFrame(columns=["Date", "Home", "Score", "Away", "Status"])

    df = pd.DataFrame(games)

    # Format score
    df["score_display"] = df.apply(
        lambda row: (
            f"{row.get('home_score', '-')} - {row.get('away_score', '-')}"
            if row.get("home_score") is not None
            else "-"
        ),
        axis=1,
    )

    # Format date
    if "date" in df.columns:
        df["date_display"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    else:
        df["date_display"] = "-"

    columns = {
        "date_display": "Date",
        "home_team_name": "Home",
        "score_display": "Score",
        "away_team_name": "Away",
        "status": "Status",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_roster_table(players: list[dict]) -> pd.DataFrame:
    """
    Format roster data for table display.

    Args:
        players: List of player dictionaries from roster.

    Returns:
        DataFrame with formatted columns.

    Expected dict keys: id, name, jersey_number, position, nationality
    """
    if not players:
        return pd.DataFrame(columns=["#", "Name", "Position", "Nationality"])

    df = pd.DataFrame(players)

    columns = {
        "jersey_number": "#",
        "name": "Name",
        "position": "Position",
        "nationality": "Nationality",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_box_score(stats: list[dict]) -> pd.DataFrame:
    """
    Format box score data for table display.

    Args:
        stats: List of player game stats dictionaries.

    Returns:
        DataFrame with full box score columns.

    Expected dict keys: player_name, minutes, points, rebounds_total,
                       assists, steals, blocks, turnovers, fouls,
                       field_goals_made, field_goals_attempted,
                       three_pointers_made, three_pointers_attempted,
                       free_throws_made, free_throws_attempted, plus_minus
    """
    if not stats:
        return pd.DataFrame(
            columns=[
                "Player",
                "MIN",
                "PTS",
                "REB",
                "AST",
                "STL",
                "BLK",
                "TO",
                "PF",
                "+/-",
            ]
        )

    df = pd.DataFrame(stats)

    # Format minutes (from seconds to MM:SS if needed)
    if "minutes" in df.columns:
        df["min_display"] = df["minutes"].apply(
            lambda x: (
                f"{x // 60}:{x % 60:02d}"
                if pd.notna(x) and isinstance(x, int) and x > 60
                else str(x) if pd.notna(x) else "-"
            )
        )
    else:
        df["min_display"] = "-"

    # Format shooting stats
    def make_shooting_formatter(made: str, att: str):
        """Create a formatter for shooting stats."""
        return lambda row: f"{row.get(made, 0)}-{row.get(att, 0)}"

    for stat in ["field_goals", "three_pointers", "free_throws"]:
        made_col = f"{stat}_made"
        att_col = f"{stat}_attempted"
        if made_col in df.columns and att_col in df.columns:
            df[f"{stat}_display"] = df.apply(
                make_shooting_formatter(made_col, att_col),
                axis=1,
            )

    columns = {
        "player_name": "Player",
        "min_display": "MIN",
        "points": "PTS",
        "rebounds_total": "REB",
        "assists": "AST",
        "steals": "STL",
        "blocks": "BLK",
        "turnovers": "TO",
        "fouls": "PF",
        "plus_minus": "+/-",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_game_log(games: list[dict]) -> pd.DataFrame:
    """
    Format player game log for table display.

    Args:
        games: List of game stat dictionaries for a player.

    Returns:
        DataFrame with game log columns.

    Expected dict keys: date, opponent_name, result, minutes, points,
                       rebounds_total, assists, plus_minus
    """
    if not games:
        return pd.DataFrame(
            columns=["Date", "Opponent", "Result", "MIN", "PTS", "REB", "AST", "+/-"]
        )

    df = pd.DataFrame(games)

    # Format date
    if "date" in df.columns:
        df["date_display"] = pd.to_datetime(df["date"]).dt.strftime("%m/%d")
    else:
        df["date_display"] = "-"

    columns = {
        "date_display": "Date",
        "opponent_name": "Opponent",
        "result": "Result",
        "minutes": "MIN",
        "points": "PTS",
        "rebounds_total": "REB",
        "assists": "AST",
        "plus_minus": "+/-",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


def format_career_history(history: list[dict]) -> pd.DataFrame:
    """
    Format player career history for table display.

    Args:
        history: List of season entries for a player.

    Returns:
        DataFrame with career history columns.

    Expected dict keys: season_name, team_name, games_played, ppg, rpg, apg
    """
    if not history:
        return pd.DataFrame(columns=["Season", "Team", "GP", "PPG", "RPG", "APG"])

    df = pd.DataFrame(history)

    columns = {
        "season_name": "Season",
        "team_name": "Team",
        "games_played": "GP",
        "ppg": "PPG",
        "rpg": "RPG",
        "apg": "APG",
    }

    result = df[[c for c in columns if c in df.columns]].copy()
    result.columns = [columns[c] for c in result.columns]

    return result


__all__ = [
    "format_league_table",
    "format_season_table",
    "format_team_table",
    "format_player_table",
    "format_game_table",
    "format_roster_table",
    "format_box_score",
    "format_game_log",
    "format_career_history",
]
