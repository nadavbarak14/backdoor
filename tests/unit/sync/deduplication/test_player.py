"""
Player Deduplication Tests

Tests for player matching and deduplication across data sources.
"""

from datetime import date

import pytest

from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.sync.deduplication.player import PlayerDeduplicator
from src.sync.types import RawPlayerInfo


@pytest.fixture
def sample_team(test_db):
    """Create a sample team for testing."""
    team = Team(
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "team-123"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def sample_league(test_db):
    """Create a sample league for testing."""
    league = League(
        name="Winner League",
        code="WINNER",
        country="Israel",
    )
    test_db.add(league)
    test_db.commit()
    return league


@pytest.fixture
def sample_season(test_db, sample_league):
    """Create a sample season for testing."""
    season = Season(
        league_id=sample_league.id,
        name="2023-24",
        start_date=date(2023, 10, 1),
        end_date=date(2024, 6, 30),
        is_current=True,
    )
    test_db.add(season)
    test_db.commit()
    return season


@pytest.fixture
def player_on_team(test_db, sample_team, sample_season):
    """Create a player with team history."""
    player = Player(
        first_name="Scottie",
        last_name="Wilbekin",
        birth_date=date(1993, 7, 19),
        height_cm=185,
        position="PG",
        external_ids={"winner": "player-123"},
    )
    test_db.add(player)
    test_db.commit()

    history = PlayerTeamHistory(
        player_id=player.id,
        team_id=sample_team.id,
        season_id=sample_season.id,
        jersey_number=1,
        position="PG",
    )
    test_db.add(history)
    test_db.commit()

    return player


class TestPlayerDeduplicatorFindOrCreate:
    """Tests for PlayerDeduplicator.find_or_create_player method."""

    def test_find_or_create_player_by_external_id(self, test_db, sample_team):
        """Test finding existing player by external_id."""
        # Create player directly
        player = Player(
            first_name="Scottie",
            last_name="Wilbekin",
            external_ids={"winner": "player-123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        found = dedup.find_or_create_player(
            source="winner",
            external_id="player-123",
            player_data=RawPlayerInfo(
                external_id="player-123",
                first_name="Scottie",
                last_name="Wilbekin",
            ),
            team_id=sample_team.id,
        )

        assert found.id == player.id

    def test_find_or_create_player_by_team_name_match(
        self, test_db, sample_team, sample_season, player_on_team
    ):
        """Test matching player on same team by name."""
        dedup = PlayerDeduplicator(test_db)

        # Try to create same player from different source
        found = dedup.find_or_create_player(
            source="euroleague",
            external_id="EL-456",
            player_data=RawPlayerInfo(
                external_id="EL-456",
                first_name="Scottie",
                last_name="Wilbekin",
            ),
            team_id=sample_team.id,
        )

        assert found.id == player_on_team.id
        assert found.external_ids == {"winner": "player-123", "euroleague": "EL-456"}

    def test_find_or_create_player_creates_new(self, test_db, sample_team):
        """Test creating new player when no match found."""
        dedup = PlayerDeduplicator(test_db)

        player = dedup.find_or_create_player(
            source="winner",
            external_id="player-999",
            player_data=RawPlayerInfo(
                external_id="player-999",
                first_name="New",
                last_name="Player",
                position="SG",
            ),
            team_id=sample_team.id,
        )

        assert player is not None
        assert player.first_name == "New"
        assert player.last_name == "Player"
        assert player.external_ids == {"winner": "player-999"}

    def test_find_or_create_player_global_match_by_birth_date(
        self, test_db, sample_team
    ):
        """Test global matching by name + birth_date for transferred player."""
        # Create player on different team (no team history for sample_team)
        other_team = Team(
            name="Hapoel Jerusalem",
            short_name="HJ",
            city="Jerusalem",
            country="Israel",
            external_ids={"winner": "team-456"},
        )
        test_db.add(other_team)
        test_db.commit()

        player = Player(
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 5, 15),
            height_cm=195,
            external_ids={"winner": "player-old"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Try to find from euroleague (player transferred to sample_team)
        found = dedup.find_or_create_player(
            source="euroleague",
            external_id="EL-789",
            player_data=RawPlayerInfo(
                external_id="EL-789",
                first_name="John",
                last_name="Smith",
                birth_date=date(1995, 5, 15),
            ),
            team_id=sample_team.id,
        )

        assert found.id == player.id
        assert found.external_ids == {"winner": "player-old", "euroleague": "EL-789"}


class TestPlayerDeduplicatorGetByExternalId:
    """Tests for PlayerDeduplicator.get_by_external_id method."""

    def test_get_by_external_id_found(self, test_db):
        """Test finding player by external_id."""
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        found = dedup.get_by_external_id("winner", "123")

        assert found is not None
        assert found.id == player.id

    def test_get_by_external_id_not_found(self, test_db):
        """Test returning None when external_id not found."""
        dedup = PlayerDeduplicator(test_db)
        found = dedup.get_by_external_id("winner", "nonexistent")

        assert found is None

    def test_get_by_external_id_wrong_source(self, test_db):
        """Test that wrong source doesn't match."""
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        found = dedup.get_by_external_id("euroleague", "123")

        assert found is None


class TestPlayerDeduplicatorMatchOnTeam:
    """Tests for PlayerDeduplicator.match_player_on_team method."""

    def test_match_player_on_team_exact_name(
        self, test_db, sample_team, sample_season, player_on_team
    ):
        """Test matching by exact normalized name."""
        dedup = PlayerDeduplicator(test_db)

        found = dedup.match_player_on_team(
            team_id=sample_team.id,
            player_name="Scottie Wilbekin",
            source="euroleague",
        )

        assert found is not None
        assert found.id == player_on_team.id

    def test_match_player_on_team_normalized_name(
        self, test_db, sample_team, sample_season, player_on_team
    ):
        """Test matching with case-insensitive name."""
        dedup = PlayerDeduplicator(test_db)

        found = dedup.match_player_on_team(
            team_id=sample_team.id,
            player_name="SCOTTIE WILBEKIN",
            source="euroleague",
        )

        assert found is not None
        assert found.id == player_on_team.id

    def test_match_player_on_team_no_match(self, test_db, sample_team, sample_season):
        """Test returning None when no name match."""
        player = Player(
            first_name="Different",
            last_name="Player",
            external_ids={"winner": "player-xyz"},
        )
        test_db.add(player)
        test_db.commit()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=sample_team.id,
            season_id=sample_season.id,
        )
        test_db.add(history)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        found = dedup.match_player_on_team(
            team_id=sample_team.id,
            player_name="Scottie Wilbekin",
            source="euroleague",
        )

        assert found is None

    def test_match_player_on_team_skips_already_mapped(
        self, test_db, sample_team, sample_season, player_on_team
    ):
        """Test that players already mapped to source are skipped."""
        # Add euroleague mapping to existing player
        player_on_team.external_ids = {"winner": "player-123", "euroleague": "existing"}
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        found = dedup.match_player_on_team(
            team_id=sample_team.id,
            player_name="Scottie Wilbekin",
            source="euroleague",
        )

        # Should not match because player already has euroleague ID
        assert found is None


class TestPlayerDeduplicatorMatchGlobally:
    """Tests for PlayerDeduplicator.match_player_globally method."""

    def test_match_globally_by_name_and_birth_date(self, test_db):
        """Test global matching by name + birth_date."""
        player = Player(
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 5, 15),
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        found = dedup.match_player_globally(
            player_name="John Smith",
            source="euroleague",
            birth_date=date(1995, 5, 15),
        )

        assert found is not None
        assert found.id == player.id

    def test_match_globally_by_name_and_height(self, test_db):
        """Test global matching by name + height within tolerance."""
        player = Player(
            first_name="John",
            last_name="Smith",
            height_cm=195,
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Match with height within tolerance (195 +/- 3)
        found = dedup.match_player_globally(
            player_name="John Smith",
            source="euroleague",
            height_cm=196,
        )

        assert found is not None
        assert found.id == player.id

    def test_match_globally_height_outside_tolerance(self, test_db):
        """Test that height outside tolerance doesn't match."""
        player = Player(
            first_name="John",
            last_name="Smith",
            height_cm=195,
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Height difference > 3cm, should not match
        found = dedup.match_player_globally(
            player_name="John Smith",
            source="euroleague",
            height_cm=200,
        )

        assert found is None

    def test_match_globally_single_name_match_with_bio(self, test_db):
        """Test that single name match is used when bio data provided."""
        player = Player(
            first_name="Unique",
            last_name="Name",
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Only one player with this name, and we have bio data
        found = dedup.match_player_globally(
            player_name="Unique Name",
            source="euroleague",
            birth_date=date(1990, 1, 1),  # Bio data provided
        )

        assert found is not None
        assert found.id == player.id


class TestPlayerDeduplicatorMergeExternalId:
    """Tests for PlayerDeduplicator.merge_external_id method."""

    def test_merge_external_id(self, test_db):
        """Test merging new external_id into existing player."""
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"winner": "123"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        updated = dedup.merge_external_id(player, "euroleague", "EL-456")

        assert updated.external_ids == {"winner": "123", "euroleague": "EL-456"}

    def test_merge_external_id_overwrites_existing(self, test_db):
        """Test that merging overwrites existing source entry."""
        player = Player(
            first_name="Test",
            last_name="Player",
            external_ids={"winner": "old-id"},
        )
        test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        updated = dedup.merge_external_id(player, "winner", "new-id")

        assert updated.external_ids == {"winner": "new-id"}


class TestPlayerDeduplicatorFindPotentialDuplicates:
    """Tests for PlayerDeduplicator.find_potential_duplicates method."""

    def test_find_potential_duplicates_by_name(self, test_db):
        """Test finding duplicates by matching names."""
        player1 = Player(
            first_name="John",
            last_name="Smith",
            external_ids={"winner": "123"},
        )
        player2 = Player(
            first_name="John",
            last_name="Smith",
            external_ids={"euroleague": "456"},
        )
        test_db.add_all([player1, player2])
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        duplicates = dedup.find_potential_duplicates()

        assert len(duplicates) == 1
        ids = {duplicates[0][0].id, duplicates[0][1].id}
        assert player1.id in ids
        assert player2.id in ids

    def test_find_potential_duplicates_by_last_name_and_birth_date(self, test_db):
        """Test finding duplicates by last name + birth date."""
        player1 = Player(
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 5, 15),
            external_ids={"winner": "123"},
        )
        player2 = Player(
            first_name="Johnny",  # Different first name
            last_name="Smith",
            birth_date=date(1995, 5, 15),  # Same birth date
            external_ids={"euroleague": "456"},
        )
        test_db.add_all([player1, player2])
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        duplicates = dedup.find_potential_duplicates()

        assert len(duplicates) == 1

    def test_find_potential_duplicates_no_duplicates(self, test_db):
        """Test returning empty when no duplicates."""
        player1 = Player(
            first_name="John",
            last_name="Smith",
            external_ids={"winner": "123"},
        )
        player2 = Player(
            first_name="Jane",
            last_name="Doe",
            external_ids={"winner": "456"},
        )
        test_db.add_all([player1, player2])
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        duplicates = dedup.find_potential_duplicates()

        assert len(duplicates) == 0
