"""
Tests for Raw to Canonical conversion utilities.

Tests the conversion functions that bridge Raw types to Canonical types
during the migration away from Raw types.
"""

from datetime import datetime

import pytest

from src.schemas.enums import EventType, GameStatus
from src.sync.raw_to_canonical import (
    _parse_clock_to_seconds,
    raw_boxscore_to_canonical_stats,
    raw_game_to_canonical,
    raw_pbp_list_to_canonical,
    raw_pbp_to_canonical,
    raw_player_stats_to_canonical,
)
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerStats,
)


class TestRawGameToCanonical:
    """Tests for raw_game_to_canonical function."""

    def test_converts_basic_game(self):
        """Basic game conversion works."""
        raw = RawGame(
            external_id="g123",
            home_team_external_id="t1",
            away_team_external_id="t2",
            game_date=datetime(2024, 11, 15, 20, 0),
            status=GameStatus.FINAL,
            home_score=85,
            away_score=78,
        )

        canonical = raw_game_to_canonical(raw, "winner", "2024-25")

        assert canonical.external_id == "g123"
        assert canonical.source == "winner"
        assert canonical.season_external_id == "2024-25"
        assert canonical.home_team_external_id == "t1"
        assert canonical.away_team_external_id == "t2"
        assert canonical.game_date == datetime(2024, 11, 15, 20, 0)
        assert canonical.status == "FINAL"
        assert canonical.home_score == 85
        assert canonical.away_score == 78

    def test_converts_status_enum_to_string(self):
        """Status enum is converted to string."""
        raw = RawGame(
            external_id="g123",
            home_team_external_id="t1",
            away_team_external_id="t2",
            game_date=datetime(2024, 11, 15, 20, 0),
            status=GameStatus.SCHEDULED,
        )

        canonical = raw_game_to_canonical(raw, "winner", "2024-25")

        assert canonical.status == "SCHEDULED"

    def test_handles_none_scores(self):
        """None scores are preserved."""
        raw = RawGame(
            external_id="g123",
            home_team_external_id="t1",
            away_team_external_id="t2",
            game_date=datetime(2024, 11, 15, 20, 0),
            status=GameStatus.SCHEDULED,
            home_score=None,
            away_score=None,
        )

        canonical = raw_game_to_canonical(raw, "winner", "2024-25")

        assert canonical.home_score is None
        assert canonical.away_score is None


class TestRawPlayerStatsToCanonical:
    """Tests for raw_player_stats_to_canonical function."""

    def test_converts_basic_stats(self):
        """Basic stats conversion works."""
        raw = RawPlayerStats(
            player_external_id="p123",
            player_name="John Doe",
            team_external_id="t1",
            minutes_played=2040,  # 34 minutes in seconds
            is_starter=True,
            points=25,
            field_goals_made=9,
            field_goals_attempted=18,
            assists=5,
            total_rebounds=7,
        )

        canonical = raw_player_stats_to_canonical(raw)

        assert canonical.player_external_id == "p123"
        assert canonical.player_name == "John Doe"
        assert canonical.team_external_id == "t1"
        assert canonical.minutes_seconds == 2040
        assert canonical.is_starter is True
        assert canonical.points == 25
        assert canonical.field_goals_made == 9
        assert canonical.field_goals_attempted == 18
        assert canonical.assists == 5
        assert canonical.total_rebounds == 7

    def test_preserves_all_stats(self):
        """All stats fields are preserved."""
        raw = RawPlayerStats(
            player_external_id="p123",
            player_name="John Doe",
            team_external_id="t1",
            minutes_played=1800,
            is_starter=False,
            points=20,
            field_goals_made=8,
            field_goals_attempted=15,
            two_pointers_made=5,
            two_pointers_attempted=10,
            three_pointers_made=3,
            three_pointers_attempted=5,
            free_throws_made=1,
            free_throws_attempted=2,
            offensive_rebounds=2,
            defensive_rebounds=4,
            total_rebounds=6,
            assists=3,
            turnovers=2,
            steals=1,
            blocks=0,
            personal_fouls=3,
            plus_minus=5,
        )

        canonical = raw_player_stats_to_canonical(raw)

        assert canonical.two_pointers_made == 5
        assert canonical.two_pointers_attempted == 10
        assert canonical.three_pointers_made == 3
        assert canonical.three_pointers_attempted == 5
        assert canonical.free_throws_made == 1
        assert canonical.free_throws_attempted == 2
        assert canonical.offensive_rebounds == 2
        assert canonical.defensive_rebounds == 4
        assert canonical.turnovers == 2
        assert canonical.steals == 1
        assert canonical.blocks == 0
        assert canonical.personal_fouls == 3
        assert canonical.plus_minus == 5


