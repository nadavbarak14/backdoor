"""
Euroleague Mapper Tests

Tests for the EuroleagueMapper class that transforms Euroleague data
to normalized Raw types.
"""

from datetime import date

import pytest

from src.sync.euroleague.mapper import EuroleagueMapper
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawPlayerStats,
    RawSeason,
    RawTeam,
)


@pytest.fixture
def mapper():
    """Create an EuroleagueMapper instance."""
    return EuroleagueMapper()


@pytest.fixture
def sample_boxscore_data():
    """Sample boxscore data from live API."""
    return {
        "Live": False,
        "ByQuarter": [
            {
                "Team": "ALBA BERLIN",
                "Quarter1": 17,
                "Quarter2": 19,
                "Quarter3": 21,
                "Quarter4": 20,
            },
            {
                "Team": "PANATHINAIKOS",
                "Quarter1": 26,
                "Quarter2": 19,
                "Quarter3": 17,
                "Quarter4": 25,
            },
        ],
        "Stats": [
            {
                "Team": "ALBA BERLIN",
                "PlayersStats": [
                    {
                        "Player_ID": "P007025",
                        "IsStarter": 1,
                        "Team": "BER",
                        "Player": "MATTISSECK, JONAS",
                        "Minutes": "24:35",
                        "Points": 6,
                        "FieldGoalsMade2": 2,
                        "FieldGoalsAttempted2": 4,
                        "FieldGoalsMade3": 0,
                        "FieldGoalsAttempted3": 2,
                        "FreeThrowsMade": 2,
                        "FreeThrowsAttempted": 2,
                        "OffensiveRebounds": 1,
                        "DefensiveRebounds": 2,
                        "TotalRebounds": 3,
                        "Assistances": 3,
                        "Steals": 0,
                        "Turnovers": 1,
                        "BlocksFavour": 0,
                        "FoulsCommited": 2,
                        "Valuation": 8,
                        "Plusminus": -5,
                    },
                ],
            },
            {
                "Team": "PANATHINAIKOS",
                "PlayersStats": [
                    {
                        "Player_ID": "P012774",
                        "IsStarter": 1,
                        "Team": "PAN",
                        "Player": "NUNN, KENDRICK",
                        "Minutes": "30:15",
                        "Points": 22,
                        "FieldGoalsMade2": 5,
                        "FieldGoalsAttempted2": 8,
                        "FieldGoalsMade3": 3,
                        "FieldGoalsAttempted3": 6,
                        "FreeThrowsMade": 3,
                        "FreeThrowsAttempted": 4,
                        "OffensiveRebounds": 0,
                        "DefensiveRebounds": 2,
                        "TotalRebounds": 2,
                        "Assistances": 4,
                        "Steals": 2,
                        "Turnovers": 1,
                        "BlocksFavour": 0,
                        "FoulsCommited": 2,
                        "Valuation": 24,
                        "Plusminus": 12,
                    },
                ],
            },
        ],
    }


class TestParseMinutesToSeconds:
    """Tests for parse_minutes_to_seconds method."""

    def test_standard_format(self, mapper):
        """Test standard MM:SS format."""
        assert mapper.parse_minutes_to_seconds("24:35") == 1475
        assert mapper.parse_minutes_to_seconds("30:15") == 1815

    def test_single_digit_minutes(self, mapper):
        """Test single digit minutes."""
        assert mapper.parse_minutes_to_seconds("5:30") == 330

    def test_empty_string(self, mapper):
        """Test empty string returns 0."""
        assert mapper.parse_minutes_to_seconds("") == 0

    def test_none_value(self, mapper):
        """Test None returns 0."""
        assert mapper.parse_minutes_to_seconds(None) == 0


class TestParseEuroleagueDate:
    """Tests for parse_euroleague_date method."""

    def test_oct_format(self, mapper):
        """Test Euroleague date format."""
        dt = mapper.parse_euroleague_date("Oct 03, 2024")
        assert dt.year == 2024
        assert dt.month == 10
        assert dt.day == 3

    def test_jan_format(self, mapper):
        """Test January date."""
        dt = mapper.parse_euroleague_date("Jan 15, 2025")
        assert dt.year == 2025
        assert dt.month == 1


