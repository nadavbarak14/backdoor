"""
Winner Mapper Tests

Tests for the WinnerMapper class that transforms Winner League data
to normalized Raw types.
"""

from datetime import date, datetime

import pytest

from src.schemas.game import EventType
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawPlayerStats,
    RawSeason,
    RawTeam,
)
from src.sync.winner.mapper import WinnerMapper
from src.sync.winner.scraper import PlayerProfile
from src.schemas.enums import GameStatus, Position


@pytest.fixture
def mapper():
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def sample_games_all_data():
    """Sample games_all API response."""
    return {
        "games": [
            {
                "GameId": "12345",
                "HomeTeamId": "100",
                "AwayTeamId": "101",
                "HomeTeamName": "Maccabi Tel Aviv",
                "AwayTeamName": "Hapoel Jerusalem",
                "HomeScore": 85,
                "AwayScore": 78,
                "GameDate": "2024-01-15T19:30:00",
                "Status": "Final",
                "Round": 15,
            },
            {
                "GameId": "12346",
                "HomeTeamId": "102",
                "AwayTeamId": "103",
                "HomeTeamName": "Hapoel Tel Aviv",
                "AwayTeamName": "Bnei Herzliya",
                "HomeScore": 92,
                "AwayScore": 88,
                "GameDate": "2024-01-16T20:00:00",
                "Status": "Final",
                "Round": 15,
            },
            {
                "GameId": "12347",
                "HomeTeamId": "104",
                "AwayTeamId": "100",
                "HomeTeamName": "Ironi Nahariya",
                "AwayTeamName": "Maccabi Tel Aviv",
                "HomeScore": None,
                "AwayScore": None,
                "GameDate": "2024-01-20T19:00:00",
                "Status": "Scheduled",
                "Round": 16,
            },
        ],
        "season": "2023-24",
        "league": "Winner League",
    }


@pytest.fixture
def sample_boxscore_data():
    """Sample boxscore API response."""
    return {
        "GameId": "12345",
        "HomeTeam": {
            "TeamId": "100",
            "TeamName": "Maccabi Tel Aviv",
            "Score": 85,
            "Players": [
                {
                    "PlayerId": "1001",
                    "Name": "John Smith",
                    "JerseyNumber": "5",
                    "Minutes": "32:15",
                    "Points": 22,
                    "Rebounds": 8,
                    "Assists": 5,
                    "Steals": 2,
                    "Blocks": 1,
                    "Turnovers": 3,
                    "FGM": 8,
                    "FGA": 15,
                    "ThreePM": 3,
                    "ThreePA": 7,
                    "FTM": 3,
                    "FTA": 4,
                },
                {
                    "PlayerId": "1002",
                    "Name": "David Cohen",
                    "JerseyNumber": "10",
                    "Minutes": "28:45",
                    "Points": 18,
                    "Rebounds": 3,
                    "Assists": 7,
                    "Steals": 1,
                    "Blocks": 0,
                    "Turnovers": 2,
                    "FGM": 6,
                    "FGA": 12,
                    "ThreePM": 2,
                    "ThreePA": 5,
                    "FTM": 4,
                    "FTA": 4,
                },
            ],
        },
        "AwayTeam": {
            "TeamId": "101",
            "TeamName": "Hapoel Jerusalem",
            "Score": 78,
            "Players": [
                {
                    "PlayerId": "2001",
                    "Name": "Alex Johnson",
                    "JerseyNumber": "7",
                    "Minutes": "30:00",
                    "Points": 20,
                    "Rebounds": 5,
                    "Assists": 4,
                    "Steals": 1,
                    "Blocks": 0,
                    "Turnovers": 2,
                    "FGM": 7,
                    "FGA": 14,
                    "ThreePM": 4,
                    "ThreePA": 8,
                    "FTM": 2,
                    "FTA": 2,
                },
            ],
        },
        "GameDate": "2024-01-15T19:30:00",
        "Arena": "Menora Mivtachim Arena",
    }


