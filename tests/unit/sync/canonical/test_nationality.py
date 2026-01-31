"""Tests for Nationality type and parse function."""

import pytest

from src.sync.canonical import Nationality, parse_nationality


class TestParseNationality:
    """Tests for parse_nationality function."""

    def test_iso_codes(self) -> None:
        """Test parsing ISO codes."""
        assert parse_nationality("ISR") == Nationality(code="ISR")
        assert parse_nationality("USA") == Nationality(code="USA")
        assert parse_nationality("ESP") == Nationality(code="ESP")
        assert parse_nationality("FRA") == Nationality(code="FRA")

    def test_iso_codes_case_insensitive(self) -> None:
        """Test ISO codes are case-insensitive."""
        assert parse_nationality("isr") == Nationality(code="ISR")
        assert parse_nationality("Isr") == Nationality(code="ISR")
        assert parse_nationality("ISR") == Nationality(code="ISR")

    def test_english_names(self) -> None:
        """Test parsing English country names."""
        assert parse_nationality("Israel") == Nationality(code="ISR")
        assert parse_nationality("United States") == Nationality(code="USA")
        assert parse_nationality("Spain") == Nationality(code="ESP")
        assert parse_nationality("France") == Nationality(code="FRA")
        assert parse_nationality("Germany") == Nationality(code="DEU")

    def test_english_names_case_insensitive(self) -> None:
        """Test English names are case-insensitive."""
        assert parse_nationality("israel") == Nationality(code="ISR")
        assert parse_nationality("ISRAEL") == Nationality(code="ISR")
        assert parse_nationality("Israel") == Nationality(code="ISR")

    def test_hebrew_names(self) -> None:
        """Test parsing Hebrew country names."""
        assert parse_nationality("ישראל") == Nationality(code="ISR")
        assert parse_nationality("ארצות הברית") == Nationality(code="USA")
        assert parse_nationality("ספרד") == Nationality(code="ESP")
        assert parse_nationality("צרפת") == Nationality(code="FRA")
        assert parse_nationality("גרמניה") == Nationality(code="DEU")

    def test_demonyms(self) -> None:
        """Test parsing demonyms (nationality adjectives)."""
        assert parse_nationality("Israeli") == Nationality(code="ISR")
        assert parse_nationality("American") == Nationality(code="USA")
        assert parse_nationality("Spanish") == Nationality(code="ESP")
        assert parse_nationality("French") == Nationality(code="FRA")
        assert parse_nationality("German") == Nationality(code="DEU")

    def test_demonyms_case_insensitive(self) -> None:
        """Test demonyms are case-insensitive."""
        assert parse_nationality("israeli") == Nationality(code="ISR")
        assert parse_nationality("AMERICAN") == Nationality(code="USA")

    def test_common_aliases(self) -> None:
        """Test common country code aliases."""
        assert parse_nationality("GER") == Nationality(code="DEU")
        assert parse_nationality("CRO") == Nationality(code="HRV")
        assert parse_nationality("SLO") == Nationality(code="SVN")
        assert parse_nationality("GRE") == Nationality(code="GRC")

    def test_none_returns_none(self) -> None:
        """Test None input returns None."""
        assert parse_nationality(None) is None

    def test_empty_returns_none(self) -> None:
        """Test empty string returns None."""
        assert parse_nationality("") is None
        assert parse_nationality("   ") is None

    def test_invalid_returns_none(self) -> None:
        """Test invalid inputs return None."""
        assert parse_nationality("invalid") is None
        assert parse_nationality("XYZ") is None
        assert parse_nationality("Atlantis") is None

    def test_us_variants(self) -> None:
        """Test various US name variants."""
        assert parse_nationality("USA") == Nationality(code="USA")
        assert parse_nationality("United States") == Nationality(code="USA")
        assert parse_nationality("United States of America") == Nationality(code="USA")
        assert parse_nationality("US") == Nationality(code="USA")
        assert parse_nationality("America") == Nationality(code="USA")

    def test_uk_variants(self) -> None:
        """Test various UK name variants."""
        assert parse_nationality("GBR") == Nationality(code="GBR")
        assert parse_nationality("United Kingdom") == Nationality(code="GBR")
        assert parse_nationality("UK") == Nationality(code="GBR")
        assert parse_nationality("Great Britain") == Nationality(code="GBR")
        assert parse_nationality("England") == Nationality(code="GBR")


class TestNationalityDataclass:
    """Tests for Nationality dataclass."""

    def test_immutable(self) -> None:
        """Test Nationality is immutable (frozen)."""
        nationality = Nationality(code="ISR")
        with pytest.raises(AttributeError):
            nationality.code = "USA"  # type: ignore

    def test_equality(self) -> None:
        """Test Nationality equality."""
        assert Nationality(code="ISR") == Nationality(code="ISR")
        assert Nationality(code="ISR") != Nationality(code="USA")

    def test_invalid_code_raises(self) -> None:
        """Test creating Nationality with invalid code raises ValueError."""
        with pytest.raises(ValueError):
            Nationality(code="invalid")
        with pytest.raises(ValueError):
            Nationality(code="IS")  # Too short
        with pytest.raises(ValueError):
            Nationality(code="ISRA")  # Too long
        with pytest.raises(ValueError):
            Nationality(code="isr")  # Not uppercase

    def test_hash(self) -> None:
        """Test Nationality is hashable."""
        n1 = Nationality(code="ISR")
        n2 = Nationality(code="ISR")
        assert hash(n1) == hash(n2)
        assert {n1, n2} == {n1}  # Same hash, same set


class TestNationalityComprehensive:
    """Comprehensive tests for nationality parsing."""

    def test_basketball_relevant_countries(self) -> None:
        """Test countries commonly seen in basketball data."""
        # European basketball countries
        assert parse_nationality("Serbia") == Nationality(code="SRB")
        assert parse_nationality("Croatia") == Nationality(code="HRV")
        assert parse_nationality("Slovenia") == Nationality(code="SVN")
        assert parse_nationality("Greece") == Nationality(code="GRC")
        assert parse_nationality("Turkey") == Nationality(code="TUR")
        assert parse_nationality("Lithuania") == Nationality(code="LTU")
        assert parse_nationality("Latvia") == Nationality(code="LVA")
        assert parse_nationality("Russia") == Nationality(code="RUS")

        # Americas
        assert parse_nationality("Brazil") == Nationality(code="BRA")
        assert parse_nationality("Argentina") == Nationality(code="ARG")
        assert parse_nationality("Canada") == Nationality(code="CAN")

        # Africa
        assert parse_nationality("Nigeria") == Nationality(code="NGA")
        assert parse_nationality("Senegal") == Nationality(code="SEN")
        assert parse_nationality("Cameroon") == Nationality(code="CMR")

        # Australia
        assert parse_nationality("Australia") == Nationality(code="AUS")
