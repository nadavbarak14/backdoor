"""
Team Matcher Tests

Tests for team matching and deduplication across data sources.
"""

from datetime import date

from src.models.league import League, Season
from src.models.team import Team, TeamSeason
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


class TestTeamMatcherFindOrCreateTeamSeason:
    """Tests for TeamMatcher.find_or_create_team_season method."""

    def test_find_or_create_team_season_new(self, test_db):
        """Test creating a new team and team_season when no match exists."""
        # Create a season
        league = League(name="Winner League", code="WINNER", country="Israel")
        test_db.add(league)
        test_db.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        test_db.add(season)
        test_db.commit()

        matcher = TeamMatcher(test_db)

        team, team_season = matcher.find_or_create_team_season(
            source="winner",
            external_id="w-123",
            team_data=RawTeam(
                external_id="w-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=season.id,
        )

        assert team is not None
        assert team.name == "Maccabi Tel Aviv"
        assert team.external_ids == {"winner": "w-123"}

        assert team_season is not None
        assert team_season.team_id == team.id
        assert team_season.season_id == season.id
        assert team_season.external_id == "w-123"

    def test_find_or_create_team_season_existing_team_new_season(self, test_db):
        """Test creating TeamSeason for existing team in a new season."""
        # Create two seasons (Winner League and Euroleague)
        winner_league = League(name="Winner League", code="WINNER", country="Israel")
        euroleague = League(name="Euroleague", code="EUROLEAGUE", country="Europe")
        test_db.add_all([winner_league, euroleague])
        test_db.commit()

        winner_season = Season(
            league_id=winner_league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        euroleague_season = Season(
            league_id=euroleague.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 5, 30),
            is_current=True,
        )
        test_db.add_all([winner_season, euroleague_season])
        test_db.commit()

        matcher = TeamMatcher(test_db)

        # Create team in Winner League
        team1, ts1 = matcher.find_or_create_team_season(
            source="winner",
            external_id="w-123",
            team_data=RawTeam(
                external_id="w-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=winner_season.id,
        )

        # Same team in Euroleague with different external_id
        team2, ts2 = matcher.find_or_create_team_season(
            source="euroleague",
            external_id="MAT",
            team_data=RawTeam(
                external_id="MAT",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=euroleague_season.id,
        )

        # Should be the same team (deduplicated)
        assert team1.id == team2.id
        assert team2.external_ids == {"winner": "w-123", "euroleague": "MAT"}

        # But different TeamSeason records
        assert ts1.season_id != ts2.season_id
        assert ts1.external_id == "w-123"
        assert ts2.external_id == "MAT"

    def test_find_or_create_team_season_same_team_same_season(self, test_db):
        """Test that repeated calls for same team-season return existing record."""
        league = League(name="Winner League", code="WINNER", country="Israel")
        test_db.add(league)
        test_db.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        test_db.add(season)
        test_db.commit()

        matcher = TeamMatcher(test_db)

        # First call
        team1, ts1 = matcher.find_or_create_team_season(
            source="winner",
            external_id="w-123",
            team_data=RawTeam(
                external_id="w-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=season.id,
        )

        # Second call with same data
        team2, ts2 = matcher.find_or_create_team_season(
            source="winner",
            external_id="w-123",
            team_data=RawTeam(
                external_id="w-123",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=season.id,
        )

        # Should be the exact same records
        assert team1.id == team2.id
        assert ts1.team_id == ts2.team_id
        assert ts1.season_id == ts2.season_id


class TestTeamMatcherGetTeamSeasonByExternalId:
    """Tests for TeamMatcher.get_team_season_by_external_id method."""

    def test_get_team_season_by_external_id_found(self, test_db):
        """Test finding TeamSeason by external_id."""
        league = League(name="Winner League", code="WINNER", country="Israel")
        test_db.add(league)
        test_db.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        test_db.add(season)
        test_db.commit()

        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={"winner": "w-123"},
        )
        test_db.add(team)
        test_db.commit()

        team_season = TeamSeason(
            team_id=team.id,
            season_id=season.id,
            external_id="w-123",
        )
        test_db.add(team_season)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        found = matcher.get_team_season_by_external_id(season.id, "w-123")

        assert found is not None
        assert found.team_id == team.id
        assert found.external_id == "w-123"

    def test_get_team_season_by_external_id_not_found(self, test_db):
        """Test returning None when external_id not found."""
        league = League(name="Winner League", code="WINNER", country="Israel")
        test_db.add(league)
        test_db.commit()

        season = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        test_db.add(season)
        test_db.commit()

        matcher = TeamMatcher(test_db)
        found = matcher.get_team_season_by_external_id(season.id, "nonexistent")

        assert found is None

    def test_get_team_season_by_external_id_wrong_season(self, test_db):
        """Test that wrong season doesn't match."""
        league = League(name="Winner League", code="WINNER", country="Israel")
        test_db.add(league)
        test_db.commit()

        season1 = Season(
            league_id=league.id,
            name="2022-23",
            start_date=date(2022, 10, 1),
            end_date=date(2023, 6, 30),
            is_current=False,
        )
        season2 = Season(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 1),
            end_date=date(2024, 6, 30),
            is_current=True,
        )
        test_db.add_all([season1, season2])
        test_db.commit()

        team = Team(
            name="Maccabi Tel Aviv",
            short_name="MTA",
            city="Tel Aviv",
            country="Israel",
            external_ids={"winner": "w-123"},
        )
        test_db.add(team)
        test_db.commit()

        # TeamSeason exists only in season1
        team_season = TeamSeason(
            team_id=team.id,
            season_id=season1.id,
            external_id="w-123",
        )
        test_db.add(team_season)
        test_db.commit()

        matcher = TeamMatcher(test_db)

        # Should find in season1
        found = matcher.get_team_season_by_external_id(season1.id, "w-123")
        assert found is not None

        # Should NOT find in season2
        found = matcher.get_team_season_by_external_id(season2.id, "w-123")
        assert found is None
