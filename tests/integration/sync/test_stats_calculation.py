"""
Integration tests for StatsCalculationService.

Tests the service's ability to:
- Calculate season totals from game stats
- Calculate averages correctly
- Create and update PlayerSeasonStats records
- Recalculate without creating duplicates
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.player import Player
from src.models.stats import PlayerSeasonStats
from src.models.team import Team
from src.services.stats_calculation import StatsCalculationService


def create_test_data(test_db: Session) -> dict:
    """Create test data for stats calculation tests."""
    # Create league
    league = League(name="Test League", code="TEST", country="Test")
    test_db.add(league)
    test_db.flush()

    # Create season
    season = Season(
        league_id=league.id,
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 6, 30),
        is_current=True,
    )
    test_db.add(season)
    test_db.flush()

    # Create teams
    home_team = Team(
        name="Home Team", short_name="HOM", city="Home City", country="Test"
    )
    away_team = Team(
        name="Away Team", short_name="AWY", city="Away City", country="Test"
    )
    test_db.add_all([home_team, away_team])
    test_db.flush()

    # Create player
    player = Player(
        first_name="Test",
        last_name="Player",
        nationality="Test",
        position="SG",
    )
    test_db.add(player)
    test_db.flush()

    return {
        "league": league,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
        "player": player,
    }


def create_game(
    test_db: Session,
    season_id,
    home_team_id,
    away_team_id,
    game_date: datetime,
) -> Game:
    """Create a game for testing."""
    game = Game(
        season_id=season_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        game_date=game_date,
        status="FINAL",
        home_score=100,
        away_score=95,
    )
    test_db.add(game)
    test_db.flush()
    return game


def create_player_game_stats(
    test_db: Session,
    game_id,
    player_id,
    team_id,
    points: int = 20,
    field_goals_made: int = 8,
    field_goals_attempted: int = 16,
    three_pointers_made: int = 2,
    three_pointers_attempted: int = 5,
    free_throws_made: int = 2,
    free_throws_attempted: int = 2,
    rebounds: int = 5,
    assists: int = 4,
    turnovers: int = 2,
    is_starter: bool = True,
) -> PlayerGameStats:
    """Create player game stats for testing."""
    stats = PlayerGameStats(
        game_id=game_id,
        player_id=player_id,
        team_id=team_id,
        minutes_played=1800,  # 30 minutes
        is_starter=is_starter,
        points=points,
        field_goals_made=field_goals_made,
        field_goals_attempted=field_goals_attempted,
        two_pointers_made=field_goals_made - three_pointers_made,
        two_pointers_attempted=field_goals_attempted - three_pointers_attempted,
        three_pointers_made=three_pointers_made,
        three_pointers_attempted=three_pointers_attempted,
        free_throws_made=free_throws_made,
        free_throws_attempted=free_throws_attempted,
        offensive_rebounds=2,
        defensive_rebounds=rebounds - 2,
        total_rebounds=rebounds,
        assists=assists,
        turnovers=turnovers,
        steals=1,
        blocks=1,
        personal_fouls=2,
        plus_minus=5,
    )
    test_db.add(stats)
    test_db.flush()
    return stats


class TestCalculateSeasonTotalsIntegration:
    """Integration tests for calculating season totals from game stats."""

    def test_calculate_season_totals(self, test_db: Session):
        """Test that season totals correctly sum all game stats."""
        data = create_test_data(test_db)

        # Create 3 games with known stats
        game_stats_data = [
            {"points": 20, "field_goals_made": 8, "field_goals_attempted": 15},
            {"points": 25, "field_goals_made": 10, "field_goals_attempted": 18},
            {"points": 15, "field_goals_made": 6, "field_goals_attempted": 14},
        ]

        for i, stats_data in enumerate(game_stats_data):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            create_player_game_stats(
                test_db,
                game.id,
                data["player"].id,
                data["home_team"].id,
                points=stats_data["points"],
                field_goals_made=stats_data["field_goals_made"],
                field_goals_attempted=stats_data["field_goals_attempted"],
            )

        test_db.commit()

        # Calculate season stats
        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        # Verify totals
        assert result is not None
        assert result.games_played == 3
        assert result.total_points == 60  # 20 + 25 + 15
        assert result.total_field_goals_made == 24  # 8 + 10 + 6
        assert result.total_field_goals_attempted == 47  # 15 + 18 + 14

    def test_calculate_season_totals_all_stats(self, test_db: Session):
        """Test that all stat categories are summed correctly."""
        data = create_test_data(test_db)

        # Create 2 games with detailed stats
        for i in range(2):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            create_player_game_stats(
                test_db,
                game.id,
                data["player"].id,
                data["home_team"].id,
                points=20,
                field_goals_made=8,
                field_goals_attempted=16,
                three_pointers_made=2,
                three_pointers_attempted=5,
                free_throws_made=2,
                free_throws_attempted=3,
                rebounds=6,
                assists=5,
                turnovers=2,
            )

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is not None
        assert result.games_played == 2
        assert result.total_points == 40
        assert result.total_field_goals_made == 16
        assert result.total_field_goals_attempted == 32
        assert result.total_three_pointers_made == 4
        assert result.total_three_pointers_attempted == 10
        assert result.total_free_throws_made == 4
        assert result.total_free_throws_attempted == 6
        assert result.total_rebounds == 12
        assert result.total_assists == 10
        assert result.total_turnovers == 4


class TestCalculateSeasonAveragesIntegration:
    """Integration tests for calculating season averages."""

    def test_calculate_season_averages(self, test_db: Session):
        """Test averages are correctly calculated by dividing totals by games."""
        data = create_test_data(test_db)

        # Create 4 games with different point totals
        game_points = [20, 24, 28, 16]  # Total: 88, Avg: 22.0

        for i, pts in enumerate(game_points):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            create_player_game_stats(
                test_db,
                game.id,
                data["player"].id,
                data["home_team"].id,
                points=pts,
            )

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is not None
        assert result.games_played == 4
        assert result.total_points == 88
        assert result.avg_points == 22.0  # 88 / 4 = 22.0


class TestCalculatePercentagesIntegration:
    """Integration tests for calculating shooting percentages."""

    def test_calculate_field_goal_pct(self, test_db: Session):
        """Test FG% = FGM/FGA correctly calculated from game totals."""
        data = create_test_data(test_db)

        # Create games: total 18 FGM / 40 FGA = 45%
        stats = [
            {"fgm": 8, "fga": 16},  # 50%
            {"fgm": 6, "fga": 14},  # 42.9%
            {"fgm": 4, "fga": 10},  # 40%
        ]

        for i, s in enumerate(stats):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            create_player_game_stats(
                test_db,
                game.id,
                data["player"].id,
                data["home_team"].id,
                points=s["fgm"] * 2,
                field_goals_made=s["fgm"],
                field_goals_attempted=s["fga"],
            )

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is not None
        assert result.total_field_goals_made == 18
        assert result.total_field_goals_attempted == 40
        # FG% = 18/40 = 0.45 (stored as decimal)
        assert result.field_goal_pct == pytest.approx(0.45, rel=0.01)

    def test_calculate_true_shooting_pct(self, test_db: Session):
        """Test TS% = PTS / (2 * (FGA + 0.44 * FTA)) * 100."""
        data = create_test_data(test_db)

        # Create 2 games
        # Total: 40 pts, 30 FGA, 10 FTA
        # TS% = 40 / (2 * (30 + 4.4)) * 100 = 40 / 68.8 * 100 = 58.1%
        game_data = [
            {"pts": 22, "fga": 16, "fta": 5},
            {"pts": 18, "fga": 14, "fta": 5},
        ]

        for i, gd in enumerate(game_data):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            create_player_game_stats(
                test_db,
                game.id,
                data["player"].id,
                data["home_team"].id,
                points=gd["pts"],
                field_goals_made=gd["fga"] // 2,
                field_goals_attempted=gd["fga"],
                free_throws_made=gd["fta"] - 1,
                free_throws_attempted=gd["fta"],
            )

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is not None
        # TS% stored as decimal (0.0-1.0+)
        assert result.true_shooting_pct is not None
        assert result.true_shooting_pct > 0.5


class TestRecalculateUpdatesExisting:
    """Integration tests for recalculation behavior."""

    def test_recalculate_updates_existing(self, test_db: Session):
        """Test that recalculating updates existing record, not duplicates."""
        data = create_test_data(test_db)

        # Create initial game
        game1 = create_game(
            test_db,
            data["season"].id,
            data["home_team"].id,
            data["away_team"].id,
            datetime(2024, 11, 1, 19, 0, tzinfo=UTC),
        )
        create_player_game_stats(
            test_db,
            game1.id,
            data["player"].id,
            data["home_team"].id,
            points=20,
        )
        test_db.commit()

        # Calculate initial stats
        service = StatsCalculationService(test_db)
        result1 = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result1 is not None
        assert result1.games_played == 1
        assert result1.total_points == 20
        original_id = result1.id

        # Count records before adding new game
        initial_count = (
            test_db.query(PlayerSeasonStats)
            .filter(
                PlayerSeasonStats.player_id == data["player"].id,
                PlayerSeasonStats.season_id == data["season"].id,
            )
            .count()
        )
        assert initial_count == 1

        # Add another game
        game2 = create_game(
            test_db,
            data["season"].id,
            data["home_team"].id,
            data["away_team"].id,
            datetime(2024, 11, 2, 19, 0, tzinfo=UTC),
        )
        create_player_game_stats(
            test_db,
            game2.id,
            data["player"].id,
            data["home_team"].id,
            points=25,
        )
        test_db.commit()

        # Recalculate
        result2 = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        # Verify update, not duplicate
        assert result2 is not None
        assert result2.id == original_id  # Same record
        assert result2.games_played == 2
        assert result2.total_points == 45  # 20 + 25

        # Verify no duplicates created
        final_count = (
            test_db.query(PlayerSeasonStats)
            .filter(
                PlayerSeasonStats.player_id == data["player"].id,
                PlayerSeasonStats.season_id == data["season"].id,
            )
            .count()
        )
        assert final_count == 1

    def test_recalculate_all_for_season(self, test_db: Session):
        """Test recalculating all player stats for a season."""
        data = create_test_data(test_db)

        # Create second player
        player2 = Player(
            first_name="Second",
            last_name="Player",
            nationality="Test",
            position="PF",
        )
        test_db.add(player2)
        test_db.flush()

        # Create game with both players
        game = create_game(
            test_db,
            data["season"].id,
            data["home_team"].id,
            data["away_team"].id,
            datetime(2024, 11, 1, 19, 0, tzinfo=UTC),
        )
        create_player_game_stats(
            test_db,
            game.id,
            data["player"].id,
            data["home_team"].id,
            points=20,
        )
        create_player_game_stats(
            test_db,
            game.id,
            player2.id,
            data["home_team"].id,
            points=15,
        )
        test_db.commit()

        # Recalculate all
        service = StatsCalculationService(test_db)
        count = service.recalculate_all_for_season(data["season"].id)

        assert count == 2

        # Verify stats exist for both players
        stats1 = (
            test_db.query(PlayerSeasonStats)
            .filter(
                PlayerSeasonStats.player_id == data["player"].id,
                PlayerSeasonStats.season_id == data["season"].id,
            )
            .first()
        )
        stats2 = (
            test_db.query(PlayerSeasonStats)
            .filter(
                PlayerSeasonStats.player_id == player2.id,
                PlayerSeasonStats.season_id == data["season"].id,
            )
            .first()
        )

        assert stats1 is not None
        assert stats1.total_points == 20
        assert stats2 is not None
        assert stats2.total_points == 15


class TestSeasonStatsMatchGameTotals:
    """Integration tests verifying season stats match game stat sums."""

    def test_season_stats_match_game_totals(self, test_db: Session):
        """Test that season totals equal sum of all game stats."""
        data = create_test_data(test_db)

        # Create 5 games with varying stats
        all_game_stats = []
        for i in range(5):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            # Varying stats per game
            pts = 18 + i * 3  # 18, 21, 24, 27, 30
            reb = 5 + i
            ast = 3 + i

            stats = create_player_game_stats(
                test_db,
                game.id,
                data["player"].id,
                data["home_team"].id,
                points=pts,
                rebounds=reb,
                assists=ast,
            )
            all_game_stats.append(stats)

        test_db.commit()

        # Calculate season stats
        service = StatsCalculationService(test_db)
        season_stats = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        # Manually sum game stats
        expected_points = sum(gs.points for gs in all_game_stats)
        expected_rebounds = sum(gs.total_rebounds for gs in all_game_stats)
        expected_assists = sum(gs.assists for gs in all_game_stats)

        # Verify match
        assert season_stats is not None
        assert season_stats.games_played == 5
        assert season_stats.total_points == expected_points
        assert season_stats.total_rebounds == expected_rebounds
        assert season_stats.total_assists == expected_assists

        # Verify averages
        assert season_stats.avg_points == pytest.approx(expected_points / 5, rel=0.1)
        assert season_stats.avg_rebounds == pytest.approx(
            expected_rebounds / 5, rel=0.1
        )
        assert season_stats.avg_assists == pytest.approx(expected_assists / 5, rel=0.1)


class TestAllPlayersHaveSeasonStats:
    """Integration tests for ensuring all players with games have stats."""

    def test_all_players_have_season_stats(self, test_db: Session):
        """Test that every player with game stats gets season stats."""
        data = create_test_data(test_db)

        # Create 3 players
        players = [data["player"]]
        for i in range(2):
            p = Player(
                first_name=f"Player{i + 2}",
                last_name=f"Test{i + 2}",
                nationality="Test",
            )
            test_db.add(p)
            test_db.flush()
            players.append(p)

        # Create game with all 3 players
        game = create_game(
            test_db,
            data["season"].id,
            data["home_team"].id,
            data["away_team"].id,
            datetime(2024, 11, 1, 19, 0, tzinfo=UTC),
        )

        for player in players:
            create_player_game_stats(
                test_db,
                game.id,
                player.id,
                data["home_team"].id,
                points=20,
            )

        test_db.commit()

        # Recalculate all
        service = StatsCalculationService(test_db)
        count = service.recalculate_all_for_season(data["season"].id)

        assert count == 3

        # Verify all players have stats
        for player in players:
            stats = (
                test_db.query(PlayerSeasonStats)
                .filter(
                    PlayerSeasonStats.player_id == player.id,
                    PlayerSeasonStats.season_id == data["season"].id,
                )
                .first()
            )
            assert stats is not None, f"Player {player.full_name} missing stats"
            assert stats.games_played == 1

    def test_no_stats_for_non_final_games(self, test_db: Session):
        """Test that games not marked FINAL don't contribute to stats."""
        data = create_test_data(test_db)

        # Create a SCHEDULED game
        game = Game(
            season_id=data["season"].id,
            home_team_id=data["home_team"].id,
            away_team_id=data["away_team"].id,
            game_date=datetime(2024, 11, 1, 19, 0, tzinfo=UTC),
            status="SCHEDULED",  # Not FINAL
        )
        test_db.add(game)
        test_db.flush()

        create_player_game_stats(
            test_db,
            game.id,
            data["player"].id,
            data["home_team"].id,
            points=20,
        )
        test_db.commit()

        # Calculate stats - should return None
        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is None  # No stats because game not FINAL