class TestParseBirthdate:
    """Tests for parse_birthdate method."""

    def test_long_format(self, mapper):
        """Test long date format like '12 March, 1998'."""
        bd = mapper.parse_birthdate("12 March, 1998")
        assert bd is not None
        assert bd.year == 1998
        assert bd.month == 3
        assert bd.day == 12

    def test_empty_returns_none(self, mapper):
        """Test empty returns None."""
        assert mapper.parse_birthdate("") is None
        assert mapper.parse_birthdate(None) is None


class TestHeightMetersToCm:
    """Tests for height_meters_to_cm method."""

    def test_standard_height(self, mapper):
        """Test standard height conversion."""
        assert mapper.height_meters_to_cm("1.8") == 180
        assert mapper.height_meters_to_cm("2.05") == 205
        assert mapper.height_meters_to_cm("1.95") == 195

    def test_empty_returns_none(self, mapper):
        """Test empty returns None."""
        assert mapper.height_meters_to_cm("") is None
        assert mapper.height_meters_to_cm(None) is None


class TestMapSeason:
    """Tests for map_season method."""

    def test_euroleague_season_normalized_name(self, mapper):
        """Test that Euroleague season name is normalized to YYYY-YY format."""
        season = mapper.map_season(2024, "E")

        assert isinstance(season, RawSeason)
        assert season.name == "2024-25"  # Normalized format
        assert season.external_id == "2024-25"  # Same as name
        assert season.source_id == "E2024"  # Original Euroleague ID preserved
        assert season.start_date == date(2024, 10, 1)
        assert season.end_date == date(2025, 5, 31)

    def test_eurocup_season_normalized_name(self, mapper):
        """Test that EuroCup season name is normalized to YYYY-YY format."""
        season = mapper.map_season(2024, "U")

        assert season.name == "2024-25"  # Normalized format
        assert season.external_id == "2024-25"
        assert season.source_id == "U2024"  # Original EuroCup ID preserved

    def test_season_source_id_for_external_reference(self, mapper):
        """Test that source_id can be used for external API calls."""
        season = mapper.map_season(2025, "E")

        # source_id should be in the format expected by Euroleague API
        assert season.source_id == "E2025"
        # name should be standardized
        assert season.name == "2025-26"

    def test_century_boundary_season(self, mapper):
        """Test season crossing century boundary."""
        season = mapper.map_season(1999, "E")

        assert season.name == "1999-00"
        assert season.source_id == "E1999"


class TestMapTeam:
    """Tests for map_team method."""

    def test_basic_team(self, mapper):
        """Test basic team mapping."""
        data = {"code": "BER", "name": "ALBA Berlin", "tv_code": "BER"}
        team = mapper.map_team(data)

        assert isinstance(team, RawTeam)
        assert team.external_id == "BER"
        assert team.name == "ALBA Berlin"
        assert team.short_name == "BER"


class TestMapGame:
    """Tests for map_game method."""

    def test_completed_game(self, mapper):
        """Test mapping a completed game."""
        data = {
            "gamecode": 1,
            "homecode": "BER",
            "awaycode": "PAN",
            "date": "Oct 03, 2024",
            "homescore": 77,
            "awayscore": 87,
        }
        game = mapper.map_game(data, 2024, "E")

        assert isinstance(game, RawGame)
        assert game.external_id == "E2024_1"
        assert game.home_team_external_id == "BER"
        assert game.away_team_external_id == "PAN"
        assert game.home_score == 77
        assert game.away_score == 87
        assert game.status == "final"

    def test_scheduled_game(self, mapper):
        """Test mapping a scheduled game."""
        data = {
            "gamecode": 10,
            "homecode": "BER",
            "awaycode": "PAN",
            "date": "Dec 15, 2024",
            "homescore": None,
            "awayscore": None,
        }
        game = mapper.map_game(data, 2024, "E")

        assert game.status == "scheduled"
        assert game.home_score is None
        assert game.away_score is None


