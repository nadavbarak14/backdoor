"""Tests for Position type and parse functions."""


from src.sync.canonical import Position, parse_position, parse_positions


class TestParsePosition:
    """Tests for parse_position function."""

    def test_standard_codes(self) -> None:
        """Test parsing standard position codes."""
        assert parse_position("PG") == Position.POINT_GUARD
        assert parse_position("SG") == Position.SHOOTING_GUARD
        assert parse_position("SF") == Position.SMALL_FORWARD
        assert parse_position("PF") == Position.POWER_FORWARD
        assert parse_position("C") == Position.CENTER
        assert parse_position("G") == Position.GUARD
        assert parse_position("F") == Position.FORWARD

    def test_case_insensitive(self) -> None:
        """Test case-insensitive parsing."""
        assert parse_position("pg") == Position.POINT_GUARD
        assert parse_position("Pg") == Position.POINT_GUARD
        assert parse_position("PG") == Position.POINT_GUARD

    def test_full_names(self) -> None:
        """Test parsing full position names."""
        assert parse_position("Point Guard") == Position.POINT_GUARD
        assert parse_position("Shooting Guard") == Position.SHOOTING_GUARD
        assert parse_position("Small Forward") == Position.SMALL_FORWARD
        assert parse_position("Power Forward") == Position.POWER_FORWARD
        assert parse_position("Center") == Position.CENTER
        assert parse_position("Guard") == Position.GUARD
        assert parse_position("Forward") == Position.FORWARD

    def test_full_names_case_insensitive(self) -> None:
        """Test full names are case-insensitive."""
        assert parse_position("point guard") == Position.POINT_GUARD
        assert parse_position("POINT GUARD") == Position.POINT_GUARD

    def test_euroleague_format(self) -> None:
        """Test Euroleague position format."""
        assert parse_position("Guard (Point)") == Position.POINT_GUARD
        assert parse_position("Guard (Shooting)") == Position.SHOOTING_GUARD
        assert parse_position("Forward (Small)") == Position.SMALL_FORWARD
        assert parse_position("Forward (Power)") == Position.POWER_FORWARD

    def test_hebrew_positions(self) -> None:
        """Test Hebrew position names."""
        assert parse_position("גארד") == Position.GUARD
        assert parse_position("פורוורד") == Position.FORWARD
        assert parse_position("סנטר") == Position.CENTER
        assert parse_position("פוינט גארד") == Position.POINT_GUARD

    def test_invalid_returns_none(self) -> None:
        """Test invalid positions return None."""
        assert parse_position("invalid") is None
        assert parse_position("XYZ") is None
        assert parse_position("Point Forward") is None

    def test_none_returns_none(self) -> None:
        """Test None input returns None."""
        assert parse_position(None) is None

    def test_empty_returns_none(self) -> None:
        """Test empty string returns None."""
        assert parse_position("") is None
        assert parse_position("   ") is None

    def test_british_spelling(self) -> None:
        """Test British spelling."""
        assert parse_position("Centre") == Position.CENTER


class TestParsePositions:
    """Tests for parse_positions function."""

    def test_single_position(self) -> None:
        """Test single position returns list with one item."""
        assert parse_positions("PG") == [Position.POINT_GUARD]
        assert parse_positions("Point Guard") == [Position.POINT_GUARD]

    def test_slash_separator(self) -> None:
        """Test slash-separated positions."""
        assert parse_positions("PG/SG") == [Position.POINT_GUARD, Position.SHOOTING_GUARD]
        assert parse_positions("G/F") == [Position.GUARD, Position.FORWARD]
        assert parse_positions("F/C") == [Position.FORWARD, Position.CENTER]

    def test_dash_separator(self) -> None:
        """Test dash-separated positions."""
        assert parse_positions("PG-SG") == [Position.POINT_GUARD, Position.SHOOTING_GUARD]
        assert parse_positions("Guard-Forward") == [Position.GUARD, Position.FORWARD]

    def test_comma_separator(self) -> None:
        """Test comma-separated positions."""
        assert parse_positions("PG, SG") == [Position.POINT_GUARD, Position.SHOOTING_GUARD]
        assert parse_positions("PG,SG,SF") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
            Position.SMALL_FORWARD,
        ]

    def test_deduplicates(self) -> None:
        """Test duplicate positions are removed."""
        assert parse_positions("PG/PG") == [Position.POINT_GUARD]
        assert parse_positions("G/G/F") == [Position.GUARD, Position.FORWARD]

    def test_preserves_order(self) -> None:
        """Test position order is preserved."""
        assert parse_positions("SF/PG") == [Position.SMALL_FORWARD, Position.POINT_GUARD]
        assert parse_positions("C/G") == [Position.CENTER, Position.GUARD]

    def test_none_returns_empty_list(self) -> None:
        """Test None returns empty list."""
        assert parse_positions(None) == []

    def test_empty_returns_empty_list(self) -> None:
        """Test empty string returns empty list."""
        assert parse_positions("") == []
        assert parse_positions("   ") == []

    def test_invalid_positions_filtered(self) -> None:
        """Test invalid positions in list are filtered out."""
        # If all are invalid, return empty list
        assert parse_positions("invalid") == []
        # If some are valid, return only valid ones
        assert parse_positions("PG/invalid") == [Position.POINT_GUARD]

    def test_hebrew_multi_position(self) -> None:
        """Test Hebrew multi-position strings."""
        assert parse_positions("גארד-פורוורד") == [Position.GUARD, Position.FORWARD]


class TestPositionEnum:
    """Tests for Position enum."""

    def test_enum_values(self) -> None:
        """Test enum values are correct."""
        assert Position.POINT_GUARD.value == "PG"
        assert Position.SHOOTING_GUARD.value == "SG"
        assert Position.SMALL_FORWARD.value == "SF"
        assert Position.POWER_FORWARD.value == "PF"
        assert Position.CENTER.value == "C"
        assert Position.GUARD.value == "G"
        assert Position.FORWARD.value == "F"

    def test_enum_str_inheritance(self) -> None:
        """Test Position inherits from str and can be used as string."""
        assert isinstance(Position.POINT_GUARD, str)
        # The value can be accessed directly since it inherits from str
        assert Position.POINT_GUARD == "PG"
        assert Position.POINT_GUARD.value == "PG"