@pytest.fixture
def sample_pbp_data():
    """Sample play-by-play API response."""
    return {
        "GameId": "12345",
        "Events": [
            {
                "EventId": "1",
                "Quarter": 1,
                "GameClock": "10:00",
                "EventType": "JUMP_BALL",
                "TeamId": "100",
                "PlayerId": "1003",
                "Description": "Jump ball won by Michael Brown",
            },
            {
                "EventId": "2",
                "Quarter": 1,
                "GameClock": "09:45",
                "EventType": "MADE_2PT",
                "TeamId": "100",
                "PlayerId": "1001",
                "Description": "John Smith makes 2-pt shot from paint",
            },
            {
                "EventId": "3",
                "Quarter": 1,
                "GameClock": "09:30",
                "EventType": "TURNOVER",
                "TeamId": "101",
                "PlayerId": "2001",
                "Description": "Alex Johnson bad pass turnover",
            },
        ],
    }


class TestParseMinutesToSeconds:
    """Tests for parse_minutes_to_seconds method."""

    def test_standard_format(self, mapper):
        """Test standard MM:SS format."""
        assert mapper.parse_minutes_to_seconds("32:15") == 1935
        assert mapper.parse_minutes_to_seconds("28:45") == 1725

    def test_single_digit_minutes(self, mapper):
        """Test single digit minutes."""
        assert mapper.parse_minutes_to_seconds("5:30") == 330
        assert mapper.parse_minutes_to_seconds("0:45") == 45

    def test_empty_string(self, mapper):
        """Test empty string returns 0."""
        assert mapper.parse_minutes_to_seconds("") == 0

    def test_none_value(self, mapper):
        """Test None returns 0."""
        assert mapper.parse_minutes_to_seconds(None) == 0

    def test_invalid_format(self, mapper):
        """Test invalid format returns 0."""
        assert mapper.parse_minutes_to_seconds("invalid") == 0
        assert mapper.parse_minutes_to_seconds("32") == 0


class TestParseDatetime:
    """Tests for parse_datetime method."""

    def test_iso_format(self, mapper):
        """Test ISO datetime format."""
        dt = mapper.parse_datetime("2024-01-15T19:30:00")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 19
        assert dt.minute == 30

    def test_iso_format_with_z(self, mapper):
        """Test ISO format with Z suffix."""
        dt = mapper.parse_datetime("2024-01-15T19:30:00Z")
        assert dt.year == 2024

    def test_empty_returns_now(self, mapper):
        """Test empty string returns current time."""
        dt = mapper.parse_datetime("")
        now = datetime.now()
        assert dt.year == now.year


class TestMapSeason:
    """Tests for map_season method."""

    def test_basic_season(self, mapper, sample_games_all_data):
        """Test basic season mapping with normalized name."""
        season = mapper.map_season("2023-24", sample_games_all_data)

        assert isinstance(season, RawSeason)
        assert season.external_id == "2023-24"
        assert season.name == "2023-24"  # Normalized YYYY-YY format
        assert season.source_id == "2023-24"  # Original input preserved
        assert season.is_current is True

    def test_date_extraction(self, mapper, sample_games_all_data):
        """Test that dates are extracted from games."""
        season = mapper.map_season("2023-24", sample_games_all_data)

        assert season.start_date is not None
        assert season.end_date is not None
        assert season.start_date <= season.end_date

    def test_season_name_normalized_format(self, mapper):
        """Test that season name is always in YYYY-YY format."""
        # Test with real API format (inferring from game_year)
        games_data = {"games": [{"game_year": 2026}]}
        season = mapper.map_season("", games_data)

        assert season.name == "2025-26"
        assert season.external_id == "2025-26"

    def test_season_source_id_preserved(self, mapper, sample_games_all_data):
        """Test that original season string is stored in source_id."""
        season = mapper.map_season("2023-24", sample_games_all_data)
        assert season.source_id == "2023-24"

    def test_season_inferred_from_game_year(self, mapper):
        """Test season inference from game_year field."""
        games_data = {"games": [{"game_year": 2026, "game_date_txt": "21/09/2025"}]}
        season = mapper.map_season("", games_data)

        assert season.name == "2025-26"
        assert season.source_id is None  # No original string provided


class TestMapTeam:
    """Tests for map_team method."""

    def test_basic_team(self, mapper):
        """Test basic team mapping."""
        data = {"TeamId": "100", "TeamName": "Maccabi Tel Aviv"}
        team = mapper.map_team(data)

        assert isinstance(team, RawTeam)
        assert team.external_id == "100"
        assert team.name == "Maccabi Tel Aviv"

    def test_team_from_game_data(self, mapper):
        """Test team mapping from game data format."""
        data = {"HomeTeamId": "100", "HomeTeamName": "Maccabi Tel Aviv"}
        team = mapper.map_team(data)

        assert team.external_id == "100"
        assert team.name == "Maccabi Tel Aviv"


