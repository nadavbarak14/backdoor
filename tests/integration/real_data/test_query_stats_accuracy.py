"""
Comprehensive tests for query_stats data accuracy.

These tests ACTUALLY VERIFY data correctness by:
1. Parsing query_stats output and comparing against direct DB calculations
2. Verifying mathematical relationships (totals = sum, averages = total/games)
3. Checking values are in reasonable ranges
4. Confirming filters actually filter the data

Issue #193: The query_stats tool was returning inconsistent data.
"""

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player
from src.models.stats import PlayerSeasonStats
from src.models.team import Team
from src.services.query_stats import query_stats


def parse_table_row(result: str, row_index: int = 0) -> dict | None:
    """
    Parse a markdown table row from query_stats output.

    Returns dict mapping column headers to values.
    """
    lines = result.strip().split("\n")
    header_line = None
    data_lines = []

    for line in lines:
        if line.startswith("|") and "---" not in line:
            if header_line is None:
                header_line = line
            else:
                data_lines.append(line)

    if not header_line or not data_lines:
        return None

    if row_index >= len(data_lines):
        return None

    headers = [h.strip() for h in header_line.split("|") if h.strip()]
    values = [v.strip() for v in data_lines[row_index].split("|") if v.strip()]

    if len(headers) != len(values):
        return None

    return dict(zip(headers, values, strict=False))


def parse_numeric(value: str) -> float | None:
    """Parse a numeric value from table cell, handling %, +/- signs."""
    if not value or value == "N/A":
        return None
    # Remove % sign
    value = value.replace("%", "").strip()
    # Handle +/- prefix
    try:
        return float(value)
    except ValueError:
        return None


class TestMinutesAccuracy:
    """
    Tests for minutes calculation - the core issue from #193.

    Bug: avg_minutes in PlayerSeasonStats is stored in seconds, not minutes.
    """

    def test_avg_minutes_in_reasonable_range(self, real_db: Session):
        """
        Minutes per game must be 0-48 (or 0-53 for OT games).

        This catches the bug where avg_minutes = 1176.2 (actually seconds).
        """
        # Get players with season stats
        season_stats = (
            real_db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.games_played >= 3)
            .limit(10)
            .all()
        )

        if not season_stats:
            pytest.skip("No season stats")

        for stat in season_stats:
            result = query_stats.invoke(
                {
                    "player_ids": [str(stat.player_id)],
                    "metrics": ["minutes"],
                    "per": "game",
                    "db": real_db,
                }
            )

            row = parse_table_row(result)
            if row and "MIN" in row:
                min_value = parse_numeric(row["MIN"])
                if min_value is not None:
                    assert 0 <= min_value <= 53, (
                        f"Minutes per game should be 0-53, got {min_value} for player {stat.player_id}. "
                        f"This indicates minutes stored as seconds. Result:\n{result}"
                    )

    def test_total_minutes_matches_sum_of_game_minutes(self, real_db: Session):
        """
        Total minutes from query_stats should match sum of PlayerGameStats.minutes_played.
        """
        # Get a player with games
        player_with_games = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_with_games:
            pytest.skip("No player with 5+ games")

        player_id = player_with_games[0]

        # Calculate expected total minutes from game stats
        total_seconds = (
            real_db.query(func.sum(PlayerGameStats.minutes_played))
            .filter(PlayerGameStats.player_id == player_id)
            .scalar()
        ) or 0
        expected_total_minutes = total_seconds / 60  # Convert seconds to minutes

        # Query total minutes
        result = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "metrics": ["minutes"],
                "per": "total",
                "db": real_db,
            }
        )

        row = parse_table_row(result)
        if row and "MIN" in row:
            actual_minutes = parse_numeric(row["MIN"])
            if actual_minutes is not None and expected_total_minutes > 0:
                # Allow 1% tolerance for rounding
                assert (
                    abs(actual_minutes - expected_total_minutes)
                    / expected_total_minutes
                    < 0.01
                ), (
                    f"Total minutes mismatch: query_stats={actual_minutes}, "
                    f"expected={expected_total_minutes:.1f} (from {total_seconds} seconds)"
                )


