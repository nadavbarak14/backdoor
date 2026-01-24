"""
Game Schema Tests

Tests for src/schemas/game.py covering:
- GameStatus enum values
- EventType enum values
- GameCreate validation
- GameUpdate validation
- GameResponse serialization
- GameWithBoxScoreResponse nested structure
- GameFilter optional fields
"""

import uuid
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.schemas.game import (
    EventType,
    GameCreate,
    GameFilter,
    GameListResponse,
    GameResponse,
    GameStatus,
    GameUpdate,
    GameWithBoxScoreResponse,
    PlayerBoxScoreResponse,
    TeamBoxScoreResponse,
)


class TestGameStatusEnum:
    """Tests for GameStatus enum."""

    def test_scheduled_value(self):
        """GameStatus.SCHEDULED should have correct value."""
        assert GameStatus.SCHEDULED.value == "SCHEDULED"

    def test_live_value(self):
        """GameStatus.LIVE should have correct value."""
        assert GameStatus.LIVE.value == "LIVE"

    def test_final_value(self):
        """GameStatus.FINAL should have correct value."""
        assert GameStatus.FINAL.value == "FINAL"

    def test_postponed_value(self):
        """GameStatus.POSTPONED should have correct value."""
        assert GameStatus.POSTPONED.value == "POSTPONED"

    def test_cancelled_value(self):
        """GameStatus.CANCELLED should have correct value."""
        assert GameStatus.CANCELLED.value == "CANCELLED"

    def test_all_statuses_count(self):
        """GameStatus should have exactly 5 values."""
        assert len(GameStatus) == 5

    def test_status_is_string_enum(self):
        """GameStatus should be usable as string."""
        status = GameStatus.FINAL
        assert status == "FINAL"
        assert status.value == "FINAL"


class TestEventTypeEnum:
    """Tests for EventType enum."""

    def test_shot_value(self):
        """EventType.SHOT should have correct value."""
        assert EventType.SHOT.value == "SHOT"

    def test_assist_value(self):
        """EventType.ASSIST should have correct value."""
        assert EventType.ASSIST.value == "ASSIST"

    def test_rebound_value(self):
        """EventType.REBOUND should have correct value."""
        assert EventType.REBOUND.value == "REBOUND"

    def test_turnover_value(self):
        """EventType.TURNOVER should have correct value."""
        assert EventType.TURNOVER.value == "TURNOVER"

    def test_steal_value(self):
        """EventType.STEAL should have correct value."""
        assert EventType.STEAL.value == "STEAL"

    def test_block_value(self):
        """EventType.BLOCK should have correct value."""
        assert EventType.BLOCK.value == "BLOCK"

    def test_foul_value(self):
        """EventType.FOUL should have correct value."""
        assert EventType.FOUL.value == "FOUL"

    def test_free_throw_value(self):
        """EventType.FREE_THROW should have correct value."""
        assert EventType.FREE_THROW.value == "FREE_THROW"

    def test_substitution_value(self):
        """EventType.SUBSTITUTION should have correct value."""
        assert EventType.SUBSTITUTION.value == "SUBSTITUTION"

    def test_timeout_value(self):
        """EventType.TIMEOUT should have correct value."""
        assert EventType.TIMEOUT.value == "TIMEOUT"

    def test_jump_ball_value(self):
        """EventType.JUMP_BALL should have correct value."""
        assert EventType.JUMP_BALL.value == "JUMP_BALL"

    def test_violation_value(self):
        """EventType.VIOLATION should have correct value."""
        assert EventType.VIOLATION.value == "VIOLATION"

    def test_period_start_value(self):
        """EventType.PERIOD_START should have correct value."""
        assert EventType.PERIOD_START.value == "PERIOD_START"

    def test_period_end_value(self):
        """EventType.PERIOD_END should have correct value."""
        assert EventType.PERIOD_END.value == "PERIOD_END"

    def test_all_event_types_count(self):
        """EventType should have exactly 14 values."""
        assert len(EventType) == 14