class TestExtractTeamsFromGames:
    """Tests for extract_teams_from_games method."""

    def test_extracts_unique_teams(self, mapper, sample_games_all_data):
        """Test that unique teams are extracted."""
        teams = mapper.extract_teams_from_games(sample_games_all_data)

        # Should have 5 unique teams: 100, 101, 102, 103, 104
        assert len(teams) == 5
        team_ids = {t.external_id for t in teams}
        assert team_ids == {"100", "101", "102", "103", "104"}

    def test_team_names_preserved(self, mapper, sample_games_all_data):
        """Test that team names are preserved."""
        teams = mapper.extract_teams_from_games(sample_games_all_data)

        team_dict = {t.external_id: t.name for t in teams}
        assert team_dict["100"] == "Maccabi Tel Aviv"
        assert team_dict["101"] == "Hapoel Jerusalem"


class TestMapGame:
    """Tests for map_game method."""

    def test_final_game(self, mapper):
        """Test mapping a completed game."""
        data = {
            "GameId": "12345",
            "HomeTeamId": "100",
            "AwayTeamId": "101",
            "HomeScore": 85,
            "AwayScore": 78,
            "GameDate": "2024-01-15T19:30:00",
            "Status": "Final",
        }
        game = mapper.map_game(data)

        assert isinstance(game, RawGame)
        assert game.external_id == "12345"
        assert game.home_team_external_id == "100"
        assert game.away_team_external_id == "101"
        assert game.home_score == 85
        assert game.away_score == 78
        assert game.status == GameStatus.FINAL

    def test_scheduled_game(self, mapper):
        """Test mapping a scheduled game."""
        data = {
            "GameId": "12347",
            "HomeTeamId": "104",
            "AwayTeamId": "100",
            "HomeScore": None,
            "AwayScore": None,
            "GameDate": "2024-01-20T19:00:00",
            "Status": "Scheduled",
        }
        game = mapper.map_game(data)

        assert game.status == GameStatus.SCHEDULED
        assert game.home_score is None
        assert game.away_score is None


class TestMapPlayerStats:
    """Tests for map_player_stats method."""

    def test_basic_stats(self, mapper):
        """Test basic player stats mapping."""
        data = {
            "PlayerId": "1001",
            "Name": "John Smith",
            "Minutes": "32:15",
            "Points": 22,
            "Rebounds": 8,
            "Assists": 5,
            "Steals": 2,
            "Blocks": 1,
            "Turnovers": 3,
            "FGM": 8,
            "FGA": 15,
            "ThreePM": 3,
            "ThreePA": 7,
            "FTM": 3,
            "FTA": 4,
        }
        stats = mapper.map_player_stats(data, "100")

        assert isinstance(stats, RawPlayerStats)
        assert stats.player_external_id == "1001"
        assert stats.player_name == "John Smith"
        assert stats.team_external_id == "100"
        assert stats.minutes_played == 1935  # 32:15 = 1935 seconds
        assert stats.points == 22
        assert stats.total_rebounds == 8
        assert stats.assists == 5
        assert stats.steals == 2
        assert stats.blocks == 1
        assert stats.turnovers == 3

    def test_two_point_calculation(self, mapper):
        """Test that 2-point FGs are calculated correctly."""
        data = {
            "PlayerId": "1001",
            "Name": "Test Player",
            "FGM": 8,  # Total FGM
            "FGA": 15,  # Total FGA
            "ThreePM": 3,  # 3-point made
            "ThreePA": 7,  # 3-point attempted
        }
        stats = mapper.map_player_stats(data, "100")

        # 2-point = Total - 3-point
        assert stats.two_pointers_made == 5  # 8 - 3
        assert stats.two_pointers_attempted == 8  # 15 - 7
        assert stats.three_pointers_made == 3
        assert stats.three_pointers_attempted == 7


