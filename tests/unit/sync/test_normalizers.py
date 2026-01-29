"""
Tests for the Normalizers module.

Tests the normalization layer that converts raw scraped values to canonical
domain types (Position, GameStatus, EventType enums).

Philosophy tested:
    - FAIL LOUDLY: Unknown values should raise NormalizationError
    - Source-aware: Error messages should include the source for debugging
    - Comprehensive mappings: All known values from all leagues should work
"""

import pytest

from src.schemas.enums import EventType, GameStatus, Position
from src.sync.normalizers import NormalizationError, Normalizers
from src.schemas.enums import GameStatus


class TestNormalizePosition:
    """Tests for Normalizers.normalize_position()."""

    def test_standard_abbreviations(self) -> None:
        """Standard position abbreviations should normalize correctly."""
        assert Normalizers.normalize_position("PG", "test") == Position.POINT_GUARD
        assert Normalizers.normalize_position("SG", "test") == Position.SHOOTING_GUARD
        assert Normalizers.normalize_position("SF", "test") == Position.SMALL_FORWARD
        assert Normalizers.normalize_position("PF", "test") == Position.POWER_FORWARD
        assert Normalizers.normalize_position("C", "test") == Position.CENTER
        assert Normalizers.normalize_position("G", "test") == Position.GUARD
        assert Normalizers.normalize_position("F", "test") == Position.FORWARD

    def test_case_insensitive(self) -> None:
        """Position normalization should be case-insensitive."""
        assert Normalizers.normalize_position("pg", "test") == Position.POINT_GUARD
        assert Normalizers.normalize_position("Pg", "test") == Position.POINT_GUARD
        assert Normalizers.normalize_position("PG", "test") == Position.POINT_GUARD

    def test_full_english_names(self) -> None:
        """Full English position names should normalize correctly."""
        assert Normalizers.normalize_position("Point Guard", "test") == Position.POINT_GUARD
        assert Normalizers.normalize_position("Shooting Guard", "test") == Position.SHOOTING_GUARD
        assert Normalizers.normalize_position("Small Forward", "test") == Position.SMALL_FORWARD
        assert Normalizers.normalize_position("Power Forward", "test") == Position.POWER_FORWARD
        assert Normalizers.normalize_position("Center", "test") == Position.CENTER
        assert Normalizers.normalize_position("Guard", "test") == Position.GUARD
        assert Normalizers.normalize_position("Forward", "test") == Position.FORWARD

    def test_hebrew_positions(self) -> None:
        """Hebrew position names should normalize correctly."""
        assert Normalizers.normalize_position("גארד", "winner") == Position.GUARD
        assert Normalizers.normalize_position("פורוורד", "winner") == Position.FORWARD
        assert Normalizers.normalize_position("סנטר", "winner") == Position.CENTER

    def test_whitespace_handling(self) -> None:
        """Whitespace should be trimmed from positions."""
        assert Normalizers.normalize_position("  PG  ", "test") == Position.POINT_GUARD
        assert Normalizers.normalize_position(" Point Guard ", "test") == Position.POINT_GUARD

    def test_empty_position_raises_error(self) -> None:
        """Empty or whitespace-only positions should raise NormalizationError."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_position("", "test")
        assert exc_info.value.field == "position"
        assert exc_info.value.source == "test"

        with pytest.raises(NormalizationError):
            Normalizers.normalize_position("   ", "test")

    def test_none_position_raises_error(self) -> None:
        """None position should raise NormalizationError with useful message."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_position(None, "test")  # type: ignore
        assert "(empty)" in str(exc_info.value)

    def test_unknown_position_raises_error(self) -> None:
        """Unknown positions should raise NormalizationError."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_position("Unknown Position", "winner")
        assert exc_info.value.field == "position"
        assert exc_info.value.value == "Unknown Position"
        assert exc_info.value.source == "winner"

    def test_error_message_includes_source(self) -> None:
        """Error messages should include the source for debugging."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_position("Invalid", "euroleague")
        assert "euroleague" in str(exc_info.value)


