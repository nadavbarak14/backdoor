"""Tests for Height type and parse function."""

import pytest

from src.sync.canonical import Height, parse_height


class TestParseHeight:
    """Tests for parse_height function."""

    def test_int_cm(self) -> None:
        """Test parsing integer cm values."""
        assert parse_height(198) == Height(cm=198)
        assert parse_height(175) == Height(cm=175)
        assert parse_height(220) == Height(cm=220)

    def test_string_cm(self) -> None:
        """Test parsing string cm values."""
        assert parse_height("198") == Height(cm=198)
        assert parse_height("198 cm") == Height(cm=198)
        assert parse_height("198cm") == Height(cm=198)
        assert parse_height("175 centimeters") == Height(cm=175)

    def test_float_meters(self) -> None:
        """Test parsing float meters values."""
        assert parse_height(1.98) == Height(cm=198)
        assert parse_height(2.05) == Height(cm=205)
        assert parse_height(1.75) == Height(cm=175)

    def test_string_meters(self) -> None:
        """Test parsing string meters values."""
        assert parse_height("1.98") == Height(cm=198)
        assert parse_height("1.98m") == Height(cm=198)
        assert parse_height("1.98 m") == Height(cm=198)
        assert parse_height("2.05 meters") == Height(cm=205)

    def test_feet_inches_quote(self) -> None:
        """Test parsing feet'inches format."""
        result = parse_height("6'8")
        assert result is not None
        assert result.cm == 203

        result = parse_height("6'8\"")
        assert result is not None
        assert result.cm == 203

        result = parse_height("7'0")
        assert result is not None
        assert result.cm == 213

    def test_feet_inches_dash(self) -> None:
        """Test parsing feet-inches format."""
        result = parse_height("6-8")
        assert result is not None
        assert result.cm == 203

        result = parse_height("5-11")
        assert result is not None
        assert result.cm == 180

    def test_feet_inches_text(self) -> None:
        """Test parsing feet/inches text format."""
        result = parse_height("6ft 8in")
        assert result is not None
        assert result.cm == 203

        result = parse_height("6 ft 8 in")
        assert result is not None
        assert result.cm == 203

        result = parse_height("6ft8in")
        assert result is not None
        assert result.cm == 203

    def test_feet_only(self) -> None:
        """Test parsing feet-only format."""
        result = parse_height("6ft")
        assert result is not None
        assert result.cm == 183

    def test_out_of_range_returns_none(self) -> None:
        """Test out-of-range values return None."""
        assert parse_height(100) is None  # Too short
        assert parse_height(300) is None  # Too tall
        assert parse_height(149) is None  # Just below min
        assert parse_height(251) is None  # Just above max

    def test_boundary_values(self) -> None:
        """Test boundary values are accepted."""
        assert parse_height(150) == Height(cm=150)
        assert parse_height(250) == Height(cm=250)

    def test_none_returns_none(self) -> None:
        """Test None input returns None."""
        assert parse_height(None) is None

    def test_empty_returns_none(self) -> None:
        """Test empty string returns None."""
        assert parse_height("") is None
        assert parse_height("   ") is None

    def test_invalid_returns_none(self) -> None:
        """Test invalid formats return None."""
        assert parse_height("invalid") is None
        assert parse_height("abc") is None
        assert parse_height("six feet") is None


class TestHeightDataclass:
    """Tests for Height dataclass."""

    def test_immutable(self) -> None:
        """Test Height is immutable (frozen)."""
        height = Height(cm=198)
        with pytest.raises(AttributeError):
            height.cm = 200  # type: ignore

    def test_equality(self) -> None:
        """Test Height equality."""
        assert Height(cm=198) == Height(cm=198)
        assert Height(cm=198) != Height(cm=199)

    def test_invalid_range_raises(self) -> None:
        """Test creating Height with invalid range raises ValueError."""
        with pytest.raises(ValueError):
            Height(cm=100)
        with pytest.raises(ValueError):
            Height(cm=300)

    def test_hash(self) -> None:
        """Test Height is hashable."""
        h1 = Height(cm=198)
        h2 = Height(cm=198)
        assert hash(h1) == hash(h2)
        assert {h1, h2} == {h1}  # Same hash, same set
