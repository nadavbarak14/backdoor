"""
Normalizer Tests

Tests for name normalization utilities used in deduplication.
"""

import pytest

from src.sync.deduplication.normalizer import (
    names_match,
    normalize_name,
    parse_full_name,
)


class TestNormalizeName:
    """Tests for normalize_name function."""

    def test_normalize_name_lowercase(self):
        """Test that names are converted to lowercase."""
        assert normalize_name("LEBRON JAMES") == "lebron james"
        assert normalize_name("LeBron James") == "lebron james"

    def test_normalize_name_removes_accents(self):
        """Test that diacritics/accents are removed."""
        assert normalize_name("Dončić") == "doncic"
        assert normalize_name("José García") == "jose garcia"
        assert normalize_name("Müller") == "muller"
        assert normalize_name("Çağlar") == "caglar"

    def test_normalize_name_strips_whitespace(self):
        """Test that leading/trailing whitespace is removed."""
        assert normalize_name("  LeBron  ") == "lebron"
        assert normalize_name("\tJames\n") == "james"

    def test_normalize_name_normalizes_internal_whitespace(self):
        """Test that multiple spaces are collapsed to single space."""
        assert normalize_name("LeBron    James") == "lebron james"
        assert normalize_name("John  Michael  Smith") == "john michael smith"

    def test_normalize_name_empty_string(self):
        """Test that empty string returns empty string."""
        assert normalize_name("") == ""

    def test_normalize_name_only_whitespace(self):
        """Test that whitespace-only string returns empty string."""
        assert normalize_name("   ") == ""

    def test_normalize_name_combined_transformations(self):
        """Test all transformations combined."""
        assert normalize_name("  LUKA  DONČIĆ  ") == "luka doncic"


class TestNamesMatch:
    """Tests for names_match function."""

    def test_names_match_exact(self):
        """Test exact name match."""
        assert names_match("LeBron James", "LeBron James") is True

    def test_names_match_case_insensitive(self):
        """Test case-insensitive matching."""
        assert names_match("LEBRON JAMES", "lebron james") is True
        assert names_match("LeBron", "LEBRON") is True

    def test_names_match_accents(self):
        """Test matching with different accent representations."""
        assert names_match("Dončić", "Doncic") is True
        assert names_match("José", "Jose") is True

    def test_names_match_whitespace_differences(self):
        """Test matching with whitespace variations."""
        assert names_match("LeBron James", "  lebron  james  ") is True

    def test_names_match_different_names(self):
        """Test that different names don't match."""
        assert names_match("LeBron", "Luka") is False
        assert names_match("James", "Jordan") is False

    def test_names_match_partial_names(self):
        """Test that partial names don't match full names."""
        assert names_match("LeBron", "LeBron James") is False


class TestParseFullName:
    """Tests for parse_full_name function."""

    def test_parse_full_name_two_parts(self):
        """Test parsing standard two-part name."""
        first, last = parse_full_name("Scottie Wilbekin")
        assert first == "Scottie"
        assert last == "Wilbekin"

    def test_parse_full_name_multiple_parts(self):
        """Test parsing name with multiple parts."""
        first, last = parse_full_name("LeBron Raymone James")
        assert first == "LeBron"
        assert last == "Raymone James"

    def test_parse_full_name_single_name(self):
        """Test parsing single name (mononym)."""
        first, last = parse_full_name("Madonna")
        assert first == "Madonna"
        assert last == ""

    def test_parse_full_name_with_whitespace(self):
        """Test parsing name with extra whitespace."""
        first, last = parse_full_name("  John   Doe  ")
        assert first == "John"
        assert last == "Doe"

    def test_parse_full_name_empty_string(self):
        """Test parsing empty string."""
        first, last = parse_full_name("")
        assert first == ""
        assert last == ""

    def test_parse_full_name_only_whitespace(self):
        """Test parsing whitespace-only string."""
        first, last = parse_full_name("   ")
        assert first == ""
        assert last == ""

    def test_parse_full_name_three_parts(self):
        """Test parsing name with three parts."""
        first, last = parse_full_name("Mary Jane Watson")
        assert first == "Mary"
        assert last == "Jane Watson"
