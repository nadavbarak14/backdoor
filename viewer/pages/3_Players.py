"""
Players Page

Browse players with filtering, career history, and game logs.

List view: Filterable table of players with team, position, nationality filters
Detail view: Player info card, career history by season, game log

Usage:
    - Access via sidebar navigation
    - Filter by season, team, position, nationality, or text search
    - Click player name to view details
    - From detail view, click teams/games to navigate to those pages
"""

import sys
from pathlib import Path

# Add project root to path for Streamlit page imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st  # noqa: E402

from src.models.game import Game, PlayerGameStats  # noqa: E402
from src.models.league import Season  # noqa: E402
from src.models.player import Player, PlayerTeamHistory  # noqa: E402
from src.models.stats import PlayerSeasonStats  # noqa: E402
from src.models.team import Team  # noqa: E402
from viewer.components.filters import (  # noqa: E402
    position_filter,
    search_box,
    season_filter,
    team_filter,
)
from viewer.components.navigation import (  # noqa: E402
    back_button,
    get_param,
    navigate_to,
)
from viewer.components.stats import entity_info_card, external_ids_display  # noqa: E402
from viewer.db import get_session  # noqa: E402

st.set_page_config(page_title="Players", page_icon="🏃", layout="wide")


# -----------------------------------------------------------------------------
# Data Fetching Functions
# -----------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_all_players() -> list[dict]:
    """
    Fetch all players with basic info.

    Returns:
        List of player dictionaries with id, name, position, nationality, height.
    """
    with get_session() as session:
        players = (
            session.query(Player).order_by(Player.last_name, Player.first_name).all()
        )
        return [
            {
                "id": str(p.id),
                "name": p.full_name,
                "position": p.position or "-",
                "nationality": p.nationality or "-",
                "height_cm": p.height_cm,
                "team_name": "-",  # Will be populated if filtered by season
            }
            for p in players
        ]


@st.cache_data(ttl=300)
def get_players_for_season(season_id: str) -> list[dict]:
    """
    Fetch players that played in a specific season.

    Args:
        season_id: UUID of the season.

    Returns:
        List of player dictionaries for players in that season.
    """
    with get_session() as session:
        histories = (
            session.query(PlayerTeamHistory)
            .join(Player)
            .join(Team)
            .filter(PlayerTeamHistory.season_id == season_id)
            .order_by(Player.last_name, Player.first_name)
            .all()
        )

        return [
            {
                "id": str(h.player_id),
                "name": h.player.full_name,
                "position": h.position or h.player.position or "-",
                "nationality": h.player.nationality or "-",
                "height_cm": h.player.height_cm,
                "team_name": h.team.name if h.team else "-",
                "team_id": str(h.team_id) if h.team_id else None,
            }
            for h in histories
        ]


@st.cache_data(ttl=300)
def get_all_seasons() -> list[dict]:
    """
    Fetch all seasons ordered by start date (most recent first).

    Returns:
        List of season dictionaries with id, name, and league info.
    """
    with get_session() as session:
        from src.models.league import League

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
def get_all_nationalities() -> list[str]:
    """
    Fetch distinct nationalities from players.

    Returns:
        List of unique nationality names.
    """
    with get_session() as session:
        nationalities = (
            session.query(Player.nationality)
            .distinct()
            .filter(Player.nationality.isnot(None))
            .order_by(Player.nationality)
            .all()
        )
        return [n[0] for n in nationalities if n[0]]


@st.cache_data(ttl=300)
def get_player_by_id(player_id: str) -> dict | None:
    """
    Fetch a single player by ID.

    Args:
        player_id: UUID of the player.

    Returns:
        Player dictionary or None if not found.
    """
    with get_session() as session:
        player = session.query(Player).filter(Player.id == player_id).first()
        if not player:
            return None

        # Calculate age if birth_date exists
        age = None
        if player.birth_date:
            from datetime import date

            today = date.today()
            age = (
                today.year
                - player.birth_date.year
                - (
                    (today.month, today.day)
                    < (player.birth_date.month, player.birth_date.day)
                )
            )

        return {
            "id": str(player.id),
            "name": player.full_name,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "position": player.position,
            "nationality": player.nationality,
            "height_cm": player.height_cm,
            "birth_date": (
                player.birth_date.strftime("%Y-%m-%d") if player.birth_date else None
            ),
            "age": age,
            "external_ids": player.external_ids,
        }