class TestNormalizePositions:
    """Tests for Normalizers.normalize_positions() - multi-position handling."""

    def test_single_position(self) -> None:
        """Single position string should return list with one element."""
        result = Normalizers.normalize_positions("PG", "test")
        assert result == [Position.POINT_GUARD]

    def test_hyphen_separated(self) -> None:
        """Hyphen-separated positions should be split correctly."""
        result = Normalizers.normalize_positions("G-F", "test")
        assert result == [Position.GUARD, Position.FORWARD]

        result = Normalizers.normalize_positions("Guard-Forward", "test")
        assert result == [Position.GUARD, Position.FORWARD]

    def test_slash_separated(self) -> None:
        """Slash-separated positions should be split correctly."""
        result = Normalizers.normalize_positions("G/F", "test")
        assert result == [Position.GUARD, Position.FORWARD]

        result = Normalizers.normalize_positions("PG/SG", "test")
        assert result == [Position.POINT_GUARD, Position.SHOOTING_GUARD]

    def test_comma_separated(self) -> None:
        """Comma-separated positions should be split correctly."""
        result = Normalizers.normalize_positions("PG, SG", "test")
        assert result == [Position.POINT_GUARD, Position.SHOOTING_GUARD]

    def test_empty_returns_empty_list(self) -> None:
        """Empty string should return empty list."""
        assert Normalizers.normalize_positions("", "test") == []
        assert Normalizers.normalize_positions("   ", "test") == []

    def test_whitespace_in_parts(self) -> None:
        """Whitespace around position parts should be trimmed."""
        result = Normalizers.normalize_positions(" G - F ", "test")
        assert result == [Position.GUARD, Position.FORWARD]

    def test_unknown_in_multi_raises_error(self) -> None:
        """Unknown position in multi-position string should raise error."""
        with pytest.raises(NormalizationError):
            Normalizers.normalize_positions("G-Unknown", "test")


class TestTryNormalizePositions:
    """Tests for Normalizers.try_normalize_positions() - non-throwing variant."""

    def test_valid_positions_return_list(self) -> None:
        """Valid positions should return the normalized list."""
        result = Normalizers.try_normalize_positions("G/F", "test")
        assert result == [Position.GUARD, Position.FORWARD]

    def test_unknown_returns_none(self) -> None:
        """Unknown positions should return None instead of raising."""
        result = Normalizers.try_normalize_positions("Unknown", "test")
        assert result is None

    def test_empty_returns_empty_list(self) -> None:
        """Empty string should return empty list."""
        result = Normalizers.try_normalize_positions("", "test")
        assert result == []

    def test_none_returns_empty_list(self) -> None:
        """None input should return empty list."""
        result = Normalizers.try_normalize_positions(None, "test")
        assert result == []


class TestNormalizeGameStatus:
    """Tests for Normalizers.normalize_game_status()."""

    def test_final_variants(self) -> None:
        """All variants of 'final' status should normalize correctly."""
        assert Normalizers.normalize_game_status("final", "test") == GameStatus.FINAL
        assert Normalizers.normalize_game_status("finished", "test") == GameStatus.FINAL
        assert Normalizers.normalize_game_status("FT", "test") == GameStatus.FINAL
        assert Normalizers.normalize_game_status("played", "test") == GameStatus.FINAL
        assert Normalizers.normalize_game_status("completed", "test") == GameStatus.FINAL

    def test_scheduled_variants(self) -> None:
        """All variants of 'scheduled' status should normalize correctly."""
        assert Normalizers.normalize_game_status("scheduled", "test") == GameStatus.SCHEDULED
        assert Normalizers.normalize_game_status("not started", "test") == GameStatus.SCHEDULED
        assert Normalizers.normalize_game_status("upcoming", "test") == GameStatus.SCHEDULED
        assert Normalizers.normalize_game_status("future", "test") == GameStatus.SCHEDULED

    def test_live_variants(self) -> None:
        """All variants of 'live' status should normalize correctly."""
        assert Normalizers.normalize_game_status("live", "test") == GameStatus.LIVE
        assert Normalizers.normalize_game_status("in progress", "test") == GameStatus.LIVE
        assert Normalizers.normalize_game_status("playing", "test") == GameStatus.LIVE

    def test_postponed_variants(self) -> None:
        """All variants of 'postponed' status should normalize correctly."""
        assert Normalizers.normalize_game_status("postponed", "test") == GameStatus.POSTPONED
        assert Normalizers.normalize_game_status("delayed", "test") == GameStatus.POSTPONED

    def test_cancelled_variants(self) -> None:
        """All variants of 'cancelled' status should normalize correctly."""
        assert Normalizers.normalize_game_status("cancelled", "test") == GameStatus.CANCELLED
        assert Normalizers.normalize_game_status("canceled", "test") == GameStatus.CANCELLED
        assert Normalizers.normalize_game_status("forfeit", "test") == GameStatus.CANCELLED

    def test_case_insensitive(self) -> None:
        """Game status normalization should be case-insensitive."""
        assert Normalizers.normalize_game_status("FINAL", "test") == GameStatus.FINAL
        assert Normalizers.normalize_game_status("Final", "test") == GameStatus.FINAL
        assert Normalizers.normalize_game_status("final", "test") == GameStatus.FINAL

    def test_empty_raises_error(self) -> None:
        """Empty status should raise NormalizationError."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_game_status("", "test")
        assert exc_info.value.field == "game_status"

    def test_unknown_raises_error(self) -> None:
        """Unknown status should raise NormalizationError."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_game_status("invalid_status", "nba")
        assert exc_info.value.field == "game_status"
        assert exc_info.value.value == "invalid_status"
        assert exc_info.value.source == "nba"