class TestZeroMinutesExcluded:
    """Tests for excluding DNP (0 minutes) games from stats."""

    def test_zero_minutes_not_counted_as_game_played(self, test_db: Session):
        """Test that games with 0 minutes don't count towards games_played."""
        data = create_test_data(test_db)

        # Create 3 games: 2 with minutes, 1 DNP (0 minutes)
        for i in range(3):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            # Game 3 is DNP (0 minutes)
            minutes = 1800 if i < 2 else 0
            stats = PlayerGameStats(
                game_id=game.id,
                player_id=data["player"].id,
                team_id=data["home_team"].id,
                minutes_played=minutes,
                is_starter=(i == 0),  # Only started game 1
                points=20 if minutes > 0 else 0,
                field_goals_made=8 if minutes > 0 else 0,
                field_goals_attempted=16 if minutes > 0 else 0,
                two_pointers_made=6 if minutes > 0 else 0,
                two_pointers_attempted=11 if minutes > 0 else 0,
                three_pointers_made=2 if minutes > 0 else 0,
                three_pointers_attempted=5 if minutes > 0 else 0,
                free_throws_made=2 if minutes > 0 else 0,
                free_throws_attempted=2 if minutes > 0 else 0,
                offensive_rebounds=1,
                defensive_rebounds=4,
                total_rebounds=5 if minutes > 0 else 0,
                assists=4 if minutes > 0 else 0,
                turnovers=2 if minutes > 0 else 0,
                steals=1,
                blocks=1,
                personal_fouls=2,
                plus_minus=5,
            )
            test_db.add(stats)

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is not None
        # Only 2 games should count (the ones with minutes)
        assert result.games_played == 2
        # Only 1 game started (with minutes)
        assert result.games_started == 1

    def test_zero_minutes_not_in_averages(self, test_db: Session):
        """Test that DNP games don't affect per-game averages."""
        data = create_test_data(test_db)

        # Create 2 games with 20 points each, 1 DNP game
        points_per_game = [20, 20, 0]  # Third is DNP
        for i, pts in enumerate(points_per_game):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            minutes = 1800 if pts > 0 else 0
            stats = PlayerGameStats(
                game_id=game.id,
                player_id=data["player"].id,
                team_id=data["home_team"].id,
                minutes_played=minutes,
                points=pts,
                field_goals_made=8 if pts > 0 else 0,
                field_goals_attempted=16 if pts > 0 else 0,
                two_pointers_made=6,
                two_pointers_attempted=11,
                three_pointers_made=2,
                three_pointers_attempted=5,
                free_throws_made=2,
                free_throws_attempted=2,
                offensive_rebounds=1,
                defensive_rebounds=4,
                total_rebounds=5 if pts > 0 else 0,
                assists=4 if pts > 0 else 0,
                turnovers=2,
                steals=1,
                blocks=1,
                personal_fouls=2,
                plus_minus=5,
            )
            test_db.add(stats)

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        assert result is not None
        assert result.games_played == 2
        assert result.total_points == 40  # 20 + 20 + 0
        # PPG should be 20.0 (40 / 2 games), not 13.3 (40 / 3 games)
        assert result.avg_points == 20.0

    def test_all_dnp_games_returns_none(self, test_db: Session):
        """Test that if all games are DNP, no season stats are created."""
        data = create_test_data(test_db)

        # Create 2 DNP games (0 minutes)
        for i in range(2):
            game = create_game(
                test_db,
                data["season"].id,
                data["home_team"].id,
                data["away_team"].id,
                datetime(2024, 11, i + 1, 19, 0, tzinfo=UTC),
            )
            stats = PlayerGameStats(
                game_id=game.id,
                player_id=data["player"].id,
                team_id=data["home_team"].id,
                minutes_played=0,  # DNP
                points=0,
                field_goals_made=0,
                field_goals_attempted=0,
                two_pointers_made=0,
                two_pointers_attempted=0,
                three_pointers_made=0,
                three_pointers_attempted=0,
                free_throws_made=0,
                free_throws_attempted=0,
                offensive_rebounds=0,
                defensive_rebounds=0,
                total_rebounds=0,
                assists=0,
                turnovers=0,
                steals=0,
                blocks=0,
                personal_fouls=0,
                plus_minus=0,
            )
            test_db.add(stats)

        test_db.commit()

        service = StatsCalculationService(test_db)
        result = service.calculate_player_season_stats(
            data["player"].id,
            data["home_team"].id,
            data["season"].id,
        )

        # Should return None since no games with actual playing time
        assert result is None