class TestMapPlayerStats:
    """Tests for map_player_stats method."""

    def test_full_stats(self, mapper):
        """Test mapping full player stats."""
        data = {
            "Player_ID": "P007025",
            "Player": "MATTISSECK, JONAS",
            "Team": "BER",
            "Minutes": "24:35",
            "IsStarter": 1,
            "Points": 6,
            "FieldGoalsMade2": 2,
            "FieldGoalsAttempted2": 4,
            "FieldGoalsMade3": 0,
            "FieldGoalsAttempted3": 2,
            "FreeThrowsMade": 2,
            "FreeThrowsAttempted": 2,
            "OffensiveRebounds": 1,
            "DefensiveRebounds": 2,
            "TotalRebounds": 3,
            "Assistances": 3,
            "Steals": 0,
            "Turnovers": 1,
            "BlocksFavour": 0,
            "FoulsCommited": 2,
            "Valuation": 8,
            "Plusminus": -5,
        }
        stats = mapper.map_player_stats(data)

        assert isinstance(stats, RawPlayerStats)
        assert stats.player_external_id == "P007025"
        assert stats.player_name == "MATTISSECK, JONAS"
        assert stats.team_external_id == "BER"
        assert stats.minutes_played == 1475  # 24:35 in seconds
        assert stats.is_starter is True
        assert stats.points == 6
        assert stats.two_pointers_made == 2
        assert stats.two_pointers_attempted == 4
        assert stats.three_pointers_made == 0
        assert stats.three_pointers_attempted == 2
        assert stats.field_goals_made == 2  # 2 + 0
        assert stats.field_goals_attempted == 6  # 4 + 2
        assert stats.free_throws_made == 2
        assert stats.offensive_rebounds == 1
        assert stats.defensive_rebounds == 2
        assert stats.total_rebounds == 3
        assert stats.assists == 3
        assert stats.turnovers == 1
        assert stats.blocks == 0
        assert stats.personal_fouls == 2
        assert stats.efficiency == 8
        assert stats.plus_minus == -5


class TestMapBoxscoreFromLive:
    """Tests for map_boxscore_from_live method."""

    def test_maps_live_boxscore(self, mapper, sample_boxscore_data):
        """Test mapping live boxscore data."""
        boxscore = mapper.map_boxscore_from_live(sample_boxscore_data, 1, 2024, "E")

        assert isinstance(boxscore, RawBoxScore)
        assert boxscore.game.external_id == "E2024_1"
        assert boxscore.game.home_team_external_id == "BER"
        assert boxscore.game.away_team_external_id == "PAN"

    def test_players_split_by_team(self, mapper, sample_boxscore_data):
        """Test that players are split by team."""
        boxscore = mapper.map_boxscore_from_live(sample_boxscore_data, 1, 2024, "E")

        assert len(boxscore.home_players) == 1
        assert len(boxscore.away_players) == 1
        assert boxscore.home_players[0].team_external_id == "BER"
        assert boxscore.away_players[0].team_external_id == "PAN"

    def test_scores_calculated(self, mapper, sample_boxscore_data):
        """Test that scores are calculated from quarters."""
        boxscore = mapper.map_boxscore_from_live(sample_boxscore_data, 1, 2024, "E")

        # Home: 17 + 19 + 21 + 20 = 77
        # Away: 26 + 19 + 17 + 25 = 87
        assert boxscore.game.home_score == 77
        assert boxscore.game.away_score == 87


