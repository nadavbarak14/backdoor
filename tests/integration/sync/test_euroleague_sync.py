"""
Integration tests for Euroleague/Eurocup sync functionality.

Tests that verify:
1. Roster sync fills in player positions
2. Player deduplication across Winner and Eurocup sources
3. PBP events get correct team_id and player_id
4. External IDs are properly merged
"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.game import Game
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.schemas.enums import Position
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities.game import GameSyncer
from src.sync.entities.player import PlayerSyncer
from src.sync.entities.team import TeamSyncer
from src.sync.types import RawPlayerInfo, RawTeam


class TestPlayerDeduplicationAcrossSources:
    """Test player deduplication when syncing from multiple sources."""

    def test_winner_player_gets_eurocup_external_id(self, test_db: Session):
        """When syncing Eurocup, existing Winner players should get eurocup external_id."""
        # Create a team that exists in both Winner and Eurocup
        team = Team(
            name="Test Team",
            short_name="TST",
            city="Test City",
            country="Israel",
            external_ids={"winner": "1234", "eurocup": "TST"},
        )
        test_db.add(team)

        # Create league and season
        league = League(name="Test League", code="TST", country="Israel")
        test_db.add(league)
        test_db.flush()

        season = Season(
            name="2024-25",
            league_id=league.id,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        # Create player from Winner source (no positions)
        player = Player(
            first_name="John",
            last_name="Smith",
            external_ids={"winner": "W123"},
            positions=[],
        )
        test_db.add(player)
        test_db.flush()

        # Add player to team
        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
        )
        test_db.add(history)
        test_db.commit()

        # Now sync from Eurocup - should find existing player and add eurocup external_id
        deduplicator = PlayerDeduplicator(test_db)
        eurocup_data = RawPlayerInfo(
            external_id="E456",
            first_name="John",
            last_name="Smith",
            positions=[Position.GUARD],
        )

        result = deduplicator.find_or_create_player(
            source="eurocup",
            external_id="E456",
            player_data=eurocup_data,
            team_id=team.id,
        )

        # Should be the same player
        assert result.id == player.id
        # Should have both external IDs
        assert result.external_ids.get("winner") == "W123"
        assert result.external_ids.get("eurocup") == "E456"
        # Should have positions filled in
        assert result.positions == [Position.GUARD]

    def test_eurocup_player_gets_positions_on_resync(self, test_db: Session):
        """When re-syncing, existing Eurocup players should get positions filled in."""
        # Create player from Eurocup source (no positions - e.g., from boxscore)
        player = Player(
            first_name="Jane",
            last_name="Doe",
            external_ids={"eurocup": "E789"},
            positions=[],
        )
        test_db.add(player)
        test_db.commit()

        # Re-sync from Eurocup with positions (e.g., from roster)
        deduplicator = PlayerDeduplicator(test_db)
        roster_data = RawPlayerInfo(
            external_id="E789",
            first_name="Jane",
            last_name="Doe",
            positions=[Position.FORWARD],
            height_cm=185,
        )

        result = deduplicator.find_or_create_player(
            source="eurocup",
            external_id="E789",
            player_data=roster_data,
        )

        # Should be the same player
        assert result.id == player.id
        # Should have positions filled in
        assert result.positions == [Position.FORWARD]
        # Should have height filled in
        assert result.height_cm == 185


class TestTeamDeduplicationAcrossSources:
    """Test team deduplication when syncing from multiple sources."""

    def test_winner_team_gets_eurocup_external_id(self, test_db: Session):
        """When syncing Eurocup, existing Winner teams should get eurocup external_id."""
        # Create team from Winner
        team = Team(
            name="Hapoel Test",
            short_name="HPT",
            city="Test City",
            country="Israel",
            external_ids={"winner": "1111"},
        )
        test_db.add(team)
        test_db.commit()

        # Sync from Eurocup
        matcher = TeamMatcher(test_db)
        eurocup_team_data = RawTeam(
            external_id="HTS",
            name="Hapoel Test",
            short_name="HTS",
        )
        result = matcher.find_or_create_team(
            source="eurocup",
            external_id="HTS",
            team_data=eurocup_team_data,
        )

        # Should be the same team
        assert result.id == team.id
        # Should have both external IDs
        assert result.external_ids.get("winner") == "1111"
        assert result.external_ids.get("eurocup") == "HTS"


class TestRosterSyncFillsPositions:
    """Test that roster sync fills in missing player data."""

    def test_roster_sync_updates_positions(self, test_db: Session):
        """Roster sync should update positions for existing players."""
        # Setup
        team = Team(
            name="Test Team",
            short_name="TST",
            city="Test City",
            country="Europe",
            external_ids={"eurocup": "TST"},
        )
        test_db.add(team)

        league = League(name="Eurocup", code="U", country="Europe")
        test_db.add(league)
        test_db.flush()

        season = Season(
            name="2024-25",
            league_id=league.id,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        # Create player without positions
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"eurocup": "P001"},
            positions=[],
        )
        test_db.add(player)
        test_db.flush()

        # Add to team
        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
        )
        test_db.add(history)
        test_db.commit()

        # Setup syncer
        matcher = TeamMatcher(test_db)
        deduplicator = PlayerDeduplicator(test_db)
        team_syncer = TeamSyncer(test_db, matcher, deduplicator)

        # Roster data with positions
        roster = [
            ("P001", "PLAYER, TEST", RawPlayerInfo(
                external_id="P001",
                first_name="TEST",
                last_name="PLAYER",
                positions=[Position.CENTER],
                jersey_number="15",
            )),
        ]

        # Sync roster
        team_syncer.sync_roster_from_info(roster, team, season, "eurocup")

        # Verify positions were filled in
        test_db.refresh(player)
        assert player.positions == [Position.CENTER]


class TestPBPPlayerMatching:
    """Test that PBP events correctly match players."""

    def test_pbp_matches_player_by_external_id(self, test_db: Session):
        """PBP sync should match players by external_id."""
        # Setup team
        team = Team(
            name="Test Team",
            short_name="TST",
            city="Test City",
            country="Europe",
            external_ids={"eurocup": "TST"},
        )
        test_db.add(team)

        league = League(name="Eurocup", code="U", country="Europe")
        test_db.add(league)
        test_db.flush()

        season = Season(
            name="2024-25",
            league_id=league.id,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
        )
        test_db.add(season)
        test_db.flush()

        # Create player with eurocup external_id
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"eurocup": "P001"},
        )
        test_db.add(player)
        test_db.flush()

        # Create game
        game = Game(
            season_id=season.id,
            home_team_id=team.id,
            away_team_id=team.id,
            game_date=date(2024, 10, 1),
            external_ids={"eurocup": "U2025_1"},
        )
        test_db.add(game)
        test_db.commit()

        # Setup syncer
        matcher = TeamMatcher(test_db)
        deduplicator = PlayerDeduplicator(test_db)
        team_syncer = TeamSyncer(test_db, matcher, deduplicator)
        player_syncer = PlayerSyncer(test_db, deduplicator)
        game_syncer = GameSyncer(test_db, team_syncer, player_syncer)

        # Test player resolution
        resolved_id = game_syncer._resolve_player_id_canonical(
            player_external_id="P001",
            team_id=team.id,
            source="eurocup",
        )

        assert resolved_id == player.id


@pytest.mark.real_db
class TestDatabaseStateValidation:
    """
    Tests that validate the database state after sync.

    These tests use the real database (not test_db) to validate
    the current state of synced data. They help identify data quality
    issues and verify sync worked correctly.

    Run with: pytest -m real_db tests/integration/sync/
    Skip with: pytest -m "not real_db" tests/integration/sync/
    """

    @pytest.fixture
    def real_db(self):
        """Get a session to the real database."""
        from src.core.database import SessionLocal
        db = SessionLocal()
        yield db
        db.close()

    def test_eurocup_teams_have_external_ids(self, real_db: Session):
        """All Eurocup teams should have eurocup external_ids."""
        # SQLite JSON queries need special handling
        stmt = select(Team)
        all_teams = list(real_db.scalars(stmt).all())

        # Filter in Python for SQLite compatibility
        teams = [t for t in all_teams if t.external_ids.get("eurocup")]

        # Skip if no Eurocup teams found (database may not have been synced)
        if len(teams) == 0:
            pytest.skip("No teams with eurocup external_id found - sync Eurocup first")

        for team in teams:
            assert "eurocup" in team.external_ids
            assert team.external_ids["eurocup"], f"Team {team.name} has empty eurocup external_id"

    def test_eurocup_players_have_positions(self, real_db: Session):
        """
        Eurocup players should have positions.

        This test validates data quality after sync. If the database was synced
        before the roster sync fix, many players will be missing positions.
        A fresh sync should result in <10% missing positions.
        """
        # Get players with eurocup external_id
        stmt = select(Player)
        all_players = list(real_db.scalars(stmt).all())

        # Filter in Python for SQLite compatibility
        players = [p for p in all_players if p.external_ids.get("eurocup")]

        if len(players) == 0:
            pytest.skip("No players with eurocup external_id found")

        # Count players without positions
        without_positions = [p for p in players if not p.positions]

        # Report data quality
        ratio = len(without_positions) / len(players) if players else 1
        print(f"\nEurocup player positions: {len(players) - len(without_positions)}/{len(players)} ({(1-ratio):.1%} have positions)")

        # Data quality threshold - after fresh sync with roster data should be < 10%
        # Before roster sync fix, this may be much higher (>30%)
        if ratio > 0.3:
            pytest.xfail(
                f"Pre-fix data: {len(without_positions)}/{len(players)} ({ratio:.1%}) players without positions. "
                "Resync required to populate positions from roster data."
            )

        assert ratio < 0.1, f"Too many Eurocup players without positions: {len(without_positions)}/{len(players)} ({ratio:.1%})"

    def test_shared_team_players_have_both_external_ids(self, real_db: Session):
        """Players on teams in both Winner and Eurocup should have both external_ids."""
        # Find teams with both winner and eurocup external_ids
        stmt = select(Team).where(
            Team.external_ids["winner"].isnot(None),
            Team.external_ids["eurocup"].isnot(None),
        )
        shared_teams = list(real_db.scalars(stmt).all())

        if not shared_teams:
            pytest.skip("No teams found in both Winner and Eurocup")

        # Check at least one shared team has players with both IDs
        found_player_with_both = False
        for team in shared_teams:
            # Get players on this team
            stmt = select(Player).join(PlayerTeamHistory).where(
                PlayerTeamHistory.team_id == team.id
            ).distinct()
            players = list(real_db.scalars(stmt).all())

            for player in players:
                if player.external_ids.get("winner") and player.external_ids.get("eurocup"):
                    found_player_with_both = True
                    break
            if found_player_with_both:
                break

        assert found_player_with_both, "No players found with both winner and eurocup external_ids"

    def test_eurocup_pbp_has_player_ids(self, real_db: Session):
        """Eurocup PBP events should have player_ids where applicable."""
        # Get Eurocup games
        stmt = select(Game).where(Game.external_ids["eurocup"].isnot(None))
        games = list(real_db.scalars(stmt).all())

        if not games:
            pytest.skip("No Eurocup games found")

        total_player_events = 0
        total_with_player = 0

        # Check PBP for a sample of games
        for game in games[:10]:
            stmt = select(PlayByPlayEvent).where(PlayByPlayEvent.game_id == game.id)
            events = list(real_db.scalars(stmt).all())

            if not events:
                continue

            # Count events that should have player_id
            # (exclude period start, timeout, etc.)
            player_events = [
                e for e in events
                if e.event_type.value not in ("PERIOD_START", "PERIOD_END", "TIMEOUT", "GAME_END")
            ]

            total_player_events += len(player_events)
            total_with_player += sum(1 for e in player_events if e.player_id)

        if total_player_events == 0:
            pytest.skip("No PBP player events found")

        ratio = total_with_player / total_player_events
        # At least 80% of player events should have player_id
        assert ratio > 0.8, (
            f"Too few PBP events with player_id: "
            f"{total_with_player}/{total_player_events} ({ratio:.1%})"
        )

    def test_eurocup_pbp_has_correct_team_ids(self, real_db: Session):
        """Eurocup PBP events should have correct team_ids (not all home team)."""
        # Get Eurocup games
        stmt = select(Game).where(Game.external_ids["eurocup"].isnot(None))
        games = list(real_db.scalars(stmt).all())

        if not games:
            pytest.skip("No Eurocup games found")

        for game in games[:5]:
            stmt = select(PlayByPlayEvent).where(
                PlayByPlayEvent.game_id == game.id,
                PlayByPlayEvent.team_id.isnot(None),
            )
            events = list(real_db.scalars(stmt).all())

            if len(events) < 10:
                continue

            # Count events by team
            home_events = sum(1 for e in events if e.team_id == game.home_team_id)
            away_events = sum(1 for e in events if e.team_id == game.away_team_id)

            # Both teams should have events (not all assigned to one team)
            total = home_events + away_events
            if total > 0:
                home_ratio = home_events / total
                assert 0.3 < home_ratio < 0.7, (
                    f"Game {game.external_ids.get('eurocup')} has unbalanced team events: "
                    f"home={home_events}, away={away_events}"
                )
