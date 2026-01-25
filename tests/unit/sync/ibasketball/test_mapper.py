"""
Unit tests for IBasketballMapper.

Tests data transformation from SportsPress API format to Raw types.
"""

from datetime import date, datetime

import pytest

from src.sync.ibasketball.mapper import IBasketballMapper
from src.sync.types import RawPBPEvent


class TestIBasketballMapper:
    """Tests for IBasketballMapper class."""

    @pytest.fixture
    def mapper(self):
        """Create mapper instance."""
        return IBasketballMapper()

    class TestParseDateTime:
        """Tests for datetime parsing."""

        def test_parse_iso_format(self, mapper):
            """Test parsing ISO format datetime."""
            dt = mapper.parse_datetime("2024-01-15T19:30:00")
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 15
            assert dt.hour == 19
            assert dt.minute == 30

        def test_parse_iso_with_z(self, mapper):
            """Test parsing ISO format with Z suffix."""
            dt = mapper.parse_datetime("2024-01-15T19:30:00Z")
            assert dt.year == 2024
            assert dt.month == 1

        def test_parse_wordpress_format(self, mapper):
            """Test parsing WordPress datetime format."""
            dt = mapper.parse_datetime("2024-01-15 19:30:00")
            assert dt.year == 2024
            assert dt.hour == 19

        def test_parse_date_only(self, mapper):
            """Test parsing date-only format."""
            dt = mapper.parse_datetime("2024-01-15")
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 15

        def test_parse_empty_returns_now(self, mapper):
            """Test empty string returns current time."""
            dt = mapper.parse_datetime("")
            assert dt.year == datetime.now().year

    class TestParseMinutesToSeconds:
        """Tests for minutes parsing."""

        def test_parse_minutes_seconds(self, mapper):
            """Test parsing MM:SS format."""
            seconds = mapper.parse_minutes_to_seconds("32:15")
            assert seconds == 32 * 60 + 15  # 1935

        def test_parse_single_digit_minutes(self, mapper):
            """Test parsing single digit minutes."""
            seconds = mapper.parse_minutes_to_seconds("5:30")
            assert seconds == 5 * 60 + 30  # 330

        def test_parse_integer_minutes(self, mapper):
            """Test parsing integer minutes."""
            seconds = mapper.parse_minutes_to_seconds(32)
            assert seconds == 32 * 60  # 1920

        def test_parse_float_minutes(self, mapper):
            """Test parsing float minutes."""
            seconds = mapper.parse_minutes_to_seconds(32.5)
            assert seconds == int(32.5 * 60)  # 1950

        def test_parse_empty_returns_zero(self, mapper):
            """Test empty string returns zero."""
            assert mapper.parse_minutes_to_seconds("") == 0
            assert mapper.parse_minutes_to_seconds(None) == 0

    class TestMapSeason:
        """Tests for season mapping."""

        def test_map_season_with_events(self, mapper):
            """Test mapping season from events data."""
            events = [
                {"date": "2024-10-15T19:30:00"},
                {"date": "2024-11-20T19:30:00"},
                {"date": "2025-01-15T19:30:00"},
            ]

            season = mapper.map_season("liga_leumit", "Liga Leumit", events)

            assert "liga_leumit" in season.external_id
            assert "2024-25" in season.external_id
            assert "Liga Leumit" in season.name
            assert season.start_date == date(2024, 10, 15)
            assert season.end_date == date(2025, 1, 15)
            assert season.is_current is True

        def test_map_season_without_events(self, mapper):
            """Test mapping season without events data."""
            season = mapper.map_season("liga_al", "Liga Alef", None)

            assert "liga_al" in season.external_id
            assert "Liga Alef" in season.name
            assert season.is_current is True

    class TestMapTeam:
        """Tests for team mapping."""

        def test_map_team(self, mapper):
            """Test mapping team from API data."""
            data = {
                "id": 100,
                "title": {"rendered": "Maccabi Tel Aviv"},
                "short_name": "MTA",
            }

            team = mapper.map_team(data)

            assert team.external_id == "100"
            assert team.name == "Maccabi Tel Aviv"
            assert team.short_name == "MTA"

        def test_map_team_with_html_entities(self, mapper):
            """Test mapping team with HTML entities in name."""
            data = {
                "id": 101,
                "title": {"rendered": "Hapoel &amp; Friends"},
            }

            team = mapper.map_team(data)

            assert team.name == "Hapoel & Friends"

    class TestExtractTeamsFromEvents:
        """Tests for extracting teams from events."""

        def test_extract_unique_teams(self, mapper):
            """Test extracting unique teams from events."""
            events = [
                {
                    "teams": [100, 101],
                    "team_names": {"100": "Team A", "101": "Team B"},
                },
                {
                    "teams": [100, 102],
                    "team_names": {"100": "Team A", "102": "Team C"},
                },
            ]

            teams = mapper.extract_teams_from_events(events)

            assert len(teams) == 3
            team_ids = [t.external_id for t in teams]
            assert "100" in team_ids
            assert "101" in team_ids
            assert "102" in team_ids

    class TestMapGame:
        """Tests for game mapping."""

        def test_map_game_final(self, mapper):
            """Test mapping a final game."""
            data = {
                "id": 12345,
                "teams": [100, 101],
                "date": "2024-01-15T19:30:00",
                "status": "publish",
                "results": {
                    "100": {"pts": 85},
                    "101": {"pts": 78},
                },
            }

            game = mapper.map_game(data)

            assert game.external_id == "12345"
            assert game.home_team_external_id == "100"
            assert game.away_team_external_id == "101"
            assert game.status == "final"
            assert game.home_score == 85
            assert game.away_score == 78

        def test_map_game_scheduled(self, mapper):
            """Test mapping a scheduled game."""
            data = {
                "id": 12346,
                "teams": [100, 101],
                "date": "2030-01-15T19:30:00",
                "status": "future",
            }

            game = mapper.map_game(data)

            assert game.status == "scheduled"
            assert game.home_score is None
            assert game.away_score is None

        def test_map_game_infers_status_from_scores(self, mapper):
            """Test game status inferred from scores."""
            data = {
                "id": 12347,
                "teams": [100, 101],
                "date": "2024-01-15T19:30:00",
                "results": {
                    "100": {"pts": 90},
                    "101": {"pts": 88},
                },
            }

            game = mapper.map_game(data)

            assert game.status == "final"

    class TestMapPlayerStats:
        """Tests for player stats mapping."""

        def test_map_player_stats(self, mapper):
            """Test mapping player statistics."""
            stats = {
                "pts": 22,
                "fgm": 8,
                "fga": 15,
                "threepm": 2,
                "threepa": 5,
                "ftm": 4,
                "fta": 5,
                "reb": 8,
                "off": 2,
                "def": 6,
                "ast": 5,
                "stl": 2,
                "blk": 1,
                "to": 3,
                "pf": 2,
                "min": "32:15",
            }

            player_stats = mapper.map_player_stats(
                "1001", "John Smith", "100", stats
            )

            assert player_stats.player_external_id == "1001"
            assert player_stats.player_name == "John Smith"
            assert player_stats.team_external_id == "100"
            assert player_stats.points == 22
            assert player_stats.field_goals_made == 8
            assert player_stats.field_goals_attempted == 15
            assert player_stats.three_pointers_made == 2
            assert player_stats.two_pointers_made == 6  # 8 - 2
            assert player_stats.total_rebounds == 8
            assert player_stats.assists == 5
            assert player_stats.minutes_played == 32 * 60 + 15

        def test_map_player_stats_with_missing_values(self, mapper):
            """Test mapping stats with missing values."""
            stats = {
                "pts": 10,
            }

            player_stats = mapper.map_player_stats(
                "1002", "Jane Doe", "101", stats
            )

            assert player_stats.points == 10
            assert player_stats.field_goals_made == 0
            assert player_stats.total_rebounds == 0

    class TestMapBoxscore:
        """Tests for boxscore mapping."""

        def test_map_boxscore(self, mapper):
            """Test mapping boxscore data."""
            data = {
                "id": 12345,
                "teams": [100, 101],
                "date": "2024-01-15T19:30:00",
                "results": {
                    "100": {"pts": 85},
                    "101": {"pts": 78},
                },
                "performance": {
                    "100": {
                        "1001": {"pts": 22, "reb": 8},
                        "1002": {"pts": 15, "reb": 5},
                    },
                    "101": {
                        "2001": {"pts": 20, "reb": 7},
                    },
                },
                "player_names": {
                    "1001": "Player A",
                    "1002": "Player B",
                    "2001": "Player C",
                },
            }

            boxscore = mapper.map_boxscore(data)

            assert boxscore.game.external_id == "12345"
            assert len(boxscore.home_players) == 2
            assert len(boxscore.away_players) == 1
            assert boxscore.home_players[0].player_name == "Player A"

    class TestMapPBPEvent:
        """Tests for PBP event mapping."""

        def test_map_pbp_event_hebrew(self, mapper):
            """Test mapping Hebrew PBP event."""
            event = mapper.map_pbp_event(
                event_num=1,
                period=1,
                clock="09:45",
                event_type="קליעה",
                player_name="John Smith",
                team_id="100",
                success=True,
            )

            assert event.event_number == 1
            assert event.period == 1
            assert event.clock == "09:45"
            assert event.event_type == "shot"
            assert event.player_name == "John Smith"
            assert event.success is True

        def test_map_pbp_event_english(self, mapper):
            """Test mapping English PBP event."""
            event = mapper.map_pbp_event(
                event_num=2,
                period=1,
                clock="09:30",
                event_type="rebound",
                player_name="Jane Doe",
                team_id="101",
                success=None,
            )

            assert event.event_type == "rebound"

        def test_normalize_pbp_event_types(self, mapper):
            """Test normalization of various event types."""
            assert mapper._normalize_pbp_event_type("קליעה") == "shot"
            assert mapper._normalize_pbp_event_type("החטאה") == "shot"
            assert mapper._normalize_pbp_event_type("ריבאונד") == "rebound"
            assert mapper._normalize_pbp_event_type("אסיסט") == "assist"
            assert mapper._normalize_pbp_event_type("חטיפה") == "steal"
            assert mapper._normalize_pbp_event_type("איבוד") == "turnover"
            assert mapper._normalize_pbp_event_type("חסימה") == "block"
            assert mapper._normalize_pbp_event_type("עבירה") == "foul"

    class TestInferPBPLinks:
        """Tests for PBP link inference."""

        def test_infer_assist_to_shot_link(self, mapper):
            """Test linking assist to made shot."""
            events = [
                RawPBPEvent(
                    event_number=1,
                    period=1,
                    clock="09:45",
                    event_type="shot",
                    team_external_id="100",
                    success=True,
                ),
                RawPBPEvent(
                    event_number=2,
                    period=1,
                    clock="09:45",
                    event_type="assist",
                    team_external_id="100",
                    success=None,
                ),
            ]

            linked = mapper.infer_pbp_links(events)

            assert linked[1].related_event_numbers == [1]

        def test_infer_rebound_to_miss_link(self, mapper):
            """Test linking rebound to missed shot."""
            events = [
                RawPBPEvent(
                    event_number=1,
                    period=1,
                    clock="09:45",
                    event_type="shot",
                    team_external_id="100",
                    success=False,
                ),
                RawPBPEvent(
                    event_number=2,
                    period=1,
                    clock="09:43",
                    event_type="rebound",
                    team_external_id="101",
                    success=None,
                ),
            ]

            linked = mapper.infer_pbp_links(events)

            assert linked[1].related_event_numbers == [1]

        def test_infer_steal_to_turnover_link(self, mapper):
            """Test linking steal to turnover (different teams)."""
            events = [
                RawPBPEvent(
                    event_number=1,
                    period=1,
                    clock="09:45",
                    event_type="turnover",
                    team_external_id="100",
                    success=None,
                ),
                RawPBPEvent(
                    event_number=2,
                    period=1,
                    clock="09:44",
                    event_type="steal",
                    team_external_id="101",
                    success=None,
                ),
            ]

            linked = mapper.infer_pbp_links(events)

            assert linked[1].related_event_numbers == [1]

    class TestMapPlayerInfo:
        """Tests for player info mapping."""

        def test_map_player_info(self, mapper):
            """Test mapping player info."""
            data = {
                "name": "John Smith",
                "height": "198cm",
                "position": "SF",
                "birth_date": "1995-05-15",
            }

            info = mapper.map_player_info("1001", data)

            assert info.external_id == "1001"
            assert info.first_name == "John"
            assert info.last_name == "Smith"
            assert info.height_cm == 198
            assert info.position == "SF"
            assert info.birth_date == date(1995, 5, 15)

        def test_map_player_info_from_title(self, mapper):
            """Test mapping player with title dict."""
            data = {
                "title": {"rendered": "Jane Doe"},
                "height_cm": 185,
            }

            info = mapper.map_player_info("1002", data)

            assert info.first_name == "Jane"
            assert info.last_name == "Doe"
            assert info.height_cm == 185

    class TestCleanHtmlText:
        """Tests for HTML text cleaning."""

        def test_clean_html_entities(self, mapper):
            """Test cleaning HTML entities."""
            assert mapper._clean_html_text("Test &amp; Value") == "Test & Value"
            # Note: <tag> gets decoded then removed as an HTML tag
            assert "Test" in mapper._clean_html_text("Test &lt;tag&gt;")

        def test_clean_html_tags(self, mapper):
            """Test removing HTML tags."""
            assert mapper._clean_html_text("<b>Bold</b> text") == "Bold text"
            assert "Text" in mapper._clean_html_text("Text <br/> more")
            assert "more" in mapper._clean_html_text("Text <br/> more")

        def test_clean_empty_string(self, mapper):
            """Test cleaning empty string."""
            assert mapper._clean_html_text("") == ""
            assert mapper._clean_html_text(None) == ""


@pytest.fixture
def mapper():
    """Create mapper instance for class tests."""
    return IBasketballMapper()