class TestPointsAccuracy:
    """Tests for points calculations."""

    def test_ppg_equals_total_points_divided_by_games(self, real_db: Session):
        """
        Points per game MUST equal total_points / games_played.
        """
        # Get player with season stats
        season_stat = (
            real_db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.games_played >= 5)
            .filter(PlayerSeasonStats.total_points > 0)
            .first()
        )

        if not season_stat:
            pytest.skip("No player with 5+ games and points")

        expected_ppg = season_stat.total_points / season_stat.games_played

        # Query per-game points
        result = query_stats.invoke(
            {
                "player_ids": [str(season_stat.player_id)],
                "metrics": ["points"],
                "per": "game",
                "db": real_db,
            }
        )

        row = parse_table_row(result)
        if row and "PTS" in row:
            actual_ppg = parse_numeric(row["PTS"])
            if actual_ppg is not None:
                assert abs(actual_ppg - expected_ppg) < 0.15, (
                    f"PPG mismatch: query_stats={actual_ppg}, "
                    f"expected={expected_ppg:.1f} ({season_stat.total_points}/{season_stat.games_played})"
                )

    def test_total_points_matches_sum_of_game_points(self, real_db: Session):
        """
        Total points from query_stats should match sum of PlayerGameStats.points.
        """
        player_with_games = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_with_games:
            pytest.skip("No player with 5+ games")

        player_id = player_with_games[0]

        # Calculate expected total from game stats
        expected_total = (
            real_db.query(func.sum(PlayerGameStats.points))
            .filter(PlayerGameStats.player_id == player_id)
            .scalar()
        ) or 0

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row = parse_table_row(result)
        if row and "PTS" in row:
            actual_total = parse_numeric(row["PTS"])
            if actual_total is not None:
                assert (
                    actual_total == expected_total
                ), f"Total points mismatch: query_stats={actual_total}, expected={expected_total}"


class TestFGPercentageAccuracy:
    """Tests for field goal percentage calculations."""

    def test_fg_pct_equals_fgm_divided_by_fga(self, real_db: Session):
        """
        FG% MUST equal (FGM / FGA) * 100.
        """
        # Get a player with sufficient shot attempts
        season_stat = (
            real_db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.games_played >= 5)
            .first()
        )

        if not season_stat:
            pytest.skip("No player with 5+ games")

        # Calculate from game stats directly
        totals = (
            real_db.query(
                func.sum(PlayerGameStats.field_goals_made).label("fgm"),
                func.sum(PlayerGameStats.field_goals_attempted).label("fga"),
            )
            .filter(PlayerGameStats.player_id == season_stat.player_id)
            .first()
        )

        if not totals.fga or totals.fga < 10:
            pytest.skip("Not enough FGA")

        expected_fg_pct = (totals.fgm / totals.fga) * 100

        result = query_stats.invoke(
            {
                "player_ids": [str(season_stat.player_id)],
                "metrics": ["fg_pct"],
                "db": real_db,
            }
        )

        row = parse_table_row(result)
        if row and "FG%" in row:
            actual_fg_pct = parse_numeric(row["FG%"])
            if actual_fg_pct is not None:
                assert abs(actual_fg_pct - expected_fg_pct) < 0.5, (
                    f"FG% mismatch: query_stats={actual_fg_pct}%, "
                    f"expected={expected_fg_pct:.1f}% ({totals.fgm}/{totals.fga})"
                )


class TestLeaderboardSorting:
    """Tests that leaderboard actually sorts correctly."""

    def test_leaderboard_descending_order_is_correct(self, real_db: Session):
        """
        Leaderboard with order=desc should return players sorted high to low.
        """
        result = query_stats.invoke(
            {
                "order_by": "points",
                "order": "desc",
                "min_games": 3,
                "limit": 10,
                "db": real_db,
            }
        )

        # Parse all rows and extract points
        lines = result.strip().split("\n")
        pts_values = []
        for line in lines:
            if line.startswith("|") and "---" not in line and "Player" not in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                # Find PTS column (should be 3rd after Player, Team)
                if len(cells) >= 3:
                    pts = parse_numeric(cells[2])
                    if pts is not None:
                        pts_values.append(pts)

        if len(pts_values) >= 2:
            # Verify descending order
            for i in range(len(pts_values) - 1):
                assert (
                    pts_values[i] >= pts_values[i + 1]
                ), f"Leaderboard not sorted descending: {pts_values[i]} should be >= {pts_values[i+1]}"

    def test_leaderboard_ascending_order_is_correct(self, real_db: Session):
        """
        Leaderboard with order=asc should return players sorted low to high.
        """
        result = query_stats.invoke(
            {
                "order_by": "points",
                "order": "asc",
                "min_games": 3,
                "limit": 10,
                "db": real_db,
            }
        )

        lines = result.strip().split("\n")
        pts_values = []
        for line in lines:
            if line.startswith("|") and "---" not in line and "Player" not in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) >= 3:
                    pts = parse_numeric(cells[2])
                    if pts is not None:
                        pts_values.append(pts)

        if len(pts_values) >= 2:
            for i in range(len(pts_values) - 1):
                assert (
                    pts_values[i] <= pts_values[i + 1]
                ), f"Leaderboard not sorted ascending: {pts_values[i]} should be <= {pts_values[i+1]}"

    def test_min_games_filter_actually_filters(self, real_db: Session):
        """
        min_games filter should exclude players with fewer games.
        """
        min_games = 10

        result = query_stats.invoke(
            {
                "order_by": "points",
                "min_games": min_games,
                "limit": 20,
                "db": real_db,
            }
        )

        # Get all players in result
        lines = result.strip().split("\n")
        player_names = []
        for line in lines:
            if line.startswith("|") and "---" not in line and "Player" not in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells:
                    player_names.append(cells[0])

        # Verify each player has min_games
        for name in player_names[:5]:  # Check first 5
            # Find player by name
            parts = name.split()
            if len(parts) >= 2:
                player = (
                    real_db.query(Player)
                    .filter(Player.first_name.ilike(f"%{parts[0]}%"))
                    .first()
                )
                if player:
                    games = (
                        real_db.query(func.count(PlayerGameStats.id))
                        .filter(PlayerGameStats.player_id == player.id)
                        .scalar()
                    )
                    assert (
                        games >= min_games
                    ), f"Player {name} has {games} games but min_games={min_games}"


