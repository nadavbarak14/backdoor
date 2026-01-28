"""
Unit tests for NBA Mapper.

Tests the NBAMapper class which transforms NBA API V3 data to Raw types.
"""

from datetime import date, datetime

from src.sync.nba.mapper import NBAMapper


class TestNBAMapperMinutesParser:
    """Tests for minutes string parsing."""

    def test_parse_pt_format(self):
        """Test parsing PT format (e.g., PT24M35.00S)."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("PT24M35.00S") == 1475

    def test_parse_pt_format_no_seconds(self):
        """Test parsing PT format with no seconds."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("PT24M00.00S") == 1440

    def test_parse_pt_format_only_seconds(self):
        """Test parsing PT format with only seconds."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("PT35.00S") == 35

    def test_parse_mm_ss_format(self):
        """Test parsing MM:SS format (boxscore V3)."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("35:56") == 2156

    def test_parse_empty_string(self):
        """Test parsing empty string returns 0."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("") == 0

    def test_parse_none(self):
        """Test parsing None returns 0."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds(None) == 0

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns 0."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("invalid") == 0


class TestNBAMapperDateParser:
    """Tests for date parsing."""

    def test_parse_iso_format(self):
        """Test parsing ISO format date."""
        mapper = NBAMapper()
        result = mapper.parse_nba_date("2023-10-24T00:00:00")
        assert result.year == 2023
        assert result.month == 10
        assert result.day == 24

    def test_parse_date_only_format(self):
        """Test parsing date-only format."""
        mapper = NBAMapper()
        result = mapper.parse_nba_date("2023-10-24")
        assert result.year == 2023
        assert result.month == 10
        assert result.day == 24

    def test_parse_us_format(self):
        """Test parsing MM/DD/YYYY format."""
        mapper = NBAMapper()
        result = mapper.parse_nba_date("10/24/2023")
        assert result.year == 2023
        assert result.month == 10
        assert result.day == 24

    def test_parse_empty_returns_now(self):
        """Test parsing empty string returns current datetime."""
        mapper = NBAMapper()
        result = mapper.parse_nba_date("")
        assert isinstance(result, datetime)


class TestNBAMapperClockParser:
    """Tests for clock string parsing."""

    def test_parse_pt_format_clock(self):
        """Test parsing PT format clock."""
        mapper = NBAMapper()
        assert mapper.parse_clock("PT10M45.00S") == "10:45"

    def test_parse_mm_ss_format_clock(self):
        """Test parsing MM:SS format clock."""
        mapper = NBAMapper()
        assert mapper.parse_clock("10:45") == "10:45"

    def test_parse_empty_clock(self):
        """Test parsing empty clock string."""
        mapper = NBAMapper()
        assert mapper.parse_clock("") == "00:00"


class TestNBAMapperSeason:
    """Tests for season mapping."""

    def test_map_season(self):
        """Test mapping a season with normalized name."""
        mapper = NBAMapper()
        season = mapper.map_season("2023-24")

        # Name is normalized YYYY-YY format
        assert season.name == "2023-24"
        assert season.external_id == "2023-24"
        # Source-specific ID preserves NBA prefix
        assert season.source_id == "NBA2023-24"
        assert season.start_date == date(2023, 10, 1)
        assert season.end_date == date(2024, 6, 30)
        assert season.is_current is False

    def test_map_season_different_year(self):
        """Test mapping a different season."""
        mapper = NBAMapper()
        season = mapper.map_season("2022-23")

        assert season.name == "2022-23"
        assert season.external_id == "2022-23"
        assert season.source_id == "NBA2022-23"
        assert season.start_date == date(2022, 10, 1)


class TestNBAMapperTeam:
    """Tests for team mapping."""

    def test_map_team(self):
        """Test mapping team data."""
        mapper = NBAMapper()
        team = mapper.map_team(
            {
                "id": 1610612737,
                "full_name": "Atlanta Hawks",
                "abbreviation": "ATL",
            }
        )

        assert team.external_id == "1610612737"
        assert team.name == "Atlanta Hawks"
        assert team.short_name == "ATL"

    def test_map_team_missing_fields(self):
        """Test mapping team with missing optional fields."""
        mapper = NBAMapper()
        team = mapper.map_team(
            {
                "id": 1610612737,
                "full_name": "Atlanta Hawks",
            }
        )

        assert team.external_id == "1610612737"
        assert team.name == "Atlanta Hawks"
        assert team.short_name == ""


