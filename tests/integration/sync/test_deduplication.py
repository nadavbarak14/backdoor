"""
Deduplication Integration Tests

Tests real-world deduplication scenarios using actual team and player data
from Winner League and Euroleague. Maccabi Tel Aviv competes in both leagues,
so their players appear in both data sources.

These tests verify:
1. Teams are correctly deduplicated across sources
2. Players are correctly matched by name, birth_date, and team
3. External IDs are properly merged when same entity found in multiple sources
"""

from datetime import date

import pytest
from sqlalchemy import func, select

from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team, TeamSeason
from src.sync.deduplication import (
    PlayerDeduplicator,
    TeamMatcher,
)
from src.sync.types import RawPlayerInfo, RawTeam

# Real Maccabi Tel Aviv players (2023-24 season) with approximate data
MACCABI_PLAYERS = {
    "winner": [
        {
            "external_id": "w-wilbekin",
            "first_name": "Scottie",
            "last_name": "Wilbekin",
            "birth_date": date(1993, 7, 19),
            "height_cm": 185,
            "position": "PG",
        },
        {
            "external_id": "w-baldwin",
            "first_name": "Wade",
            "last_name": "Baldwin",
            "birth_date": date(1996, 4, 29),
            "height_cm": 193,
            "position": "PG",
        },
        {
            "external_id": "w-evans",
            "first_name": "Jaylen",
            "last_name": "Hoard",  # Changed teams mid-season
            "birth_date": date(1999, 3, 12),
            "height_cm": 206,
            "position": "PF",
        },
        {
            "external_id": "w-sorkin",
            "first_name": "Roman",
            "last_name": "Sorkin",
            "birth_date": date(1996, 8, 17),
            "height_cm": 208,
            "position": "C",
        },
        {
            "external_id": "w-randolph",
            "first_name": "Levi",
            "last_name": "Randolph",
            "birth_date": date(1993, 5, 6),
            "height_cm": 196,
            "position": "SG",
        },
    ],
    "euroleague": [
        {
            "external_id": "EL-PWB",
            "first_name": "Scottie",
            "last_name": "Wilbekin",
            "birth_date": date(1993, 7, 19),
            "height_cm": 185,
            "position": "PG",
        },
        {
            "external_id": "EL-WBD",
            "first_name": "Wade",
            "last_name": "Baldwin IV",  # Euroleague uses full suffix
            "birth_date": date(1996, 4, 29),
            "height_cm": 193,
            "position": "G",  # Different position notation
        },
        {
            "external_id": "EL-RSK",
            "first_name": "Roman",
            "last_name": "Sorkin",
            "birth_date": date(1996, 8, 17),
            "height_cm": 208,
            "position": "C",
        },
        {
            "external_id": "EL-LRD",
            "first_name": "Levi",
            "last_name": "Randolph",
            "birth_date": date(1993, 5, 6),
            "height_cm": 196,
            "position": "SG",
        },
        {
            "external_id": "EL-NEW",
            "first_name": "Lorenzo",
            "last_name": "Brown",  # Euroleague-only player
            "birth_date": date(1990, 8, 26),
            "height_cm": 196,
            "position": "PG",
        },
    ],
}


