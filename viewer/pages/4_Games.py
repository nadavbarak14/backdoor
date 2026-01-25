"""
Games Page

Browse games with box scores and play-by-play.

List view: Filterable table of games with date, teams, score, status filters
Detail view: Game header, quarter scores, team stats comparison, box scores, play-by-play

Usage:
    - Access via sidebar navigation
    - Filter by season, team, date range, or status
    - Click game score to view details
    - From detail view, click teams/players to navigate to those pages
"""

import sys
from datetime import date
from pathlib import Path

# Add project root to path for Streamlit page imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st  # noqa: E402

from src.models.game import Game, PlayerGameStats, TeamGameStats  # noqa: E402
from src.models.league import League, Season  # noqa: E402
from src.models.play_by_play import PlayByPlayEvent  # noqa: E402
from src.models.team import Team  # noqa: E402
from viewer.components.filters import (  # noqa: E402
    season_filter,
    status_filter,
    team_filter,
)
from viewer.components.navigation import (  # noqa: E402
    back_button,
    get_param,
    navigate_to,
)
from viewer.components.stats import (  # noqa: E402
    comparison_table,
    game_header,
)
from viewer.db import get_session  # noqa: E402

st.set_page_config(page_title="Games", page_icon="🎮", layout="wide")


# -----------------------------------------------------------------------------
# Data Fetching Functions
# -----------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_all_games(limit: int = 100) -> list[dict]:
    """
    Fetch recent games ordered by date.

    Args:
        limit: Maximum number of games to return.

    Returns:
        List of game dictionaries.
    """
    with get_session() as session:
        games = session.query(Game).order_by(Game.game_date.desc()).limit(limit).all()
        return [
            {
                "id": str(g.id),
                "date": g.game_date.strftime("%Y-%m-%d"),
                "datetime": g.game_date,
                "home_team_id": str(g.home_team_id),
                "home_team_name": g.home_team.name if g.home_team else "Unknown",
                "away_team_id": str(g.away_team_id),
                "away_team_name": g.away_team.name if g.away_team else "Unknown",
                "home_score": g.home_score,
                "away_score": g.away_score,
                "status": g.status,
                "season_id": str(g.season_id),
            }
            for g in games
        ]


@st.cache_data(ttl=300)
def get_games_for_season(season_id: str, limit: int = 200) -> list[dict]:
    """
    Fetch games for a specific season.

    Args:
        season_id: UUID of the season.
        limit: Maximum number of games to return.

    Returns:
        List of game dictionaries for that season.
    """
    with get_session() as session:
        games = (
            session.query(Game)
            .filter(Game.season_id == season_id)
            .order_by(Game.game_date.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(g.id),
                "date": g.game_date.strftime("%Y-%m-%d"),
                "datetime": g.game_date,
                "home_team_id": str(g.home_team_id),
                "home_team_name": g.home_team.name if g.home_team else "Unknown",
                "away_team_id": str(g.away_team_id),
                "away_team_name": g.away_team.name if g.away_team else "Unknown",
                "home_score": g.home_score,
                "away_score": g.away_score,
                "status": g.status,
                "season_id": str(g.season_id),
            }
            for g in games
        ]