class TestNBAMapperGame:
    """Tests for game mapping from schedule."""

    def test_map_game_from_schedule_home(self):
        """Test mapping a home game from schedule."""
        mapper = NBAMapper()
        game = mapper.map_game_from_schedule(
            {
                "GAME_ID": "0022300001",
                "TEAM_ID": 1610612737,
                "MATCHUP": "ATL vs. CHI",
                "GAME_DATE": "2023-10-24",
                "WL": "W",
                "PTS": 112,
            }
        )

        assert game.external_id == "0022300001"
        assert game.home_team_external_id == "1610612737"
        assert game.away_team_external_id == ""
        assert game.status == "final"
        assert game.home_score == 112
        assert game.away_score is None

    def test_map_game_from_schedule_away(self):
        """Test mapping an away game from schedule."""
        mapper = NBAMapper()
        game = mapper.map_game_from_schedule(
            {
                "GAME_ID": "0022300001",
                "TEAM_ID": 1610612747,
                "MATCHUP": "LAL @ GSW",
                "GAME_DATE": "2023-10-24",
                "WL": "L",
                "PTS": 108,
            }
        )

        assert game.external_id == "0022300001"
        assert game.home_team_external_id == ""
        assert game.away_team_external_id == "1610612747"
        assert game.status == "final"
        assert game.home_score is None
        assert game.away_score == 108

    def test_map_game_scheduled(self):
        """Test mapping a scheduled game."""
        mapper = NBAMapper()
        game = mapper.map_game_from_schedule(
            {
                "GAME_ID": "0022300100",
                "TEAM_ID": 1610612737,
                "MATCHUP": "ATL vs. BOS",
                "GAME_DATE": "2024-01-15",
                "WL": None,
                "PTS": None,
            }
        )

        assert game.external_id == "0022300100"
        assert game.status == "scheduled"
        assert game.home_score is None
        assert game.away_score is None


class TestNBAMapperPlayerStatsV3:
    """Tests for V3 player stats mapping."""

    def test_map_player_stats_v3(self):
        """Test mapping V3 player statistics with nested structure."""
        mapper = NBAMapper()
        stats = mapper.map_player_stats_v3(
            {
                "personId": 1627759,
                "firstName": "Jaylen",
                "familyName": "Brown",
                "position": "F",
                "statistics": {
                    "minutes": "35:56",
                    "points": 37,
                    "fieldGoalsMade": 14,
                    "fieldGoalsAttempted": 22,
                    "threePointersMade": 3,
                    "threePointersAttempted": 6,
                    "freeThrowsMade": 6,
                    "freeThrowsAttempted": 10,
                    "reboundsOffensive": 2,
                    "reboundsDefensive": 3,
                    "reboundsTotal": 5,
                    "assists": 2,
                    "turnovers": 6,
                    "steals": 1,
                    "blocks": 0,
                    "foulsPersonal": 3,
                    "plusMinusPoints": 0.0,
                },
            },
            "1610612738",
        )

        assert stats.player_external_id == "1627759"
        assert stats.player_name == "Jaylen Brown"
        assert stats.team_external_id == "1610612738"
        assert stats.minutes_played == 2156  # 35:56 in seconds
        assert stats.points == 37
        assert stats.field_goals_made == 14
        assert stats.field_goals_attempted == 22
        assert stats.two_pointers_made == 11  # 14 - 3
        assert stats.two_pointers_attempted == 16  # 22 - 6
        assert stats.three_pointers_made == 3
        assert stats.three_pointers_attempted == 6
        assert stats.free_throws_made == 6
        assert stats.free_throws_attempted == 10
        assert stats.offensive_rebounds == 2
        assert stats.defensive_rebounds == 3
        assert stats.total_rebounds == 5
        assert stats.assists == 2
        assert stats.turnovers == 6
        assert stats.steals == 1
        assert stats.blocks == 0
        assert stats.personal_fouls == 3
        assert stats.plus_minus == 0
        assert stats.is_starter is True  # Has position

    def test_map_player_stats_v3_bench(self):
        """Test mapping V3 bench player stats."""
        mapper = NBAMapper()
        stats = mapper.map_player_stats_v3(
            {
                "personId": 12345,
                "firstName": "Bench",
                "familyName": "Player",
                "position": "",  # Empty position = bench
                "statistics": {
                    "minutes": "10:00",
                    "points": 5,
                },
            },
            "1610612738",
        )

        assert stats.is_starter is False