@st.cache_data(ttl=300)
def get_career_history(player_id: str) -> list[dict]:
    """
    Fetch career history for a player (seasons/teams with stats).

    Args:
        player_id: UUID of the player.

    Returns:
        List of season entries with team and stats.
    """
    with get_session() as session:
        # Get season stats for this player
        stats = (
            session.query(PlayerSeasonStats)
            .join(Season)
            .join(Team)
            .filter(PlayerSeasonStats.player_id == player_id)
            .order_by(Season.start_date.desc())
            .all()
        )

        if stats:
            return [
                {
                    "season_id": str(s.season_id),
                    "season_name": (
                        f"{s.season.league.name} - {s.season.name}"
                        if s.season.league
                        else s.season.name
                    ),
                    "team_id": str(s.team_id),
                    "team_name": s.team.name if s.team else "-",
                    "games_played": s.games_played,
                    "ppg": round(s.avg_points, 1) if s.avg_points else 0.0,
                    "rpg": round(s.avg_rebounds, 1) if s.avg_rebounds else 0.0,
                    "apg": round(s.avg_assists, 1) if s.avg_assists else 0.0,
                }
                for s in stats
            ]

        # Fallback: Get team history without stats
        histories = (
            session.query(PlayerTeamHistory)
            .join(Season)
            .join(Team)
            .filter(PlayerTeamHistory.player_id == player_id)
            .order_by(Season.start_date.desc())
            .all()
        )

        return [
            {
                "season_id": str(h.season_id),
                "season_name": (
                    f"{h.season.league.name} - {h.season.name}"
                    if h.season.league
                    else h.season.name
                ),
                "team_id": str(h.team_id),
                "team_name": h.team.name if h.team else "-",
                "games_played": "-",
                "ppg": "-",
                "rpg": "-",
                "apg": "-",
            }
            for h in histories
        ]


@st.cache_data(ttl=300)
def get_game_log(player_id: str, season_id: str | None = None) -> list[dict]:
    """
    Fetch game log for a player, optionally filtered by season.

    Args:
        player_id: UUID of the player.
        season_id: Optional UUID of season to filter by.

    Returns:
        List of game stat entries.
    """
    with get_session() as session:
        query = (
            session.query(PlayerGameStats)
            .join(Game)
            .join(Team, PlayerGameStats.team_id == Team.id)
            .filter(PlayerGameStats.player_id == player_id)
        )

        if season_id:
            query = query.filter(Game.season_id == season_id)

        game_stats = query.order_by(Game.game_date.desc()).limit(50).all()

        result = []
        for gs in game_stats:
            game = gs.game
            # Determine opponent
            player_team_id = str(gs.team_id)
            if str(game.home_team_id) == player_team_id:
                opponent = game.away_team
                team_score = game.home_score
                opp_score = game.away_score
            else:
                opponent = game.home_team
                team_score = game.away_score
                opp_score = game.home_score

            # Determine result
            if team_score is not None and opp_score is not None:
                if team_score > opp_score:
                    result_str = f"W {team_score}-{opp_score}"
                elif team_score < opp_score:
                    result_str = f"L {team_score}-{opp_score}"
                else:
                    result_str = f"T {team_score}-{opp_score}"
            else:
                result_str = "-"

            # Format minutes
            minutes = gs.minutes_played
            if minutes and minutes > 60:
                min_display = f"{minutes // 60}:{minutes % 60:02d}"
            else:
                min_display = str(minutes) if minutes else "0"

            result.append(
                {
                    "game_id": str(game.id),
                    "date": game.game_date.strftime("%Y-%m-%d"),
                    "opponent_id": str(opponent.id) if opponent else None,
                    "opponent_name": opponent.name if opponent else "Unknown",
                    "result": result_str,
                    "minutes": min_display,
                    "points": gs.points,
                    "rebounds_total": gs.total_rebounds,
                    "assists": gs.assists,
                    "plus_minus": gs.plus_minus,
                }
            )

        return result


