"""
Unit tests for AnalyticsService situational filtering.

Tests situational shot filtering with:
- Fixture-based validation: known scenarios with exact expected results
- Property-based validation: all results satisfy filter properties
- Edge cases: empty results, player/team filtering
"""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.analytics import SituationalFilter
from src.schemas.game import GameCreate, GameStatus
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate
from src.schemas.team import TeamCreate
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.team import TeamService
from src.schemas.enums import GameStatus, Position


class TestSituationalFilter:
    """Tests for SituationalFilter schema."""

    def test_situational_filter_defaults(self):
        """Verify all filter fields default to None (no filtering)."""
        filter = SituationalFilter()

        assert filter.fast_break is None
        assert filter.second_chance is None
        assert filter.contested is None
        assert filter.shot_type is None

    def test_situational_filter_custom_values(self):
        """Test custom filter values."""
        filter = SituationalFilter(
            fast_break=True,
            second_chance=False,
            contested=True,
            shot_type="CATCH_AND_SHOOT",
        )

        assert filter.fast_break is True
        assert filter.second_chance is False
        assert filter.contested is True
        assert filter.shot_type == "CATCH_AND_SHOOT"


class TestGetSituationalShots:
    """Tests for AnalyticsService.get_situational_shots()."""

    @pytest.fixture
    def league(self, test_db: Session) -> League:
        """Create a league for testing."""
        service = LeagueService(test_db)
        return service.create_league(
            LeagueCreate(name="NBA", code="NBA", country="USA")
        )

    @pytest.fixture
    def season(self, test_db: Session, league: League) -> Season:
        """Create a season for testing."""
        service = SeasonService(test_db)
        return service.create_season(
            SeasonCreate(
                league_id=league.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
                is_current=True,
            )
        )

    @pytest.fixture
    def lakers(self, test_db: Session) -> Team:
        """Create Lakers team for testing."""
        service = TeamService(test_db)
        return service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )

    @pytest.fixture
    def celtics(self, test_db: Session) -> Team:
        """Create Celtics team for testing."""
        service = TeamService(test_db)
        return service.create_team(
            TeamCreate(
                name="Boston Celtics",
                short_name="BOS",
                city="Boston",
                country="USA",
            )
        )

    @pytest.fixture
    def lebron(self, test_db: Session) -> Player:
        """Create LeBron James for testing."""
        service = PlayerService(test_db)
        return service.create_player(
            PlayerCreate(first_name="LeBron", last_name="James", position="SF")
        )

    @pytest.fixture
    def tatum(self, test_db: Session) -> Player:
        """Create Jayson Tatum for testing."""
        service = PlayerService(test_db)
        return service.create_player(
            PlayerCreate(first_name="Jayson", last_name="Tatum", position="SF")
        )

    @pytest.fixture
    def game(
        self, test_db: Session, season: Season, lakers: Team, celtics: Team
    ) -> Game:
        """Create a game for testing."""
        service = GameService(test_db)
        return service.create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

    # =========================================================================
    # Fixture-based tests: known scenarios with exact expected results
    # =========================================================================

    def test_get_fast_break_shots_returns_expected(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """
        Create 5 shots, 2 with fast_break=True.
        Verify exactly 2 returned when filtering for fast breaks.
        """
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create 5 shots: 2 fast break, 3 non-fast break
        fast_break_1 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )
        fast_break_2 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,
                "attributes": {"fast_break": True},
            }
        )
        # Non-fast break shots
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "8:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": False},
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 4,
                "period": 1,
                "clock": "7:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": False},
            }
        )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 5,
                "period": 1,
                "clock": "6:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,
                "attributes": {},  # No fast_break attribute
            }
        )

        # Filter for fast break shots
        filter = SituationalFilter(fast_break=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        assert len(shots) == 2
        shot_ids = {s.id for s in shots}
        assert fast_break_1.id in shot_ids
        assert fast_break_2.id in shot_ids

    def test_get_contested_shots_returns_expected(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Verify exact contested shots returned when filtering."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create shots with contested attribute
        contested_1 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,
                "attributes": {"contested": True},
            }
        )
        contested_2 = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"contested": True},
            }
        )
        # Uncontested shot
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "8:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"contested": False},
            }
        )

        filter = SituationalFilter(contested=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        assert len(shots) == 2
        shot_ids = {s.id for s in shots}
        assert contested_1.id in shot_ids
        assert contested_2.id in shot_ids

    def test_combined_filters_returns_expected(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """
        Test combined filters (fast_break AND contested).
        Verify only shots matching BOTH criteria are returned.
        """
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Shot 1: fast_break=True, contested=True (matches both)
        both_match = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True, "contested": True},
            }
        )
        # Shot 2: fast_break=True, contested=False (doesn't match)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True, "contested": False},
            }
        )
        # Shot 3: fast_break=False, contested=True (doesn't match)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "8:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": False, "contested": True},
            }
        )

        # Filter for both fast_break AND contested
        filter = SituationalFilter(fast_break=True, contested=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        assert len(shots) == 1
        assert shots[0].id == both_match.id

    # =========================================================================
    # Property-based tests: all results satisfy filter properties
    # =========================================================================

    def test_all_fast_break_shots_have_attribute(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Assert ALL returned events have attributes.fast_break == True."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create a mix of shots
        for i in range(10):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1,
                    "clock": f"{10 - i}:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": i % 2 == 0,
                    "attributes": {"fast_break": i % 3 == 0},  # Some are fast break
                }
            )

        filter = SituationalFilter(fast_break=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        # Property: ALL returned shots must have fast_break=True
        for shot in shots:
            assert (
                shot.attributes.get("fast_break") is True
            ), f"Shot {shot.id} has fast_break={shot.attributes.get('fast_break')}"

    def test_all_contested_shots_have_attribute(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Assert ALL returned events have attributes.contested == True."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create a mix of shots
        for i in range(10):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1,
                    "clock": f"{10 - i}:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": i % 2 == 0,
                    "attributes": {"contested": i % 2 == 0},  # Alternating
                }
            )

        filter = SituationalFilter(contested=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        # Property: ALL returned shots must have contested=True
        for shot in shots:
            assert (
                shot.attributes.get("contested") is True
            ), f"Shot {shot.id} has contested={shot.attributes.get('contested')}"

    def test_situational_stats_matches_manual_count(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Verify FG% calculation matches manual count."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create 4 fast break shots: 3 made, 1 missed
        for i in range(3):
            pbp_service.create_event(
                {
                    "game_id": game.id,
                    "event_number": i + 1,
                    "period": 1,
                    "clock": f"{10 - i}:00",
                    "event_type": "SHOT",
                    "event_subtype": "2PT",
                    "player_id": lebron.id,
                    "team_id": lakers.id,
                    "success": True,
                    "attributes": {"fast_break": True},
                }
            )
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 4,
                "period": 1,
                "clock": "7:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,
                "attributes": {"fast_break": True},
            }
        )
        # Non-fast break shot (should not be counted)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 5,
                "period": 1,
                "clock": "6:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": False},
            }
        )

        filter = SituationalFilter(fast_break=True)
        stats = service.get_situational_stats(
            game_ids=[game.id],
            player_id=lebron.id,
            filter=filter,
        )

        assert stats["made"] == 3
        assert stats["attempted"] == 4
        assert stats["pct"] == 0.75  # 3/4 = 75%

    # =========================================================================
    # Edge cases
    # =========================================================================

    def test_no_matching_events_returns_empty(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Graceful empty result when no events match filter."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Create shots without fast_break attribute
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": False},
            }
        )

        # Filter for fast break shots (none exist)
        filter = SituationalFilter(fast_break=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        assert shots == []

    def test_filter_with_player_id(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Only returns specified player's shots."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # LeBron's fast break shot
        lebron_shot = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )
        # Tatum's fast break shot
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )

        filter = SituationalFilter(fast_break=True)
        shots = service.get_situational_shots(
            game.id, player_id=lebron.id, filter=filter
        )

        assert len(shots) == 1
        assert shots[0].id == lebron_shot.id

    def test_filter_with_team_id(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        tatum: Player,
        lakers: Team,
        celtics: Team,
    ):
        """Only returns specified team's shots."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Lakers' contested shot
        lakers_shot = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"contested": True},
            }
        )
        # Celtics' contested shot
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": tatum.id,
                "team_id": celtics.id,
                "success": True,
                "attributes": {"contested": True},
            }
        )

        filter = SituationalFilter(contested=True)
        shots = service.get_situational_shots(game.id, team_id=lakers.id, filter=filter)

        assert len(shots) == 1
        assert shots[0].id == lakers_shot.id

    def test_shot_type_filter(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Filter by shot_type attribute."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Catch and shoot
        catch_and_shoot = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "3PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"shot_type": "CATCH_AND_SHOOT"},
            }
        )
        # Pull up
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"shot_type": "PULL_UP"},
            }
        )
        # Post up
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 3,
                "period": 1,
                "clock": "8:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"shot_type": "POST_UP"},
            }
        )

        filter = SituationalFilter(shot_type="CATCH_AND_SHOOT")
        shots = service.get_situational_shots(game.id, filter=filter)

        assert len(shots) == 1
        assert shots[0].id == catch_and_shoot.id

    def test_stats_with_no_shots_returns_zero(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
    ):
        """Stats return 0/0/0.0 when no matching shots."""
        service = AnalyticsService(test_db)

        filter = SituationalFilter(fast_break=True)
        stats = service.get_situational_stats(
            game_ids=[game.id],
            player_id=lebron.id,
            filter=filter,
        )

        assert stats["made"] == 0
        assert stats["attempted"] == 0
        assert stats["pct"] == 0.0

    def test_stats_across_multiple_games(
        self,
        test_db: Session,
        season: Season,
        lakers: Team,
        celtics: Team,
        lebron: Player,
    ):
        """Stats aggregate correctly across multiple games."""
        game_service = GameService(test_db)
        pbp_service = PlayByPlayService(test_db)
        service = AnalyticsService(test_db)

        # Create two games
        game1 = game_service.create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 15, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )
        game2 = game_service.create_game(
            GameCreate(
                season_id=season.id,
                home_team_id=lakers.id,
                away_team_id=celtics.id,
                game_date=datetime(2024, 1, 20, 19, 30, tzinfo=UTC),
                status=GameStatus.FINAL,
            )
        )

        # Game 1: 2 fast break shots, 1 made
        pbp_service.create_event(
            {
                "game_id": game1.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )
        pbp_service.create_event(
            {
                "game_id": game1.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": False,
                "attributes": {"fast_break": True},
            }
        )

        # Game 2: 2 fast break shots, 2 made
        pbp_service.create_event(
            {
                "game_id": game2.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )
        pbp_service.create_event(
            {
                "game_id": game2.id,
                "event_number": 2,
                "period": 1,
                "clock": "9:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )

        filter = SituationalFilter(fast_break=True)
        stats = service.get_situational_stats(
            game_ids=[game1.id, game2.id],
            player_id=lebron.id,
            filter=filter,
        )

        # Total: 4 attempts, 3 made
        assert stats["made"] == 3
        assert stats["attempted"] == 4
        assert stats["pct"] == 0.75

    def test_nonexistent_game_returns_empty(self, test_db: Session):
        """Nonexistent game returns empty list."""
        service = AnalyticsService(test_db)
        fake_id = uuid4()

        filter = SituationalFilter(fast_break=True)
        shots = service.get_situational_shots(fake_id, filter=filter)

        assert shots == []

    def test_only_shot_events_returned(
        self,
        test_db: Session,
        game: Game,
        lebron: Player,
        lakers: Team,
    ):
        """Non-SHOT events are not returned even with matching attributes."""
        service = AnalyticsService(test_db)
        pbp_service = PlayByPlayService(test_db)

        # Shot with fast_break
        shot = pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 1,
                "period": 1,
                "clock": "10:00",
                "event_type": "SHOT",
                "event_subtype": "2PT",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "success": True,
                "attributes": {"fast_break": True},
            }
        )
        # Rebound with fast_break (should NOT be returned)
        pbp_service.create_event(
            {
                "game_id": game.id,
                "event_number": 2,
                "period": 1,
                "clock": "10:00",
                "event_type": "REBOUND",
                "event_subtype": "OFFENSIVE",
                "player_id": lebron.id,
                "team_id": lakers.id,
                "attributes": {"fast_break": True},
            }
        )

        filter = SituationalFilter(fast_break=True)
        shots = service.get_situational_shots(game.id, filter=filter)

        assert len(shots) == 1
        assert shots[0].id == shot.id
