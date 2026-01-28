"""
Sync Types Tests

Tests for the raw data types used in the sync layer.
"""

from datetime import date

import pytest

from src.sync.season import SeasonFormatError
from src.sync.types import RawSeason


class TestRawSeasonValidation:
    """Tests for RawSeason format validation."""

    def test_valid_season_format(self):
        """Test that valid YYYY-YY format is accepted."""
        season = RawSeason(
            external_id="2024-25",
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 5, 31),
        )
        assert season.name == "2024-25"

    def test_valid_season_with_source_id(self):
        """Test valid season with source-specific ID."""
        season = RawSeason(
            external_id="2024-25",
            name="2024-25",
            source_id="E2024",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 5, 31),
        )
        assert season.source_id == "E2024"

    def test_invalid_euroleague_format_raises_error(self):
        """Test that Euroleague format (E2024) raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError) as exc_info:
            RawSeason(
                external_id="E2024",
                name="E2024",  # Invalid - should be 2024-25
            )
        assert "E2024" in str(exc_info.value)

    def test_invalid_format_wrong_suffix(self):
        """Test that incorrect suffix raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            RawSeason(
                external_id="2024-26",
                name="2024-26",  # Invalid - should be 2024-25
            )

    def test_invalid_format_no_dash(self):
        """Test that format without dash raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            RawSeason(
                external_id="202425",
                name="202425",
            )

    def test_invalid_format_with_text(self):
        """Test that format with extra text raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            RawSeason(
                external_id="2024-25 Season",
                name="2024-25 Season",
            )

    def test_century_boundary_valid(self):
        """Test that century boundary is handled correctly."""
        season = RawSeason(
            external_id="1999-00",
            name="1999-00",
        )
        assert season.name == "1999-00"

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        season = RawSeason(
            external_id="2024-25",
            name="2024-25",
        )
        assert season.source_id is None
        assert season.start_date is None
        assert season.end_date is None
        assert season.is_current is False