class TestGameCreate:
    """Tests for GameCreate schema validation."""

    def test_valid_game_create(self):
        """GameCreate should accept valid data."""
        season_id = uuid.uuid4()
        home_team_id = uuid.uuid4()
        away_team_id = uuid.uuid4()

        data = GameCreate(
            season_id=season_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            game_date=datetime(2024, 1, 15, 19, 30),
            status=GameStatus.SCHEDULED,
            venue="Crypto.com Arena",
            external_ids={"nba": "0022300567"},
        )

        assert data.season_id == season_id
        assert data.home_team_id == home_team_id
        assert data.away_team_id == away_team_id
        assert data.game_date == datetime(2024, 1, 15, 19, 30)
        assert data.status == GameStatus.SCHEDULED
        assert data.venue == "Crypto.com Arena"
        assert data.external_ids == {"nba": "0022300567"}

    def test_season_id_required(self):
        """GameCreate should require season_id."""
        with pytest.raises(ValidationError) as exc_info:
            GameCreate(
                home_team_id=uuid.uuid4(),
                away_team_id=uuid.uuid4(),
                game_date=datetime(2024, 1, 15, 19, 30),
            )
        assert "season_id" in str(exc_info.value)

    def test_home_team_id_required(self):
        """GameCreate should require home_team_id."""
        with pytest.raises(ValidationError) as exc_info:
            GameCreate(
                season_id=uuid.uuid4(),
                away_team_id=uuid.uuid4(),
                game_date=datetime(2024, 1, 15, 19, 30),
            )
        assert "home_team_id" in str(exc_info.value)

    def test_away_team_id_required(self):
        """GameCreate should require away_team_id."""
        with pytest.raises(ValidationError) as exc_info:
            GameCreate(
                season_id=uuid.uuid4(),
                home_team_id=uuid.uuid4(),
                game_date=datetime(2024, 1, 15, 19, 30),
            )
        assert "away_team_id" in str(exc_info.value)

    def test_game_date_required(self):
        """GameCreate should require game_date."""
        with pytest.raises(ValidationError) as exc_info:
            GameCreate(
                season_id=uuid.uuid4(),
                home_team_id=uuid.uuid4(),
                away_team_id=uuid.uuid4(),
            )
        assert "game_date" in str(exc_info.value)

    def test_default_status_scheduled(self):
        """GameCreate should default status to SCHEDULED."""
        data = GameCreate(
            season_id=uuid.uuid4(),
            home_team_id=uuid.uuid4(),
            away_team_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
        )
        assert data.status == GameStatus.SCHEDULED

    def test_optional_fields(self):
        """GameCreate should allow optional fields to be None."""
        data = GameCreate(
            season_id=uuid.uuid4(),
            home_team_id=uuid.uuid4(),
            away_team_id=uuid.uuid4(),
            game_date=datetime(2024, 1, 15, 19, 30),
        )
        assert data.venue is None
        assert data.external_ids is None

    def test_venue_max_length(self):
        """GameCreate should validate venue max length."""
        with pytest.raises(ValidationError) as exc_info:
            GameCreate(
                season_id=uuid.uuid4(),
                home_team_id=uuid.uuid4(),
                away_team_id=uuid.uuid4(),
                game_date=datetime(2024, 1, 15, 19, 30),
                venue="A" * 201,
            )
        assert "venue" in str(exc_info.value)


class TestGameUpdate:
    """Tests for GameUpdate schema validation."""

    def test_partial_update(self):
        """GameUpdate should allow partial data."""
        data = GameUpdate(status=GameStatus.FINAL, home_score=112, away_score=108)
        assert data.status == GameStatus.FINAL
        assert data.home_score == 112
        assert data.away_score == 108
        assert data.game_date is None
        assert data.venue is None

    def test_all_fields_optional(self):
        """GameUpdate should allow empty data."""
        data = GameUpdate()
        assert data.game_date is None
        assert data.status is None
        assert data.home_score is None
        assert data.away_score is None
        assert data.venue is None
        assert data.attendance is None
        assert data.external_ids is None

    def test_score_validation_non_negative(self):
        """GameUpdate should validate scores are non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            GameUpdate(home_score=-1)
        assert "home_score" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            GameUpdate(away_score=-1)
        assert "away_score" in str(exc_info.value)

    def test_attendance_validation_non_negative(self):
        """GameUpdate should validate attendance is non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            GameUpdate(attendance=-100)
        assert "attendance" in str(exc_info.value)


