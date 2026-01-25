"""
Team Matcher Tests

Tests for team matching and deduplication across data sources.
"""

from src.models.team import Team
from src.sync.deduplication.team_matcher import TeamMatcher
from src.sync.types import RawTeam


class TestTeamMatcherFindOrCreate:
    """Tests for TeamMatcher.find_or_create_team method."""

    def test_find_or_create_team_new(self, test_db):
        """Test creating a new team when no match exists."""
        matcher = TeamMatcher(test_db)

        team = matcher.find_or_create_team(
            source="winner",
            external_id="team-123",
            team_data=RawTeam(
                external_id="team-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        assert team is not None
        assert team.name == "Maccabi Tel Aviv"
        assert team.short_name == "MTA"
        assert team.external_ids == {"winner": "team-123"}

    def test_find_or_create_team_existing_same_source(self, test_db):
        """Test finding existing team by same source external_id."""
        matcher = TeamMatcher(test_db)

        # Create initial team
        team1 = matcher.find_or_create_team(
            source="winner",
            external_id="team-123",
            team_data=RawTeam(
                external_id="team-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        # Try to create with same source and external_id
        team2 = matcher.find_or_create_team(
            source="winner",
            external_id="team-123",
            team_data=RawTeam(
                external_id="team-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        assert team1.id == team2.id
        assert team2.external_ids == {"winner": "team-123"}

    def test_find_or_create_team_existing_different_source_merges(self, test_db):
        """Test that different source external_id is merged into existing team."""
        matcher = TeamMatcher(test_db)

        # Create initial team from Winner
        team1 = matcher.find_or_create_team(
            source="winner",
            external_id="w-123",
            team_data=RawTeam(
                external_id="w-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        # Create from Euroleague - should match by name and merge
        team2 = matcher.find_or_create_team(
            source="euroleague",
            external_id="MAT",
            team_data=RawTeam(
                external_id="MAT",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        assert team1.id == team2.id
        assert team2.external_ids == {"winner": "w-123", "euroleague": "MAT"}


class TestTeamMatcherGetByExternalId:
    """Tests for TeamMatcher.get_by_external_id method."""

    def test_get_by_external_id_found(self, test_db):
        """Test finding team by external_id."""
        # Create team directly
        team = Team(
            name="Test Team",
            short_name="TT",
            city="Test City",
            country="Israel",
            external_ids={"winner": "123"},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        found = matcher.get_by_external_id("winner", "123")

        assert found is not None
        assert found.id == team.id

    def test_get_by_external_id_not_found(self, test_db):
        """Test returning None when external_id not found."""
        matcher = TeamMatcher(test_db)
        found = matcher.get_by_external_id("winner", "nonexistent")

        assert found is None

    def test_get_by_external_id_wrong_source(self, test_db):
        """Test that wrong source doesn't match."""
        team = Team(
            name="Test Team",
            short_name="TT",
            city="Test City",
            country="Israel",
            external_ids={"winner": "123"},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        found = matcher.get_by_external_id("euroleague", "123")

        assert found is None


class TestTeamMatcherMatchAcrossSources:
    """Tests for TeamMatcher.match_team_across_sources method."""

    def test_match_team_across_sources_by_name(self, test_db):
        """Test matching team by normalized name."""
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={"winner": "123"},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)

        # Match with exact name
        found = matcher.match_team_across_sources("Maccabi Tel Aviv")
        assert found is not None
        assert found.id == team.id

        # Match with different case
        found = matcher.match_team_across_sources("MACCABI TEL AVIV")
        assert found is not None
        assert found.id == team.id

    def test_match_team_across_sources_not_found(self, test_db):
        """Test returning None when no name match."""
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={"winner": "123"},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        found = matcher.match_team_across_sources("Hapoel Jerusalem")

        assert found is None


class TestTeamMatcherMergeExternalId:
    """Tests for TeamMatcher.merge_external_id method."""

    def test_merge_external_id(self, test_db):
        """Test merging new external_id into existing team."""
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={"winner": "123"},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        updated = matcher.merge_external_id(team, "euroleague", "MAT")

        assert updated.external_ids == {"winner": "123", "euroleague": "MAT"}

    def test_merge_external_id_overwrites_existing(self, test_db):
        """Test that merging overwrites existing source entry."""
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={"winner": "old-id"},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        updated = matcher.merge_external_id(team, "winner", "new-id")

        assert updated.external_ids == {"winner": "new-id"}

    def test_merge_external_id_multiple_sources(self, test_db):
        """Test merging multiple sources."""
        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={},
        )
        test_db.add(team)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        matcher.merge_external_id(team, "winner", "123")
        matcher.merge_external_id(team, "euroleague", "MAT")
        updated = matcher.merge_external_id(team, "nba", "456")

        assert updated.external_ids == {
            "winner": "123",
            "euroleague": "MAT",
            "nba": "456",
        }