class TestMapPbpEvent:
    """Tests for map_pbp_event method."""

    def test_made_shot(self, mapper):
        """Test mapping a made shot."""
        data = {
            "PLAYTYPE": "2FGM",
            "PERIOD": 1,
            "MARKERTIME": "09:45",
            "TEAM": "BER",
            "PLAYERNAME": "MATTISSECK, JONAS",
        }
        event = mapper.map_pbp_event(data, 1)

        assert isinstance(event, RawPBPEvent)
        assert event.event_number == 1
        assert event.period == 1
        assert event.clock == "09:45"
        assert event.event_type == "shot"
        assert event.success is True
        assert event.team_external_id == "BER"

    def test_missed_shot(self, mapper):
        """Test mapping a missed shot."""
        data = {
            "PLAYTYPE": "3FGA",
            "PERIOD": 2,
            "MARKERTIME": "05:30",
            "TEAM": "PAN",
        }
        event = mapper.map_pbp_event(data, 2)

        assert event.event_type == "shot"
        assert event.success is False

    def test_event_type_mapping(self, mapper):
        """Test various event type mappings."""
        event_mappings = [
            ("2FGM", "shot"),
            ("3FGA", "shot"),
            ("FTM", "free_throw"),
            ("O", "rebound"),
            ("D", "rebound"),
            ("AS", "assist"),
            ("TO", "turnover"),
            ("ST", "steal"),
            ("BLK", "block"),
            ("CM", "foul"),
        ]

        for euro_type, expected_type in event_mappings:
            data = {"PLAYTYPE": euro_type, "PERIOD": 1, "MARKERTIME": "05:00"}
            event = mapper.map_pbp_event(data, 1)
            assert (
                event.event_type == expected_type
            ), f"{euro_type} should map to {expected_type}"


class TestMapPbpFromLive:
    """Tests for map_pbp_from_live method."""

    def test_combines_quarters(self, mapper):
        """Test that quarters are combined correctly."""
        live_pbp = {
            "FirstQuarter": [
                {"PLAYTYPE": "2FGM", "MARKERTIME": "09:00"},
            ],
            "SecondQuarter": [
                {"PLAYTYPE": "3FGA", "MARKERTIME": "08:00"},
            ],
        }
        events = mapper.map_pbp_from_live(live_pbp)

        assert len(events) == 2
        assert events[0].period == 1
        assert events[1].period == 2

    def test_event_numbering(self, mapper):
        """Test that events are numbered sequentially."""
        live_pbp = {
            "FirstQuarter": [
                {"PLAYTYPE": "2FGM", "MARKERTIME": "09:00"},
                {"PLAYTYPE": "O", "MARKERTIME": "08:50"},
            ],
            "SecondQuarter": [
                {"PLAYTYPE": "TO", "MARKERTIME": "07:00"},
            ],
        }
        events = mapper.map_pbp_from_live(live_pbp)

        assert events[0].event_number == 1
        assert events[1].event_number == 2
        assert events[2].event_number == 3


class TestMapPlayerInfo:
    """Tests for map_player_info method."""

    def test_standard_name_format(self, mapper):
        """Test parsing 'LASTNAME, FIRSTNAME' format."""
        data = {
            "name": "EDWARDS, CARSEN",
            "height": "1.8",
            "birthdate": "12 March, 1998",
            "position": "Guard",
            "code": "P011987",
        }
        info = mapper.map_player_info(data)

        assert isinstance(info, RawPlayerInfo)
        assert info.external_id == "P011987"
        assert info.first_name == "CARSEN"
        assert info.last_name == "EDWARDS"
        assert info.height_cm == 180
        assert info.birth_date == date(1998, 3, 12)
        assert info.position == "Guard"

    def test_multi_part_last_name(self, mapper):
        """Test name with only last name provided."""
        data = {"name": "DE LA TORRE, SERGIO"}
        info = mapper.map_player_info(data)

        assert info.first_name == "SERGIO"
        assert info.last_name == "DE LA TORRE"


class TestMapPlayerFromRoster:
    """Tests for map_player_from_roster method."""

    def test_basic_roster_player(self, mapper):
        """Test mapping player from roster."""
        data = {
            "code": "P007025",
            "name": "MATTISSECK, JONAS",
            "position": "Guard",
        }
        info = mapper.map_player_from_roster(data, "BER")

        assert info.external_id == "P007025"
        assert info.first_name == "JONAS"
        assert info.last_name == "MATTISSECK"
        assert info.position == "Guard"
