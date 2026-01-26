"""
Integration tests for Winner League game sync.

Tests the full game sync flow from API response parsing through
database storage. Uses real API response fixtures.

Tests cover:
- Full sync creates expected game count
- Game dates are correctly parsed (not fallback dates)
- All games have valid team references
- Re-sync is idempotent (running twice doesn't duplicate)
"""

import json
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.team import Team
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities import GameSyncer
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
def all_teams(test_db: Session, games_all_response: list) -> dict[str, Team]:
    """Create all teams from the fixture data."""
    # Extract from API response (it's wrapped in a list)
    data = (
        games_all_response[0]
        if isinstance(games_all_response, list)
        else games_all_response
    )
    games = data.get("games", [])

    teams_dict: dict[str, Team] = {}

    for game in games:
        # Extract team1 (home)
        team1_id = str(game.get("team1", ""))
        team1_name = game.get("team_name_eng_1") or game.get("team_name_1") or ""
        if team1_id and team1_id not in teams_dict:
            team = Team(
                id=uuid4(),
                name=team1_name,
                short_name=team1_name[:3].upper() if team1_name else "T1",
                city="",
                country="Israel",
                external_ids={"winner": team1_id},
            )
            test_db.add(team)
            teams_dict[team1_id] = team

        # Extract team2 (away)
        team2_id = str(game.get("team2", ""))
        team2_name = game.get("team_name_eng_2") or game.get("team_name_2") or ""
        if team2_id and team2_id not in teams_dict:
            team = Team(
                id=uuid4(),
                name=team2_name,
                short_name=team2_name[:3].upper() if team2_name else "T2",
                city="",
                country="Israel",
                external_ids={"winner": team2_id},
            )
            test_db.add(team)
            teams_dict[team2_id] = team

    test_db.commit()
    return teams_dict


@pytest.fixture
def team_matcher(test_db: Session) -> TeamMatcher:
    """Create TeamMatcher."""
    return TeamMatcher(test_db)


@pytest.fixture
def player_deduplicator(test_db: Session) -> PlayerDeduplicator:
    """Create PlayerDeduplicator."""
    return PlayerDeduplicator(test_db)


@pytest.fixture
def game_syncer(
    test_db: Session, team_matcher: TeamMatcher, player_deduplicator: PlayerDeduplicator
) -> GameSyncer:
    """Create GameSyncer."""
    return GameSyncer(test_db, team_matcher, player_deduplicator)