class TestNBAMapperBoxscoreV3:
    """Tests for V3 boxscore mapping."""

    def test_map_boxscore_v3(self):
        """Test mapping V3 boxscore with nested structure."""
        mapper = NBAMapper()
        boxscore_data = {
            "boxScoreTraditional": {
                "gameId": "0022400001",
                "homeTeamId": 1610612738,
                "awayTeamId": 1610612737,
                "homeTeam": {
                    "teamId": 1610612738,
                    "teamCity": "Boston",
                    "teamName": "Celtics",
                    "players": [
                        {
                            "personId": 1627759,
                            "firstName": "Jaylen",
                            "familyName": "Brown",
                            "position": "F",
                            "statistics": {"points": 37, "minutes": "35:00"},
                        }
                    ],
                    "statistics": {"points": 132},
                },
                "awayTeam": {
                    "teamId": 1610612737,
                    "teamCity": "Atlanta",
                    "teamName": "Hawks",
                    "players": [
                        {
                            "personId": 1629027,
                            "firstName": "Trae",
                            "familyName": "Young",
                            "position": "G",
                            "statistics": {"points": 22, "minutes": "32:00"},
                        }
                    ],
                    "statistics": {"points": 109},
                },
            }
        }

        boxscore = mapper.map_boxscore(boxscore_data, "0022400001")

        assert boxscore.game.external_id == "0022400001"
        assert boxscore.game.home_team_external_id == "1610612738"
        assert boxscore.game.away_team_external_id == "1610612737"
        assert boxscore.game.home_score == 132
        assert boxscore.game.away_score == 109
        assert len(boxscore.home_players) == 1
        assert len(boxscore.away_players) == 1
        assert boxscore.home_players[0].player_name == "Jaylen Brown"
        assert boxscore.home_players[0].points == 37
        assert boxscore.away_players[0].player_name == "Trae Young"
        assert boxscore.away_players[0].points == 22


class TestNBAMapperPBPV3:
    """Tests for V3 play-by-play mapping."""

    def test_map_pbp_event_jump_ball(self):
        """Test mapping a Jump Ball event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event(
            {
                "actionNumber": 4,
                "period": 1,
                "clock": "PT12M00.00S",
                "actionType": "Jump Ball",
                "teamId": 1610612738,
                "playerNameI": "A. Horford",
            }
        )

        assert event.event_number == 4
        assert event.period == 1
        assert event.clock == "12:00"
        assert event.event_type == "jump_ball"
        assert event.team_external_id == "1610612738"
        assert event.player_name == "A. Horford"

    def test_map_pbp_event_made_shot(self):
        """Test mapping a Made Shot event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event(
            {
                "actionNumber": 10,
                "period": 1,
                "clock": "PT10M30.00S",
                "actionType": "Made Shot",
                "shotResult": "Made",
                "teamId": 1610612737,
                "xLegacy": -168,
                "yLegacy": 205,
            }
        )

        assert event.event_type == "shot"
        assert event.success is True
        assert event.coord_x == -168
        assert event.coord_y == 205

    def test_map_pbp_event_missed_shot(self):
        """Test mapping a Missed Shot event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event(
            {
                "actionNumber": 11,
                "period": 1,
                "clock": "PT10M25.00S",
                "actionType": "Missed Shot",
                "shotResult": "Missed",
            }
        )

        assert event.event_type == "shot"
        assert event.success is False

    def test_map_pbp_event_rebound(self):
        """Test mapping a Rebound event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event(
            {
                "actionNumber": 9,
                "period": 1,
                "clock": "PT11M42.00S",
                "actionType": "Rebound",
                "teamId": 1610612737,
                "playerNameI": "Z. Risacher",
            }
        )

        assert event.event_type == "rebound"
        assert event.player_name == "Z. Risacher"

    def test_map_pbp_event_no_team(self):
        """Test mapping event with no team (period start)."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event(
            {
                "actionNumber": 2,
                "period": 1,
                "clock": "PT12M00.00S",
                "actionType": "period",
                "teamId": 0,
            }
        )

        assert event.event_type == "period_event"
        assert event.team_external_id is None

    def test_map_pbp_events(self):
        """Test mapping multiple PBP events."""
        mapper = NBAMapper()
        pbp_data = [
            {
                "actionNumber": 1,
                "period": 1,
                "clock": "PT12M00.00S",
                "actionType": "period",
            },
            {
                "actionNumber": 2,
                "period": 1,
                "clock": "PT11M45.00S",
                "actionType": "Made Shot",
            },
        ]

        events = mapper.map_pbp_events(pbp_data)

        assert len(events) == 2
        assert events[0].event_number == 1
        assert events[1].event_number == 2
