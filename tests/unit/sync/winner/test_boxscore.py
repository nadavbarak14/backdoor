"""
Unit tests for Winner boxscore parsing and enrichment.

Tests the mapping of segevstats JSON-RPC boxscore format to internal types,
including:
- String to integer conversion for stat fields
- Player name enrichment from PBP roster data

Addresses Issue #128: Sync game boxscores with player stats.
"""

import pytest

from src.schemas.enums import GameStatus
from src.sync.types import RawBoxScore, RawGame, RawPlayerStats
from src.sync.winner.mapper import PlayerRoster, WinnerMapper


@pytest.fixture
def mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


class TestMapPlayerStatsHandlesStrings:
    """Test that string values from segevstats are converted to integers.

    The segevstats API returns all stat values as strings (e.g., "22" for points).
    The mapper must convert these to integers.
    """

    def test_points_string_to_int(self, mapper: WinnerMapper) -> None:
        """Points should be converted from string "22" to int 22."""
        data = {
            "playerId": "1019",
            "points": "22",
            "minutes": "00:00",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.points == 22
        assert isinstance(stats.points, int)

    def test_minutes_string_parsed(self, mapper: WinnerMapper) -> None:
        """Minutes string "27:06" should be converted to 1626 seconds."""
        data = {
            "playerId": "1019",
            "minutes": "27:06",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.minutes_played == 1626
        assert isinstance(stats.minutes_played, int)

    def test_field_goals_strings_to_int(self, mapper: WinnerMapper) -> None:
        """Field goal makes/misses should be converted from strings."""
        data = {
            "playerId": "1019",
            "fg_2m": "6",
            "fg_2mis": "2",
            "fg_3m": "1",
            "fg_3mis": "3",
            "minutes": "00:00",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.two_pointers_made == 6
        assert stats.two_pointers_attempted == 8  # 6 + 2
        assert stats.three_pointers_made == 1
        assert stats.three_pointers_attempted == 4  # 1 + 3
        assert stats.field_goals_made == 7  # 6 + 1
        assert stats.field_goals_attempted == 12  # 8 + 4
        assert isinstance(stats.two_pointers_made, int)

    def test_free_throws_strings_to_int(self, mapper: WinnerMapper) -> None:
        """Free throw makes/misses should be converted from strings."""
        data = {
            "playerId": "1019",
            "ft_m": "7",
            "ft_mis": "1",
            "minutes": "00:00",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.free_throws_made == 7
        assert stats.free_throws_attempted == 8  # 7 + 1
        assert isinstance(stats.free_throws_made, int)

    def test_rebounds_strings_to_int(self, mapper: WinnerMapper) -> None:
        """Rebounds should be converted from strings."""
        data = {
            "playerId": "1019",
            "reb_d": "2",
            "reb_o": "3",
            "minutes": "00:00",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.defensive_rebounds == 2
        assert stats.offensive_rebounds == 3
        assert stats.total_rebounds == 5
        assert isinstance(stats.total_rebounds, int)

    def test_other_stats_strings_to_int(self, mapper: WinnerMapper) -> None:
        """Assists, steals, blocks, turnovers, fouls should be converted."""
        data = {
            "playerId": "1019",
            "ast": "1",
            "stl": "2",
            "blk": "2",
            "to": "1",
            "f": "3",
            "plusMinus": "3",
            "minutes": "00:00",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.assists == 1
        assert stats.steals == 2
        assert stats.blocks == 2
        assert stats.turnovers == 1
        assert stats.personal_fouls == 3
        assert stats.plus_minus == 3
        assert isinstance(stats.assists, int)

    def test_negative_plus_minus_string(self, mapper: WinnerMapper) -> None:
        """Negative plus/minus string "-7" should be converted correctly."""
        data = {
            "playerId": "1000",
            "plusMinus": "-7",
            "minutes": "00:00",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.plus_minus == -7
        assert isinstance(stats.plus_minus, int)

    def test_empty_string_defaults_to_zero(self, mapper: WinnerMapper) -> None:
        """Empty string values should default to 0."""
        data = {
            "playerId": "1019",
            "points": "",
            "ast": "",
            "minutes": "",
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.points == 0
        assert stats.assists == 0
        assert stats.minutes_played == 0

    def test_none_values_default_to_zero(self, mapper: WinnerMapper) -> None:
        """None values should default to 0."""
        data = {
            "playerId": "1019",
            "points": None,
            "ast": None,
            "minutes": None,
        }
        stats = mapper.map_player_stats(data, "100")

        assert stats.points == 0
        assert stats.assists == 0
        assert stats.minutes_played == 0


class TestEnrichBoxscoreWithNames:
    """Test that boxscore player stats are enriched with names from PBP roster."""

    @pytest.fixture
    def sample_boxscore(self, mapper: WinnerMapper) -> RawBoxScore:
        """Create a sample boxscore without names."""
        return RawBoxScore(
            game=RawGame(
                external_id="24",
                home_team_external_id="2",
                away_team_external_id="4",
                game_date=mapper.parse_datetime("2025-09-21"),
                status=GameStatus.FINAL,
                home_score=79,
                away_score=84,
            ),
            home_players=[
                RawPlayerStats(
                    player_external_id="1019",
                    player_name="",  # Empty - needs enrichment
                    team_external_id="2",
                    points=22,
                ),
                RawPlayerStats(
                    player_external_id="1014",
                    player_name="",
                    team_external_id="2",
                    points=12,
                ),
            ],
            away_players=[
                RawPlayerStats(
                    player_external_id="1044",
                    player_name="",
                    team_external_id="4",
                    points=21,
                ),
            ],
        )

    @pytest.fixture
    def sample_roster(self) -> PlayerRoster:
        """Create a sample roster with player names."""
        return PlayerRoster(
            players={
                "1019": ("ROMAN", "SORKIN"),
                "1014": ("JIMMY", "CLARK III"),
                "1044": ("IFTACH", "ZION"),
            }
        )

    def test_enrich_adds_player_names(
        self,
        mapper: WinnerMapper,
        sample_boxscore: RawBoxScore,
        sample_roster: PlayerRoster,
    ) -> None:
        """Player names should be added from roster."""
        enriched = mapper.enrich_boxscore_with_names(sample_boxscore, sample_roster)

        # Home players should have names
        player_1019 = next(
            p for p in enriched.home_players if p.player_external_id == "1019"
        )
        assert player_1019.player_name == "ROMAN SORKIN"

        player_1014 = next(
            p for p in enriched.home_players if p.player_external_id == "1014"
        )
        assert player_1014.player_name == "JIMMY CLARK III"

        # Away player should have name
        player_1044 = next(
            p for p in enriched.away_players if p.player_external_id == "1044"
        )
        assert player_1044.player_name == "IFTACH ZION"

    def test_enrich_preserves_stats(
        self,
        mapper: WinnerMapper,
        sample_boxscore: RawBoxScore,
        sample_roster: PlayerRoster,
    ) -> None:
        """Enrichment should preserve existing stats."""
        enriched = mapper.enrich_boxscore_with_names(sample_boxscore, sample_roster)

        player_1019 = next(
            p for p in enriched.home_players if p.player_external_id == "1019"
        )
        assert player_1019.points == 22
        assert player_1019.team_external_id == "2"

    def test_enrich_unknown_player_has_empty_name(
        self,
        mapper: WinnerMapper,
        sample_roster: PlayerRoster,
    ) -> None:
        """Players not in roster should have empty name."""
        boxscore = RawBoxScore(
            game=RawGame(
                external_id="24",
                home_team_external_id="2",
                away_team_external_id="4",
                game_date=mapper.parse_datetime("2025-09-21"),
                status=GameStatus.FINAL,
                home_score=79,
                away_score=84,
            ),
            home_players=[
                RawPlayerStats(
                    player_external_id="9999",  # Not in roster
                    player_name="",
                    team_external_id="2",
                    points=10,
                ),
            ],
            away_players=[],
        )

        enriched = mapper.enrich_boxscore_with_names(boxscore, sample_roster)

        player = enriched.home_players[0]
        assert player.player_name == ""

    def test_enrich_preserves_game_info(
        self,
        mapper: WinnerMapper,
        sample_boxscore: RawBoxScore,
        sample_roster: PlayerRoster,
    ) -> None:
        """Game info should be preserved after enrichment."""
        enriched = mapper.enrich_boxscore_with_names(sample_boxscore, sample_roster)

        assert enriched.game.external_id == "24"
        assert enriched.game.home_score == 79
        assert enriched.game.away_score == 84
        assert enriched.game.status == GameStatus.FINAL


class TestExtractPlayerRoster:
    """Test extraction of player roster from PBP response."""

    def test_extract_roster_from_pbp(self, mapper: WinnerMapper) -> None:
        """Roster should be extracted from PBP gameInfo structure."""
        pbp_data = {
            "result": {
                "gameInfo": {
                    "homeTeam": {
                        "players": [
                            {
                                "id": "1019",
                                "firstName": "ROMAN",
                                "lastName": "SORKIN",
                            },
                            {
                                "id": "1014",
                                "firstName": "JIMMY",
                                "lastName": "CLARK III",
                            },
                        ]
                    },
                    "awayTeam": {
                        "players": [
                            {
                                "id": "1044",
                                "firstName": "IFTACH",
                                "lastName": "ZION",
                            },
                        ]
                    },
                }
            }
        }

        roster = mapper.extract_player_roster(pbp_data)

        assert "1019" in roster.players
        assert "1014" in roster.players
        assert "1044" in roster.players

        assert roster.get_full_name("1019") == "ROMAN SORKIN"
        assert roster.get_full_name("1014") == "JIMMY CLARK III"
        assert roster.get_full_name("1044") == "IFTACH ZION"

    def test_extract_roster_unknown_id(self, mapper: WinnerMapper) -> None:
        """Unknown player ID should return empty string."""
        pbp_data = {
            "result": {
                "gameInfo": {
                    "homeTeam": {"players": []},
                    "awayTeam": {"players": []},
                }
            }
        }

        roster = mapper.extract_player_roster(pbp_data)

        assert roster.get_full_name("9999") == ""

    def test_extract_roster_handles_empty_names(self, mapper: WinnerMapper) -> None:
        """Empty first/last names should result in empty full name."""
        pbp_data = {
            "result": {
                "gameInfo": {
                    "homeTeam": {
                        "players": [
                            {
                                "id": "1019",
                                "firstName": "",
                                "lastName": "",
                            },
                        ]
                    },
                    "awayTeam": {"players": []},
                }
            }
        }

        roster = mapper.extract_player_roster(pbp_data)

        # Empty names should produce empty string (after strip)
        assert roster.get_full_name("1019") == ""


class TestParseInt:
    """Test the internal _parse_int method."""

    def test_parse_int_string(self, mapper: WinnerMapper) -> None:
        """String integers should be parsed."""
        assert mapper._parse_int("22") == 22
        assert mapper._parse_int("0") == 0
        assert mapper._parse_int("-5") == -5

    def test_parse_int_actual_int(self, mapper: WinnerMapper) -> None:
        """Actual integers should pass through."""
        assert mapper._parse_int(22) == 22
        assert mapper._parse_int(0) == 0
        assert mapper._parse_int(-5) == -5

    def test_parse_int_none(self, mapper: WinnerMapper) -> None:
        """None should return default (0)."""
        assert mapper._parse_int(None) == 0
        assert mapper._parse_int(None, default=10) == 10

    def test_parse_int_empty_string(self, mapper: WinnerMapper) -> None:
        """Empty string should return default."""
        assert mapper._parse_int("") == 0
        assert mapper._parse_int("", default=5) == 5

    def test_parse_int_invalid(self, mapper: WinnerMapper) -> None:
        """Invalid strings should return default."""
        assert mapper._parse_int("abc") == 0
        assert mapper._parse_int("12.5") == 0  # Float string not valid int
