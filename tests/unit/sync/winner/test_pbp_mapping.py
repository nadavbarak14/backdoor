"""
Tests for segevstats PBP mapping in WinnerMapper.
"""

import pytest

from src.sync.winner.mapper import WinnerMapper


@pytest.fixture
def mapper():
    return WinnerMapper()


@pytest.fixture
def pbp_fixture():
    """Minimal segevstats PBP response for testing."""
    return {
        "result": {
            "gameInfo": {
                "homeTeam": {
                    "id": 2,
                    "players": [
                        {"id": "1000", "firstName": "JAYLEN", "lastName": "HOARD"},
                        {"id": "1019", "firstName": "ROMAN", "lastName": "SORKIN"},
                    ],
                },
                "awayTeam": {
                    "id": 4,
                    "players": [
                        {"id": "1002", "firstName": "MARCUS", "lastName": "FOSTER"},
                    ],
                },
            },
            "actions": [
                {
                    "type": "shot",
                    "quarter": 1,
                    "quarterTime": "09:42",
                    "playerId": 1000,
                    "teamId": 2,
                    "parameters": {
                        "made": "made",
                        "type": "dunk",
                        "coordX": 705.0,
                        "coordY": 140.0,
                    },
                },
                {
                    "type": "shot",
                    "quarter": 1,
                    "quarterTime": "09:30",
                    "playerId": 1019,
                    "teamId": 2,
                    "parameters": {"made": "missed", "type": "lay-up"},
                },
                {
                    "type": "rebound",
                    "quarter": 1,
                    "quarterTime": "09:28",
                    "playerId": 1002,
                    "teamId": 4,
                    "parameters": {"type": "defensive"},
                },
                {
                    "type": "freeThrow",
                    "quarter": 2,
                    "quarterTime": "05:00",
                    "playerId": 1019,
                    "teamId": 2,
                    "parameters": {"made": "made", "freeThrowNumber": 1},
                },
                {
                    "type": "freeThrow",
                    "quarter": 2,
                    "quarterTime": "05:00",
                    "playerId": 1019,
                    "teamId": 2,
                    "parameters": {"made": "missed", "freeThrowNumber": 2},
                },
                {
                    "type": "assist",
                    "quarter": 3,
                    "quarterTime": "08:00",
                    "playerId": 1000,
                    "teamId": 2,
                    "parameters": {},
                },
                {
                    "type": "turnover",
                    "quarter": 3,
                    "quarterTime": "07:00",
                    "playerId": 1002,
                    "teamId": 4,
                    "parameters": {},
                },
                {
                    "type": "steal",
                    "quarter": 3,
                    "quarterTime": "06:59",
                    "playerId": 1019,
                    "teamId": 2,
                    "parameters": {},
                },
                {
                    "type": "foul",
                    "quarter": 4,
                    "quarterTime": "02:00",
                    "playerId": 1000,
                    "teamId": 2,
                    "parameters": {"type": "personal"},
                },
                {
                    "type": "block",
                    "quarter": 4,
                    "quarterTime": "01:00",
                    "playerId": 1019,
                    "teamId": 2,
                    "parameters": {},
                },
                {
                    "type": "substitution",
                    "quarter": 4,
                    "quarterTime": "00:30",
                    "playerId": 1000,
                    "teamId": 2,
                    "parameters": {"playerIn": "1", "playerOut": "9"},
                },
                {
                    "type": "timeout",
                    "quarter": 4,
                    "quarterTime": "00:15",
                    "playerId": 0,
                    "teamId": 2,
                    "parameters": {},
                },
            ],
        }
    }