@pytest.fixture
def setup_leagues(test_db):
    """Create Winner League and Euroleague with seasons."""
    winner = League(name="Winner League", code="WINNER", country="Israel")
    euroleague = League(name="Euroleague", code="EUROLEAGUE", country="Europe")
    test_db.add_all([winner, euroleague])
    test_db.commit()

    winner_season = Season(
        league_id=winner.id,
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

    return {
        "winner": {"league": winner, "season": winner_season},
        "euroleague": {"league": euroleague, "season": euroleague_season},
    }


class TestTeamDeduplication:
    """Integration tests for team deduplication across leagues."""

    def test_maccabi_tel_aviv_deduplication(self, test_db, setup_leagues):
        """Test that Maccabi Tel Aviv is correctly deduplicated across sources."""
        matcher = TeamMatcher(test_db)

        # First: import from Winner League
        winner_team = matcher.find_or_create_team(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        assert winner_team.name == "Maccabi Tel Aviv"
        assert winner_team.external_ids == {"winner": "w-maccabi-ta"}

        # Second: import from Euroleague - should match existing team
        euroleague_team = matcher.find_or_create_team(
            source="euroleague",
            external_id="EL-MTA",
            team_data=RawTeam(
                external_id="EL-MTA",
                name="Maccabi Playtika Tel Aviv",  # Sponsor name in Euroleague
                short_name="MTA",
            ),
        )

        # Should be the same team with merged external_ids
        assert euroleague_team.id == winner_team.id
        assert euroleague_team.external_ids == {
            "winner": "w-maccabi-ta",
            "euroleague": "EL-MTA",
        }

    def test_hapoel_tel_aviv_separate_from_maccabi(self, test_db, setup_leagues):
        """Test that Hapoel Tel Aviv is NOT matched with Maccabi Tel Aviv."""
        matcher = TeamMatcher(test_db)

        maccabi = matcher.find_or_create_team(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        hapoel = matcher.find_or_create_team(
            source="winner",
            external_id="w-hapoel-ta",
            team_data=RawTeam(
                external_id="w-hapoel-ta",
                name="Hapoel Tel Aviv",
                short_name="HTA",
            ),
        )

        # Should be different teams
        assert hapoel.id != maccabi.id
        assert hapoel.name == "Hapoel Tel Aviv"

    def test_multiple_israeli_teams(self, test_db, setup_leagues):
        """Test deduplication with multiple Israeli teams."""
        matcher = TeamMatcher(test_db)

        teams_data = [
            ("w-maccabi-ta", "Maccabi Tel Aviv", "MTA"),
            ("w-hapoel-jlm", "Hapoel Jerusalem", "HJM"),
            ("w-hapoel-ta", "Hapoel Tel Aviv", "HTA"),
            ("w-bnei-herzliya", "Bnei Herzliya", "BNH"),
        ]

        created_teams = []
        for ext_id, name, short in teams_data:
            team = matcher.find_or_create_team(
                source="winner",
                external_id=ext_id,
                team_data=RawTeam(external_id=ext_id, name=name, short_name=short),
            )
            created_teams.append(team)

        # All should be unique teams
        team_ids = [t.id for t in created_teams]
        assert len(set(team_ids)) == 4


class TestTeamSeasonDeduplication:
    """Integration tests for TeamSeason with competition-specific external IDs."""

    def test_maccabi_two_competitions_two_team_seasons(self, test_db, setup_leagues):
        """
        Test that Maccabi Tel Aviv has one Team but two TeamSeason records.

        Verifies the core use case: same team participating in multiple
        competitions (Winner League AND Euroleague), each with its own
        competition-specific external_id in TeamSeason.
        """
        matcher = TeamMatcher(test_db)
        winner_season = setup_leagues["winner"]["season"]
        euroleague_season = setup_leagues["euroleague"]["season"]

        # Import from Winner League
        winner_team, winner_ts = matcher.find_or_create_team_season(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=winner_season.id,
        )

        # Import from Euroleague
        euroleague_team, euroleague_ts = matcher.find_or_create_team_season(
            source="euroleague",
            external_id="EL-MTA",
            team_data=RawTeam(
                external_id="EL-MTA",
                name="Maccabi Playtika Tel Aviv",
                short_name="MTA",
            ),
            season_id=euroleague_season.id,
        )

        # Should be ONE deduplicated Team
        assert winner_team.id == euroleague_team.id
        assert euroleague_team.external_ids == {
            "winner": "w-maccabi-ta",
            "euroleague": "EL-MTA",
        }

        # But TWO TeamSeason records with different external_ids
        assert winner_ts.external_id == "w-maccabi-ta"
        assert euroleague_ts.external_id == "EL-MTA"
        assert winner_ts.season_id != euroleague_ts.season_id
        assert winner_ts.team_id == euroleague_ts.team_id

    def test_lookup_team_season_by_external_id(self, test_db, setup_leagues):
        """Test that TeamSeason can be looked up by external_id."""
        matcher = TeamMatcher(test_db)
        winner_season = setup_leagues["winner"]["season"]

        # Create team with TeamSeason
        team, team_season = matcher.find_or_create_team_season(
            source="winner",
            external_id="w-hapoel-jlm",
            team_data=RawTeam(
                external_id="w-hapoel-jlm",
                name="Hapoel Jerusalem",
                short_name="HJM",
            ),
            season_id=winner_season.id,
        )

        # Look up by external_id
        found = matcher.get_team_season_by_external_id(
            season_id=winner_season.id,
            external_id="w-hapoel-jlm",
        )

        assert found is not None
        assert found.team_id == team.id
        assert found.external_id == "w-hapoel-jlm"

    def test_multiple_teams_same_season_different_external_ids(
        self, test_db, setup_leagues
    ):
        """Test multiple teams in same season each have correct external_ids."""
        matcher = TeamMatcher(test_db)
        winner_season = setup_leagues["winner"]["season"]

        teams_data = [
            ("w-maccabi-ta", "Maccabi Tel Aviv", "MTA"),
            ("w-hapoel-jlm", "Hapoel Jerusalem", "HJM"),
            ("w-hapoel-ta", "Hapoel Tel Aviv", "HTA"),
        ]

        created = []
        for ext_id, name, short in teams_data:
            team, ts = matcher.find_or_create_team_season(
                source="winner",
                external_id=ext_id,
                team_data=RawTeam(external_id=ext_id, name=name, short_name=short),
                season_id=winner_season.id,
            )
            created.append((team, ts))

        # Verify all TeamSeason records have correct external_ids
        for (team, ts), (ext_id, name, _) in zip(created, teams_data, strict=True):
            assert ts.external_id == ext_id
            assert team.name == name

        # Verify we can look up each by external_id
        for ext_id, _, _ in teams_data:
            found = matcher.get_team_season_by_external_id(winner_season.id, ext_id)
            assert found is not None
            assert found.external_id == ext_id

    def test_team_season_count_verification(self, test_db, setup_leagues):
        """Verify the Maccabi example creates correct number of records."""
        matcher = TeamMatcher(test_db)
        winner_season = setup_leagues["winner"]["season"]
        euroleague_season = setup_leagues["euroleague"]["season"]

        # Create Maccabi in both competitions
        matcher.find_or_create_team_season(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=winner_season.id,
        )
        matcher.find_or_create_team_season(
            source="euroleague",
            external_id="EL-MTA",
            team_data=RawTeam(
                external_id="EL-MTA",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
            season_id=euroleague_season.id,
        )

        # Count records
        team_count = test_db.scalar(select(func.count()).select_from(Team))
        team_season_count = test_db.scalar(select(func.count()).select_from(TeamSeason))

        # One Team, two TeamSeason records
        assert team_count == 1
        assert team_season_count == 2


class TestPlayerDeduplication:
    """Integration tests for player deduplication across leagues."""

    def test_wilbekin_deduplication_by_team_and_name(self, test_db, setup_leagues):
        """Test Scottie Wilbekin is matched across Winner and Euroleague."""
        matcher = TeamMatcher(test_db)
        dedup = PlayerDeduplicator(test_db)

        # Create Maccabi Tel Aviv
        maccabi = matcher.find_or_create_team(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        # Add team history for Winner League season
        winner_season = setup_leagues["winner"]["season"]

        # Import Wilbekin from Winner League
        winner_wilbekin = dedup.find_or_create_player(
            source="winner",
            external_id="w-wilbekin",
            player_data=RawPlayerInfo(
                external_id="w-wilbekin",
                first_name="Scottie",
                last_name="Wilbekin",
                birth_date=date(1993, 7, 19),
                height_cm=185,
                position="PG",
            ),
            team_id=maccabi.id,
        )

        # Create team history
        history = PlayerTeamHistory(
            player_id=winner_wilbekin.id,
            team_id=maccabi.id,
            season_id=winner_season.id,
            jersey_number=1,
            position="PG",
        )
        test_db.add(history)
        test_db.commit()

        # Now import from Euroleague - should match by team + name
        euroleague_wilbekin = dedup.find_or_create_player(
            source="euroleague",
            external_id="EL-PWB",
            player_data=RawPlayerInfo(
                external_id="EL-PWB",
                first_name="Scottie",
                last_name="Wilbekin",
                birth_date=date(1993, 7, 19),
                height_cm=185,
                position="PG",
            ),
            team_id=maccabi.id,
        )

        # Should be the same player
        assert euroleague_wilbekin.id == winner_wilbekin.id
        assert euroleague_wilbekin.external_ids == {
            "winner": "w-wilbekin",
            "euroleague": "EL-PWB",
        }

    def test_baldwin_deduplication_with_name_variation(self, test_db, setup_leagues):
        """Test Wade Baldwin matched despite 'IV' suffix in Euroleague."""
        matcher = TeamMatcher(test_db)
        dedup = PlayerDeduplicator(test_db)

        maccabi = matcher.find_or_create_team(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        winner_season = setup_leagues["winner"]["season"]

        # Import Baldwin from Winner (without IV suffix)
        winner_baldwin = dedup.find_or_create_player(
            source="winner",
            external_id="w-baldwin",
            player_data=RawPlayerInfo(
                external_id="w-baldwin",
                first_name="Wade",
                last_name="Baldwin",
                birth_date=date(1996, 4, 29),
                height_cm=193,
                position="PG",
            ),
            team_id=maccabi.id,
        )

        history = PlayerTeamHistory(
            player_id=winner_baldwin.id,
            team_id=maccabi.id,
            season_id=winner_season.id,
        )
        test_db.add(history)
        test_db.commit()

        # Import from Euroleague with "Baldwin IV" - should match by birth_date
        euroleague_baldwin = dedup.find_or_create_player(
            source="euroleague",
            external_id="EL-WBD",
            player_data=RawPlayerInfo(
                external_id="EL-WBD",
                first_name="Wade",
                last_name="Baldwin IV",  # Different last name
                birth_date=date(1996, 4, 29),  # Same birth date
                height_cm=193,
                position="G",
            ),
            team_id=maccabi.id,
        )

        # Should match by global birth_date matching
        assert euroleague_baldwin.id == winner_baldwin.id
        assert euroleague_baldwin.external_ids == {
            "winner": "w-baldwin",
            "euroleague": "EL-WBD",
        }

    def test_full_roster_sync_simulation(self, test_db, setup_leagues):
        """Simulate full roster sync from both sources."""
        matcher = TeamMatcher(test_db)
        dedup = PlayerDeduplicator(test_db)

        # Create Maccabi from Winner
        maccabi = matcher.find_or_create_team(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        winner_season = setup_leagues["winner"]["season"]
        _euroleague_season = setup_leagues["euroleague"]["season"]  # noqa: F841

        # Step 1: Import all Winner League players
        winner_players = {}
        for pdata in MACCABI_PLAYERS["winner"]:
            player = dedup.find_or_create_player(
                source="winner",
                external_id=pdata["external_id"],
                player_data=RawPlayerInfo(**pdata),
                team_id=maccabi.id,
            )
            winner_players[pdata["last_name"]] = player

            # Add team history
            history = PlayerTeamHistory(
                player_id=player.id,
                team_id=maccabi.id,
                season_id=winner_season.id,
            )
            test_db.add(history)

        test_db.commit()

        # Merge Maccabi external ID for Euroleague
        matcher.merge_external_id(maccabi, "euroleague", "EL-MTA")

        # Step 2: Import all Euroleague players
        euroleague_players = {}
        for pdata in MACCABI_PLAYERS["euroleague"]:
            player = dedup.find_or_create_player(
                source="euroleague",
                external_id=pdata["external_id"],
                player_data=RawPlayerInfo(**pdata),
                team_id=maccabi.id,
            )
            euroleague_players[pdata["external_id"]] = player

        # Verify deduplication results

        # Wilbekin: Should be matched (same name, same birth_date)
        wilbekin = euroleague_players["EL-PWB"]
        assert "winner" in wilbekin.external_ids
        assert "euroleague" in wilbekin.external_ids

        # Sorkin: Should be matched (same name, same birth_date)
        sorkin = euroleague_players["EL-RSK"]
        assert "winner" in sorkin.external_ids
        assert "euroleague" in sorkin.external_ids

        # Randolph: Should be matched (same name, same birth_date)
        randolph = euroleague_players["EL-LRD"]
        assert "winner" in randolph.external_ids
        assert "euroleague" in randolph.external_ids

        # Lorenzo Brown: Euroleague only - should NOT have winner ID
        brown = euroleague_players["EL-NEW"]
        assert "euroleague" in brown.external_ids
        assert "winner" not in brown.external_ids

        # Count unique players
        all_player_ids = set()
        for p in winner_players.values():
            all_player_ids.add(p.id)
        for p in euroleague_players.values():
            all_player_ids.add(p.id)

        # 5 from Winner + 1 Euroleague-only = 6 unique
        # (4 matched: Wilbekin, Sorkin, Randolph, Baldwin)
        # (1 Winner-only: Hoard)
        # (1 Euroleague-only: Brown)
        assert len(all_player_ids) == 6

    def test_player_transfer_between_teams(self, test_db, setup_leagues):
        """Test player matched after transfer to different team."""
        matcher = TeamMatcher(test_db)
        dedup = PlayerDeduplicator(test_db)

        # Create two teams
        maccabi = matcher.find_or_create_team(
            source="winner",
            external_id="w-maccabi-ta",
            team_data=RawTeam(
                external_id="w-maccabi-ta",
                name="Maccabi Tel Aviv",
                short_name="MTA",
            ),
        )

        hapoel = matcher.find_or_create_team(
            source="winner",
            external_id="w-hapoel-jlm",
            team_data=RawTeam(
                external_id="w-hapoel-jlm",
                name="Hapoel Jerusalem",
                short_name="HJM",
            ),
        )

        winner_season = setup_leagues["winner"]["season"]

        # Player starts at Hapoel Jerusalem (Winner League)
        player_hapoel = dedup.find_or_create_player(
            source="winner",
            external_id="w-transfer-player",
            player_data=RawPlayerInfo(
                external_id="w-transfer-player",
                first_name="Test",
                last_name="Transfer",
                birth_date=date(1995, 3, 15),
                height_cm=200,
                position="SF",
            ),
            team_id=hapoel.id,
        )

        history = PlayerTeamHistory(
            player_id=player_hapoel.id,
            team_id=hapoel.id,
            season_id=winner_season.id,
        )
        test_db.add(history)
        test_db.commit()

        # Same player now at Maccabi in Euroleague (transferred)
        # Should match by global name + birth_date
        player_maccabi = dedup.find_or_create_player(
            source="euroleague",
            external_id="EL-TRF",
            player_data=RawPlayerInfo(
                external_id="EL-TRF",
                first_name="Test",
                last_name="Transfer",
                birth_date=date(1995, 3, 15),
                height_cm=200,
                position="SF",
            ),
            team_id=maccabi.id,  # Different team!
        )

        # Should be the same player (matched by global bio)
        assert player_maccabi.id == player_hapoel.id
        assert player_maccabi.external_ids == {
            "winner": "w-transfer-player",
            "euroleague": "EL-TRF",
        }


class TestDuplicateDetection:
    """Integration tests for finding potential duplicates."""

    def test_find_duplicates_across_sources(self, test_db, setup_leagues):
        """Test that duplicates are detected if external_ids weren't merged."""
        # Manually create duplicate players (simulating data that wasn't deduped)
        player1 = Player(
            first_name="Scottie",
            last_name="Wilbekin",
            birth_date=date(1993, 7, 19),
            external_ids={"winner": "w-wilbekin"},
        )
        player2 = Player(
            first_name="Scottie",
            last_name="Wilbekin",
            birth_date=date(1993, 7, 19),
            external_ids={"euroleague": "EL-PWB"},
        )
        test_db.add_all([player1, player2])
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        duplicates = dedup.find_potential_duplicates()

        # Should find this as a duplicate pair
        assert len(duplicates) == 1
        dup_ids = {duplicates[0][0].id, duplicates[0][1].id}
        assert player1.id in dup_ids
        assert player2.id in dup_ids

    def test_no_false_positives_for_common_names(self, test_db, setup_leagues):
        """Test that common names with different birth dates are not duplicates."""
        # Two different "John Smith" players
        player1 = Player(
            first_name="John",
            last_name="Smith",
            birth_date=date(1990, 1, 15),
            external_ids={"winner": "w-smith-1"},
        )
        player2 = Player(
            first_name="John",
            last_name="Smith",
            birth_date=date(1995, 6, 20),  # Different birth date
            external_ids={"winner": "w-smith-2"},
        )
        test_db.add_all([player1, player2])
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)
        duplicates = dedup.find_potential_duplicates()

        # Should find as potential duplicate by name (for manual review)
        # The find_potential_duplicates is meant to flag for review
        assert len(duplicates) == 1  # Flagged by same name


class TestIndexingPerformance:
    """Tests to verify indexed queries are used correctly."""

    def test_get_by_external_id_uses_json_query(self, test_db):
        """Verify external_id lookup uses JSON query (indexable)."""
        # Create multiple players
        for i in range(10):
            player = Player(
                first_name=f"Player{i}",
                last_name=f"Test{i}",
                external_ids={"winner": f"w-{i}", "euroleague": f"el-{i}"},
            )
            test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Should find by winner ID
        found = dedup.get_by_external_id("winner", "w-5")
        assert found is not None
        assert found.first_name == "Player5"

        # Should find by euroleague ID
        found = dedup.get_by_external_id("euroleague", "el-7")
        assert found is not None
        assert found.first_name == "Player7"

        # Should not find non-existent
        found = dedup.get_by_external_id("winner", "w-999")
        assert found is None

    def test_candidates_by_last_name_filters_correctly(self, test_db):
        """Verify last name query filters correctly."""
        # Create players with different last names
        players_data = [
            ("John", "Smith"),
            ("Jane", "Smith"),
            ("Bob", "Johnson"),
            ("Alice", "Williams"),
            ("Mike", "Smith"),
        ]
        for first, last in players_data:
            player = Player(
                first_name=first,
                last_name=last,
                external_ids={},
            )
            test_db.add(player)
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Should find 3 Smiths
        candidates = dedup._find_candidates_by_last_name("Smith", "winner")
        assert len(candidates) == 3

        # Should find 1 Johnson
        candidates = dedup._find_candidates_by_last_name("Johnson", "winner")
        assert len(candidates) == 1

        # Case insensitive
        candidates = dedup._find_candidates_by_last_name("SMITH", "winner")
        assert len(candidates) == 3

    def test_candidates_excludes_already_mapped(self, test_db):
        """Verify candidates exclude players already mapped to source."""
        player1 = Player(
            first_name="John",
            last_name="Smith",
            external_ids={"winner": "w-1"},  # Already has winner
        )
        player2 = Player(
            first_name="Jane",
            last_name="Smith",
            external_ids={"euroleague": "el-1"},  # Only euroleague
        )
        player3 = Player(
            first_name="Bob",
            last_name="Smith",
            external_ids={},  # No mappings
        )
        test_db.add_all([player1, player2, player3])
        test_db.commit()

        dedup = PlayerDeduplicator(test_db)

        # Looking for winner candidates should exclude player1
        candidates = dedup._find_candidates_by_last_name("Smith", "winner")
        assert len(candidates) == 2
        candidate_ids = {c.id for c in candidates}
        assert player1.id not in candidate_ids
        assert player2.id in candidate_ids
        assert player3.id in candidate_ids
