"""Tests for WinnerConverter class."""

import json
from datetime import date
from pathlib import Path

import pytest

from src.sync.canonical import (
    ConversionError,
    EventType,
    FoulType,
    Position,
    ShotType,
)
from src.sync.winner.converter import WinnerConverter

FIXTURES = Path(__file__).parent.parent.parent.parent / "fixtures" / "winner"


class TestWinnerConverterWithRealData:
    """Tests using real fixture data from Winner API."""

    @pytest.fixture
    def roster_data(self) -> list[dict]:
        """Load real roster data from fixture."""
        with open(FIXTURES / "roster_sample.json") as f:
            return json.load(f)

    @pytest.fixture
    def boxscore_data(self) -> dict:
        """Load real boxscore data from fixture."""
        with open(FIXTURES / "boxscore.json") as f:
            return json.load(f)

    @pytest.fixture
    def games_data(self) -> list[dict]:
        """Load real games data from fixture."""
        with open(FIXTURES / "games_2024_25.json") as f:
            data = json.load(f)
            # Handle nested structure
            if isinstance(data, list) and data and "games" in data[0]:
                return data[0]["games"]
            return data

    @pytest.fixture
    def pbp_data(self) -> dict:
        """Load real PBP data from fixture."""
        with open(FIXTURES / "pbp_events.json") as f:
            return json.load(f)

    @pytest.fixture
    def converter(self) -> WinnerConverter:
        return WinnerConverter()

    def test_source_is_winner(self, converter: WinnerConverter) -> None:
        """Test that source attribute is set correctly."""
        assert converter.source == "winner"

    # === Player Conversion Tests ===

    def test_convert_all_roster_players(
        self, converter: WinnerConverter, roster_data: list[dict]
    ) -> None:
        """All players in roster convert without errors."""
        players = []
        for raw in roster_data:
            player = converter.convert_player(raw)
            players.append(player)

        assert len(players) == len(roster_data)
        for player in players:
            assert player.external_id
            assert player.first_name or player.last_name
            assert player.source == "winner"

    def test_real_player_positions_are_valid(
        self, converter: WinnerConverter, roster_data: list[dict]
    ) -> None:
        """All positions from real data are valid."""
        valid_positions = {
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
            Position.SMALL_FORWARD,
            Position.POWER_FORWARD,
            Position.CENTER,
        }
        for raw in roster_data:
            player = converter.convert_player(raw)
            for pos in player.positions:
                assert pos in valid_positions, f"Invalid position: {pos}"

    def test_real_player_heights_in_range(
        self, converter: WinnerConverter, roster_data: list[dict]
    ) -> None:
        """All heights from real data are in valid range."""
        for raw in roster_data:
            player = converter.convert_player(raw)
            if player.height_cm:
                assert 150 <= player.height_cm <= 250, f"Bad height: {player.height_cm}"

    def test_real_player_birthdates_reasonable(
        self, converter: WinnerConverter, roster_data: list[dict]
    ) -> None:
        """All birthdates from real data are reasonable."""
        for raw in roster_data:
            player = converter.convert_player(raw)
            if player.birth_date:
                assert player.birth_date.year >= 1970
                assert player.birth_date < date.today()

    def test_real_player_jersey_numbers(
        self, converter: WinnerConverter, roster_data: list[dict]
    ) -> None:
        """All jersey numbers from real data are preserved."""
        for raw in roster_data:
            player = converter.convert_player(raw)
            if raw.get("jersey_number"):
                assert player.jersey_number == str(raw["jersey_number"])

    # === Stats Conversion Tests ===

    def test_convert_boxscore_players(
        self, converter: WinnerConverter, boxscore_data: dict
    ) -> None:
        """All players in boxscore convert without errors."""
        home_players = boxscore_data["result"]["boxscore"]["homeTeam"]["players"]
        away_players = boxscore_data["result"]["boxscore"]["awayTeam"]["players"]

        all_stats = []
        for raw in home_players + away_players:
            stats = converter.convert_player_stats(raw)
            all_stats.append(stats)

        assert len(all_stats) == len(home_players) + len(away_players)
        for stats in all_stats:
            assert stats.minutes_seconds >= 0
            assert stats.points >= 0

    def test_boxscore_minutes_converted_to_seconds(
        self, converter: WinnerConverter, boxscore_data: dict
    ) -> None:
        """Minutes in MM:SS format are converted to seconds."""
        home_players = boxscore_data["result"]["boxscore"]["homeTeam"]["players"]

        # First player has "25:25" minutes
        first_player = home_players[0]
        stats = converter.convert_player_stats(first_player)
        # 25 * 60 + 25 = 1525
        assert stats.minutes_seconds == 1525

    def test_boxscore_shooting_stats_calculated(
        self, converter: WinnerConverter, boxscore_data: dict
    ) -> None:
        """Shooting stats are correctly calculated from raw data."""
        home_players = boxscore_data["result"]["boxscore"]["homeTeam"]["players"]

        # Find a player with actual shooting attempts
        for raw in home_players:
            if int(raw.get("fg_2m", 0)) > 0 or int(raw.get("fg_3m", 0)) > 0:
                stats = converter.convert_player_stats(raw)
                fg_2m = int(raw["fg_2m"])
                fg_3m = int(raw["fg_3m"])
                assert stats.field_goals_made == fg_2m + fg_3m
                break

    # === Game Conversion Tests ===

    def test_convert_all_games(
        self, converter: WinnerConverter, games_data: list[dict]
    ) -> None:
        """All games convert without errors."""
        games = []
        for raw in games_data:
            game = converter.convert_game(raw)
            games.append(game)

        assert len(games) == len(games_data)
        for game in games:
            assert game.external_id
            assert game.home_team_external_id
            assert game.away_team_external_id
            assert game.source == "winner"

    def test_game_dates_parsed(
        self, converter: WinnerConverter, games_data: list[dict]
    ) -> None:
        """Game dates are correctly parsed."""
        for raw in games_data:
            game = converter.convert_game(raw)
            assert game.game_date is not None
            assert game.game_date.year >= 2024

    def test_game_scores_parsed(
        self, converter: WinnerConverter, games_data: list[dict]
    ) -> None:
        """Game scores are correctly parsed."""
        for raw in games_data:
            game = converter.convert_game(raw)
            if raw.get("score_team1") is not None:
                assert game.home_score == int(raw["score_team1"])
                assert game.away_score == int(raw["score_team2"])

    # === PBP Conversion Tests ===

    def test_convert_pbp_events(
        self, converter: WinnerConverter, pbp_data: dict
    ) -> None:
        """PBP events convert without errors."""
        events = []
        for raw in pbp_data["Events"]:
            event = converter.convert_pbp_event(raw)
            if event:  # Some events may be filtered
                events.append(event)

        assert len(events) > 0
        for event in events:
            assert event.event_type is not None
            assert event.period >= 1

    def test_pbp_shot_events_have_attributes(
        self, converter: WinnerConverter, pbp_data: dict
    ) -> None:
        """Shot events have proper shot_type and success attributes."""
        for raw in pbp_data["Events"]:
            event = converter.convert_pbp_event(raw)
            if event and event.event_type == EventType.SHOT:
                assert event.shot_type in [ShotType.TWO_POINT, ShotType.THREE_POINT]
                assert event.success is not None


class TestWinnerConverterEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def converter(self) -> WinnerConverter:
        return WinnerConverter()

    # === Player Edge Cases ===

    def test_missing_position_returns_empty_list(
        self, converter: WinnerConverter
    ) -> None:
        raw = {"external_id": "1", "first_name": "Test", "last_name": "Player"}
        player = converter.convert_player(raw)
        assert player.positions == []

    def test_unknown_position_returns_empty_list(
        self, converter: WinnerConverter
    ) -> None:
        raw = {
            "external_id": "1",
            "first_name": "Test",
            "last_name": "Player",
            "position": "UNKNOWN",
        }
        player = converter.convert_player(raw)
        assert player.positions == []

    def test_invalid_height_raises_error(self, converter: WinnerConverter) -> None:
        raw = {
            "external_id": "1",
            "first_name": "Test",
            "last_name": "Player",
            "height_cm": 300,
        }
        with pytest.raises(ConversionError, match="Invalid height"):
            converter.convert_player(raw)

    def test_missing_external_id_raises_error(self, converter: WinnerConverter) -> None:
        raw = {"first_name": "Test", "last_name": "Player"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_player(raw)

    def test_player_with_full_name_only(self, converter: WinnerConverter) -> None:
        """Test parsing player with only full name, no first/last."""
        raw = {"external_id": "1", "name": "John Smith"}
        player = converter.convert_player(raw)
        assert player.first_name == "John"
        assert player.last_name == "Smith"

    def test_player_with_single_name(self, converter: WinnerConverter) -> None:
        """Test parsing player with single name."""
        raw = {"external_id": "1", "name": "Neymar"}
        player = converter.convert_player(raw)
        assert player.first_name == "Neymar"
        assert player.last_name == ""

    def test_player_nationality_is_none(self, converter: WinnerConverter) -> None:
        """Winner doesn't reliably provide nationality."""
        raw = {"external_id": "1", "first_name": "Test", "last_name": "Player"}
        player = converter.convert_player(raw)
        assert player.nationality is None

    # === Position Mapping Edge Cases ===

    def test_position_mapping_case_insensitive(
        self, converter: WinnerConverter
    ) -> None:
        assert converter.map_position("g") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]
        assert converter.map_position("G") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]
        assert converter.map_position("guard") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]
        assert converter.map_position("Guard") == [
            Position.POINT_GUARD,
            Position.SHOOTING_GUARD,
        ]

    def test_position_mapping_all_types(self, converter: WinnerConverter) -> None:
        """Test all position types are mapped correctly."""
        assert Position.POINT_GUARD in converter.map_position("PG")
        assert Position.SHOOTING_GUARD in converter.map_position("SG")
        assert Position.SMALL_FORWARD in converter.map_position("SF")
        assert Position.POWER_FORWARD in converter.map_position("PF")
        assert Position.CENTER in converter.map_position("C")
        assert converter.map_position("G-F") == [
            Position.SHOOTING_GUARD,
            Position.SMALL_FORWARD,
        ]
        assert converter.map_position("F-C") == [
            Position.POWER_FORWARD,
            Position.CENTER,
        ]

    # === Minutes Conversion Edge Cases ===

    def test_minutes_conversion_various_formats(
        self, converter: WinnerConverter
    ) -> None:
        assert converter.parse_minutes_to_seconds("25:30") == 1530
        assert converter.parse_minutes_to_seconds("00:00") == 0
        assert converter.parse_minutes_to_seconds("08:45") == 525
        assert converter.parse_minutes_to_seconds(25) == 1500
        assert converter.parse_minutes_to_seconds(None) == 0
        assert converter.parse_minutes_to_seconds("") == 0

    # === Game Conversion Edge Cases ===

    def test_game_missing_external_id_raises_error(
        self, converter: WinnerConverter
    ) -> None:
        raw = {"team1": 100, "team2": 200, "game_date_txt": "01/01/2024"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_game(raw)

    def test_game_missing_team_ids_raises_error(
        self, converter: WinnerConverter
    ) -> None:
        raw = {"ExternalID": "1", "game_date_txt": "01/01/2024"}
        with pytest.raises(ConversionError, match="missing team IDs"):
            converter.convert_game(raw)

    def test_game_missing_date_raises_error(self, converter: WinnerConverter) -> None:
        raw = {"ExternalID": "1", "team1": 100, "team2": 200}
        with pytest.raises(ConversionError, match="missing date"):
            converter.convert_game(raw)

    def test_game_status_detection(self, converter: WinnerConverter) -> None:
        """Test game status is correctly determined."""
        # Final game with scores
        game1 = converter.convert_game(
            {
                "ExternalID": "1",
                "team1": 100,
                "team2": 200,
                "game_date_txt": "01/01/2024",
                "score_team1": 85,
                "score_team2": 78,
                "gameFinished": True,
            }
        )
        assert game1.status == "FINAL"

        # Scheduled game without scores
        game2 = converter.convert_game(
            {
                "ExternalID": "2",
                "team1": 100,
                "team2": 200,
                "game_date_txt": "01/01/2024",
            }
        )
        assert game2.status == "SCHEDULED"

    # === Team Conversion Edge Cases ===

    def test_team_missing_external_id_raises_error(
        self, converter: WinnerConverter
    ) -> None:
        raw = {"name": "Test Team"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_team(raw)

    def test_team_missing_name_raises_error(self, converter: WinnerConverter) -> None:
        raw = {"team_id": "100"}
        with pytest.raises(ConversionError, match="missing name"):
            converter.convert_team(raw)

    def test_team_country_defaults_to_israel(self, converter: WinnerConverter) -> None:
        raw = {"team_id": "100", "name": "Test Team"}
        team = converter.convert_team(raw)
        assert team.country == "Israel"

    # === PBP Event Edge Cases ===

    def test_pbp_unknown_event_returns_none(self, converter: WinnerConverter) -> None:
        raw = {"EventType": "UNKNOWN_EVENT", "Quarter": 1, "GameClock": "10:00"}
        event = converter.convert_pbp_event(raw)
        assert event is None

    def test_pbp_empty_event_type_returns_none(
        self, converter: WinnerConverter
    ) -> None:
        raw = {"EventType": "", "Quarter": 1, "GameClock": "10:00"}
        event = converter.convert_pbp_event(raw)
        assert event is None

    def test_pbp_foul_has_foul_type(self, converter: WinnerConverter) -> None:
        raw = {
            "EventId": "1",
            "EventType": "FOUL",
            "Quarter": 1,
            "GameClock": "10:00",
            "PlayerId": "1001",
        }
        event = converter.convert_pbp_event(raw)
        assert event is not None
        assert event.event_type == EventType.FOUL
        assert event.foul_type == FoulType.PERSONAL

    def test_pbp_clock_parsed_correctly(self, converter: WinnerConverter) -> None:
        raw = {
            "EventId": "1",
            "EventType": "MADE_2PT",
            "Quarter": 1,
            "GameClock": "09:45",
            "PlayerId": "1001",
        }
        event = converter.convert_pbp_event(raw)
        assert event is not None
        # 9 * 60 + 45 = 585
        assert event.clock_seconds == 585

    # === Season Conversion Edge Cases ===

    def test_season_missing_external_id_raises_error(
        self, converter: WinnerConverter
    ) -> None:
        raw = {"name": "2024-25"}
        with pytest.raises(ConversionError, match="missing external_id"):
            converter.convert_season(raw)

    def test_season_name_generated_from_year(self, converter: WinnerConverter) -> None:
        raw = {"game_year": 2025}
        season = converter.convert_season(raw)
        assert season.name == "2024-25"

    def test_season_is_current_default_false(self, converter: WinnerConverter) -> None:
        raw = {"game_year": 2025}
        season = converter.convert_season(raw)
        assert season.is_current is False


class TestWinnerConverterEventMapping:
    """Tests for event type mapping."""

    @pytest.fixture
    def converter(self) -> WinnerConverter:
        return WinnerConverter()

    def test_shot_events(self, converter: WinnerConverter) -> None:
        event_type, attrs = converter.map_event_type("MADE_2PT")
        assert event_type == EventType.SHOT
        assert attrs["shot_type"] == ShotType.TWO_POINT
        assert attrs["success"] is True

        event_type, attrs = converter.map_event_type("MISS_2PT")
        assert event_type == EventType.SHOT
        assert attrs["success"] is False

        event_type, attrs = converter.map_event_type("MADE_3PT")
        assert attrs["shot_type"] == ShotType.THREE_POINT
        assert attrs["success"] is True

    def test_free_throw_events(self, converter: WinnerConverter) -> None:
        event_type, attrs = converter.map_event_type("MADE_FT")
        assert event_type == EventType.FREE_THROW
        assert attrs["success"] is True

        event_type, attrs = converter.map_event_type("MISS_FT")
        assert event_type == EventType.FREE_THROW
        assert attrs["success"] is False

    def test_other_events(self, converter: WinnerConverter) -> None:
        assert converter.map_event_type("REBOUND")[0] == EventType.REBOUND
        assert converter.map_event_type("ASSIST")[0] == EventType.ASSIST
        assert converter.map_event_type("TURNOVER")[0] == EventType.TURNOVER
        assert converter.map_event_type("STEAL")[0] == EventType.STEAL
        assert converter.map_event_type("BLOCK")[0] == EventType.BLOCK
        assert converter.map_event_type("TIMEOUT")[0] == EventType.TIMEOUT
        assert converter.map_event_type("SUBSTITUTION")[0] == EventType.SUBSTITUTION