class TestMapPbpEventsFromActions:
    """Test result.actions parsed correctly."""

    def test_parses_actions_array(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert len(events) == 12

    def test_skips_clock_events(self, mapper):
        data = {
            "result": {
                "gameInfo": {"homeTeam": {"players": []}, "awayTeam": {"players": []}},
                "actions": [
                    {"type": "clock", "quarter": 1, "quarterTime": "09:00"},
                    {"type": "game", "quarter": 1, "quarterTime": "10:00"},
                    {"type": "quarter", "quarter": 1, "quarterTime": "10:00"},
                    {
                        "type": "shot",
                        "quarter": 1,
                        "quarterTime": "09:00",
                        "playerId": 1,
                        "teamId": 1,
                        "parameters": {"made": "made"},
                    },
                ],
            }
        }
        events = mapper.map_pbp_events(data)
        assert len(events) == 1
        assert events[0].event_type == "shot"


class TestMapShotSuccess:
    """Test parameters.made mapping."""

    def test_made_shot_success_true(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        shot_event = events[0]
        assert shot_event.event_type == "shot"
        assert shot_event.success is True

    def test_missed_shot_success_false(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        missed_shot = events[1]
        assert missed_shot.event_type == "shot"
        assert missed_shot.success is False


class TestMapEventTypes:
    """Test all action types mapped correctly."""

    def test_shot_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[0].event_type == "shot"

    def test_free_throw_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[3].event_type == "free_throw"

    def test_rebound_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[2].event_type == "rebound"

    def test_assist_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[5].event_type == "assist"

    def test_turnover_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[6].event_type == "turnover"

    def test_steal_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[7].event_type == "steal"

    def test_foul_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[8].event_type == "foul"

    def test_block_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[9].event_type == "block"

    def test_substitution_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[10].event_type == "substitution"

    def test_timeout_type(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[11].event_type == "timeout"


class TestExtractPlayerRosterFromPbp:
    """Test player names from gameInfo."""

    def test_extracts_home_team_players(self, mapper, pbp_fixture):
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1000") == "JAYLEN HOARD"
        assert roster.get_full_name("1019") == "ROMAN SORKIN"

    def test_extracts_away_team_players(self, mapper, pbp_fixture):
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("1002") == "MARCUS FOSTER"

    def test_unknown_player_returns_empty(self, mapper, pbp_fixture):
        roster = mapper.extract_player_roster(pbp_fixture)
        assert roster.get_full_name("9999") == ""


class TestMapCoordinates:
    """Test coordX/coordY extracted for shots."""

    def test_shot_has_coordinates(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        shot = events[0]
        assert shot.coord_x == 705.0
        assert shot.coord_y == 140.0

    def test_shot_without_coords_is_none(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        missed_shot = events[1]
        assert missed_shot.coord_x is None
        assert missed_shot.coord_y is None


class TestResolvePlayerByExternalId:
    """Test playerId → player_external_id mapping."""

    def test_player_external_id_set(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[0].player_external_id == "1000"
        assert events[1].player_external_id == "1019"
        assert events[2].player_external_id == "1002"

    def test_player_name_resolved_from_roster(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[0].player_name == "JAYLEN HOARD"
        assert events[1].player_name == "ROMAN SORKIN"
        assert events[2].player_name == "MARCUS FOSTER"


class TestEventSubtype:
    """Test event subtype extraction."""

    def test_shot_subtype(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[0].event_subtype == "dunk"
        assert events[1].event_subtype == "lay-up"

    def test_rebound_subtype(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[2].event_subtype == "defensive"

    def test_foul_subtype(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        assert events[8].event_subtype == "personal"


class TestTeamMapping:
    """Test team ID mapping to home/away."""

    def test_home_team_mapped(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        # teamId=2 is home team in fixture
        home_events = [e for e in events if e.team_external_id == "home"]
        assert len(home_events) > 0

    def test_away_team_mapped(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        # teamId=4 is away team in fixture
        away_events = [e for e in events if e.team_external_id == "away"]
        assert len(away_events) > 0

    def test_both_teams_have_events(self, mapper, pbp_fixture):
        events = mapper.map_pbp_events(pbp_fixture)
        team_ids = {e.team_external_id for e in events if e.team_external_id}
        assert "home" in team_ids
        assert "away" in team_ids
