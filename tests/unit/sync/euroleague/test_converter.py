"""Tests for EuroleagueConverter class."""

import json
from pathlib import Path

import pytest

from src.sync.canonical import (
    ConversionError,
    EventType,
    FoulType,
    Position,
    ReboundType,
    ShotType,
)
from src.sync.euroleague.converter import EuroleagueConverter

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "euroleague"


class TestEuroleagueConverterWithRealData:
    """Tests using real fixture data from Euroleague API."""

    @pytest.fixture
    def schedule_data(self) -> list[dict]:
        """Load real schedule data from fixture."""
        with open(FIXTURES / "schedule.json") as f:
            return json.load(f)

    @pytest.fixture
    def boxscore_data(self) -> list[dict]:
        """Load real boxscore data from fixture."""
        with open(FIXTURES / "boxscore.json") as f:
            return json.load(f)

    @pytest.fixture
    def pbp_data(self) -> list[dict]:
        """Load real PBP data from fixture."""
        with open(FIXTURES / "pbp.json") as f:
            return json.load(f)

    @pytest.fixture
    def converter(self) -> EuroleagueConverter:
        return EuroleagueConverter()

    def test_source_is_euroleague(self, converter: EuroleagueConverter) -> None:
        """Test that source attribute is set correctly."""
        assert converter.source == "euroleague"

    # === Game Conversion Tests ===

    def test_convert_all_games(
        self, converter: EuroleagueConverter, schedule_data: list[dict]
    ) -> None:
        """All games in schedule convert without errors."""
        games = []
        for raw in schedule_data:
            game = converter.convert_game(raw)
            games.append(game)

        assert len(games) == len(schedule_data)
        for game in games:
            assert game.external_id
            assert game.home_team_external_id
            assert game.away_team_external_id
            assert game.source == "euroleague"

    def test_game_dates_parsed(
        self, converter: EuroleagueConverter, schedule_data: list[dict]
    ) -> None:
        """Game dates in 'Oct 03, 2024' format are correctly parsed."""
        for raw in schedule_data:
            game = converter.convert_game(raw)
            assert game.game_date is not None
            assert game.game_date.year >= 2024

    def test_game_venue_preserved(
        self, converter: EuroleagueConverter, schedule_data: list[dict]
    ) -> None:
        """Arena name is preserved as venue."""
        for raw in schedule_data:
            game = converter.convert_game(raw)
            if raw.get("arenaname"):
                assert game.venue == raw["arenaname"]

    # === Stats Conversion Tests ===

    def test_convert_boxscore_players(
        self, converter: EuroleagueConverter, boxscore_data: list[dict]
    ) -> None:
        """All players in boxscore convert without errors."""
        all_stats = []
        for raw in boxscore_data:
            stats = converter.convert_player_stats(raw)
            all_stats.append(stats)

        assert len(all_stats) == len(boxscore_data)
        for stats in all_stats:
            assert stats.minutes_seconds >= 0
            assert stats.points >= 0

    def test_boxscore_minutes_converted_to_seconds(
        self, converter: EuroleagueConverter, boxscore_data: list[dict]
    ) -> None:
        """Minutes in MM:SS format are converted to seconds."""
        # Find a player with actual minutes played
        for raw in boxscore_data:
            if raw.get("Minutes") and raw["Minutes"] != "DNP":
                stats = converter.convert_player_stats(raw)
                assert stats.minutes_seconds > 0
                break

    def test_boxscore_dnp_handled(
        self, converter: EuroleagueConverter, boxscore_data: list[dict]
    ) -> None:
        """DNP (Did Not Play) is handled as 0 seconds."""
        for raw in boxscore_data:
            if raw.get("Minutes") == "DNP":
                stats = converter.convert_player_stats(raw)
                assert stats.minutes_seconds == 0
                break

    def test_boxscore_shooting_stats_calculated(
        self, converter: EuroleagueConverter, boxscore_data: list[dict]
    ) -> None:
        """Shooting stats are correctly summed."""
        for raw in boxscore_data:
            fg_2m = raw.get("FieldGoalsMade2") or 0
            fg_3m = raw.get("FieldGoalsMade3") or 0
            if fg_2m > 0 or fg_3m > 0:
                stats = converter.convert_player_stats(raw)
                assert stats.field_goals_made == fg_2m + fg_3m
                break

    # === PBP Conversion Tests ===

    def test_convert_pbp_events(
        self, converter: EuroleagueConverter, pbp_data: list[dict]
    ) -> None:
        """PBP events convert without errors."""
        events = []
        for raw in pbp_data:
            event = converter.convert_pbp_event(raw)
            if event:  # Some events may be filtered
                events.append(event)

        assert len(events) > 0
        for event in events:
            assert event.event_type is not None
            assert event.period >= 1

    def test_pbp_shot_events_have_attributes(
        self, converter: EuroleagueConverter, pbp_data: list[dict]
    ) -> None:
        """Shot events have proper shot_type and success attributes."""
        for raw in pbp_data:
            event = converter.convert_pbp_event(raw)
            if event and event.event_type == EventType.SHOT:
                assert event.shot_type in [ShotType.TWO_POINT, ShotType.THREE_POINT]
                assert event.success is not None

    def test_pbp_rebound_events_have_type(
        self, converter: EuroleagueConverter, pbp_data: list[dict]
    ) -> None:
        """Rebound events have proper rebound_type."""
        for raw in pbp_data:
            event = converter.convert_pbp_event(raw)
            if event and event.event_type == EventType.REBOUND:
                assert event.rebound_type in [
                    ReboundType.OFFENSIVE,
                    ReboundType.DEFENSIVE,
                ]


class TestEuroleagueConverterEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def converter(self) -> EuroleagueConverter:
        return EuroleagueConverter()

    # === Player Edge Cases ===

    def test_player_height_meters_to_cm(self, converter: EuroleagueConverter) -> None:
        """Height in meters is converted to cm."""
        raw = {
            "code": "P001",
            "name": "SMITH, JOHN",
            "height": "1.98",
        }
        player = converter.convert_player(raw)
        assert player.height_cm == 198

    def test_player_height_short_player(self, converter: EuroleagueConverter) -> None:
        """Short height is converted correctly."""
        raw = {
            "code": "P001",
            "name": "SMITH, JOHN",
            "height": "1.75",
        }
        player = converter.convert_player(raw)
        assert player.height_cm == 175

    def test_player_height_tall_player(self, converter: EuroleagueConverter) -> None:
        """Tall height is converted correctly."""
        raw = {
            "code": "P001",
            "name": "SMITH, JOHN",
            "height": "2.21",
        }
        player = converter.convert_player(raw)
        assert player.height_cm == 221

    def test_player_invalid_height_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        """Invalid height (outside 150-250 cm) raises error."""
        raw = {
            "code": "P001",
            "name": "SMITH, JOHN",
            "height": "3.50",  # 350 cm - impossible
        }
        with pytest.raises(ConversionError, match="Invalid height"):
            converter.convert_player(raw)

    def test_player_name_last_first_format(
        self, converter: EuroleagueConverter
    ) -> None:
        """Name in 'LAST, FIRST' format is parsed correctly."""
        raw = {
            "code": "P001",
            "name": "GILGEOUS-ALEXANDER, SHAI",
        }
        player = converter.convert_player(raw)
        assert player.first_name == "Shai"
        assert player.last_name == "Gilgeous-Alexander"

    def test_player_name_single_name(self, converter: EuroleagueConverter) -> None:
        """Single name (no comma) is handled."""
        raw = {
            "code": "P001",
            "name": "NEYMAR",
        }
        player = converter.convert_player(raw)
        assert player.first_name == "Neymar"
        assert player.last_name == ""

    def test_player_missing_external_id_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"name": "SMITH, JOHN"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_player(raw)

    def test_player_id_with_trailing_spaces(
        self, converter: EuroleagueConverter
    ) -> None:
        """Player ID with trailing spaces is trimmed."""
        raw = {
            "Player_ID": "P001234   ",  # Has trailing spaces
            "name": "SMITH, JOHN",
        }
        player = converter.convert_player(raw)
        assert player.external_id == "P001234"

    # === Position Mapping Edge Cases ===

    def test_position_mapping_guard(self, converter: EuroleagueConverter) -> None:
        assert converter.map_position("Guard") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]

    def test_position_mapping_forward(self, converter: EuroleagueConverter) -> None:
        assert converter.map_position("Forward") == [
            Position.SMALL_FORWARD,
            Position.POWER_FORWARD,
        ]

    def test_position_mapping_center(self, converter: EuroleagueConverter) -> None:
        assert converter.map_position("Center") == [Position.CENTER]

    def test_position_mapping_point_guard(self, converter: EuroleagueConverter) -> None:
        assert converter.map_position("Point Guard") == [Position.POINT_GUARD]

    def test_position_mapping_case_insensitive(
        self, converter: EuroleagueConverter
    ) -> None:
        assert converter.map_position("GUARD") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]
        assert converter.map_position("guard") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]

    def test_position_mapping_unknown_returns_empty(
        self, converter: EuroleagueConverter
    ) -> None:
        assert converter.map_position("UNKNOWN") == []
        assert converter.map_position(None) == []

    # === Minutes Conversion Edge Cases ===

    def test_minutes_conversion_mm_ss(self, converter: EuroleagueConverter) -> None:
        assert converter.parse_minutes_to_seconds("25:30") == 1530
        assert converter.parse_minutes_to_seconds("16:18") == 978
        assert converter.parse_minutes_to_seconds("00:00") == 0

    def test_minutes_conversion_dnp(self, converter: EuroleagueConverter) -> None:
        assert converter.parse_minutes_to_seconds("DNP") == 0

    def test_minutes_conversion_none(self, converter: EuroleagueConverter) -> None:
        assert converter.parse_minutes_to_seconds(None) == 0
        assert converter.parse_minutes_to_seconds("") == 0

    # === Game Conversion Edge Cases ===

    def test_game_missing_external_id_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"homecode": "BER", "awaycode": "PAN", "date": "Oct 03, 2024"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_game(raw)

    def test_game_missing_team_codes_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"gamecode": "E2024_1", "date": "Oct 03, 2024"}
        with pytest.raises(ConversionError, match="missing team codes"):
            converter.convert_game(raw)

    def test_game_missing_date_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"gamecode": "E2024_1", "homecode": "BER", "awaycode": "PAN"}
        with pytest.raises(ConversionError, match="missing date"):
            converter.convert_game(raw)

    def test_game_season_id_extracted_from_gamecode(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {
            "gamecode": "E2024_1",
            "homecode": "BER",
            "awaycode": "PAN",
            "date": "Oct 03, 2024",
        }
        game = converter.convert_game(raw)
        assert game.season_external_id == "E2024"

    def test_game_status_played(self, converter: EuroleagueConverter) -> None:
        raw = {
            "gamecode": "E2024_1",
            "homecode": "BER",
            "awaycode": "PAN",
            "date": "Oct 03, 2024",
            "played": "true",
        }
        game = converter.convert_game(raw)
        assert game.status == "FINAL"

    def test_game_status_scheduled(self, converter: EuroleagueConverter) -> None:
        raw = {
            "gamecode": "E2024_1",
            "homecode": "BER",
            "awaycode": "PAN",
            "date": "Oct 03, 2024",
        }
        game = converter.convert_game(raw)
        assert game.status == "SCHEDULED"

    # === Team Conversion Edge Cases ===

    def test_team_missing_external_id_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"name": "ALBA Berlin"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_team(raw)

    def test_team_missing_name_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"code": "BER"}
        with pytest.raises(ConversionError, match="missing name"):
            converter.convert_team(raw)

    def test_team_short_name_is_code(self, converter: EuroleagueConverter) -> None:
        raw = {"code": "BER", "name": "ALBA Berlin"}
        team = converter.convert_team(raw)
        assert team.short_name == "BER"

    # === PBP Event Edge Cases ===

    def test_pbp_unknown_event_returns_none(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"PLAYTYPE": "AG", "PERIOD": 1, "MARKERTIME": "10:00"}  # Skipped event
        event = converter.convert_pbp_event(raw)
        assert event is None

    def test_pbp_empty_event_type_returns_none(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"PLAYTYPE": "", "PERIOD": 1, "MARKERTIME": "10:00"}
        event = converter.convert_pbp_event(raw)
        assert event is None

    def test_pbp_clock_parsed_correctly(self, converter: EuroleagueConverter) -> None:
        raw = {
            "PLAYTYPE": "2FGM",
            "PERIOD": 1,
            "MARKERTIME": "09:45",
            "PLAYER_ID": "P001",
        }
        event = converter.convert_pbp_event(raw)
        assert event is not None
        # 9 * 60 + 45 = 585
        assert event.clock_seconds == 585

    # === Season Conversion Edge Cases ===

    def test_season_missing_external_id_raises_error(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"name": "2024-25"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_season(raw)

    def test_season_name_generated_from_code(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"season_code": "E2024"}
        season = converter.convert_season(raw)
        assert season.name == "2024-25"

    def test_season_constructed_from_year(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"year": 2024}
        season = converter.convert_season(raw)
        assert season.external_id == "E2024"
        assert season.name == "2024-25"

    def test_season_is_current_default_false(
        self, converter: EuroleagueConverter
    ) -> None:
        raw = {"season_code": "E2024"}
        season = converter.convert_season(raw)
        assert season.is_current is False


class TestEuroleagueConverterEventMapping:
    """Tests for event type mapping."""

    @pytest.fixture
    def converter(self) -> EuroleagueConverter:
        return EuroleagueConverter()

    def test_shot_events(self, converter: EuroleagueConverter) -> None:
        event_type, attrs = converter.map_event_type("2FGM")
        assert event_type == EventType.SHOT
        assert attrs["shot_type"] == ShotType.TWO_POINT
        assert attrs["success"] is True

        event_type, attrs = converter.map_event_type("2FGA")
        assert event_type == EventType.SHOT
        assert attrs["success"] is False

        event_type, attrs = converter.map_event_type("3FGM")
        assert attrs["shot_type"] == ShotType.THREE_POINT
        assert attrs["success"] is True

        event_type, attrs = converter.map_event_type("3FGA")
        assert attrs["shot_type"] == ShotType.THREE_POINT
        assert attrs["success"] is False

    def test_free_throw_events(self, converter: EuroleagueConverter) -> None:
        event_type, attrs = converter.map_event_type("FTM")
        assert event_type == EventType.FREE_THROW
        assert attrs["success"] is True

        event_type, attrs = converter.map_event_type("FTA")
        assert event_type == EventType.FREE_THROW
        assert attrs["success"] is False

    def test_rebound_events(self, converter: EuroleagueConverter) -> None:
        event_type, attrs = converter.map_event_type("O")
        assert event_type == EventType.REBOUND
        assert attrs["rebound_type"] == ReboundType.OFFENSIVE

        event_type, attrs = converter.map_event_type("D")
        assert event_type == EventType.REBOUND
        assert attrs["rebound_type"] == ReboundType.DEFENSIVE

    def test_other_events(self, converter: EuroleagueConverter) -> None:
        assert converter.map_event_type("AS")[0] == EventType.ASSIST
        assert converter.map_event_type("TO")[0] == EventType.TURNOVER
        assert converter.map_event_type("ST")[0] == EventType.STEAL
        assert converter.map_event_type("BLK")[0] == EventType.BLOCK
        assert converter.map_event_type("FV")[0] == EventType.BLOCK
        assert converter.map_event_type("BP")[0] == EventType.PERIOD_START
        assert converter.map_event_type("EP")[0] == EventType.PERIOD_END

    def test_foul_events(self, converter: EuroleagueConverter) -> None:
        event_type, attrs = converter.map_event_type("CM")
        assert event_type == EventType.FOUL
        assert attrs["foul_type"] == FoulType.PERSONAL

        event_type, attrs = converter.map_event_type("CMT")
        assert event_type == EventType.FOUL
        assert attrs["foul_type"] == FoulType.TECHNICAL