@st.cache_data(ttl=300)
def get_seasons_for_player(player_id: str) -> list[dict]:
    """
    Fetch all seasons a player has game stats for.

    Args:
        player_id: UUID of the player.

    Returns:
        List of season dictionaries.
    """
    with get_session() as session:
        seasons = (
            session.query(Season)
            .join(Game)
            .join(PlayerGameStats)
            .filter(PlayerGameStats.player_id == player_id)
            .distinct()
            .order_by(Season.start_date.desc())
            .all()
        )

        return [
            {
                "id": str(s.id),
                "name": f"{s.league.name} - {s.name}" if s.league else s.name,
                "is_current": s.is_current,
            }
            for s in seasons
        ]


# -----------------------------------------------------------------------------
# Filtering Logic
# -----------------------------------------------------------------------------


def filter_players(
    players: list[dict],
    search: str,
    position: str | None,
    nationality: str | None,
    team_id: str | None,
) -> list[dict]:
    """
    Filter players by various criteria.

    Args:
        players: List of player dictionaries.
        search: Text search term.
        position: Position filter.
        nationality: Nationality filter.
        team_id: Team filter (only works if players have team_id).

    Returns:
        Filtered list of players.
    """
    result = players

    # Filter by search term
    if search:
        search_lower = search.lower()
        result = [p for p in result if search_lower in p["name"].lower()]

    # Filter by position
    if position:
        result = [
            p
            for p in result
            if p.get("position", "").lower().startswith(position.lower())
            or position.lower() in p.get("position", "").lower()
        ]

    # Filter by nationality
    if nationality:
        result = [p for p in result if p.get("nationality") == nationality]

    # Filter by team (if available)
    if team_id:
        result = [p for p in result if p.get("team_id") == team_id]

    return result


# -----------------------------------------------------------------------------
# View Rendering
# -----------------------------------------------------------------------------


def render_list_view():
    """Render the player list view with filters and table."""
    st.header("🏃 Players")

    # Fetch filter data
    all_seasons = get_all_seasons()
    all_teams = get_all_teams()
    all_nationalities = get_all_nationalities()

    # Filters in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_season = season_filter(all_seasons, key="player_season_filter")

    with col2:
        selected_team = team_filter(all_teams, key="player_team_filter")

    with col3:
        selected_position = position_filter(key="player_position_filter")

    with col4:
        # Nationality dropdown
        nationality_options = ["All Nationalities"] + all_nationalities
        selected_nationality_option = st.selectbox(
            "Nationality", nationality_options, key="player_nationality_filter"
        )
        selected_nationality = (
            None
            if selected_nationality_option == "All Nationalities"
            else selected_nationality_option
        )

    # Search box
    search = search_box("Search players by name...", key="player_search")

    # Fetch players based on season filter
    if selected_season:
        players = get_players_for_season(selected_season)
    else:
        players = get_all_players()

    # Apply additional filters
    filtered = filter_players(
        players, search, selected_position, selected_nationality, selected_team
    )

    # Display count
    if (
        search
        or selected_season
        or selected_position
        or selected_nationality
        or selected_team
    ):
        st.caption(f"Showing {len(filtered)} of {len(players)} players")
    else:
        st.caption(f"{len(filtered)} players")

    if not filtered:
        st.info("No players found matching your filters.")
        return

    # Table header
    st.markdown("Click a player name to view details:")
    cols = st.columns([3, 2, 2, 2, 1])
    cols[0].markdown("**Player**")
    cols[1].markdown("**Team**")
    cols[2].markdown("**Position**")
    cols[3].markdown("**Nationality**")
    cols[4].markdown("**Height**")

    # Table rows
    for player in filtered:
        cols = st.columns([3, 2, 2, 2, 1])

        with cols[0]:
            if st.button(player["name"], key=f"player_{player['id']}"):
                navigate_to("3_Players", player_id=player["id"])

        cols[1].write(player.get("team_name", "-"))
        cols[2].write(player.get("position", "-"))
        cols[3].write(player.get("nationality", "-"))

        height = player.get("height_cm")
        cols[4].write(f"{height} cm" if height else "-")