class TestMapBoxscore:
    """Tests for map_boxscore method."""

    def test_complete_boxscore(self, mapper, sample_boxscore_data):
        """Test mapping a complete boxscore."""
        boxscore = mapper.map_boxscore(sample_boxscore_data)

        assert isinstance(boxscore, RawBoxScore)
        assert boxscore.game.external_id == "12345"
        assert boxscore.game.home_score == 85
        assert boxscore.game.away_score == 78

        # Check player counts
        assert len(boxscore.home_players) == 2
        assert len(boxscore.away_players) == 1

        # Check first home player
        home_player = boxscore.home_players[0]
        assert home_player.player_name == "John Smith"
        assert home_player.team_external_id == "100"

    def test_team_ids_correct(self, mapper, sample_boxscore_data):
        """Test that team IDs are correctly assigned."""
        boxscore = mapper.map_boxscore(sample_boxscore_data)

        assert boxscore.game.home_team_external_id == "100"
        assert boxscore.game.away_team_external_id == "101"

        for player in boxscore.home_players:
            assert player.team_external_id == "100"

        for player in boxscore.away_players:
            assert player.team_external_id == "101"


class TestMapPbpEvent:
    """Tests for map_pbp_event method."""

    def test_made_shot(self, mapper):
        """Test mapping a made shot event."""
        data = {
            "Quarter": 1,
            "GameClock": "09:45",
            "EventType": "MADE_2PT",
            "TeamId": "100",
            "PlayerId": "1001",
            "Description": "John Smith makes 2-pt shot",
        }
        event = mapper.map_pbp_event(data, 1)

        assert isinstance(event, RawPBPEvent)
        assert event.event_number == 1
        assert event.period == 1
        assert event.clock == "09:45"
        assert event.event_type == EventType.SHOT
        assert event.success is True
        assert event.team_external_id == "100"

    def test_missed_shot(self, mapper):
        """Test mapping a missed shot event."""
        data = {
            "Quarter": 1,
            "GameClock": "09:30",
            "EventType": "MISS_3PT",
            "TeamId": "101",
        }
        event = mapper.map_pbp_event(data, 2)

        assert event.event_type == EventType.SHOT
        assert event.success is False

    def test_event_type_mapping(self, mapper):
        """Test various event type mappings."""
        event_mappings = [
            ("REBOUND", EventType.REBOUND),
            ("TURNOVER", EventType.TURNOVER),
            ("STEAL", EventType.STEAL),
            ("BLOCK", EventType.BLOCK),
            ("FOUL", EventType.FOUL),
            ("MADE_FT", EventType.FREE_THROW),
        ]

        for winner_type, expected_type in event_mappings:
            data = {"Quarter": 1, "GameClock": "05:00", "EventType": winner_type}
            event = mapper.map_pbp_event(data, 1)
            assert event.event_type == expected_type


class TestMapPbpEvents:
    """Tests for map_pbp_events method."""

    def test_maps_all_events(self, mapper, sample_pbp_data):
        """Test that all events are mapped."""
        events = mapper.map_pbp_events(sample_pbp_data)

        assert len(events) == 3
        assert events[0].event_number == 1
        assert events[1].event_number == 2
        assert events[2].event_number == 3


class TestMapPlayerInfo:
    """Tests for map_player_info method."""

    def test_basic_profile(self, mapper):
        """Test mapping a basic player profile."""
        profile = PlayerProfile(
            player_id="1001",
            name="John Smith",
            height_cm=198,
            birth_date=datetime(1995, 5, 15),
            position="Guard",
        )
        info = mapper.map_player_info(profile)

        assert isinstance(info, RawPlayerInfo)
        assert info.external_id == "1001"
        assert info.first_name == "John"
        assert info.last_name == "Smith"
        assert info.height_cm == 198
        assert info.birth_date == date(1995, 5, 15)
        assert info.positions == [Position.GUARD]

    def test_multi_part_last_name(self, mapper):
        """Test name splitting with multi-part last name."""
        profile = PlayerProfile(
            player_id="1001",
            name="John van der Berg",
        )
        info = mapper.map_player_info(profile)

        assert info.first_name == "John"
        assert info.last_name == "van der Berg"

    def test_single_name(self, mapper):
        """Test profile with single name."""
        profile = PlayerProfile(
            player_id="1001",
            name="Ronaldo",
        )
        info = mapper.map_player_info(profile)

        assert info.first_name == ""
        assert info.last_name == "Ronaldo"