class TestGameResponse:
    """Tests for GameResponse schema."""

    def test_game_response_structure(self):
        """GameResponse should have correct structure."""
        game_id = uuid.uuid4()
        season_id = uuid.uuid4()
        home_team_id = uuid.uuid4()
        away_team_id = uuid.uuid4()
        now = datetime.now()

        response = GameResponse(
            id=game_id,
            season_id=season_id,
            home_team_id=home_team_id,
            home_team_name="Los Angeles Lakers",
            away_team_id=away_team_id,
            away_team_name="Boston Celtics",
            game_date=datetime(2024, 1, 15, 19, 30),
            status="FINAL",
            home_score=112,
            away_score=108,
            venue="Crypto.com Arena",
            attendance=18997,
            external_ids={"nba": "0022300567"},
            created_at=now,
            updated_at=now,
        )

        assert response.id == game_id
        assert response.season_id == season_id
        assert response.home_team_id == home_team_id
        assert response.home_team_name == "Los Angeles Lakers"
        assert response.away_team_id == away_team_id
        assert response.away_team_name == "Boston Celtics"
        assert response.game_date == datetime(2024, 1, 15, 19, 30)
        assert response.status == "FINAL"
        assert response.home_score == 112
        assert response.away_score == 108
        assert response.venue == "Crypto.com Arena"
        assert response.attendance == 18997
        assert response.external_ids == {"nba": "0022300567"}

    def test_game_response_nullable_scores(self):
        """GameResponse should allow null scores for scheduled games."""
        response = GameResponse(
            id=uuid.uuid4(),
            season_id=uuid.uuid4(),
            home_team_id=uuid.uuid4(),
            home_team_name="Los Angeles Lakers",
            away_team_id=uuid.uuid4(),
            away_team_name="Boston Celtics",
            game_date=datetime(2024, 1, 15, 19, 30),
            status="SCHEDULED",
            home_score=None,
            away_score=None,
            venue=None,
            attendance=None,
            external_ids={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert response.home_score is None
        assert response.away_score is None


class TestGameListResponse:
    """Tests for GameListResponse schema."""

    def test_list_response_structure(self):
        """GameListResponse should contain items and total."""
        game = GameResponse(
            id=uuid.uuid4(),
            season_id=uuid.uuid4(),
            home_team_id=uuid.uuid4(),
            home_team_name="Los Angeles Lakers",
            away_team_id=uuid.uuid4(),
            away_team_name="Boston Celtics",
            game_date=datetime(2024, 1, 15, 19, 30),
            status="FINAL",
            home_score=112,
            away_score=108,
            venue="Crypto.com Arena",
            attendance=18997,
            external_ids={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        response = GameListResponse(items=[game], total=100)

        assert len(response.items) == 1
        assert response.total == 100
        assert response.items[0].home_team_name == "Los Angeles Lakers"


class TestGameFilter:
    """Tests for GameFilter schema."""

    def test_all_fields_optional(self):
        """GameFilter should allow empty data."""
        data = GameFilter()
        assert data.season_id is None
        assert data.team_id is None
        assert data.start_date is None
        assert data.end_date is None
        assert data.status is None

    def test_filter_by_season_id(self):
        """GameFilter should accept season_id."""
        season_id = uuid.uuid4()
        data = GameFilter(season_id=season_id)
        assert data.season_id == season_id

    def test_filter_by_team_id(self):
        """GameFilter should accept team_id."""
        team_id = uuid.uuid4()
        data = GameFilter(team_id=team_id)
        assert data.team_id == team_id

    def test_filter_by_dates(self):
        """GameFilter should accept date range."""
        data = GameFilter(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )
        assert data.start_date == date(2024, 1, 1)
        assert data.end_date == date(2024, 6, 30)

    def test_filter_by_status(self):
        """GameFilter should accept status."""
        data = GameFilter(status=GameStatus.FINAL)
        assert data.status == GameStatus.FINAL

    def test_combined_filters(self):
        """GameFilter should accept multiple filters."""
        season_id = uuid.uuid4()
        team_id = uuid.uuid4()
        data = GameFilter(
            season_id=season_id,
            team_id=team_id,
            status=GameStatus.FINAL,
            start_date=date(2024, 1, 1),
        )
        assert data.season_id == season_id
        assert data.team_id == team_id
        assert data.status == GameStatus.FINAL
        assert data.start_date == date(2024, 1, 1)


class TestGameWithBoxScoreResponse:
    """Tests for GameWithBoxScoreResponse schema."""

    def test_nested_structure(self):
        """GameWithBoxScoreResponse should include game and box score data."""
        game_id = uuid.uuid4()
        season_id = uuid.uuid4()
        home_team_id = uuid.uuid4()
        away_team_id = uuid.uuid4()
        player_id = uuid.uuid4()
        now = datetime.now()

        home_team_stats = TeamBoxScoreResponse(
            team_id=home_team_id,
            team_name="Los Angeles Lakers",
            is_home=True,
            points=112,
            field_goals_made=42,
            field_goals_attempted=88,
            field_goal_pct=47.7,
            three_pointers_made=12,
            three_pointers_attempted=30,
            three_point_pct=40.0,
            free_throws_made=16,
            free_throws_attempted=20,
            free_throw_pct=80.0,
            offensive_rebounds=10,
            defensive_rebounds=35,
            total_rebounds=45,
            assists=25,
            turnovers=12,
            steals=8,
            blocks=5,
            personal_fouls=18,
            fast_break_points=14,
            points_in_paint=48,
            second_chance_points=12,
            bench_points=35,
        )

        player_stats = PlayerBoxScoreResponse(
            player_id=player_id,
            player_name="LeBron James",
            team_id=home_team_id,
            is_starter=True,
            minutes_played=2040,
            minutes_display="34:00",
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            field_goal_pct=50.0,
            three_pointers_made=3,
            three_pointers_attempted=7,
            three_point_pct=42.9,
            free_throws_made=4,
            free_throws_attempted=5,
            free_throw_pct=80.0,
            offensive_rebounds=1,
            defensive_rebounds=7,
            total_rebounds=8,
            assists=10,
            turnovers=3,
            steals=2,
            blocks=1,
            personal_fouls=2,
            plus_minus=15,
        )

        response = GameWithBoxScoreResponse(
            id=game_id,
            season_id=season_id,
            home_team_id=home_team_id,
            home_team_name="Los Angeles Lakers",
            away_team_id=away_team_id,
            away_team_name="Boston Celtics",
            game_date=datetime(2024, 1, 15, 19, 30),
            status="FINAL",
            home_score=112,
            away_score=108,
            venue="Crypto.com Arena",
            attendance=18997,
            external_ids={},
            home_team_stats=home_team_stats,
            away_team_stats=None,
            home_players=[player_stats],
            away_players=[],
            created_at=now,
            updated_at=now,
        )

        assert response.id == game_id
        assert response.home_team_name == "Los Angeles Lakers"
        assert response.home_team_stats is not None
        assert response.home_team_stats.points == 112
        assert response.away_team_stats is None
        assert len(response.home_players) == 1
        assert response.home_players[0].player_name == "LeBron James"
        assert response.home_players[0].points == 25
        assert len(response.away_players) == 0


class TestImports:
    """Tests for module imports."""

    def test_import_from_game_module(self):
        """Should be able to import from game schema module."""
        from src.schemas.game import (
            EventType,
            GameCreate,
            GameFilter,
            GameListResponse,
            GameResponse,
            GameStatus,
            GameUpdate,
            GameWithBoxScoreResponse,
            PlayerBoxScoreResponse,
            TeamBoxScoreResponse,
        )

        assert GameStatus is not None
        assert EventType is not None
        assert GameCreate is not None
        assert GameUpdate is not None
        assert GameResponse is not None
        assert GameListResponse is not None
        assert GameFilter is not None
        assert GameWithBoxScoreResponse is not None
        assert TeamBoxScoreResponse is not None
        assert PlayerBoxScoreResponse is not None

    def test_import_from_schemas_package(self):
        """Should be able to import from schemas package."""
        from src.schemas import (
            EventType,
            GameCreate,
            GameResponse,
            GameStatus,
        )

        assert GameStatus is not None
        assert EventType is not None
        assert GameCreate is not None
        assert GameResponse is not None