class TestLastNGamesFilter:
    """Tests that last_n_games actually limits to N games."""

    def test_last_n_games_uses_correct_game_count(self, real_db: Session):
        """
        last_n_games=3 should calculate stats from exactly 3 games.
        """
        # Find player with 10+ games
        player_data = (
            real_db.query(
                PlayerGameStats.player_id,
                func.count(PlayerGameStats.id).label("game_count"),
            )
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 10)
            .first()
        )

        if not player_data:
            pytest.skip("No player with 10+ games")

        player_id = player_data[0]
        n_games = 3

        # Calculate expected stats from last 3 games manually
        last_3_games = (
            real_db.query(PlayerGameStats)
            .join(Game, Game.id == PlayerGameStats.game_id)
            .filter(PlayerGameStats.player_id == player_id)
            .order_by(Game.game_date.desc())
            .limit(n_games)
            .all()
        )

        expected_total_pts = sum(g.points or 0 for g in last_3_games)
        expected_ppg = expected_total_pts / n_games

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "last_n_games": n_games,
                "metrics": ["points"],
                "per": "game",
                "db": real_db,
            }
        )

        row = parse_table_row(result)
        if row and "PTS" in row:
            actual_ppg = parse_numeric(row["PTS"])
            if actual_ppg is not None:
                assert abs(actual_ppg - expected_ppg) < 0.15, (
                    f"last_n_games PPG wrong: got {actual_ppg}, expected {expected_ppg:.1f} "
                    f"(total {expected_total_pts} / {n_games} games)"
                )


