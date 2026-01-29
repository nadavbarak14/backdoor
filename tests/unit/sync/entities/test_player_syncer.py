"""
Tests for PlayerSyncer cross-source deduplication.

Tests cover:
- Matching existing players on team roster by name
- Merging external_ids when matching across sources
- Creating new players when no roster match exists
- Handling name format variations (LASTNAME, FIRSTNAME vs FIRSTNAME LASTNAME)
"""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.sync.deduplication import PlayerDeduplicator
from src.sync.entities.player import PlayerSyncer
from src.sync.types import RawPlayerStats


@pytest.fixture
def league(test_db: Session) -> League:
    """Create a test league."""
    league = League(
        id=uuid4(),
        name="Test League",
        code="TST",
        country="Test Country",
    )
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def season(test_db: Session, league: League) -> Season:
    """Create a test season."""
    season = Season(
        id=uuid4(),
        league_id=league.id,
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 6, 30),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def team(test_db: Session) -> Team:
    """Create a test team."""
    team = Team(
        id=uuid4(),
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "mta-123", "euroleague": "MTA"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def existing_player(test_db: Session, team: Team, season: Season) -> Player:
    """Create an existing player on the team roster (from Winner League)."""
    player = Player(
        id=uuid4(),
        first_name="Jeff",
        last_name="Downtin",
        external_ids={"winner": "jeff-downtin-winner"},
    )
    test_db.add(player)
    test_db.flush()

    # Create team history (roster entry)
    history = PlayerTeamHistory(
        player_id=player.id,
        team_id=team.id,
        season_id=season.id,
        jersey_number=5,
    )
    test_db.add(history)
    test_db.commit()
    return player


@pytest.fixture
def player_deduplicator(test_db: Session) -> PlayerDeduplicator:
    """Create a PlayerDeduplicator instance."""
    return PlayerDeduplicator(test_db)


@pytest.fixture
def player_syncer(
    test_db: Session, player_deduplicator: PlayerDeduplicator
) -> PlayerSyncer:
    """Create a PlayerSyncer instance."""
    return PlayerSyncer(test_db, player_deduplicator)


class TestSyncPlayerFromStatsTeamRosterMatch:
    """Tests for matching players by team roster name."""

    def test_matches_existing_player_on_team_by_name(
        self,
        player_syncer: PlayerSyncer,
        existing_player: Player,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should match existing player on team by normalized name."""
        # Simulate Euroleague boxscore with same player name but different format
        raw_stats = RawPlayerStats(
            player_external_id="PJDO",  # Euroleague external ID
            player_name="DOWNTIN, JEFF",  # Euroleague format: LASTNAME, FIRSTNAME
            team_external_id="MTA",
            minutes_played=1800,
            is_starter=True,
            points=15,
            field_goals_made=5,
            field_goals_attempted=10,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        # Should return the existing player, not create a new one
        assert matched_player is not None
        assert matched_player.id == existing_player.id
        assert matched_player.full_name == "Jeff Downtin"

    def test_merges_external_id_when_matching(
        self,
        player_syncer: PlayerSyncer,
        existing_player: Player,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should add external_id from new source when matching."""
        raw_stats = RawPlayerStats(
            player_external_id="PJDO",
            player_name="DOWNTIN, JEFF",
            team_external_id="MTA",
            minutes_played=1800,
            is_starter=True,
            points=15,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        # Should have both external_ids
        assert matched_player is not None
        assert "winner" in matched_player.external_ids
        assert "euroleague" in matched_player.external_ids
        assert matched_player.external_ids["winner"] == "jeff-downtin-winner"
        assert matched_player.external_ids["euroleague"] == "PJDO"

    def test_creates_new_when_no_team_roster_match(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should create new player when no roster match exists."""
        # New player not on the roster
        raw_stats = RawPlayerStats(
            player_external_id="PNEW",
            player_name="NEW, PLAYER",
            team_external_id="MTA",
            minutes_played=1200,
            is_starter=False,
            points=8,
        )

        new_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        assert new_player is not None
        assert new_player.first_name == "PLAYER"
        assert new_player.last_name == "NEW"
        assert new_player.external_ids == {"euroleague": "PNEW"}

    def test_returns_existing_by_external_id_first(
        self,
        player_syncer: PlayerSyncer,
        existing_player: Player,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should return existing player by external_id without checking roster."""
        # Add euroleague external_id to existing player
        existing_player.external_ids = {
            "winner": "jeff-downtin-winner",
            "euroleague": "PJDO",
        }
        test_db.commit()

        raw_stats = RawPlayerStats(
            player_external_id="PJDO",  # Same external_id
            player_name="DOWNTIN, JEFF",
            team_external_id="MTA",
            minutes_played=1800,
            points=15,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        assert matched_player is not None
        assert matched_player.id == existing_player.id


class TestNameFormatHandling:
    """Tests for handling various name formats."""

    def test_parse_lastname_firstname_format(
        self,
        player_syncer: PlayerSyncer,
    ) -> None:
        """Should parse LASTNAME, FIRSTNAME format correctly."""
        result = player_syncer._parse_player_name("DOWNTIN, JEFF")
        assert result == "JEFF DOWNTIN"

    def test_parse_firstname_lastname_format(
        self,
        player_syncer: PlayerSyncer,
    ) -> None:
        """Should return FIRSTNAME LASTNAME format unchanged."""
        result = player_syncer._parse_player_name("Jeff Downtin")
        assert result == "Jeff Downtin"

    def test_parse_single_name(
        self,
        player_syncer: PlayerSyncer,
    ) -> None:
        """Should handle single name (no comma, no space)."""
        result = player_syncer._parse_player_name("Neymar")
        assert result == "Neymar"

    def test_parse_empty_string(
        self,
        player_syncer: PlayerSyncer,
    ) -> None:
        """Should handle empty string."""
        result = player_syncer._parse_player_name("")
        assert result == ""

    def test_matches_with_case_insensitive_name(
        self,
        player_syncer: PlayerSyncer,
        existing_player: Player,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should match names case-insensitively."""
        raw_stats = RawPlayerStats(
            player_external_id="PJDO",
            player_name="downtin, jeff",  # All lowercase
            team_external_id="MTA",
            minutes_played=1800,
            points=15,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        assert matched_player is not None
        assert matched_player.id == existing_player.id


class TestJerseyNumberFallback:
    """Tests for jersey number matching fallback."""

    def test_falls_back_to_jersey_when_no_name(
        self,
        player_syncer: PlayerSyncer,
        existing_player: Player,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should match by jersey number when no name/external_id."""
        raw_stats = RawPlayerStats(
            player_external_id=None,
            player_name=None,
            team_external_id="MTA",
            jersey_number="5",  # Same as existing_player
            minutes_played=1800,
            points=15,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source=None,  # No source, so jersey fallback
        )

        assert matched_player is not None
        assert matched_player.id == existing_player.id

    def test_returns_none_when_no_match(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should return None when no match possible."""
        raw_stats = RawPlayerStats(
            player_external_id=None,
            player_name=None,
            team_external_id="MTA",
            jersey_number="99",  # Non-existent jersey
            minutes_played=1800,
            points=15,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source=None,
        )

        assert matched_player is None


class TestTeamHistoryCreation:
    """Tests for team history creation on new players."""

    def test_creates_team_history_for_new_player(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should create team history when creating new player."""
        raw_stats = RawPlayerStats(
            player_external_id="PNEW",
            player_name="NEW, PLAYER",
            team_external_id="MTA",
            minutes_played=1200,
            points=8,
        )

        new_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        # Check team history was created
        histories = (
            test_db.query(PlayerTeamHistory).filter_by(player_id=new_player.id).all()
        )

        assert len(histories) == 1
        assert histories[0].team_id == team.id
        assert histories[0].season_id == season.id


class TestBirthdateMatching:
    """Tests for birthdate-based cross-source player matching."""

    def test_matches_by_birthdate_and_name_similarity(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should match player by birthdate + name similarity across sources."""
        # Create a player from Winner League (no team history needed)
        winner_player = Player(
            first_name="Jeff",
            last_name="Downtin",
            birth_date=date(1994, 7, 18),
            external_ids={"winner": "jeff-winner-123"},
        )
        test_db.add(winner_player)
        test_db.commit()

        # Euroleague boxscore with same player (different name format)
        raw_stats = RawPlayerStats(
            player_external_id="PJDO",
            player_name="DOWNTIN, JEFF",  # Euroleague format
            team_external_id="MTA",
            birth_date=date(1994, 7, 18),  # Same birthdate
            minutes_played=1800,
            points=15,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        # Should match the existing Winner player, not create a new one
        assert matched_player is not None
        assert matched_player.id == winner_player.id
        assert "euroleague" in matched_player.external_ids
        assert matched_player.external_ids["euroleague"] == "PJDO"

    def test_does_not_match_different_birthdate(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should not match players with different birthdates even if similar name."""
        # Create a player from Winner League
        winner_player = Player(
            first_name="Jeff",
            last_name="Downtin",
            birth_date=date(1994, 7, 18),  # July 18, 1994
            external_ids={"winner": "jeff-winner-123"},
        )
        test_db.add(winner_player)
        test_db.commit()

        # Euroleague boxscore with different birthdate
        raw_stats = RawPlayerStats(
            player_external_id="POTHER",
            player_name="DOWNTIN, JEFF",
            team_external_id="MTA",
            birth_date=date(1995, 3, 22),  # Different birthdate
            minutes_played=1800,
            points=15,
        )

        new_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        # Should create a new player, not match the existing one
        assert new_player is not None
        assert new_player.id != winner_player.id
        assert new_player.external_ids == {"euroleague": "POTHER"}

    def test_birthdate_matching_with_similar_names(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should match players with slight name variations but same birthdate."""
        # Create player with slightly different spelling
        winner_player = Player(
            first_name="Scottie",
            last_name="Wilbekin",
            birth_date=date(1993, 7, 19),
            external_ids={"winner": "scottie-123"},
        )
        test_db.add(winner_player)
        test_db.commit()

        # Euroleague with "Scott" instead of "Scottie"
        raw_stats = RawPlayerStats(
            player_external_id="PSWB",
            player_name="WILBEKIN, SCOTT",  # Slightly different first name
            team_external_id="MTA",
            birth_date=date(1993, 7, 19),  # Same birthdate
            minutes_played=2100,
            points=22,
        )

        matched_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        # Should match by birthdate even with name variation
        assert matched_player is not None
        assert matched_player.id == winner_player.id

    def test_saves_birthdate_when_creating_new_player(
        self,
        player_syncer: PlayerSyncer,
        team: Team,
        season: Season,
        test_db: Session,
    ) -> None:
        """Should save birthdate when creating new player from boxscore."""
        raw_stats = RawPlayerStats(
            player_external_id="PNEW",
            player_name="NEW, PLAYER",
            team_external_id="MTA",
            birth_date=date(1998, 5, 10),
            minutes_played=1200,
            points=8,
        )

        new_player = player_syncer.sync_player_from_stats(
            raw=raw_stats,
            team_id=team.id,
            season_id=season.id,
            source="euroleague",
        )

        assert new_player is not None
        assert new_player.birth_date == date(1998, 5, 10)
