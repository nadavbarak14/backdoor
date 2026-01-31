"""Tests for BaseLeagueConverter abstract base class."""

from typing import Any

import pytest

from src.sync.canonical import (
    BaseLeagueConverter,
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayer,
    CanonicalPlayerStats,
    CanonicalSeason,
    CanonicalTeam,
    EventType,
    Position,
)


class TestBaseLeagueConverter:
    """Tests for BaseLeagueConverter ABC."""

    def test_cannot_instantiate_directly(self) -> None:
        """Test that BaseLeagueConverter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseLeagueConverter()  # type: ignore

    def test_requires_all_abstract_methods(self) -> None:
        """Test that subclass must implement all abstract methods."""

        class IncompleteConverter(BaseLeagueConverter):
            source = "test"
            # Missing all abstract method implementations

        with pytest.raises(TypeError):
            IncompleteConverter()  # type: ignore

    def test_partial_implementation_fails(self) -> None:
        """Test that partial implementation still fails."""

        class PartialConverter(BaseLeagueConverter):
            source = "test"

            def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
                pass  # type: ignore

            # Missing other methods

        with pytest.raises(TypeError):
            PartialConverter()  # type: ignore

    def test_complete_implementation_works(self) -> None:
        """Test that complete implementation can be instantiated."""

        class CompleteConverter(BaseLeagueConverter):
            source = "test"

            def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
                return CanonicalPlayer(
                    external_id="1",
                    source=self.source,
                    first_name="Test",
                    last_name="Player",
                    positions=[],
                    height=None,
                    birth_date=None,
                    nationality=None,
                    jersey_number=None,
                )

            def map_position(self, raw: str | None) -> list[Position]:
                return []

            def convert_team(self, raw: dict[str, Any]) -> CanonicalTeam:
                return CanonicalTeam(
                    external_id="1",
                    source=self.source,
                    name="Test Team",
                    short_name=None,
                    city=None,
                    country=None,
                )

            def convert_game(self, raw: dict[str, Any]) -> CanonicalGame:
                from datetime import datetime

                return CanonicalGame(
                    external_id="1",
                    source=self.source,
                    season_external_id="S1",
                    home_team_external_id="T1",
                    away_team_external_id="T2",
                    game_date=datetime.now(),
                    status="SCHEDULED",
                    home_score=None,
                    away_score=None,
                )

            def convert_player_stats(self, raw: dict[str, Any]) -> CanonicalPlayerStats:
                return CanonicalPlayerStats(
                    player_external_id="1",
                    player_name="Test",
                    team_external_id="T1",
                    minutes_seconds=0,
                )

            def parse_minutes_to_seconds(self, raw: str | int | None) -> int:
                return 0

            def convert_pbp_event(self, raw: dict[str, Any]) -> CanonicalPBPEvent | None:
                return None

            def map_event_type(self, raw: str) -> tuple[EventType, dict[str, Any]]:
                return (EventType.SHOT, {})

            def convert_season(self, raw: dict[str, Any]) -> CanonicalSeason:
                return CanonicalSeason(
                    external_id="1",
                    source=self.source,
                    name="2024-25",
                    start_date=None,
                    end_date=None,
                )

        # Should not raise
        converter = CompleteConverter()
        assert converter.source == "test"

    def test_source_attribute(self) -> None:
        """Test that source attribute can be set on subclass."""

        class MyConverter(BaseLeagueConverter):
            source = "my_league"

            def convert_player(self, raw: dict[str, Any]) -> CanonicalPlayer:
                return CanonicalPlayer(
                    external_id="1",
                    source=self.source,
                    first_name="Test",
                    last_name="Player",
                    positions=[],
                    height=None,
                    birth_date=None,
                    nationality=None,
                    jersey_number=None,
                )

            def map_position(self, raw: str | None) -> list[Position]:
                return []

            def convert_team(self, raw: dict[str, Any]) -> CanonicalTeam:
                return CanonicalTeam(
                    external_id="1",
                    source=self.source,
                    name="Test",
                    short_name=None,
                    city=None,
                    country=None,
                )

            def convert_game(self, raw: dict[str, Any]) -> CanonicalGame:
                from datetime import datetime

                return CanonicalGame(
                    external_id="1",
                    source=self.source,
                    season_external_id="S1",
                    home_team_external_id="T1",
                    away_team_external_id="T2",
                    game_date=datetime.now(),
                    status="SCHEDULED",
                    home_score=None,
                    away_score=None,
                )

            def convert_player_stats(self, raw: dict[str, Any]) -> CanonicalPlayerStats:
                return CanonicalPlayerStats(
                    player_external_id="1",
                    player_name="Test",
                    team_external_id="T1",
                    minutes_seconds=0,
                )

            def parse_minutes_to_seconds(self, raw: str | int | None) -> int:
                return 0

            def convert_pbp_event(self, raw: dict[str, Any]) -> CanonicalPBPEvent | None:
                return None

            def map_event_type(self, raw: str) -> tuple[EventType, dict[str, Any]]:
                return (EventType.SHOT, {})

            def convert_season(self, raw: dict[str, Any]) -> CanonicalSeason:
                return CanonicalSeason(
                    external_id="1",
                    source=self.source,
                    name="2024-25",
                    start_date=None,
                    end_date=None,
                )

        converter = MyConverter()
        assert converter.source == "my_league"

        # Test that convert_player uses the source
        player = converter.convert_player({})
        assert player.source == "my_league"
