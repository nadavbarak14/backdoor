"""Tests for birthdate parse function."""

from datetime import date, datetime

from src.sync.canonical import parse_birthdate


class TestParseBirthdate:
    """Tests for parse_birthdate function."""

    def test_iso_format(self) -> None:
        """Test parsing ISO date format."""
        assert parse_birthdate("1995-05-15") == date(1995, 5, 15)
        assert parse_birthdate("2000-01-01") == date(2000, 1, 1)
        assert parse_birthdate("1985-12-31") == date(1985, 12, 31)

    def test_iso_format_with_slash(self) -> None:
        """Test parsing ISO format with slash separator."""
        assert parse_birthdate("1995/05/15") == date(1995, 5, 15)

    def test_european_format_slash(self) -> None:
        """Test parsing European format with slash."""
        assert parse_birthdate("15/05/1995") == date(1995, 5, 15)
        assert parse_birthdate("01/12/2000") == date(2000, 12, 1)

    def test_european_format_dash(self) -> None:
        """Test parsing European format with dash."""
        assert parse_birthdate("15-05-1995") == date(1995, 5, 15)

    def test_european_format_dot(self) -> None:
        """Test parsing European format with dot."""
        assert parse_birthdate("15.05.1995") == date(1995, 5, 15)

    def test_text_format_mdy(self) -> None:
        """Test parsing Month Day, Year format."""
        assert parse_birthdate("May 15, 1995") == date(1995, 5, 15)
        assert parse_birthdate("January 1, 2000") == date(2000, 1, 1)
        assert parse_birthdate("December 31, 1985") == date(1985, 12, 31)

    def test_text_format_dmy(self) -> None:
        """Test parsing Day Month Year format."""
        assert parse_birthdate("15 May 1995") == date(1995, 5, 15)
        assert parse_birthdate("1 January 2000") == date(2000, 1, 1)

    def test_text_format_abbreviated_month(self) -> None:
        """Test parsing abbreviated month names."""
        assert parse_birthdate("May 15, 1995") == date(1995, 5, 15)
        assert parse_birthdate("Jan 1, 2000") == date(2000, 1, 1)
        assert parse_birthdate("Dec 31, 1985") == date(1985, 12, 31)

    def test_datetime_input(self) -> None:
        """Test parsing datetime objects."""
        dt = datetime(1995, 5, 15, 10, 30, 0)
        assert parse_birthdate(dt) == date(1995, 5, 15)

    def test_date_input(self) -> None:
        """Test parsing date objects."""
        d = date(1995, 5, 15)
        assert parse_birthdate(d) == date(1995, 5, 15)

    def test_future_date_returns_none(self) -> None:
        """Test future dates return None."""
        assert parse_birthdate("2050-01-01") is None
        assert parse_birthdate("2099-12-31") is None

    def test_year_before_1950_returns_none(self) -> None:
        """Test years before 1950 return None."""
        assert parse_birthdate("1949-12-31") is None
        assert parse_birthdate("1900-01-01") is None

    def test_boundary_years(self) -> None:
        """Test boundary year values."""
        assert parse_birthdate("1950-01-01") == date(1950, 1, 1)
        # Current year should work for past dates
        current_year = datetime.now().year
        assert parse_birthdate(f"{current_year}-01-01") == date(current_year, 1, 1)

    def test_none_returns_none(self) -> None:
        """Test None input returns None."""
        assert parse_birthdate(None) is None

    def test_empty_returns_none(self) -> None:
        """Test empty string returns None."""
        assert parse_birthdate("") is None
        assert parse_birthdate("   ") is None

    def test_invalid_returns_none(self) -> None:
        """Test invalid formats return None."""
        assert parse_birthdate("invalid") is None
        assert parse_birthdate("not-a-date") is None
        assert parse_birthdate("1995") is None  # Year only

    def test_invalid_date_returns_none(self) -> None:
        """Test invalid date values return None."""
        assert parse_birthdate("1995-13-01") is None  # Invalid month
        assert parse_birthdate("1995-02-30") is None  # Invalid day
        assert parse_birthdate("1995-00-15") is None  # Zero month


class TestDateDisambiguation:
    """Tests for date format disambiguation."""

    def test_unambiguous_european(self) -> None:
        """Test unambiguous European format (day > 12)."""
        # 15/05/1995 - day=15 > 12, so must be DD/MM/YYYY
        assert parse_birthdate("15/05/1995") == date(1995, 5, 15)
        assert parse_birthdate("25/12/2000") == date(2000, 12, 25)

    def test_ambiguous_defaults_to_european(self) -> None:
        """Test ambiguous dates default to European format."""
        # 05/06/1995 - both could be day or month
        # Should default to European (DD/MM/YYYY)
        assert parse_birthdate("05/06/1995") == date(1995, 6, 5)