class TestSyncCurrentSeasonGames:
    """Tests for syncing all games from current season."""

    def test_sync_creates_expected_game_count(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test full sync creates expected number of games."""
        # Extract games from response
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        # Map and sync each game
        synced_count = 0
        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            game_syncer.sync_game(raw_game, season.id, "winner")
            synced_count += 1

        test_db.commit()

        # Verify count matches
        db_count = test_db.query(Game).count()
        assert db_count == synced_count
        assert db_count == len(raw_games)

    def test_sync_fixture_has_multiple_games(
        self,
        games_all_response: list,
    ) -> None:
        """Test fixture contains multiple games for meaningful test."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        games = data.get("games", [])

        # Fixture should have at least several games
        assert len(games) >= 5, "Fixture should contain multiple games"


class TestSyncGamesHaveValidDates:
    """Tests that synced games have correctly parsed dates."""

    def test_no_dates_equal_to_today(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test that no game dates fall back to today's date."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        today = datetime.now().date()

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            # Game date should not be today (that would indicate fallback)
            game_date = synced_game.game_date.date()
            assert game_date != today, (
                f"Game {synced_game.external_ids.get('winner')} has "
                f"today's date ({today}), indicating fallback parsing"
            )

        test_db.commit()

    def test_dates_match_api_response(
        self,
        winner_mapper: WinnerMapper,
        games_all_response: list,
    ) -> None:
        """Test parsed dates match the API game_date_txt values."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            game_date_txt = game_data.get("game_date_txt", "")

            if game_date_txt:
                # Parse expected date from DD/MM/YYYY format
                parts = game_date_txt.split("/")
                expected_day = int(parts[0])
                expected_month = int(parts[1])
                expected_year = int(parts[2])

                assert raw_game.game_date.year == expected_year
                assert raw_game.game_date.month == expected_month
                assert raw_game.game_date.day == expected_day

    def test_all_dates_in_season_range(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test all game dates fall within expected season range."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        # 2025-26 season should have games between Sep 2025 and Jun 2026
        earliest_expected = date(2025, 9, 1)
        latest_expected = date(2026, 6, 30)

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            game_date = raw_game.game_date.date()

            assert (
                game_date >= earliest_expected
            ), f"Game date {game_date} is before season start {earliest_expected}"
            assert (
                game_date <= latest_expected
            ), f"Game date {game_date} is after season end {latest_expected}"


class TestSyncGamesHaveValidTeams:
    """Tests that synced games have valid team references."""

    def test_all_games_have_home_team(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test all synced games have a valid home team."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            assert synced_game.home_team_id is not None
            # Verify team exists
            home_team = (
                test_db.query(Team).filter_by(id=synced_game.home_team_id).first()
            )
            assert home_team is not None

        test_db.commit()

    def test_all_games_have_away_team(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test all synced games have a valid away team."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            assert synced_game.away_team_id is not None
            # Verify team exists
            away_team = (
                test_db.query(Team).filter_by(id=synced_game.away_team_id).first()
            )
            assert away_team is not None

        test_db.commit()

    def test_home_and_away_teams_are_different(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test home and away teams are different for each game."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            assert (
                synced_game.home_team_id != synced_game.away_team_id
            ), f"Game has same home and away team: {synced_game.home_team_id}"

        test_db.commit()


class TestResyncIsIdempotent:
    """Tests that re-syncing doesn't create duplicates."""

    def test_resync_produces_same_count(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test syncing twice produces same game count."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        # First sync
        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            game_syncer.sync_game(raw_game, season.id, "winner")
        test_db.commit()

        first_sync_count = test_db.query(Game).count()

        # Second sync (same data)
        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            game_syncer.sync_game(raw_game, season.id, "winner")
        test_db.commit()

        second_sync_count = test_db.query(Game).count()

        assert second_sync_count == first_sync_count

    def test_resync_preserves_game_ids(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test re-syncing preserves existing game UUIDs."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        # First sync - collect game IDs
        first_sync_ids = {}
        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")
            first_sync_ids[raw_game.external_id] = synced_game.id
        test_db.commit()

        # Second sync - verify same IDs
        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            expected_id = first_sync_ids[raw_game.external_id]
            assert synced_game.id == expected_id, (
                f"Game {raw_game.external_id} ID changed from "
                f"{expected_id} to {synced_game.id}"
            )

    def test_resync_three_times_still_idempotent(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test three syncs still produce consistent results."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        # Sync three times
        for _ in range(3):
            for game_data in raw_games:
                raw_game = winner_mapper.map_game(game_data)
                game_syncer.sync_game(raw_game, season.id, "winner")
            test_db.commit()

        # Should still have same count as fixtures
        final_count = test_db.query(Game).count()
        assert final_count == len(raw_games)


class TestSyncGamesHaveCorrectScores:
    """Tests that synced games have correct score values."""

    def test_completed_games_have_scores(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test completed games have both scores populated."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            if synced_game.status == "FINAL":
                assert synced_game.home_score is not None, (
                    f"Final game {synced_game.external_ids.get('winner')} "
                    "has null home_score"
                )
                assert synced_game.away_score is not None, (
                    f"Final game {synced_game.external_ids.get('winner')} "
                    "has null away_score"
                )

        test_db.commit()

    def test_scores_match_api_values(
        self,
        winner_mapper: WinnerMapper,
        game_syncer: GameSyncer,
        season: Season,
        all_teams: dict[str, Team],
        games_all_response: list,
        test_db: Session,
    ) -> None:
        """Test synced scores match API response values."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )
        raw_games = data.get("games", [])

        for game_data in raw_games:
            raw_game = winner_mapper.map_game(game_data)
            synced_game = game_syncer.sync_game(raw_game, season.id, "winner")

            expected_home = game_data.get("score_team1")
            expected_away = game_data.get("score_team2")

            assert synced_game.home_score == expected_home
            assert synced_game.away_score == expected_away

        test_db.commit()


class TestExtractTeamsFromGamesAll:
    """Tests for extracting teams from games_all response."""

    def test_extracts_all_unique_teams(
        self,
        winner_mapper: WinnerMapper,
        games_all_response: list,
    ) -> None:
        """Test all unique teams are extracted from games."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )

        teams = winner_mapper.extract_teams_from_games(data)

        # Should have multiple teams
        assert len(teams) >= 2

        # All should have external_ids
        for team in teams:
            assert team.external_id
            assert team.name

    def test_no_duplicate_teams(
        self,
        winner_mapper: WinnerMapper,
        games_all_response: list,
    ) -> None:
        """Test no duplicate teams in extracted list."""
        data = (
            games_all_response[0]
            if isinstance(games_all_response, list)
            else games_all_response
        )

        teams = winner_mapper.extract_teams_from_games(data)

        team_ids = [t.external_id for t in teams]
        unique_ids = set(team_ids)

        assert len(team_ids) == len(unique_ids), "Duplicate teams found"