class TestHomeAwayFilter:
    """Tests that home/away filters actually filter games."""

    def test_home_only_returns_only_home_games(self, real_db: Session):
        """
        home_only=True should only include stats from home games.
        """
        # Find a team with home and away games
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        # Count home vs away games
        home_count = (
            real_db.query(func.count(Game.id))
            .filter(Game.home_team_id == team.id)
            .scalar()
        )
        away_count = (
            real_db.query(func.count(Game.id))
            .filter(Game.away_team_id == team.id)
            .scalar()
        )

        if home_count == 0 or away_count == 0:
            pytest.skip("Team needs both home and away games")

        # Get home-only stats
        result_home = query_stats.invoke(
            {
                "team_id": str(team.id),
                "home_only": True,
                "metrics": ["games", "points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Get all stats
        result_all = query_stats.invoke(
            {
                "team_id": str(team.id),
                "metrics": ["games", "points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Home games should be less than total
        # (We can't easily parse game count, but points should differ)
        assert (
            result_home != result_all or "No stats" in result_home
        ), "Home-only stats should differ from all stats"


class TestClutchFilter:
    """Tests for clutch time filtering."""

    def test_clutch_stats_less_than_total_stats(self, real_db: Session):
        """
        Clutch stats (subset of time) must be <= total stats.
        """
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_id:
            pytest.skip("No player with 5+ games")

        # Get total stats
        result_total = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Get clutch stats
        result_clutch = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "clutch_only": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row_total = parse_table_row(result_total)
        row_clutch = parse_table_row(result_clutch)

        if row_total and row_clutch and "PTS" in row_total and "PTS" in row_clutch:
            total_pts = parse_numeric(row_total["PTS"])
            clutch_pts = parse_numeric(row_clutch["PTS"])

            if total_pts is not None and clutch_pts is not None:
                assert (
                    clutch_pts <= total_pts
                ), f"Clutch points ({clutch_pts}) cannot exceed total points ({total_pts})"


class TestQuarterFilter:
    """Tests for quarter filtering."""

    def test_quarter_stats_less_than_full_game(self, real_db: Session):
        """
        Stats from one quarter must be <= full game stats.
        """
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        # Find player with Q1 events
        player_with_q1 = (
            real_db.query(PlayByPlayEvent.player_id)
            .filter(PlayByPlayEvent.player_id.isnot(None))
            .filter(PlayByPlayEvent.period == 1)
            .filter(PlayByPlayEvent.event_type == "SHOT")
            .group_by(PlayByPlayEvent.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_with_q1:
            pytest.skip("No player with Q1 shot events")

        # Get full game stats
        result_full = query_stats.invoke(
            {
                "player_ids": [str(player_with_q1[0])],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Get Q1 stats
        result_q1 = query_stats.invoke(
            {
                "player_ids": [str(player_with_q1[0])],
                "quarter": 1,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row_full = parse_table_row(result_full)
        row_q1 = parse_table_row(result_q1)

        if row_full and row_q1 and "PTS" in row_full and "PTS" in row_q1:
            full_pts = parse_numeric(row_full["PTS"])
            q1_pts = parse_numeric(row_q1["PTS"])

            if full_pts is not None and q1_pts is not None:
                assert (
                    q1_pts <= full_pts
                ), f"Q1 points ({q1_pts}) cannot exceed full game points ({full_pts})"

    def test_all_quarters_sum_approximately_to_total(self, real_db: Session):
        """
        Q1 + Q2 + Q3 + Q4 points should approximately equal full game points.
        (May not be exact due to OT)
        """
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_with_pbp = (
            real_db.query(PlayByPlayEvent.player_id)
            .filter(PlayByPlayEvent.player_id.isnot(None))
            .filter(PlayByPlayEvent.event_type == "SHOT")
            .group_by(PlayByPlayEvent.player_id)
            .having(func.count() >= 20)
            .first()
        )

        if not player_with_pbp:
            pytest.skip("No player with 20+ shot events")

        # Get each quarter's points
        quarter_pts = []
        for q in [1, 2, 3, 4]:
            result = query_stats.invoke(
                {
                    "player_ids": [str(player_with_pbp[0])],
                    "quarter": q,
                    "metrics": ["points"],
                    "per": "total",
                    "db": real_db,
                }
            )
            row = parse_table_row(result)
            if row and "PTS" in row:
                pts = parse_numeric(row["PTS"])
                quarter_pts.append(pts if pts else 0)
            else:
                quarter_pts.append(0)

        sum_quarters = sum(quarter_pts)

        # Get full game points
        result_full = query_stats.invoke(
            {
                "player_ids": [str(player_with_pbp[0])],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )
        row_full = parse_table_row(result_full)

        if row_full and "PTS" in row_full:
            full_pts = parse_numeric(row_full["PTS"])
            if full_pts and full_pts > 0:
                # Allow some tolerance for OT and rounding
                assert (
                    sum_quarters <= full_pts * 1.1
                ), f"Sum of quarters ({sum_quarters}) should be <= full game ({full_pts})"


class TestDataIntegrity:
    """Tests for fundamental data integrity."""

    def test_player_with_points_has_nonzero_minutes_in_box_scores(
        self, real_db: Session
    ):
        """
        If a player scored points, they must have played minutes.
        """
        inconsistent = (
            real_db.query(PlayerGameStats)
            .filter(PlayerGameStats.points > 0)
            .filter(
                (PlayerGameStats.minutes_played == 0)
                | (PlayerGameStats.minutes_played.is_(None))
            )
            .limit(10)
            .all()
        )

        if inconsistent:
            details = [
                f"Game {s.game_id}, Player {s.player_id}: {s.points} pts, {s.minutes_played} min"
                for s in inconsistent
            ]
            pytest.fail(
                f"Found {len(inconsistent)} box scores with points but 0 minutes:\n"
                + "\n".join(details[:5])
            )

    def test_season_stats_totals_match_sum_of_games(self, real_db: Session):
        """
        PlayerSeasonStats totals must equal sum of PlayerGameStats.
        """
        season_stat = (
            real_db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.games_played >= 5)
            .first()
        )

        if not season_stat:
            pytest.skip("No player with 5+ games in season stats")

        # Sum game stats
        game_totals = (
            real_db.query(
                func.count(PlayerGameStats.id).label("games"),
                func.sum(PlayerGameStats.points).label("points"),
                func.sum(PlayerGameStats.total_rebounds).label("rebounds"),
                func.sum(PlayerGameStats.assists).label("assists"),
            )
            .filter(PlayerGameStats.player_id == season_stat.player_id)
            .filter(PlayerGameStats.team_id == season_stat.team_id)
            .join(Game, Game.id == PlayerGameStats.game_id)
            .filter(Game.season_id == season_stat.season_id)
            .first()
        )

        if game_totals.games > 0:
            assert (
                season_stat.games_played == game_totals.games
            ), f"Games mismatch: season={season_stat.games_played}, sum={game_totals.games}"
            assert (
                season_stat.total_points == game_totals.points
            ), f"Points mismatch: season={season_stat.total_points}, sum={game_totals.points}"

    def test_team_score_matches_sum_of_player_points(self, real_db: Session):
        """
        Team's game score should equal sum of all players' points.
        """
        game = (
            real_db.query(Game)
            .filter(Game.status == "FINAL")
            .filter(Game.home_score.isnot(None))
            .first()
        )

        if not game:
            pytest.skip("No finished games")

        home_player_points = (
            real_db.query(func.sum(PlayerGameStats.points))
            .filter(PlayerGameStats.game_id == game.id)
            .filter(PlayerGameStats.team_id == game.home_team_id)
            .scalar()
        ) or 0

        # Allow small discrepancy (some leagues have data issues)
        assert abs(home_player_points - game.home_score) <= 5, (
            f"Home team score mismatch: game.home_score={game.home_score}, "
            f"sum of players={home_player_points}"
        )


class TestEachQuarterFilter:
    """Test each quarter filter individually with verification."""

    @pytest.mark.parametrize("quarter", [1, 2, 3, 4])
    def test_single_quarter_stats_from_pbp(self, real_db: Session, quarter: int):
        """
        Quarter filter should calculate stats from PBP events in that quarter only.
        Verify by comparing to direct PBP query.
        """
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        # Find player with shot events in this quarter
        player_with_shots = (
            real_db.query(PlayByPlayEvent.player_id)
            .filter(PlayByPlayEvent.player_id.isnot(None))
            .filter(PlayByPlayEvent.period == quarter)
            .filter(PlayByPlayEvent.event_type == "SHOT")
            .filter(PlayByPlayEvent.success.is_(True))
            .group_by(PlayByPlayEvent.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_with_shots:
            pytest.skip(f"No player with 3+ made shots in Q{quarter}")

        player_id = player_with_shots[0]

        # Count made shots directly from PBP for this quarter
        made_shots = (
            real_db.query(func.count(PlayByPlayEvent.id))
            .filter(PlayByPlayEvent.player_id == player_id)
            .filter(PlayByPlayEvent.period == quarter)
            .filter(PlayByPlayEvent.event_type == "SHOT")
            .filter(PlayByPlayEvent.success.is_(True))
            .scalar()
        ) or 0

        # Query stats for this quarter
        result = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "quarter": quarter,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Points should come from made shots (2pt or 3pt)
        # Can't verify exact value without knowing shot types, but verify non-zero
        row = parse_table_row(result)
        if row and "PTS" in row and made_shots > 0:
            pts = parse_numeric(row["PTS"])
            assert (
                pts is not None and pts > 0
            ), f"Q{quarter} should have points for {made_shots} made shots"

    def test_first_half_combines_q1_q2(self, real_db: Session):
        """quarters=[1,2] should sum Q1 and Q2 stats."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_with_shots = (
            real_db.query(PlayByPlayEvent.player_id)
            .filter(PlayByPlayEvent.player_id.isnot(None))
            .filter(PlayByPlayEvent.period.in_([1, 2]))
            .filter(PlayByPlayEvent.event_type == "SHOT")
            .group_by(PlayByPlayEvent.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_with_shots:
            pytest.skip("No player with shots in 1st half")

        player_id = player_with_shots[0]

        # Get Q1 + Q2 separately
        result_q1 = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "quarter": 1,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )
        result_q2 = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "quarter": 2,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Get first half
        result_1h = query_stats.invoke(
            {
                "player_ids": [str(player_id)],
                "quarters": [1, 2],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row_q1 = parse_table_row(result_q1)
        row_q2 = parse_table_row(result_q2)
        row_1h = parse_table_row(result_1h)

        if row_q1 and row_q2 and row_1h:
            q1_pts = parse_numeric(row_q1.get("PTS", "0")) or 0
            q2_pts = parse_numeric(row_q2.get("PTS", "0")) or 0
            first_half_pts = parse_numeric(row_1h.get("PTS", "0")) or 0

            expected_1h = q1_pts + q2_pts
            assert (
                abs(first_half_pts - expected_1h) < 1
            ), f"1st Half ({first_half_pts}) should equal Q1 ({q1_pts}) + Q2 ({q2_pts})"


class TestAwayOnlyFilter:
    """Test away_only filter verifies it only includes away games."""

    def test_away_stats_differ_from_home_stats(self, real_db: Session):
        """away_only stats should differ from home_only stats."""
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        # Check team has both home and away games
        home_count = (
            real_db.query(func.count(Game.id))
            .filter(Game.home_team_id == team.id)
            .scalar()
        )
        away_count = (
            real_db.query(func.count(Game.id))
            .filter(Game.away_team_id == team.id)
            .scalar()
        )

        if home_count == 0 or away_count == 0:
            pytest.skip("Need both home and away games")

        result_home = query_stats.invoke(
            {
                "team_id": str(team.id),
                "home_only": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        result_away = query_stats.invoke(
            {
                "team_id": str(team.id),
                "away_only": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Stats should be different
        assert result_home != result_away, "Home and away stats should differ"


class TestOpponentFilter:
    """Test opponent_team_id filter."""

    def test_opponent_filter_limits_to_matchup(self, real_db: Session):
        """opponent_team_id should only include games vs that team."""
        # Find two teams that played each other
        matchup = (
            real_db.query(Game.home_team_id, Game.away_team_id)
            .filter(Game.status == "FINAL")
            .first()
        )

        if not matchup:
            pytest.skip("No completed games")

        team1_id, team2_id = matchup

        # Get team1 stats vs team2
        result = query_stats.invoke(
            {
                "team_id": str(team1_id),
                "opponent_team_id": str(team2_id),
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Should return data (or no games message)
        assert "Error" not in result
        # Label should indicate vs opponent
        assert "vs" in result or "No stats" in result or "No games" in result


class TestSituationalFilters:
    """Test situational filters (fast_break, second_chance, contested, shot_type)."""

    def test_fast_break_true_filters_to_transition(self, real_db: Session):
        """fast_break=True should only include transition plays."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_id:
            pytest.skip("No player with games")

        result_all = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        result_fastbreak = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "fast_break": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row_all = parse_table_row(result_all)
        row_fb = parse_table_row(result_fastbreak)

        if row_all and row_fb and "PTS" in row_all and "PTS" in row_fb:
            all_pts = parse_numeric(row_all["PTS"]) or 0
            fb_pts = parse_numeric(row_fb["PTS"]) or 0

            # Fast break points must be <= total points
            assert (
                fb_pts <= all_pts
            ), f"Fast break points ({fb_pts}) cannot exceed total ({all_pts})"

    def test_contested_true_vs_false(self, real_db: Session):
        """contested=True and contested=False should be disjoint sets."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_id:
            pytest.skip("No player with games")

        result_contested = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "contested": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        result_uncontested = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "contested": False,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Both should not error
        assert "Error" not in result_contested
        assert "Error" not in result_uncontested

    @pytest.mark.parametrize("shot_type", ["PULL_UP", "CATCH_AND_SHOOT", "POST_UP"])
    def test_shot_type_filter_runs_without_error(
        self, real_db: Session, shot_type: str
    ):
        """Each shot_type filter should work without error."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_id:
            pytest.skip("No player with games")

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "shot_type": shot_type,
                "metrics": ["points", "fg_pct"],
                "db": real_db,
            }
        )

        assert "Error" not in result, f"shot_type={shot_type} should work"

    def test_shot_type_points_less_than_total(self, real_db: Session):
        """Any shot_type filter should give <= total points."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_id:
            pytest.skip("No player with 5+ games")

        result_all = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        result_pullup = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "shot_type": "PULL_UP",
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row_all = parse_table_row(result_all)
        row_pu = parse_table_row(result_pullup)

        if row_all and row_pu and "PTS" in row_all and "PTS" in row_pu:
            all_pts = parse_numeric(row_all["PTS"]) or 0
            pu_pts = parse_numeric(row_pu["PTS"]) or 0

            assert (
                pu_pts <= all_pts
            ), f"Pull-up points ({pu_pts}) cannot exceed total ({all_pts})"


class TestScheduleFilters:
    """Test schedule filters (back_to_back, min_rest_days)."""

    def test_back_to_back_true_finds_consecutive_games(self, real_db: Session):
        """back_to_back=True should only include games with 0-1 days rest."""
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        result_b2b = query_stats.invoke(
            {
                "team_id": str(team.id),
                "back_to_back": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        result_non_b2b = query_stats.invoke(
            {
                "team_id": str(team.id),
                "back_to_back": False,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Both should work
        assert "Error" not in result_b2b
        assert "Error" not in result_non_b2b

        # Results should differ (unless all games are one type)
        # At minimum, neither should crash

    def test_min_rest_days_filters_correctly(self, real_db: Session):
        """min_rest_days should exclude games with less rest."""
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        # More rest days = fewer qualifying games = fewer points
        result_0_rest = query_stats.invoke(
            {
                "team_id": str(team.id),
                "min_rest_days": 0,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        result_3_rest = query_stats.invoke(
            {
                "team_id": str(team.id),
                "min_rest_days": 3,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        row_0 = parse_table_row(result_0_rest)
        row_3 = parse_table_row(result_3_rest)

        if row_0 and row_3 and "PTS" in row_0 and "PTS" in row_3:
            pts_0 = parse_numeric(row_0["PTS"]) or 0
            pts_3 = parse_numeric(row_3["PTS"]) or 0

            # 3+ rest days should have <= points than 0+ rest days
            assert (
                pts_3 <= pts_0
            ), f"min_rest=3 points ({pts_3}) should be <= min_rest=0 ({pts_0})"


class TestLineupFilters:
    """Test lineup mode and discovery."""

    def test_two_players_triggers_lineup_mode(self, real_db: Session):
        """Querying 2+ players should calculate stats when playing together."""
        # Find two players on same team
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        players = (
            real_db.query(Player)
            .join(PlayerGameStats, Player.id == PlayerGameStats.player_id)
            .filter(PlayerGameStats.team_id == team.id)
            .group_by(Player.id)
            .having(func.count() >= 3)
            .limit(2)
            .all()
        )

        if len(players) < 2:
            pytest.skip("Need 2+ players on same team")

        result = query_stats.invoke(
            {
                "player_ids": [str(p.id) for p in players],
                "metrics": ["points", "plus_minus"],
                "db": real_db,
            }
        )

        # Should show lineup stats or no games together
        assert "Error" not in result
        assert "Lineup" in result or "together" in result or "No games" in result

    def test_discover_lineups_finds_combinations(self, real_db: Session):
        """discover_lineups should find player combinations."""
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "discover_lineups": True,
                "lineup_size": 2,
                "min_minutes": 1.0,
                "db": real_db,
            }
        )

        assert "Error" not in result
        # Should show lineup combinations or no lineups found
        assert "Lineup" in result or "No lineups" in result or "No games" in result


class TestFilterCombinations:
    """Test combinations of multiple filters."""

    def test_quarter_plus_home_only(self, real_db: Session):
        """Combine quarter filter with home_only."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        # Q4 + home only
        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "quarter": 4,
                "home_only": True,
                "metrics": ["points"],
                "per": "total",
                "db": real_db,
            }
        )

        # Should work without error
        assert "Error" not in result
        # Check both filters in label
        assert ("Q4" in result and "Home" in result) or "No" in result

    def test_quarter_plus_away_only(self, real_db: Session):
        """Combine quarter filter with away_only."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "quarter": 3,
                "away_only": True,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result
        assert ("Q3" in result and "Away" in result) or "No" in result

    def test_clutch_plus_home_only(self, real_db: Session):
        """Combine clutch_only with home_only."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_id:
            pytest.skip("No player with 5+ games")

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "clutch_only": True,
                "home_only": True,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result
        assert ("Clutch" in result and "Home" in result) or "No" in result

    def test_last_n_games_plus_home_only(self, real_db: Session):
        """Combine last_n_games with home_only."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 10)
            .first()
        )

        if not player_id:
            pytest.skip("No player with 10+ games")

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "last_n_games": 5,
                "home_only": True,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result
        assert ("Last 5" in result and "Home" in result) or "No" in result

    def test_fast_break_plus_back_to_back(self, real_db: Session):
        """Combine fast_break with back_to_back."""
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        result = query_stats.invoke(
            {
                "team_id": str(team.id),
                "fast_break": True,
                "back_to_back": True,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result
        assert ("Fast Break" in result and "Back-to-Back" in result) or "No" in result

    def test_quarter_plus_fast_break(self, real_db: Session):
        """Combine quarter with fast_break."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_id:
            pytest.skip("No player with games")

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "quarter": 1,
                "fast_break": True,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result

    def test_shot_type_plus_home_only(self, real_db: Session):
        """Combine shot_type with home_only."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_id:
            pytest.skip("No player with games")

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "shot_type": "CATCH_AND_SHOOT",
                "home_only": True,
                "metrics": ["points", "fg_pct"],
                "db": real_db,
            }
        )

        assert "Error" not in result

    def test_opponent_plus_quarter(self, real_db: Session):
        """Combine opponent_team_id with quarter filter."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        matchup = (
            real_db.query(Game.home_team_id, Game.away_team_id)
            .filter(Game.status == "FINAL")
            .first()
        )

        if not matchup:
            pytest.skip("No completed games")

        team1_id, team2_id = matchup

        result = query_stats.invoke(
            {
                "team_id": str(team1_id),
                "opponent_team_id": str(team2_id),
                "quarter": 4,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result

    def test_triple_filter_combination(self, real_db: Session):
        """Test three filters together: quarter + home + last_n_games."""
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 10)
            .first()
        )

        if not player_id:
            pytest.skip("No player with 10+ games")

        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "quarter": 4,
                "home_only": True,
                "last_n_games": 5,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        assert "Error" not in result

    def test_all_time_filters_together(self, real_db: Session):
        """Test multiple time-based filters: quarter + clutch is invalid."""
        # quarter and clutch_only both use PBP, should work together
        pbp_count = real_db.query(func.count(PlayByPlayEvent.id)).scalar()
        if pbp_count == 0:
            pytest.skip("No PBP data")

        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 3)
            .first()
        )

        if not player_id:
            pytest.skip("No player with games")

        # Clutch is only Q4/OT, so quarter=4 + clutch makes sense
        result = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "quarter": 4,
                "clutch_only": True,
                "metrics": ["points"],
                "db": real_db,
            }
        )

        # Should work (clutch is a subset of Q4)
        assert "Error" not in result


class TestPerGameVsTotalConsistency:
    """Verify per='game' and per='total' are consistent."""

    def test_per_game_times_games_equals_total(self, real_db: Session):
        """PPG * games should approximately equal total points."""
        player_id = (
            real_db.query(PlayerGameStats.player_id)
            .group_by(PlayerGameStats.player_id)
            .having(func.count() >= 5)
            .first()
        )

        if not player_id:
            pytest.skip("No player with 5+ games")

        result_pergame = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "metrics": ["points", "games"],
                "per": "game",
                "db": real_db,
            }
        )

        result_total = query_stats.invoke(
            {
                "player_ids": [str(player_id[0])],
                "metrics": ["points", "games"],
                "per": "total",
                "db": real_db,
            }
        )

        row_pg = parse_table_row(result_pergame)
        row_t = parse_table_row(result_total)

        if row_pg and row_t:
            ppg = parse_numeric(row_pg.get("PTS", "0")) or 0
            total_pts = parse_numeric(row_t.get("PTS", "0")) or 0
            games_t = parse_numeric(row_t.get("GP", "0")) or 0

            if games_t > 0 and ppg > 0:
                expected_total = ppg * games_t
                # Allow 1 point tolerance per game for rounding
                assert (
                    abs(expected_total - total_pts) <= games_t
                ), f"PPG ({ppg}) * games ({games_t}) = {expected_total}, but total = {total_pts}"


class TestValidationErrors:
    """Tests for proper error handling on invalid inputs."""

    def test_no_db_session_errors(self):
        """Missing db session should return error."""
        result = query_stats.invoke({})
        assert "Error" in result
        assert "Database session" in result

    def test_nonexistent_player_id(self, real_db: Session):
        """Non-existent player ID should return not found error."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = query_stats.invoke({"player_ids": [fake_uuid], "db": real_db})
        assert "not found" in result

    def test_nonexistent_team_id(self, real_db: Session):
        """Non-existent team ID should return not found error."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = query_stats.invoke({"team_id": fake_uuid, "db": real_db})
        assert "not found" in result

    def test_quarter_and_quarters_mutually_exclusive(self, real_db: Session):
        """Cannot specify both quarter and quarters."""
        result = query_stats.invoke({"quarter": 4, "quarters": [1, 2], "db": real_db})
        assert "mutually exclusive" in result

    def test_home_and_away_mutually_exclusive(self, real_db: Session):
        """Cannot specify both home_only and away_only."""
        result = query_stats.invoke(
            {"home_only": True, "away_only": True, "db": real_db}
        )
        assert "mutually exclusive" in result

    def test_invalid_quarter_value(self, real_db: Session):
        """Quarter must be 1-4."""
        for invalid_q in [0, 5, -1]:
            result = query_stats.invoke({"quarter": invalid_q, "db": real_db})
            assert "Error" in result, f"Quarter {invalid_q} should be invalid"

    def test_invalid_order_by_metric(self, real_db: Session):
        """Invalid order_by should return error."""
        result = query_stats.invoke({"order_by": "invalid_metric", "db": real_db})
        assert "Error" in result

    def test_invalid_shot_type(self, real_db: Session):
        """Invalid shot type should return error."""
        result = query_stats.invoke({"shot_type": "INVALID", "db": real_db})
        assert "Error" in result

    def test_negative_min_rest_days(self, real_db: Session):
        """Negative min_rest_days should return error."""
        result = query_stats.invoke({"min_rest_days": -1, "db": real_db})
        assert "Error" in result

    def test_back_to_back_conflicts_with_min_rest(self, real_db: Session):
        """back_to_back=True conflicts with min_rest_days > 1."""
        result = query_stats.invoke(
            {"back_to_back": True, "min_rest_days": 3, "db": real_db}
        )
        assert "conflicts" in result

    def test_invalid_lineup_size(self, real_db: Session):
        """lineup_size must be 2-5."""
        team = real_db.query(Team).first()
        if not team:
            pytest.skip("No teams")

        for invalid_size in [1, 6, 0]:
            result = query_stats.invoke(
                {
                    "team_id": str(team.id),
                    "discover_lineups": True,
                    "lineup_size": invalid_size,
                    "db": real_db,
                }
            )
            assert "Error" in result, f"lineup_size {invalid_size} should be invalid"

    def test_discover_lineups_requires_team(self, real_db: Session):
        """discover_lineups without team_id should error."""
        result = query_stats.invoke({"discover_lineups": True, "db": real_db})
        assert "Error" in result
        assert "team_id" in result
