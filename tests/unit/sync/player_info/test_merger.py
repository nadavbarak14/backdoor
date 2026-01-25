"""
Player Info Merger Tests

Tests for the merge_player_info function and MergedPlayerInfo dataclass.
"""

from datetime import date

import pytest

from src.sync.player_info.merger import MergedPlayerInfo, merge_player_info
from src.sync.types import RawPlayerInfo


class TestMergedPlayerInfo:
    """Tests for MergedPlayerInfo dataclass."""

    def test_required_fields(self):
        """Test that required fields are set correctly."""
        merged = MergedPlayerInfo(
            first_name="John",
            last_name="Smith",
        )

        assert merged.first_name == "John"
        assert merged.last_name == "Smith"

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None."""
        merged = MergedPlayerInfo(
            first_name="John",
            last_name="Smith",
        )

        assert merged.birth_date is None
        assert merged.height_cm is None
        assert merged.position is None

    def test_sources_default_to_empty_dict(self):
        """Test that sources defaults to empty dict."""
        merged = MergedPlayerInfo(
            first_name="John",
            last_name="Smith",
        )

        assert merged.sources == {}

    def test_all_fields_set(self):
        """Test that all fields can be set."""
        merged = MergedPlayerInfo(
            first_name="LeBron",
            last_name="James",
            birth_date=date(1984, 12, 30),
            height_cm=206,
            position="SF",
            sources={"height_cm": "winner"},
        )

        assert merged.first_name == "LeBron"
        assert merged.last_name == "James"
        assert merged.birth_date == date(1984, 12, 30)
        assert merged.height_cm == 206
        assert merged.position == "SF"
        assert merged.sources == {"height_cm": "winner"}


class TestMergePlayerInfoSingleSource:
    """Tests for merge_player_info with a single source."""

    def test_single_source_required_fields(self):
        """Test merge with single source returns required fields."""
        info = RawPlayerInfo(
            external_id="123",
            first_name="John",
            last_name="Smith",
        )

        merged = merge_player_info([("winner", info)])

        assert merged.first_name == "John"
        assert merged.last_name == "Smith"

    def test_single_source_all_fields(self):
        """Test merge with single source returns all available fields."""
        info = RawPlayerInfo(
            external_id="123",
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 5, 15),
            height_cm=198,
            position="PG",
        )

        merged = merge_player_info([("winner", info)])

        assert merged.first_name == "John"
        assert merged.last_name == "Smith"
        assert merged.birth_date == date(1995, 5, 15)
        assert merged.height_cm == 198
        assert merged.position == "PG"

    def test_single_source_tracks_sources(self):
        """Test that sources are tracked for single source."""
        info = RawPlayerInfo(
            external_id="123",
            first_name="John",
            last_name="Smith",
            height_cm=198,
            position="PG",
        )

        merged = merge_player_info([("winner", info)])

        assert merged.sources["first_name"] == "winner"
        assert merged.sources["last_name"] == "winner"
        assert merged.sources["height_cm"] == "winner"
        assert merged.sources["position"] == "winner"

    def test_single_source_null_fields_not_tracked(self):
        """Test that null fields are not tracked in sources."""
        info = RawPlayerInfo(
            external_id="123",
            first_name="John",
            last_name="Smith",
        )

        merged = merge_player_info([("winner", info)])

        assert "birth_date" not in merged.sources
        assert "height_cm" not in merged.sources
        assert "position" not in merged.sources


class TestMergePlayerInfoMultipleSources:
    """Tests for merge_player_info with multiple sources."""

    def test_first_source_priority_for_names(self):
        """Test that first source has priority for names."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="LeBron",
            last_name="James",
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="Lebron",
            last_name="JAMES",
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.first_name == "LeBron"
        assert merged.last_name == "James"
        assert merged.sources["first_name"] == "winner"
        assert merged.sources["last_name"] == "winner"

    def test_first_source_priority_for_height(self):
        """Test that first source with height wins."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="LeBron",
            last_name="James",
            height_cm=206,
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="Lebron",
            last_name="James",
            height_cm=205,
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.height_cm == 206
        assert merged.sources["height_cm"] == "winner"

    def test_first_source_priority_for_birth_date(self):
        """Test that first source with birth_date wins."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="LeBron",
            last_name="James",
            birth_date=date(1984, 12, 30),
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="Lebron",
            last_name="James",
            birth_date=date(1984, 12, 31),  # Different date
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.birth_date == date(1984, 12, 30)
        assert merged.sources["birth_date"] == "winner"

    def test_first_source_priority_for_position(self):
        """Test that first source with position wins."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="LeBron",
            last_name="James",
            position="SF",
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="Lebron",
            last_name="James",
            position="PF",
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.position == "SF"
        assert merged.sources["position"] == "winner"

    def test_fallback_to_second_source_for_missing_fields(self):
        """Test that missing fields are filled from later sources."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="LeBron",
            last_name="James",
            height_cm=206,
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="Lebron",
            last_name="James",
            birth_date=date(1984, 12, 30),
            position="SF",
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        # From winner (first source)
        assert merged.first_name == "LeBron"
        assert merged.height_cm == 206
        assert merged.sources["height_cm"] == "winner"

        # From euroleague (second source, not available in first)
        assert merged.birth_date == date(1984, 12, 30)
        assert merged.position == "SF"
        assert merged.sources["birth_date"] == "euroleague"
        assert merged.sources["position"] == "euroleague"

    def test_three_sources(self):
        """Test merge with three sources."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )
        info3 = RawPlayerInfo(
            external_id="n789",
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 5, 15),
            position="PG",
        )

        merged = merge_player_info(
            [
                ("winner", info1),
                ("euroleague", info2),
                ("nba", info3),
            ]
        )

        assert merged.first_name == "John"
        assert merged.sources["first_name"] == "winner"
        assert merged.height_cm == 198
        assert merged.sources["height_cm"] == "euroleague"
        assert merged.birth_date == date(1995, 5, 15)
        assert merged.sources["birth_date"] == "nba"
        assert merged.position == "PG"
        assert merged.sources["position"] == "nba"


class TestMergePlayerInfoEdgeCases:
    """Tests for edge cases in merge_player_info."""

    def test_empty_sources_raises_error(self):
        """Test that empty sources list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot merge empty sources"):
            merge_player_info([])

    def test_empty_first_name_falls_back(self):
        """Test that empty first_name in first source falls back to second."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="",
            last_name="James",
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="LeBron",
            last_name="James",
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.first_name == "LeBron"
        assert merged.sources["first_name"] == "euroleague"

    def test_empty_last_name_falls_back(self):
        """Test that empty last_name in first source falls back to second."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="LeBron",
            last_name="",
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="LeBron",
            last_name="James",
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.last_name == "James"
        assert merged.sources["last_name"] == "euroleague"

    def test_all_sources_have_null_optional_fields(self):
        """Test merge when no source has optional fields."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="John",
            last_name="Smith",
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        assert merged.birth_date is None
        assert merged.height_cm is None
        assert merged.position is None

    def test_sources_dict_immutability(self):
        """Test that sources dict is independent for each merge."""
        info = RawPlayerInfo(
            external_id="123",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )

        merged1 = merge_player_info([("winner", info)])
        merged2 = merge_player_info([("euroleague", info)])

        assert merged1.sources["height_cm"] == "winner"
        assert merged2.sources["height_cm"] == "euroleague"

    def test_zero_height_is_valid(self):
        """Test that zero height is treated as a valid value (not null)."""
        info1 = RawPlayerInfo(
            external_id="w123",
            first_name="John",
            last_name="Smith",
            height_cm=0,
        )
        info2 = RawPlayerInfo(
            external_id="e456",
            first_name="John",
            last_name="Smith",
            height_cm=198,
        )

        merged = merge_player_info([("winner", info1), ("euroleague", info2)])

        # Zero is a valid value, so first source wins
        assert merged.height_cm == 0
        assert merged.sources["height_cm"] == "winner"
