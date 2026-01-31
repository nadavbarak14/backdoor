"""Tests for canonical entity dataclasses."""

from datetime import date, datetime

import pytest

from src.sync.canonical import (
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayer,
    CanonicalPlayerStats,
    CanonicalSeason,
    CanonicalTeam,
    EventType,
    Height,
    Nationality,
    Position,
    ShotType,
)
from src.sync.season import SeasonFormatError


class TestCanonicalPlayer:
    """Tests for CanonicalPlayer dataclass."""

    def test_full_name_property(self) -> None:
        """Test full_name property combines first and last name."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="James",
            positions=[Position.SMALL_FORWARD, Position.POWER_FORWARD],
            height=Height(cm=206),
            birth_date=date(1984, 12, 30),
            nationality=Nationality(code="USA"),
            jersey_number="23",
        )
        assert player.full_name == "LeBron James"

    def test_full_name_with_empty_first_name(self) -> None:
        """Test full_name handles empty first name."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="",
            last_name="James",
            positions=[],
            height=None,
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.full_name == "James"

    def test_full_name_with_empty_last_name(self) -> None:
        """Test full_name handles empty last name."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="",
            positions=[],
            height=None,
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.full_name == "LeBron"

    def test_primary_position_returns_first(self) -> None:
        """Test primary_position returns first position."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="James",
            positions=[Position.SMALL_FORWARD, Position.POWER_FORWARD],
            height=None,
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.primary_position == Position.SMALL_FORWARD

    def test_primary_position_empty_returns_none(self) -> None:
        """Test primary_position returns None when no positions."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="Unknown",
            last_name="Player",
            positions=[],
            height=None,
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.primary_position is None

    def test_height_cm_property(self) -> None:
        """Test height_cm returns height in cm."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="James",
            positions=[],
            height=Height(cm=206),
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.height_cm == 206

    def test_height_cm_none_returns_none(self) -> None:
        """Test height_cm returns None when height is not set."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="James",
            positions=[],
            height=None,
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.height_cm is None

    def test_nationality_code_property(self) -> None:
        """Test nationality_code returns ISO code."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="James",
            positions=[],
            height=None,
            birth_date=None,
            nationality=Nationality(code="USA"),
            jersey_number=None,
        )
        assert player.nationality_code == "USA"

    def test_nationality_code_none_returns_none(self) -> None:
        """Test nationality_code returns None when nationality is not set."""
        player = CanonicalPlayer(
            external_id="1",
            source="test",
            first_name="LeBron",
            last_name="James",
            positions=[],
            height=None,
            birth_date=None,
            nationality=None,
            jersey_number=None,
        )
        assert player.nationality_code is None


class TestCanonicalTeam:
    """Tests for CanonicalTeam dataclass."""

    def test_team_creation(self) -> None:
        """Test creating a team with all fields."""
        team = CanonicalTeam(
            external_id="100",
            source="euroleague",
            name="Maccabi Tel Aviv",
            short_name="MAC",
            city="Tel Aviv",
            country="Israel",
        )
        assert team.external_id == "100"
        assert team.name == "Maccabi Tel Aviv"
        assert team.short_name == "MAC"

    def test_team_with_none_optionals(self) -> None:
        """Test team with None optional fields."""
        team = CanonicalTeam(
            external_id="100",
            source="test",
            name="Test Team",
            short_name=None,
            city=None,
            country=None,
        )
        assert team.short_name is None
        assert team.city is None
        assert team.country is None


class TestCanonicalGame:
    """Tests for CanonicalGame dataclass."""

    def test_game_creation(self) -> None:
        """Test creating a game with all fields."""
        game = CanonicalGame(
            external_id="G123",
            source="euroleague",
            season_external_id="E2024",
            home_team_external_id="T100",
            away_team_external_id="T200",
            game_date=datetime(2024, 11, 15, 20, 0),
            status="FINAL",
            home_score=85,
            away_score=78,
            venue="Menora Mivtachim Arena",
        )
        assert game.external_id == "G123"
        assert game.status == "FINAL"
        assert game.home_score == 85
        assert game.away_score == 78

    def test_game_scheduled_no_score(self) -> None:
        """Test scheduled game with no scores."""
        game = CanonicalGame(
            external_id="G123",
            source="euroleague",
            season_external_id="E2024",
            home_team_external_id="T100",
            away_team_external_id="T200",
            game_date=datetime(2024, 11, 15, 20, 0),
            status="SCHEDULED",
            home_score=None,
            away_score=None,
        )
        assert game.home_score is None
        assert game.away_score is None
        assert game.venue is None  # Default


