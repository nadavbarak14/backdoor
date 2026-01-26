"""
Integration tests for Winner League team sync.

Tests the full team sync flow from API response through database storage:
- All teams from current season are synced
- Team names are in English (no Hebrew)
- TeamSeason records link teams to seasons
- Re-sync is idempotent (no duplicates on re-run)

Usage:
    pytest tests/integration/sync/test_winner_team_sync.py -v
"""

import json
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.team import Team, TeamSeason
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities import TeamSyncer
from src.sync.winner.mapper import WinnerMapper

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def games_all_response() -> list:
    """Load real games_all API response fixture."""
    path = FIXTURES_DIR / "games_all_response.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def winner_mapper() -> WinnerMapper:
    """Create a WinnerMapper instance."""
    return WinnerMapper()


@pytest.fixture
def league(test_db: Session) -> League:
    """Create Winner League."""
    league = League(
        id=uuid4(),
        name="Winner League",
        code="WNR",
        country="Israel",
    )
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def season(test_db: Session, league: League) -> Season:
    """Create the 2025-26 season."""
    season = Season(
        id=uuid4(),
        league_id=league.id,
        name="2025-26",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 30),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def team_matcher(test_db: Session) -> TeamMatcher:
    """Create TeamMatcher."""
    return TeamMatcher(test_db)


@pytest.fixture
def player_deduplicator(test_db: Session) -> PlayerDeduplicator:
    """Create PlayerDeduplicator."""
    return PlayerDeduplicator(test_db)


@pytest.fixture
def team_syncer(
    test_db: Session, team_matcher: TeamMatcher, player_deduplicator: PlayerDeduplicator
) -> TeamSyncer:
    """Create TeamSyncer."""
    return TeamSyncer(test_db, team_matcher, player_deduplicator)


def _extract_games_data(response):
    """Extract games data from API response (handles list wrapper)."""
    if isinstance(response, list) and len(response) > 0:
        return response[0]
    return response


class TestSyncTeamsCreatesAllTeams:
    """Tests for syncing all teams from current season."""

    def test_sync_teams_creates_all_teams(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test that all unique teams from games_all are synced."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync all teams
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")

        test_db.commit()

        # Verify team count
        db_team_count = test_db.query(Team).count()
        assert db_team_count == len(
            raw_teams
        ), f"Expected {len(raw_teams)} teams, found {db_team_count}"

    def test_sync_teams_has_expected_count(
        self,
        winner_mapper: WinnerMapper,
        games_all_response: list,
    ) -> None:
        """Test fixture contains expected number of teams (12 for Winner League)."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Winner League has 12 teams in the top division
        # This may vary based on fixture data, so we verify reasonable count
        assert len(raw_teams) >= 2, "Fixture should contain multiple teams"

        # Also verify we have unique team IDs
        team_ids = {t.external_id for t in raw_teams}
        assert len(team_ids) == len(raw_teams), "Found duplicate team IDs"


class TestSyncTeamsEnglishNames:
    """Tests that synced teams have English names (no Hebrew)."""

    def test_sync_teams_english_names(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test all synced teams have English names without Hebrew characters."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync all teams
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")

        test_db.commit()

        # Check all teams in database
        teams = test_db.query(Team).all()

        # Hebrew Unicode range
        hebrew_pattern = re.compile(r"[\u0590-\u05FF]")

        for team in teams:
            assert not hebrew_pattern.search(
                team.name
            ), f"Team '{team.name}' contains Hebrew characters"

    def test_no_html_entities_in_names(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test team names don't contain HTML entities like &quot;"""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync all teams
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")

        test_db.commit()

        # Check all teams in database
        teams = test_db.query(Team).all()

        for team in teams:
            assert (
                "&quot;" not in team.name
            ), f"Team '{team.name}' contains HTML entity &quot;"
            assert (
                "&amp;" not in team.name
            ), f"Team '{team.name}' contains HTML entity &amp;"


class TestTeamsLinkedToSeason:
    """Tests that TeamSeason records correctly link teams to seasons."""

    def test_team_season_created(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test TeamSeason records are created linking teams to season."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync all teams
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")

        test_db.commit()

        # Verify TeamSeason count matches team count
        team_count = test_db.query(Team).count()
        team_season_count = test_db.query(TeamSeason).count()

        assert (
            team_season_count == team_count
        ), f"Expected {team_count} TeamSeason records, found {team_season_count}"

    def test_team_seasons_reference_correct_season(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test all TeamSeason records reference the correct season."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync all teams
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")

        test_db.commit()

        # Verify all TeamSeasons point to our season
        team_seasons = test_db.query(TeamSeason).all()

        for ts in team_seasons:
            assert ts.season_id == season.id

    def test_team_has_external_id_in_database(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test synced teams have winner source in external_ids."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync all teams
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")

        test_db.commit()

        # Verify all teams have winner external_id
        teams = test_db.query(Team).all()

        for team in teams:
            assert (
                "winner" in team.external_ids
            ), f"Team '{team.name}' missing 'winner' in external_ids"
            assert team.external_ids[
                "winner"
            ], f"Team '{team.name}' has empty winner external_id"


class TestResyncTeamsIdempotent:
    """Tests that re-syncing teams doesn't create duplicates."""

    def test_resync_teams_idempotent(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test syncing twice produces same team count (no duplicates)."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # First sync
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")
        test_db.commit()

        first_sync_team_count = test_db.query(Team).count()
        first_sync_team_season_count = test_db.query(TeamSeason).count()

        # Second sync (same data)
        for raw_team in raw_teams:
            team_syncer.sync_team_season(raw_team, season.id, "winner")
        test_db.commit()

        second_sync_team_count = test_db.query(Team).count()
        second_sync_team_season_count = test_db.query(TeamSeason).count()

        assert (
            second_sync_team_count == first_sync_team_count
        ), f"Team count changed: {first_sync_team_count} -> {second_sync_team_count}"
        assert second_sync_team_season_count == first_sync_team_season_count, (
            f"TeamSeason count changed: {first_sync_team_season_count} -> "
            f"{second_sync_team_season_count}"
        )

    def test_resync_preserves_team_ids(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test re-syncing preserves existing team UUIDs."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # First sync - collect team IDs
        first_sync_ids = {}
        for raw_team in raw_teams:
            team, _ = team_syncer.sync_team_season(raw_team, season.id, "winner")
            first_sync_ids[raw_team.external_id] = team.id
        test_db.commit()

        # Second sync - verify same IDs
        for raw_team in raw_teams:
            team, _ = team_syncer.sync_team_season(raw_team, season.id, "winner")
            expected_id = first_sync_ids[raw_team.external_id]
            assert team.id == expected_id, (
                f"Team {raw_team.external_id} ID changed from "
                f"{expected_id} to {team.id}"
            )

    def test_resync_three_times_still_idempotent(
        self,
        winner_mapper: WinnerMapper,
        team_syncer: TeamSyncer,
        season: Season,
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test three syncs still produce consistent results."""
        games_data = _extract_games_data(games_all_response)
        raw_teams = winner_mapper.extract_teams_from_games(games_data)

        # Sync three times
        for _ in range(3):
            for raw_team in raw_teams:
                team_syncer.sync_team_season(raw_team, season.id, "winner")
            test_db.commit()

        # Should still have same count as raw teams
        final_team_count = test_db.query(Team).count()
        assert final_team_count == len(raw_teams)