class TestNormalizeEventType:
    """Tests for Normalizers.normalize_event_type()."""

    def test_shot_variants(self) -> None:
        """All shot-related event types should normalize to SHOT."""
        assert Normalizers.normalize_event_type("shot", "test") == EventType.SHOT
        assert Normalizers.normalize_event_type("made shot", "test") == EventType.SHOT
        assert Normalizers.normalize_event_type("missed shot", "test") == EventType.SHOT

    def test_free_throw_variants(self) -> None:
        """All free throw variants should normalize correctly."""
        assert Normalizers.normalize_event_type("free throw", "test") == EventType.FREE_THROW
        assert Normalizers.normalize_event_type("ft", "test") == EventType.FREE_THROW

    def test_other_event_types(self) -> None:
        """Other standard event types should normalize correctly."""
        assert Normalizers.normalize_event_type("rebound", "test") == EventType.REBOUND
        assert Normalizers.normalize_event_type("assist", "test") == EventType.ASSIST
        assert Normalizers.normalize_event_type("turnover", "test") == EventType.TURNOVER
        assert Normalizers.normalize_event_type("steal", "test") == EventType.STEAL
        assert Normalizers.normalize_event_type("block", "test") == EventType.BLOCK
        assert Normalizers.normalize_event_type("foul", "test") == EventType.FOUL
        assert Normalizers.normalize_event_type("substitution", "test") == EventType.SUBSTITUTION
        assert Normalizers.normalize_event_type("timeout", "test") == EventType.TIMEOUT
        assert Normalizers.normalize_event_type("jump ball", "test") == EventType.JUMP_BALL
        assert Normalizers.normalize_event_type("violation", "test") == EventType.VIOLATION

    def test_unknown_raises_error(self) -> None:
        """Unknown event type should raise NormalizationError."""
        with pytest.raises(NormalizationError) as exc_info:
            Normalizers.normalize_event_type("unknown_event", "winner")
        assert exc_info.value.field == "event_type"


class TestTryNormalizeEventType:
    """Tests for Normalizers.try_normalize_event_type() - non-throwing variant."""

    def test_valid_event_returns_enum(self) -> None:
        """Valid event type should return the enum."""
        result = Normalizers.try_normalize_event_type("shot", "test")
        assert result == EventType.SHOT

    def test_unknown_returns_none(self) -> None:
        """Unknown event type should return None instead of raising."""
        result = Normalizers.try_normalize_event_type("unknown", "test")
        assert result is None

    def test_none_returns_none(self) -> None:
        """None input should return None."""
        result = Normalizers.try_normalize_event_type(None, "test")
        assert result is None


class TestNormalizationErrorException:
    """Tests for the NormalizationError exception class."""

    def test_exception_attributes(self) -> None:
        """Exception should have correct attributes."""
        error = NormalizationError("position", "Unknown", "winner")
        assert error.field == "position"
        assert error.value == "Unknown"
        assert error.source == "winner"

    def test_exception_message(self) -> None:
        """Exception message should be informative."""
        error = NormalizationError("position", "Unknown", "winner")
        message = str(error)
        assert "position" in message
        assert "Unknown" in message
        assert "winner" in message
        assert "mapping" in message.lower()  # Should suggest adding a mapping