class TestRawBoxscoreToCanonicalStats:
    """Tests for raw_boxscore_to_canonical_stats function."""

    def test_converts_both_teams(self):
        """Both home and away players are converted."""
        home_stats = RawPlayerStats(
            player_external_id="h1",
            player_name="Home Player",
            team_external_id="t1",
            points=20,
            jersey_number="5",
        )
        away_stats = RawPlayerStats(
            player_external_id="a1",
            player_name="Away Player",
            team_external_id="t2",
            points=15,
            jersey_number="10",
        )

        raw = RawBoxScore(
            game=RawGame(
                external_id="g1",
                home_team_external_id="t1",
                away_team_external_id="t2",
                game_date=datetime.now(),
                status=GameStatus.FINAL,
            ),
            home_players=[home_stats],
            away_players=[away_stats],
        )

        canonical_stats, jersey_numbers = raw_boxscore_to_canonical_stats(raw)

        assert len(canonical_stats) == 2
        assert canonical_stats[0].player_external_id == "h1"
        assert canonical_stats[0].points == 20
        assert canonical_stats[1].player_external_id == "a1"
        assert canonical_stats[1].points == 15
        assert jersey_numbers == ["5", "10"]

    def test_handles_empty_boxscore(self):
        """Empty boxscore returns empty list."""
        raw = RawBoxScore(
            game=RawGame(
                external_id="g1",
                home_team_external_id="t1",
                away_team_external_id="t2",
                game_date=datetime.now(),
                status=GameStatus.FINAL,
            ),
            home_players=[],
            away_players=[],
        )

        canonical_stats, jersey_numbers = raw_boxscore_to_canonical_stats(raw)

        assert canonical_stats == []
        assert jersey_numbers == []

    def test_overrides_team_ids(self):
        """Team IDs can be overridden for correct mapping."""
        home_stats = RawPlayerStats(
            player_external_id="h1",
            player_name="Home Player",
            team_external_id="2",  # Internal ID
            points=20,
        )
        away_stats = RawPlayerStats(
            player_external_id="a1",
            player_name="Away Player",
            team_external_id="4",  # Internal ID
            points=15,
        )

        raw = RawBoxScore(
            game=RawGame(
                external_id="g1",
                home_team_external_id="2",
                away_team_external_id="4",
                game_date=datetime.now(),
                status=GameStatus.FINAL,
            ),
            home_players=[home_stats],
            away_players=[away_stats],
        )

        # Override with real IDs
        canonical_stats, _ = raw_boxscore_to_canonical_stats(
            raw,
            home_team_external_id="1109",
            away_team_external_id="1112",
        )

        assert canonical_stats[0].team_external_id == "1109"
        assert canonical_stats[1].team_external_id == "1112"


class TestRawPbpToCanonical:
    """Tests for raw_pbp_to_canonical function."""

    def test_converts_basic_event(self):
        """Basic event conversion works."""
        raw = RawPBPEvent(
            event_number=42,
            period=2,
            clock="05:30",
            event_type=EventType.SHOT,
            player_external_id="p123",
            player_name="John Doe",
            team_external_id="t1",
            success=True,
        )

        canonical = raw_pbp_to_canonical(raw)

        assert canonical.event_number == 42
        assert canonical.period == 2
        assert canonical.clock_seconds == 330  # 5:30 = 330 seconds
        assert canonical.event_type == EventType.SHOT
        assert canonical.player_external_id == "p123"
        assert canonical.player_name == "John Doe"
        assert canonical.team_external_id == "t1"
        assert canonical.success is True

    def test_preserves_coordinates(self):
        """Shot coordinates are preserved."""
        raw = RawPBPEvent(
            event_number=1,
            period=1,
            clock="10:00",
            event_type=EventType.SHOT,
            coord_x=25.5,
            coord_y=8.0,
        )

        canonical = raw_pbp_to_canonical(raw)

        assert canonical.coord_x == 25.5
        assert canonical.coord_y == 8.0

    def test_preserves_related_events(self):
        """Related event IDs are preserved."""
        raw = RawPBPEvent(
            event_number=10,
            period=1,
            clock="08:00",
            event_type=EventType.ASSIST,
            related_event_numbers=[9],
        )

        canonical = raw_pbp_to_canonical(raw)

        assert canonical.related_event_ids == [9]


class TestRawPbpListToCanonical:
    """Tests for raw_pbp_list_to_canonical function."""

    def test_converts_multiple_events(self):
        """Multiple events are converted."""
        events = [
            RawPBPEvent(
                event_number=1,
                period=1,
                clock="10:00",
                event_type=EventType.SHOT,
            ),
            RawPBPEvent(
                event_number=2,
                period=1,
                clock="09:45",
                event_type=EventType.REBOUND,
            ),
        ]

        canonical_events = raw_pbp_list_to_canonical(events)

        assert len(canonical_events) == 2
        assert canonical_events[0].event_number == 1
        assert canonical_events[1].event_number == 2

    def test_handles_empty_list(self):
        """Empty list returns empty list."""
        canonical_events = raw_pbp_list_to_canonical([])

        assert canonical_events == []


class TestParseClockToSeconds:
    """Tests for _parse_clock_to_seconds helper."""

    def test_parses_standard_clock(self):
        """Standard MM:SS format is parsed."""
        assert _parse_clock_to_seconds("10:30") == 630
        assert _parse_clock_to_seconds("5:00") == 300
        assert _parse_clock_to_seconds("0:45") == 45

    def test_handles_single_digit_minutes(self):
        """Single digit minutes are handled."""
        assert _parse_clock_to_seconds("5:30") == 330
        assert _parse_clock_to_seconds("1:00") == 60

    def test_handles_invalid_clock(self):
        """Invalid clock returns 0."""
        assert _parse_clock_to_seconds("") == 0
        assert _parse_clock_to_seconds("invalid") == 0
        assert _parse_clock_to_seconds("abc:def") == 0
