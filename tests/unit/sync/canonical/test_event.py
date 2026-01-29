"""Tests for Event types and GameStatus."""


from src.sync.canonical import (
    EventType,
    FoulType,
    GameStatus,
    ReboundType,
    ShotType,
    TurnoverType,
    parse_game_status,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_all_event_types_exist(self) -> None:
        """Test all expected event types exist."""
        assert EventType.SHOT.value == "SHOT"
        assert EventType.ASSIST.value == "ASSIST"
        assert EventType.REBOUND.value == "REBOUND"
        assert EventType.TURNOVER.value == "TURNOVER"
        assert EventType.STEAL.value == "STEAL"
        assert EventType.BLOCK.value == "BLOCK"
        assert EventType.FOUL.value == "FOUL"
        assert EventType.FREE_THROW.value == "FREE_THROW"
        assert EventType.SUBSTITUTION.value == "SUBSTITUTION"
        assert EventType.TIMEOUT.value == "TIMEOUT"
        assert EventType.JUMP_BALL.value == "JUMP_BALL"
        assert EventType.PERIOD_START.value == "PERIOD_START"
        assert EventType.PERIOD_END.value == "PERIOD_END"

    def test_enum_str_inheritance(self) -> None:
        """Test EventType inherits from str and can be used as string."""
        assert isinstance(EventType.SHOT, str)
        # The value can be accessed directly since it inherits from str
        assert EventType.SHOT == "SHOT"
        assert EventType.SHOT.value == "SHOT"


class TestShotType:
    """Tests for ShotType enum."""

    def test_shot_types(self) -> None:
        """Test shot type values."""
        assert ShotType.TWO_POINT.value == "2PT"
        assert ShotType.THREE_POINT.value == "3PT"
        assert ShotType.DUNK.value == "DUNK"
        assert ShotType.LAYUP.value == "LAYUP"

    def test_enum_str_inheritance(self) -> None:
        """Test ShotType inherits from str."""
        assert isinstance(ShotType.TWO_POINT, str)


class TestReboundType:
    """Tests for ReboundType enum."""

    def test_rebound_types(self) -> None:
        """Test rebound type values."""
        assert ReboundType.OFFENSIVE.value == "OFF"
        assert ReboundType.DEFENSIVE.value == "DEF"


class TestFoulType:
    """Tests for FoulType enum."""

    def test_foul_types(self) -> None:
        """Test foul type values."""
        assert FoulType.PERSONAL.value == "PERSONAL"
        assert FoulType.TECHNICAL.value == "TECHNICAL"
        assert FoulType.FLAGRANT.value == "FLAGRANT"
        assert FoulType.OFFENSIVE.value == "OFFENSIVE"


class TestTurnoverType:
    """Tests for TurnoverType enum."""

    def test_turnover_types(self) -> None:
        """Test turnover type values."""
        assert TurnoverType.BAD_PASS.value == "BAD_PASS"
        assert TurnoverType.LOST_BALL.value == "LOST_BALL"
        assert TurnoverType.TRAVEL.value == "TRAVEL"
        assert TurnoverType.BACKCOURT.value == "BACKCOURT"
        assert TurnoverType.SHOT_CLOCK.value == "SHOT_CLOCK"
        assert TurnoverType.OFFENSIVE_FOUL.value == "OFFENSIVE_FOUL"
        assert TurnoverType.OTHER.value == "OTHER"


class TestGameStatus:
    """Tests for GameStatus enum."""

    def test_game_status_values(self) -> None:
        """Test game status values."""
        assert GameStatus.SCHEDULED.value == "SCHEDULED"
        assert GameStatus.LIVE.value == "LIVE"
        assert GameStatus.FINAL.value == "FINAL"
        assert GameStatus.POSTPONED.value == "POSTPONED"
        assert GameStatus.CANCELLED.value == "CANCELLED"

    def test_enum_str_inheritance(self) -> None:
        """Test GameStatus inherits from str and can be used as string."""
        assert isinstance(GameStatus.FINAL, str)
        # The value can be accessed directly since it inherits from str
        assert GameStatus.FINAL == "FINAL"
        assert GameStatus.FINAL.value == "FINAL"


class TestParseGameStatus:
    """Tests for parse_game_status function."""

    def test_final_variations(self) -> None:
        """Test parsing final/completed status variations."""
        assert parse_game_status("final") == GameStatus.FINAL
        assert parse_game_status("finished") == GameStatus.FINAL
        assert parse_game_status("FT") == GameStatus.FINAL
        assert parse_game_status("played") == GameStatus.FINAL
        assert parse_game_status("completed") == GameStatus.FINAL

    def test_scheduled_variations(self) -> None:
        """Test parsing scheduled status variations."""
        assert parse_game_status("scheduled") == GameStatus.SCHEDULED
        assert parse_game_status("not started") == GameStatus.SCHEDULED
        assert parse_game_status("upcoming") == GameStatus.SCHEDULED
        assert parse_game_status("pending") == GameStatus.SCHEDULED

    def test_live_variations(self) -> None:
        """Test parsing live status variations."""
        assert parse_game_status("live") == GameStatus.LIVE
        assert parse_game_status("in progress") == GameStatus.LIVE
        assert parse_game_status("playing") == GameStatus.LIVE
        assert parse_game_status("ongoing") == GameStatus.LIVE

    def test_postponed_variations(self) -> None:
        """Test parsing postponed status variations."""
        assert parse_game_status("postponed") == GameStatus.POSTPONED
        assert parse_game_status("delayed") == GameStatus.POSTPONED
        assert parse_game_status("suspended") == GameStatus.POSTPONED

    def test_cancelled_variations(self) -> None:
        """Test parsing cancelled status variations."""
        assert parse_game_status("cancelled") == GameStatus.CANCELLED
        assert parse_game_status("canceled") == GameStatus.CANCELLED  # US spelling
        assert parse_game_status("abandoned") == GameStatus.CANCELLED
        assert parse_game_status("forfeit") == GameStatus.CANCELLED

    def test_case_insensitive(self) -> None:
        """Test case-insensitive parsing."""
        assert parse_game_status("FINAL") == GameStatus.FINAL
        assert parse_game_status("Final") == GameStatus.FINAL
        assert parse_game_status("final") == GameStatus.FINAL

    def test_none_returns_none(self) -> None:
        """Test None input returns None."""
        assert parse_game_status(None) is None

    def test_empty_returns_none(self) -> None:
        """Test empty string returns None."""
        assert parse_game_status("") is None
        assert parse_game_status("   ") is None

    def test_invalid_returns_none(self) -> None:
        """Test invalid inputs return None."""
        assert parse_game_status("invalid") is None
        assert parse_game_status("unknown") is None