def render_detail_view(player_id: str):
    """
    Render the player detail view.

    Args:
        player_id: UUID of the player to display.
    """
    player = get_player_by_id(player_id)

    if not player:
        st.error("Player not found")
        if back_button():
            st.rerun()
        return

    # Back button
    if back_button("← Back to players"):
        st.rerun()

    # Player header
    st.header(f"🏃 {player['name']}")

    # Player info card
    info_data = {
        "Full Name": player["name"],
        "Position": player["position"] or "-",
        "Height": f"{player['height_cm']} cm" if player["height_cm"] else "-",
        "Nationality": player["nationality"] or "-",
        "Date of Birth": player["birth_date"] or "-",
        "Age": player["age"] or "-",
    }
    entity_info_card("Player Information", info_data)

    # External IDs
    external_ids_display(player.get("external_ids"))

    st.divider()

    # Career history
    st.subheader("Career History")

    career = get_career_history(player_id)

    if not career:
        st.info("No career history available.")
    else:
        # Career table header
        cols = st.columns([3, 2, 1, 1, 1, 1])
        cols[0].markdown("**Season**")
        cols[1].markdown("**Team**")
        cols[2].markdown("**GP**")
        cols[3].markdown("**PPG**")
        cols[4].markdown("**RPG**")
        cols[5].markdown("**APG**")

        # Career table rows
        for entry in career:
            cols = st.columns([3, 2, 1, 1, 1, 1])

            cols[0].write(entry["season_name"])

            with cols[1]:
                if entry["team_id"]:
                    if st.button(
                        entry["team_name"],
                        key=f"career_team_{entry['season_id']}_{entry['team_id']}",
                    ):
                        navigate_to("2_Teams", team_id=entry["team_id"])
                else:
                    st.write(entry["team_name"])

            cols[2].write(str(entry["games_played"]))
            cols[3].write(str(entry["ppg"]))
            cols[4].write(str(entry["rpg"]))
            cols[5].write(str(entry["apg"]))

    st.divider()

    # Game log
    st.subheader("Game Log")

    # Get seasons for this player
    player_seasons = get_seasons_for_player(player_id)

    if not player_seasons:
        st.info("No game log available.")
    else:
        # Season selector
        season_names = [s["name"] for s in player_seasons]
        selected_season_name = st.selectbox(
            "Select Season",
            season_names,
            index=0,
            key="gamelog_season_select",
        )

        # Get selected season ID
        selected_season = next(
            (s for s in player_seasons if s["name"] == selected_season_name), None
        )

        if selected_season:
            game_log = get_game_log(player_id, selected_season["id"])

            if not game_log:
                st.info("No games found for this season.")
            else:
                # Game log header
                cols = st.columns([2, 2, 2, 1, 1, 1, 1, 1])
                cols[0].markdown("**Date**")
                cols[1].markdown("**Opponent**")
                cols[2].markdown("**Result**")
                cols[3].markdown("**MIN**")
                cols[4].markdown("**PTS**")
                cols[5].markdown("**REB**")
                cols[6].markdown("**AST**")
                cols[7].markdown("**+/-**")

                # Game log rows
                for game in game_log:
                    cols = st.columns([2, 2, 2, 1, 1, 1, 1, 1])

                    with cols[0]:
                        if st.button(game["date"], key=f"game_{game['game_id']}"):
                            navigate_to("4_Games", game_id=game["game_id"])

                    with cols[1]:
                        if game["opponent_id"]:
                            if st.button(
                                game["opponent_name"],
                                key=f"opp_{game['game_id']}",
                            ):
                                navigate_to("2_Teams", team_id=game["opponent_id"])
                        else:
                            st.write(game["opponent_name"])

                    # Color-code result
                    result = game["result"]
                    if result.startswith("W"):
                        cols[2].markdown(f":green[{result}]")
                    elif result.startswith("L"):
                        cols[2].markdown(f":red[{result}]")
                    else:
                        cols[2].write(result)

                    cols[3].write(game["minutes"])
                    cols[4].write(str(game["points"]))
                    cols[5].write(str(game["rebounds_total"]))
                    cols[6].write(str(game["assists"]))

                    pm = game["plus_minus"]
                    if pm and pm > 0:
                        cols[7].markdown(f":green[+{pm}]")
                    elif pm and pm < 0:
                        cols[7].markdown(f":red[{pm}]")
                    else:
                        cols[7].write(str(pm) if pm else "-")


# -----------------------------------------------------------------------------
# Main Router
# -----------------------------------------------------------------------------


def main():
    """Main page router based on URL parameters."""
    player_id = get_param("player_id")

    if player_id:
        render_detail_view(player_id)
    else:
        render_list_view()


if __name__ == "__main__":
    main()