@st.cache_data(ttl=300)
def get_all_seasons() -> list[dict]:
    """
    Fetch all seasons ordered by start date (most recent first).

    Returns:
        List of season dictionaries.
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
                "is_current": s.is_current,
            }
            for s in seasons
        ]


@st.cache_data(ttl=300)
def get_all_teams() -> list[dict]:
    """
    Fetch all teams.

    Returns:
        List of team dictionaries with id and name.
    """
    with get_session() as session:
        teams = session.query(Team).order_by(Team.name).all()
        return [{"id": str(t.id), "name": t.name} for t in teams]


@st.cache_data(ttl=300)
def get_game_by_id(game_id: str) -> dict | None:
    """
    Fetch a single game by ID with full details.

    Args:
        game_id: UUID of the game.

    Returns:
        Game dictionary or None if not found.
    """
    with get_session() as session:
        game = session.query(Game).filter(Game.id == game_id).first()
        if not game:
            return None

        return {
            "id": str(game.id),
            "date": game.game_date.strftime("%Y-%m-%d"),
            "time": game.game_date.strftime("%H:%M"),
            "home_team_id": str(game.home_team_id),
            "home_team_name": game.home_team.name if game.home_team else "Unknown",
            "away_team_id": str(game.away_team_id),
            "away_team_name": game.away_team.name if game.away_team else "Unknown",
            "home_score": game.home_score,
            "away_score": game.away_score,
            "status": game.status,
            "venue": game.venue,
            "attendance": game.attendance,
            "season_name": (
                f"{game.season.league.name} - {game.season.name}"
                if game.season and game.season.league
                else game.season.name if game.season else "-"
            ),
            "external_ids": game.external_ids,
        }


@st.cache_data(ttl=300)
def get_team_game_stats(game_id: str) -> dict:
    """
    Fetch team-level stats for a game.

    Args:
        game_id: UUID of the game.

    Returns:
        Dictionary with 'home' and 'away' team stats.
    """
    with get_session() as session:
        stats = (
            session.query(TeamGameStats).filter(TeamGameStats.game_id == game_id).all()
        )

        result = {"home": None, "away": None}

        for s in stats:
            key = "home" if s.is_home else "away"

            # Calculate percentages
            fg_pct = (
                f"{(s.field_goals_made / s.field_goals_attempted * 100):.1f}%"
                if s.field_goals_attempted > 0
                else "-"
            )
            three_pct = (
                f"{(s.three_pointers_made / s.three_pointers_attempted * 100):.1f}%"
                if s.three_pointers_attempted > 0
                else "-"
            )
            ft_pct = (
                f"{(s.free_throws_made / s.free_throws_attempted * 100):.1f}%"
                if s.free_throws_attempted > 0
                else "-"
            )

            result[key] = {
                "Points": s.points,
                "FG": f"{s.field_goals_made}-{s.field_goals_attempted}",
                "FG%": fg_pct,
                "3P": f"{s.three_pointers_made}-{s.three_pointers_attempted}",
                "3P%": three_pct,
                "FT": f"{s.free_throws_made}-{s.free_throws_attempted}",
                "FT%": ft_pct,
                "Rebounds": s.total_rebounds,
                "Off Reb": s.offensive_rebounds,
                "Def Reb": s.defensive_rebounds,
                "Assists": s.assists,
                "Turnovers": s.turnovers,
                "Steals": s.steals,
                "Blocks": s.blocks,
                "Fouls": s.personal_fouls,
                "Fast Break Pts": s.fast_break_points,
                "Pts in Paint": s.points_in_paint,
                "2nd Chance Pts": s.second_chance_points,
                "Bench Pts": s.bench_points,
            }

        return result


@st.cache_data(ttl=300)
def get_box_score(game_id: str, team_id: str) -> list[dict]:
    """
    Fetch player box score for a team in a game.

    Args:
        game_id: UUID of the game.
        team_id: UUID of the team.

    Returns:
        List of player stat dictionaries.
    """
    with get_session() as session:
        stats = (
            session.query(PlayerGameStats)
            .filter(
                PlayerGameStats.game_id == game_id,
                PlayerGameStats.team_id == team_id,
            )
            .order_by(
                PlayerGameStats.is_starter.desc(), PlayerGameStats.minutes_played.desc()
            )
            .all()
        )

        result = []
        for s in stats:
            # Format minutes
            if s.minutes_played and s.minutes_played > 60:
                min_display = f"{s.minutes_played // 60}:{s.minutes_played % 60:02d}"
            else:
                min_display = str(s.minutes_played) if s.minutes_played else "0"

            result.append(
                {
                    "player_id": str(s.player_id),
                    "player_name": s.player.full_name if s.player else "Unknown",
                    "is_starter": s.is_starter,
                    "minutes": min_display,
                    "points": s.points,
                    "fg": f"{s.field_goals_made}-{s.field_goals_attempted}",
                    "three_pt": f"{s.three_pointers_made}-{s.three_pointers_attempted}",
                    "ft": f"{s.free_throws_made}-{s.free_throws_attempted}",
                    "rebounds_total": s.total_rebounds,
                    "offensive_rebounds": s.offensive_rebounds,
                    "defensive_rebounds": s.defensive_rebounds,
                    "assists": s.assists,
                    "steals": s.steals,
                    "blocks": s.blocks,
                    "turnovers": s.turnovers,
                    "fouls": s.personal_fouls,
                    "plus_minus": s.plus_minus,
                    "efficiency": s.efficiency,
                }
            )

        return result


@st.cache_data(ttl=300)
def get_play_by_play(game_id: str, period: int | None = None) -> list[dict]:
    """
    Fetch play-by-play events for a game.

    Args:
        game_id: UUID of the game.
        period: Optional period to filter by.

    Returns:
        List of play-by-play event dictionaries.
    """
    with get_session() as session:
        query = session.query(PlayByPlayEvent).filter(
            PlayByPlayEvent.game_id == game_id
        )

        if period:
            query = query.filter(PlayByPlayEvent.period == period)

        events = query.order_by(PlayByPlayEvent.event_number).all()

        return [
            {
                "event_number": e.event_number,
                "period": e.period,
                "clock": e.clock,
                "event_type": e.event_type,
                "event_subtype": e.event_subtype,
                "team_name": e.team.name if e.team else "-",
                "player_name": e.player.full_name if e.player else "-",
                "description": e.description or "-",
                "success": e.success,
            }
            for e in events
        ]


@st.cache_data(ttl=300)
def get_periods_for_game(game_id: str) -> list[int]:
    """
    Fetch distinct periods for a game.

    Args:
        game_id: UUID of the game.

    Returns:
        List of period numbers.
    """
    with get_session() as session:
        periods = (
            session.query(PlayByPlayEvent.period)
            .filter(PlayByPlayEvent.game_id == game_id)
            .distinct()
            .order_by(PlayByPlayEvent.period)
            .all()
        )
        return [p[0] for p in periods]


# -----------------------------------------------------------------------------
# Filtering Logic
# -----------------------------------------------------------------------------


def filter_games(
    games: list[dict],
    team_id: str | None,
    start_date: date | None,
    end_date: date | None,
    status: str | None,
) -> list[dict]:
    """
    Filter games by various criteria.

    Args:
        games: List of game dictionaries.
        team_id: Team filter (shows games involving this team).
        start_date: Start date filter.
        end_date: End date filter.
        status: Status filter.

    Returns:
        Filtered list of games.
    """
    result = games

    # Filter by team
    if team_id:
        result = [
            g
            for g in result
            if g["home_team_id"] == team_id or g["away_team_id"] == team_id
        ]

    # Filter by date range
    if start_date:
        result = [g for g in result if g["datetime"].date() >= start_date]

    if end_date:
        result = [g for g in result if g["datetime"].date() <= end_date]

    # Filter by status
    if status:
        result = [g for g in result if g["status"].lower() == status.lower()]

    return result


# -----------------------------------------------------------------------------
# View Rendering
# -----------------------------------------------------------------------------


def render_list_view():
    """Render the game list view with filters and table."""
    st.header("🎮 Games")

    # Fetch filter data
    all_seasons = get_all_seasons()
    all_teams = get_all_teams()

    # Filters in columns
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_season = season_filter(all_seasons, key="game_season_filter")

    with col2:
        selected_team = team_filter(all_teams, key="game_team_filter")

    with col3:
        selected_status = status_filter(key="game_status_filter")

    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=None, key="game_start_date")
    with col2:
        end_date = st.date_input("End Date", value=None, key="game_end_date")

    # Fetch games based on season filter
    if selected_season:
        games = get_games_for_season(selected_season)
    else:
        games = get_all_games()

    # Apply additional filters
    filtered = filter_games(games, selected_team, start_date, end_date, selected_status)

    # Display count
    if selected_team or start_date or end_date or selected_status:
        st.caption(f"Showing {len(filtered)} of {len(games)} games")
    else:
        st.caption(f"{len(filtered)} games")

    if not filtered:
        st.info("No games found matching your filters.")
        return

    # Table header
    st.markdown("Click a score to view game details:")
    cols = st.columns([2, 3, 2, 3, 2])
    cols[0].markdown("**Date**")
    cols[1].markdown("**Home**")
    cols[2].markdown("**Score**")
    cols[3].markdown("**Away**")
    cols[4].markdown("**Status**")

    # Table rows
    for game in filtered:
        cols = st.columns([2, 3, 2, 3, 2])

        cols[0].write(game["date"])

        # Home team - clickable
        with cols[1]:
            if st.button(game["home_team_name"], key=f"home_{game['id']}"):
                navigate_to("2_Teams", team_id=game["home_team_id"])

        # Score - clickable to game detail
        with cols[2]:
            if game["home_score"] is not None and game["away_score"] is not None:
                score_str = f"{game['home_score']} - {game['away_score']}"
            else:
                score_str = "vs"
            if st.button(score_str, key=f"game_{game['id']}"):
                navigate_to("4_Games", game_id=game["id"])

        # Away team - clickable
        with cols[3]:
            if st.button(game["away_team_name"], key=f"away_{game['id']}"):
                navigate_to("2_Teams", team_id=game["away_team_id"])

        # Status - color coded
        status = game["status"]
        if status.lower() == "finished" or status.lower() == "final":
            cols[4].markdown(f":green[{status}]")
        elif status.lower() == "live":
            cols[4].markdown(f":red[{status}]")
        elif status.lower() == "scheduled":
            cols[4].markdown(f":blue[{status}]")
        else:
            cols[4].write(status)


def render_detail_view(game_id: str):
    """
    Render the game detail view.

    Args:
        game_id: UUID of the game to display.
    """
    game = get_game_by_id(game_id)

    if not game:
        st.error("Game not found")
        if back_button():
            st.rerun()
        return

    # Back button
    if back_button("← Back to games"):
        st.rerun()

    # Game header with scores
    game_header(
        home_team=game["home_team_name"],
        away_team=game["away_team_name"],
        home_score=game["home_score"],
        away_score=game["away_score"],
        status=game["status"],
        date=game["date"],
        venue=game["venue"],
    )

    # Team links
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if st.button(f"View {game['home_team_name']}", key="view_home_team"):
            navigate_to("2_Teams", team_id=game["home_team_id"])
    with col3:
        if st.button(f"View {game['away_team_name']}", key="view_away_team"):
            navigate_to("2_Teams", team_id=game["away_team_id"])

    st.caption(f"Season: {game['season_name']}")
    if game["attendance"]:
        st.caption(f"Attendance: {game['attendance']:,}")

    st.divider()

    # Team stats comparison
    team_stats = get_team_game_stats(game_id)

    if team_stats["home"] and team_stats["away"]:
        st.subheader("Team Stats Comparison")
        comparison_table(
            team_stats["home"],
            team_stats["away"],
            game["home_team_name"],
            game["away_team_name"],
        )
        st.divider()

    # Box scores
    st.subheader("Box Score")

    # Toggle between home and away
    box_team = st.radio(
        "Select Team",
        [game["home_team_name"], game["away_team_name"]],
        horizontal=True,
        key="box_score_team",
    )

    box_team_id = (
        game["home_team_id"]
        if box_team == game["home_team_name"]
        else game["away_team_id"]
    )

    box_score = get_box_score(game_id, box_team_id)

    if not box_score:
        st.info("No box score data available.")
    else:
        # Separate starters and bench
        starters = [p for p in box_score if p["is_starter"]]
        bench = [p for p in box_score if not p["is_starter"]]

        def render_box_score_section(players: list[dict], title: str):
            """Render a section of the box score."""
            if not players:
                return

            st.markdown(f"**{title}**")

            # Box score header
            cols = st.columns([3, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1])
            cols[0].markdown("**Player**")
            cols[1].markdown("**MIN**")
            cols[2].markdown("**PTS**")
            cols[3].markdown("**FG**")
            cols[4].markdown("**3PT**")
            cols[5].markdown("**FT**")
            cols[6].markdown("**REB**")
            cols[7].markdown("**AST**")
            cols[8].markdown("**STL**")
            cols[9].markdown("**BLK**")
            cols[10].markdown("**TO**")
            cols[11].markdown("**+/-**")

            # Totals for summary
            total_pts = 0
            total_reb = 0
            total_ast = 0

            for player in players:
                cols = st.columns([3, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 1])

                # Player name - clickable
                with cols[0]:
                    if st.button(
                        player["player_name"],
                        key=f"box_{title}_{player['player_id']}",
                    ):
                        navigate_to("3_Players", player_id=player["player_id"])

                cols[1].write(player["minutes"])
                cols[2].write(str(player["points"]))
                cols[3].write(player["fg"])
                cols[4].write(player["three_pt"])
                cols[5].write(player["ft"])
                cols[6].write(str(player["rebounds_total"]))
                cols[7].write(str(player["assists"]))
                cols[8].write(str(player["steals"]))
                cols[9].write(str(player["blocks"]))
                cols[10].write(str(player["turnovers"]))

                pm = player["plus_minus"]
                if pm and pm > 0:
                    cols[11].markdown(f":green[+{pm}]")
                elif pm and pm < 0:
                    cols[11].markdown(f":red[{pm}]")
                else:
                    cols[11].write(str(pm) if pm else "-")

                total_pts += player["points"]
                total_reb += player["rebounds_total"]
                total_ast += player["assists"]

            return total_pts, total_reb, total_ast

        # Render starters
        starter_totals = (
            render_box_score_section(starters, "Starters") if starters else (0, 0, 0)
        )

        # Render bench
        bench_totals = (
            render_box_score_section(bench, "Bench") if bench else (0, 0, 0)
        )

        # Team totals
        total_pts = starter_totals[0] + bench_totals[0]
        total_reb = starter_totals[1] + bench_totals[1]
        total_ast = starter_totals[2] + bench_totals[2]

        st.markdown(
            f"**Team Totals:** {total_pts} PTS | {total_reb} REB | {total_ast} AST"
        )

    st.divider()

    # Play-by-play (collapsible)
    with st.expander("Play-by-Play"):
        periods = get_periods_for_game(game_id)

        if not periods:
            st.info("No play-by-play data available.")
        else:
            # Period selector
            period_labels = {
                1: "Q1",
                2: "Q2",
                3: "Q3",
                4: "Q4",
                5: "OT1",
                6: "OT2",
                7: "OT3",
            }

            period_options = ["All"] + [period_labels.get(p, f"P{p}") for p in periods]
            selected_period_label = st.selectbox(
                "Select Period",
                period_options,
                key="pbp_period",
            )

            # Get period number
            if selected_period_label == "All":
                selected_period = None
            else:
                # Find the period number
                reverse_labels = {v: k for k, v in period_labels.items()}
                selected_period = reverse_labels.get(selected_period_label)
                if selected_period is None:
                    # Parse P{n} format
                    try:
                        selected_period = int(selected_period_label[1:])
                    except (ValueError, IndexError):
                        selected_period = None

            pbp = get_play_by_play(game_id, selected_period)

            if not pbp:
                st.info("No events found for this period.")
            else:
                # PBP header
                cols = st.columns([1, 1, 2, 2, 4])
                cols[0].markdown("**Q**")
                cols[1].markdown("**Clock**")
                cols[2].markdown("**Team**")
                cols[3].markdown("**Player**")
                cols[4].markdown("**Action**")

                for event in pbp:
                    cols = st.columns([1, 1, 2, 2, 4])

                    cols[0].write(str(event["period"]))
                    cols[1].write(event["clock"])
                    cols[2].write(event["team_name"])
                    cols[3].write(event["player_name"])

                    # Format description with event type
                    event_desc = event["description"]
                    event_type = event["event_type"]
                    if event["event_subtype"]:
                        event_type = f"{event_type} ({event['event_subtype']})"

                    if event["success"] is True:
                        cols[4].markdown(f":green[{event_type}] - {event_desc}")
                    elif event["success"] is False:
                        cols[4].markdown(f":red[{event_type}] - {event_desc}")
                    else:
                        cols[4].write(f"{event_type} - {event_desc}")


# -----------------------------------------------------------------------------
# Main Router
# -----------------------------------------------------------------------------


def main():
    """Main page router based on URL parameters."""
    game_id = get_param("game_id")

    if game_id:
        render_detail_view(game_id)
    else:
        render_list_view()


if __name__ == "__main__":
    main()
