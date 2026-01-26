"""
Unit tests for NBA Mapper.

Tests the NBAMapper class which transforms NBA API data to Raw types.
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
        """Test parsing MM:SS format."""
        mapper = NBAMapper()
        assert mapper.parse_minutes_to_seconds("24:35") == 1475

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
        """Test mapping a season."""
        mapper = NBAMapper()
        season = mapper.map_season("2023-24")

        assert season.external_id == "NBA2023-24"
        assert season.name == "2023-24 NBA Season"
        assert season.start_date == date(2023, 10, 1)
        assert season.end_date == date(2024, 6, 30)
        assert season.is_current is False

    def test_map_season_different_year(self):
        """Test mapping a different season."""
        mapper = NBAMapper()
        season = mapper.map_season("2022-23")

        assert season.external_id == "NBA2022-23"
        assert season.name == "2022-23 NBA Season"
        assert season.start_date == date(2022, 10, 1)


class TestNBAMapperTeam:
    """Tests for team mapping."""

    def test_map_team(self):
        """Test mapping team data."""
        mapper = NBAMapper()
        team = mapper.map_team({
            "id": 1610612737,
            "full_name": "Atlanta Hawks",
            "abbreviation": "ATL",
        })

        assert team.external_id == "1610612737"
        assert team.name == "Atlanta Hawks"
        assert team.short_name == "ATL"

    def test_map_team_missing_fields(self):
        """Test mapping team with missing optional fields."""
        mapper = NBAMapper()
        team = mapper.map_team({
            "id": 1610612737,
            "full_name": "Atlanta Hawks",
        })

        assert team.external_id == "1610612737"
        assert team.name == "Atlanta Hawks"
        assert team.short_name == ""


class TestNBAMapperGame:
    """Tests for game mapping."""

    def test_map_game_from_schedule_home(self):
        """Test mapping a home game from schedule."""
        mapper = NBAMapper()
        game = mapper.map_game_from_schedule({
            "GAME_ID": "0022300001",
            "TEAM_ID": 1610612737,
            "MATCHUP": "ATL vs. CHI",
            "GAME_DATE": "2023-10-24",
            "WL": "W",
            "PTS": 112,
        })

        assert game.external_id == "0022300001"
        assert game.home_team_external_id == "1610612737"
        assert game.away_team_external_id == ""  # Not available from single row
        assert game.status == "final"
        assert game.home_score == 112
        assert game.away_score is None

    def test_map_game_from_schedule_away(self):
        """Test mapping an away game from schedule."""
        mapper = NBAMapper()
        game = mapper.map_game_from_schedule({
            "GAME_ID": "0022300001",
            "TEAM_ID": 1610612747,
            "MATCHUP": "LAL @ GSW",
            "GAME_DATE": "2023-10-24",
            "WL": "L",
            "PTS": 108,
        })

        assert game.external_id == "0022300001"
        assert game.home_team_external_id == ""
        assert game.away_team_external_id == "1610612747"
        assert game.status == "final"
        assert game.home_score is None
        assert game.away_score == 108

    def test_map_game_scheduled(self):
        """Test mapping a scheduled game."""
        mapper = NBAMapper()
        game = mapper.map_game_from_schedule({
            "GAME_ID": "0022300100",
            "TEAM_ID": 1610612737,
            "MATCHUP": "ATL vs. BOS",
            "GAME_DATE": "2024-01-15",
            "WL": None,
            "PTS": None,
        })

        assert game.external_id == "0022300100"
        assert game.status == "scheduled"
        assert game.home_score is None
        assert game.away_score is None


class TestNBAMapperPlayerStats:
    """Tests for player stats mapping."""

    def test_map_player_stats(self):
        """Test mapping player statistics."""
        mapper = NBAMapper()
        stats = mapper.map_player_stats({
            "playerId": 203507,
            "playerName": "Giannis Antetokounmpo",
            "teamId": 1610612749,
            "minutes": "PT34M12.00S",
            "points": 32,
            "fieldGoalsMade": 12,
            "fieldGoalsAttempted": 20,
            "threePointersMade": 2,
            "threePointersAttempted": 5,
            "freeThrowsMade": 6,
            "freeThrowsAttempted": 8,
            "reboundsOffensive": 2,
            "reboundsDefensive": 10,
            "reboundsTotal": 12,
            "assists": 5,
            "turnovers": 3,
            "steals": 1,
            "blocks": 2,
            "foulsPersonal": 3,
            "plusMinusPoints": 15,
            "starter": "1",
        })

        assert stats.player_external_id == "203507"
        assert stats.player_name == "Giannis Antetokounmpo"
        assert stats.team_external_id == "1610612749"
        assert stats.minutes_played == 2052  # 34:12 in seconds
        assert stats.points == 32
        assert stats.field_goals_made == 12
        assert stats.field_goals_attempted == 20
        assert stats.two_pointers_made == 10  # 12 - 2
        assert stats.two_pointers_attempted == 15  # 20 - 5
        assert stats.three_pointers_made == 2
        assert stats.three_pointers_attempted == 5
        assert stats.free_throws_made == 6
        assert stats.free_throws_attempted == 8
        assert stats.offensive_rebounds == 2
        assert stats.defensive_rebounds == 10
        assert stats.total_rebounds == 12
        assert stats.assists == 5
        assert stats.turnovers == 3
        assert stats.steals == 1
        assert stats.blocks == 2
        assert stats.personal_fouls == 3
        assert stats.plus_minus == 15
        assert stats.is_starter is True

    def test_map_player_stats_non_starter(self):
        """Test mapping non-starter player stats."""
        mapper = NBAMapper()
        stats = mapper.map_player_stats({
            "playerId": 12345,
            "playerName": "Bench Player",
            "teamId": 1610612749,
            "minutes": "PT10M00.00S",
            "points": 5,
            "starter": "",
        })

        assert stats.is_starter is False


class TestNBAMapperBoxscore:
    """Tests for boxscore mapping."""

    def test_map_boxscore(self):
        """Test mapping a complete boxscore."""
        mapper = NBAMapper()
        boxscore_data = {
            "TeamStats": [
                {"teamId": 1610612737, "points": 112, "gameDateEst": "2023-10-24"},
                {"teamId": 1610612741, "points": 108},
            ],
            "PlayerStats": [
                {
                    "playerId": 1,
                    "playerName": "Player 1",
                    "teamId": 1610612737,
                    "points": 20,
                },
                {
                    "playerId": 2,
                    "playerName": "Player 2",
                    "teamId": 1610612741,
                    "points": 15,
                },
            ],
        }

        boxscore = mapper.map_boxscore(boxscore_data, "0022300001")

        assert boxscore.game.external_id == "0022300001"
        assert boxscore.game.home_team_external_id == "1610612737"
        assert boxscore.game.away_team_external_id == "1610612741"
        assert boxscore.game.home_score == 112
        assert boxscore.game.away_score == 108
        assert len(boxscore.home_players) == 1
        assert len(boxscore.away_players) == 1
        assert boxscore.home_players[0].player_name == "Player 1"
        assert boxscore.away_players[0].player_name == "Player 2"


class TestNBAMapperPBP:
    """Tests for play-by-play mapping."""

    def test_map_pbp_event(self):
        """Test mapping a single PBP event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event({
            "actionNumber": 1,
            "period": 1,
            "clock": "PT12M00.00S",
            "actionType": "jump ball",
            "teamId": 1610612737,
            "playerNameI": "Trae Young",
        }, 1)

        assert event.event_number == 1
        assert event.period == 1
        assert event.clock == "12:00"
        assert event.event_type == "jump_ball"
        assert event.team_external_id == "1610612737"
        assert event.player_name == "Trae Young"

    def test_map_pbp_event_shot_made(self):
        """Test mapping a made shot event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event({
            "actionNumber": 10,
            "period": 1,
            "clock": "PT10M30.00S",
            "actionType": "3pt shot",
            "shotResult": "MADE",
            "teamId": 1610612737,
            "xLegacy": 25.5,
            "yLegacy": 8.0,
        }, 10)

        assert event.event_type == "shot"
        assert event.success is True
        assert event.coord_x == 25.5
        assert event.coord_y == 8.0

    def test_map_pbp_event_shot_missed(self):
        """Test mapping a missed shot event."""
        mapper = NBAMapper()
        event = mapper.map_pbp_event({
            "actionNumber": 11,
            "period": 1,
            "clock": "PT10M25.00S",
            "actionType": "2pt shot",
            "shotResult": "MISSED",
        }, 11)

        assert event.event_type == "shot"
        assert event.success is False

    def test_map_pbp_events(self):
        """Test mapping multiple PBP events."""
        mapper = NBAMapper()
        pbp_data = [
            {"actionNumber": 1, "period": 1, "clock": "PT12M00.00S", "actionType": "jumpball"},
            {"actionNumber": 2, "period": 1, "clock": "PT11M45.00S", "actionType": "2pt shot"},
        ]

        events = mapper.map_pbp_events(pbp_data)

        assert len(events) == 2
        assert events[0].event_number == 1
        assert events[1].event_number == 2
