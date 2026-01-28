"""
Season Format Utilities Tests

Tests for the centralized season name normalization functions.
"""

import pytest

from src.sync.season import (
    SeasonFormatError,
    normalize_season_name,
    parse_season_year,
    validate_season_format,
)


class TestNormalizeSeasonName:
    """Tests for normalize_season_name function."""

    def test_standard_year(self):
        """Test normalization of standard years."""
        assert normalize_season_name(2025) == "2025-26"
        assert normalize_season_name(2024) == "2024-25"
        assert normalize_season_name(2023) == "2023-24"

    def test_century_boundary(self):
        """Test years crossing century boundary."""
        assert normalize_season_name(1999) == "1999-00"
        assert normalize_season_name(2099) == "2099-00"

    def test_early_century(self):
        """Test early years in century."""
        assert normalize_season_name(2000) == "2000-01"
        assert normalize_season_name(2001) == "2001-02"

    def test_invalid_year_too_low(self):
        """Test that years before 1900 raise ValueError."""
        with pytest.raises(ValueError, match="Invalid year"):
            normalize_season_name(1899)

    def test_invalid_year_too_high(self):
        """Test that years after 2100 raise ValueError."""
        with pytest.raises(ValueError, match="Invalid year"):
            normalize_season_name(2101)

    def test_invalid_year_type(self):
        """Test that non-integer types raise error."""
        with pytest.raises((ValueError, TypeError)):
            normalize_season_name("2025")  # type: ignore

        with pytest.raises((ValueError, TypeError)):
            normalize_season_name(2025.5)  # type: ignore


class TestParseSeasonYear:
    """Tests for parse_season_year function."""

    def test_standard_format(self):
        """Test parsing standard YYYY-YY format."""
        assert parse_season_year("2025-26") == 2025
        assert parse_season_year("2024-25") == 2024
        assert parse_season_year("1999-00") == 1999

    def test_century_boundary(self):
        """Test parsing years crossing century boundary."""
        assert parse_season_year("1999-00") == 1999
        assert parse_season_year("2099-00") == 2099

    def test_invalid_format_euroleague(self):
        """Test that Euroleague format raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError) as exc_info:
            parse_season_year("E2025")
        assert "E2025" in str(exc_info.value)

    def test_invalid_format_no_dash(self):
        """Test that format without dash raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            parse_season_year("202526")

    def test_invalid_format_wrong_suffix(self):
        """Test that incorrect suffix raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError) as exc_info:
            parse_season_year("2025-27")  # Should be 26
        assert "Expected suffix '26'" in str(exc_info.value)

    def test_invalid_format_extra_chars(self):
        """Test that extra characters raise SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            parse_season_year("2025-26 Season")

    def test_invalid_format_empty(self):
        """Test that empty string raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            parse_season_year("")


class TestValidateSeasonFormat:
    """Tests for validate_season_format function."""

    def test_valid_formats(self):
        """Test that valid formats return True."""
        assert validate_season_format("2025-26") is True
        assert validate_season_format("2024-25") is True
        assert validate_season_format("1999-00") is True
        assert validate_season_format("2000-01") is True

    def test_invalid_formats(self):
        """Test that invalid formats return False."""
        assert validate_season_format("E2025") is False
        assert validate_season_format("2025-27") is False
        assert validate_season_format("202526") is False
        assert validate_season_format("2025-26 Season") is False
        assert validate_season_format("") is False
        assert validate_season_format("2025") is False


class TestSeasonFormatError:
    """Tests for SeasonFormatError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = SeasonFormatError("E2025")
        assert "E2025" in str(error)
        assert "YYYY-YY" in str(error)

    def test_custom_message(self):
        """Test custom error message."""
        error = SeasonFormatError("E2025", "Custom message")
        assert str(error) == "Custom message"

    def test_value_attribute(self):
        """Test that value attribute is set."""
        error = SeasonFormatError("E2025")
        assert error.value == "E2025"
