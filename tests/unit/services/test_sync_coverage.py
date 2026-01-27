"""
Unit tests for SyncCoverageService.

Tests sync coverage tracking operations including:
- get_season_coverage: Per-season sync statistics
- get_all_seasons_coverage: All seasons statistics
- get_games_missing_boxscore: Games without PlayerGameStats
- get_games_missing_pbp: Games without PlayByPlayEvent
- get_players_missing_bio: Players without position/height
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.services.sync_coverage import SyncCoverageService


@pytest.fixture
def league(test_db: Session) -> League:
    """Create a test league."""
    league = League(name="Test League", code="TL", country="Test")
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def season(test_db: Session, league: League) -> Season:
    """Create a test season."""
    season = Season(
        league_id=league.id,
        name="2024-25",
        start_date=datetime(2024, 10, 1, tzinfo=UTC),
        end_date=datetime(2025, 6, 30, tzinfo=UTC),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def teams(test_db: Session) -> tuple[Team, Team]:
    """Create two test teams."""
    team1 = Team(name="Team A", short_name="TA", city="City A", country="Test")
    team2 = Team(name="Team B", short_name="TB", city="City B", country="Test")
    test_db.add_all([team1, team2])
    test_db.commit()
    return team1, team2


@pytest.fixture
def players(test_db: Session) -> list[Player]:
    """Create test players."""
    players = [
        Player(
            first_name=f"Player{i}",
            last_name=f"Test{i}",
            position="PG" if i % 2 == 0 else None,
            height_cm=180 if i % 3 == 0 else None,
        )
        for i in range(5)
    ]
    test_db.add_all(players)
    test_db.commit()
    return players


class TestSyncCoverageService:
    """Tests for SyncCoverageService."""

    def test_get_season_coverage_empty(self, test_db: Session, season: Season):
        """Test coverage for season with no data."""
        service = SyncCoverageService(test_db)

        coverage = service.get_season_coverage(season.id)

        assert coverage is not None
        assert coverage.season_id == season.id
        assert coverage.season_name == "2024-25"
        assert coverage.games_total == 0
        assert coverage.games_with_boxscore == 0
        assert coverage.games_with_pbp == 0
        assert coverage.players_total == 0
        assert coverage.players_with_bio == 0
        assert coverage.boxscore_pct == 0.0
        assert coverage.pbp_pct == 0.0
        assert coverage.bio_pct == 0.0

    def test_get_season_coverage_not_found(self, test_db: Session):
        """Test coverage for non-existent season returns None."""
        service = SyncCoverageService(test_db)
        fake_id = uuid.uuid4()

        coverage = service.get_season_coverage(fake_id)

        assert coverage is None

    def test_get_season_coverage_with_games(
        self, test_db: Session, season: Season, teams: tuple[Team, Team]
    ):
        """Test coverage counts FINAL games correctly."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create games with different statuses
        game_final = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 15, tzinfo=UTC),
            status="FINAL",
            home_score=100,
            away_score=95,
        )
        game_scheduled = Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 11, 15, tzinfo=UTC),
            status="SCHEDULED",
        )
        test_db.add_all([game_final, game_scheduled])
        test_db.commit()

        coverage = service.get_season_coverage(season.id)

        # Only FINAL games should be counted
        assert coverage.games_total == 1

    def test_get_season_coverage_with_boxscore(
        self,
        test_db: Session,
        season: Season,
        teams: tuple[Team, Team],
        players: list[Player],
    ):
        """Test coverage counts games with boxscore data."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create two FINAL games
        game1 = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 15, tzinfo=UTC),
            status="FINAL",
            home_score=100,
            away_score=95,
        )
        game2 = Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 10, 20, tzinfo=UTC),
            status="FINAL",
            home_score=110,
            away_score=105,
        )
        test_db.add_all([game1, game2])
        test_db.commit()

        # Add boxscore to only game1
        stat = PlayerGameStats(
            game_id=game1.id,
            player_id=players[0].id,
            team_id=team1.id,
            points=20,
        )
        test_db.add(stat)
        test_db.commit()

        coverage = service.get_season_coverage(season.id)

        assert coverage.games_total == 2
        assert coverage.games_with_boxscore == 1
        assert coverage.boxscore_pct == 50.0

    def test_get_season_coverage_with_pbp(
        self,
        test_db: Session,
        season: Season,
        teams: tuple[Team, Team],
        players: list[Player],
    ):
        """Test coverage counts games with play-by-play data."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create two FINAL games
        game1 = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 15, tzinfo=UTC),
            status="FINAL",
            home_score=100,
            away_score=95,
        )
        game2 = Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 10, 20, tzinfo=UTC),
            status="FINAL",
            home_score=110,
            away_score=105,
        )
        test_db.add_all([game1, game2])
        test_db.commit()

        # Add PBP to only game1
        event = PlayByPlayEvent(
            game_id=game1.id,
            event_number=1,
            period=1,
            clock="10:00",
            event_type="SHOT",
            team_id=team1.id,
            player_id=players[0].id,
        )
        test_db.add(event)
        test_db.commit()

        coverage = service.get_season_coverage(season.id)

        assert coverage.games_total == 2
        assert coverage.games_with_pbp == 1
        assert coverage.pbp_pct == 50.0

    def test_get_season_coverage_with_players(
        self, test_db: Session, season: Season, players: list[Player]
    ):
        """Test coverage counts players in season via PlayerTeamHistory."""
        service = SyncCoverageService(test_db)

        # Create a dummy team for player history
        team = Team(name="Team X", short_name="TX", city="City X", country="Test")
        test_db.add(team)
        test_db.commit()

        # Add some players to this season
        for player in players[:3]:
            history = PlayerTeamHistory(
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
            )
            test_db.add(history)
        test_db.commit()

        coverage = service.get_season_coverage(season.id)

        assert coverage.players_total == 3
        # Players with bio: Player0 has position, Player2 has position
        # (position: 0,2 have PG; height: 0,3 have 180cm, but player3 not in season)
        # So player0 has both, player1 has neither, player2 has position only
        assert coverage.players_with_bio == 2
        assert coverage.bio_pct == pytest.approx(66.7, rel=0.1)

    def test_get_all_seasons_coverage(self, test_db: Session, league: League):
        """Test getting coverage for all seasons."""
        service = SyncCoverageService(test_db)

        # Create multiple seasons
        season1 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=datetime(2023, 10, 1, tzinfo=UTC),
            end_date=datetime(2024, 6, 30, tzinfo=UTC),
        )
        season2 = Season(
            league_id=league.id,
            name="2024-25",
            start_date=datetime(2024, 10, 1, tzinfo=UTC),
            end_date=datetime(2025, 6, 30, tzinfo=UTC),
        )
        test_db.add_all([season1, season2])
        test_db.commit()

        coverage_list = service.get_all_seasons_coverage()

        assert len(coverage_list) == 2
        # Ordered by season name descending
        assert coverage_list[0].season_name == "2024-25"
        assert coverage_list[1].season_name == "2023-24"

    def test_get_games_missing_boxscore(
        self,
        test_db: Session,
        season: Season,
        teams: tuple[Team, Team],
        players: list[Player],
    ):
        """Test finding games without boxscore data."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create three FINAL games
        game1 = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 15, tzinfo=UTC),
            status="FINAL",
            home_score=100,
            away_score=95,
        )
        game2 = Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 10, 20, tzinfo=UTC),
            status="FINAL",
            home_score=110,
            away_score=105,
        )
        game3 = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 25, tzinfo=UTC),
            status="FINAL",
            home_score=108,
            away_score=102,
        )
        test_db.add_all([game1, game2, game3])
        test_db.commit()

        # Add boxscore to game1 only
        stat = PlayerGameStats(
            game_id=game1.id,
            player_id=players[0].id,
            team_id=team1.id,
            points=20,
        )
        test_db.add(stat)
        test_db.commit()

        missing = service.get_games_missing_boxscore(season.id)

        assert len(missing) == 2
        game_ids = {g.id for g in missing}
        assert game2.id in game_ids
        assert game3.id in game_ids
        assert game1.id not in game_ids

    def test_get_games_missing_boxscore_excludes_scheduled(
        self, test_db: Session, season: Season, teams: tuple[Team, Team]
    ):
        """Test that scheduled games are not in missing boxscore list."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create a SCHEDULED game (shouldn't be in missing list)
        game = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 12, 15, tzinfo=UTC),
            status="SCHEDULED",
        )
        test_db.add(game)
        test_db.commit()

        missing = service.get_games_missing_boxscore(season.id)

        assert len(missing) == 0

    def test_get_games_missing_pbp(
        self,
        test_db: Session,
        season: Season,
        teams: tuple[Team, Team],
        players: list[Player],
    ):
        """Test finding games without play-by-play data."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create two FINAL games
        game1 = Game(
            season_id=season.id,
            home_team_id=team1.id,
            away_team_id=team2.id,
            game_date=datetime(2024, 10, 15, tzinfo=UTC),
            status="FINAL",
            home_score=100,
            away_score=95,
        )
        game2 = Game(
            season_id=season.id,
            home_team_id=team2.id,
            away_team_id=team1.id,
            game_date=datetime(2024, 10, 20, tzinfo=UTC),
            status="FINAL",
            home_score=110,
            away_score=105,
        )
        test_db.add_all([game1, game2])
        test_db.commit()

        # Add PBP to game1 only
        event = PlayByPlayEvent(
            game_id=game1.id,
            event_number=1,
            period=1,
            clock="10:00",
            event_type="SHOT",
            team_id=team1.id,
            player_id=players[0].id,
        )
        test_db.add(event)
        test_db.commit()

        missing = service.get_games_missing_pbp(season.id)

        assert len(missing) == 1
        assert missing[0].id == game2.id

    def test_get_players_missing_bio(
        self, test_db: Session, season: Season, players: list[Player]
    ):
        """Test finding players without bio data."""
        service = SyncCoverageService(test_db)

        # Create team for player history
        team = Team(name="Team Y", short_name="TY", city="City Y", country="Test")
        test_db.add(team)
        test_db.commit()

        # Add all players to season
        for player in players:
            history = PlayerTeamHistory(
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
            )
            test_db.add(history)
        test_db.commit()

        missing = service.get_players_missing_bio(season.id)

        # Players missing bio = those with position=None AND height_cm=None
        # Player0: position=PG, height=180 -> has bio
        # Player1: position=None, height=None -> missing bio
        # Player2: position=PG, height=None -> has bio (position counts)
        # Player3: position=None, height=180 -> has bio (height counts)
        # Player4: position=PG, height=None -> has bio
        assert len(missing) == 1
        assert missing[0].first_name == "Player1"

    def test_get_players_missing_bio_only_in_season(
        self, test_db: Session, season: Season, players: list[Player]
    ):
        """Test that only players in the season are checked for missing bio."""
        service = SyncCoverageService(test_db)

        # Don't add any players to this season
        missing = service.get_players_missing_bio(season.id)

        # No players in season, so no missing bio
        assert len(missing) == 0

    def test_coverage_percentages(
        self,
        test_db: Session,
        season: Season,
        teams: tuple[Team, Team],
        players: list[Player],
    ):
        """Test that percentage calculations are correct."""
        service = SyncCoverageService(test_db)
        team1, team2 = teams

        # Create 3 FINAL games
        games = []
        for i in range(3):
            game = Game(
                season_id=season.id,
                home_team_id=team1.id,
                away_team_id=team2.id,
                game_date=datetime(2024, 10, 15 + i, tzinfo=UTC),
                status="FINAL",
                home_score=100 + i,
                away_score=95 + i,
            )
            games.append(game)
        test_db.add_all(games)
        test_db.commit()

        # Add boxscore to 2 games
        for game in games[:2]:
            stat = PlayerGameStats(
                game_id=game.id,
                player_id=players[0].id,
                team_id=team1.id,
                points=20,
            )
            test_db.add(stat)

        # Add PBP to 1 game
        event = PlayByPlayEvent(
            game_id=games[0].id,
            event_number=1,
            period=1,
            clock="10:00",
            event_type="SHOT",
            team_id=team1.id,
            player_id=players[0].id,
        )
        test_db.add(event)
        test_db.commit()

        coverage = service.get_season_coverage(season.id)

        assert coverage.games_total == 3
        assert coverage.games_with_boxscore == 2
        assert coverage.games_with_pbp == 1
        assert coverage.boxscore_pct == pytest.approx(66.7, rel=0.1)
        assert coverage.pbp_pct == pytest.approx(33.3, rel=0.1)


class TestSeasonCoverageClass:
    """Tests for SeasonCoverage data class."""

    def test_percentage_with_zero_total(self):
        """Test percentages return 0 when total is 0."""
        from src.services.sync_coverage import SeasonCoverage

        coverage = SeasonCoverage(
            season_id=uuid.uuid4(),
            season_name="2024-25",
            league_name="Test",
            games_total=0,
            games_with_boxscore=0,
            games_with_pbp=0,
            players_total=0,
            players_with_bio=0,
        )

        assert coverage.boxscore_pct == 0.0
        assert coverage.pbp_pct == 0.0
        assert coverage.bio_pct == 0.0

    def test_percentage_calculation(self):
        """Test percentage calculations are correct."""
        from src.services.sync_coverage import SeasonCoverage

        coverage = SeasonCoverage(
            season_id=uuid.uuid4(),
            season_name="2024-25",
            league_name="Test",
            games_total=100,
            games_with_boxscore=75,
            games_with_pbp=50,
            players_total=200,
            players_with_bio=150,
        )

        assert coverage.boxscore_pct == 75.0
        assert coverage.pbp_pct == 50.0
        assert coverage.bio_pct == 75.0