class TestCanonicalPlayerStats:
    """Tests for CanonicalPlayerStats dataclass."""

    def test_stats_defaults_to_zero(self) -> None:
        """Test stats default to zero."""
        stats = CanonicalPlayerStats(
            player_external_id="1",
            player_name="Test Player",
            team_external_id="T1",
            minutes_seconds=0,
        )
        assert stats.points == 0
        assert stats.assists == 0
        assert stats.total_rebounds == 0
        assert stats.field_goals_made == 0
        assert stats.is_starter is False

    def test_stats_with_values(self) -> None:
        """Test stats with actual values."""
        stats = CanonicalPlayerStats(
            player_external_id="1",
            player_name="LeBron James",
            team_external_id="T1",
            minutes_seconds=2100,  # 35 minutes
            is_starter=True,
            points=28,
            assists=8,
            total_rebounds=7,
            field_goals_made=10,
            field_goals_attempted=18,
            three_pointers_made=2,
            three_pointers_attempted=5,
        )
        assert stats.minutes_seconds == 2100
        assert stats.points == 28
        assert stats.is_starter is True

    def test_minutes_seconds_is_seconds(self) -> None:
        """Verify minutes_seconds is actually in seconds."""
        stats = CanonicalPlayerStats(
            player_external_id="1",
            player_name="Test",
            team_external_id="T1",
            minutes_seconds=1530,  # 25:30 in seconds
        )
        # Convert to minutes for verification
        assert stats.minutes_seconds / 60 == 25.5


class TestCanonicalPBPEvent:
    """Tests for CanonicalPBPEvent dataclass."""

    def test_shot_with_subtype(self) -> None:
        """Test shot event with shot subtype."""
        event = CanonicalPBPEvent(
            event_number=1,
            period=1,
            clock_seconds=600,
            event_type=EventType.SHOT,
            shot_type=ShotType.THREE_POINT,
            success=True,
            player_external_id="P1",
            team_external_id="T1",
        )
        assert event.event_type == EventType.SHOT
        assert event.shot_type == ShotType.THREE_POINT
        assert event.success is True

    def test_event_defaults(self) -> None:
        """Test event defaults to None for optional fields."""
        event = CanonicalPBPEvent(
            event_number=1,
            period=1,
            clock_seconds=600,
            event_type=EventType.TIMEOUT,
        )
        assert event.shot_type is None
        assert event.player_external_id is None
        assert event.success is None
        assert event.coord_x is None
        assert event.related_event_ids is None

    def test_event_with_coordinates(self) -> None:
        """Test event with shot coordinates."""
        event = CanonicalPBPEvent(
            event_number=42,
            period=2,
            clock_seconds=330,
            event_type=EventType.SHOT,
            shot_type=ShotType.TWO_POINT,
            player_external_id="P123",
            coord_x=7.5,
            coord_y=0.5,
            success=True,
        )
        assert event.coord_x == 7.5
        assert event.coord_y == 0.5


class TestCanonicalSeason:
    """Tests for CanonicalSeason dataclass."""

    def test_season_creation(self) -> None:
        """Test creating a season with all fields."""
        season = CanonicalSeason(
            external_id="E2024",
            source="euroleague",
            name="2024-25",
            start_date=date(2024, 10, 1),
            end_date=date(2025, 5, 31),
            is_current=True,
        )
        assert season.external_id == "E2024"
        assert season.name == "2024-25"
        assert season.is_current is True

    def test_season_defaults(self) -> None:
        """Test season with default is_current."""
        season = CanonicalSeason(
            external_id="E2023",
            source="euroleague",
            name="2023-24",
            start_date=None,
            end_date=None,
        )
        assert season.is_current is False

    def test_season_invalid_format_raises_error(self) -> None:
        """Test that invalid season name format raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            CanonicalSeason(
                external_id="E2024",
                source="euroleague",
                name="E2024",  # Invalid - not YYYY-YY format
                start_date=None,
                end_date=None,
            )

    def test_season_wrong_suffix_raises_error(self) -> None:
        """Test that wrong year suffix raises SeasonFormatError."""
        with pytest.raises(SeasonFormatError):
            CanonicalSeason(
                external_id="E2024",
                source="euroleague",
                name="2024-26",  # Invalid - should be 2024-25
                start_date=None,
                end_date=None,
            )
