"""
Integration tests for player bio data sync.

Tests the full player bio sync flow from fetching rosters to updating
players with biographical data (position, height, birthdate).

Tests cover:
- Players have bio data after sync
- Player name matching works between PBP and roster
- No duplicate players are created
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team, TeamSeason
from src.schemas.enums import Position
from src.sync.config import SyncConfig, SyncSourceConfig
from src.sync.manager import SyncManager
from src.sync.types import RawPlayerInfo


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
    """Create the current season."""
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
def team(test_db: Session) -> Team:
    """Create a test team."""
    team = Team(
        id=uuid4(),
        name="Maccabi Tel Aviv",
        short_name="MTA",
        city="Tel Aviv",
        country="Israel",
        external_ids={"winner": "100"},
    )
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def team_season(test_db: Session, team: Team, season: Season) -> TeamSeason:
    """Create team-season link."""
    ts = TeamSeason(
        team_id=team.id,
        season_id=season.id,
        external_id="100",
    )
    test_db.add(ts)
    test_db.commit()
    return ts


@pytest.fixture
def players_without_bio(test_db: Session, team: Team, season: Season) -> list[Player]:
    """Create players without bio data (as they would be from PBP sync)."""
    players = []
    for _i, name in enumerate(["John Smith", "David Cohen", "Michael Brown"]):
        first, last = name.split(" ", 1)
        player = Player(
            id=uuid4(),
            first_name=first,
            last_name=last,
            external_ids={},  # No external IDs yet
        )
        test_db.add(player)
        test_db.flush()

        # Add team history
        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
        )
        test_db.add(history)
        players.append(player)

    test_db.commit()
    return players


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Create a mock adapter that returns roster data."""
    adapter = MagicMock()
    adapter.source_name = "winner"

    # Create roster data with bio info
    roster_data = [
        (
            "1001",
            "John Smith",
            RawPlayerInfo(
                external_id="1001",
                first_name="John",
                last_name="Smith",
                positions=[Position.GUARD],
                height_cm=195,
                birth_date=date(1995, 5, 15),
            ),
        ),
        (
            "1002",
            "David Cohen",
            RawPlayerInfo(
                external_id="1002",
                first_name="David",
                last_name="Cohen",
                positions=[Position.POINT_GUARD],
                height_cm=185,
                birth_date=date(1998, 3, 20),
            ),
        ),
        (
            "1003",
            "Michael Brown",
            RawPlayerInfo(
                external_id="1003",
                first_name="Michael",
                last_name="Brown",
                positions=[Position.CENTER],
                height_cm=210,
                birth_date=date(1992, 11, 8),
            ),
        ),
    ]

    # Make get_team_roster async and return roster data
    adapter.get_team_roster = AsyncMock(return_value=roster_data)

    return adapter


@pytest.fixture
def sync_config() -> SyncConfig:
    """Create sync config with winner enabled."""
    config = SyncConfig(
        sources={
            "winner": SyncSourceConfig(source_name="winner", enabled=True),
        }
    )
    return config


class TestSyncPlayersHaveBioData:
    """Tests that players have bio data after sync."""

    @pytest.mark.asyncio
    async def test_sync_updates_player_position(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test sync updates player position."""
        # Setup
        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        # Execute
        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        # Verify
        test_db.refresh(players_without_bio[0])
        # Position property returns the enum value (e.g., "G" for Guard)
        assert players_without_bio[0].positions == [Position.GUARD]
        assert players_without_bio[0].positions == [Position.GUARD]

    @pytest.mark.asyncio
    async def test_sync_updates_player_height(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test sync updates player height."""
        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        test_db.refresh(players_without_bio[0])
        assert players_without_bio[0].height_cm == 195

    @pytest.mark.asyncio
    async def test_sync_updates_player_birthdate(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test sync updates player birth_date."""
        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        test_db.refresh(players_without_bio[0])
        assert players_without_bio[0].birth_date == date(1995, 5, 15)

    @pytest.mark.asyncio
    async def test_sync_updates_external_id(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test sync adds external_id for matched players."""
        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        test_db.refresh(players_without_bio[0])
        assert "winner" in players_without_bio[0].external_ids
        assert players_without_bio[0].external_ids["winner"] == "1001"


class TestPlayerNameMatchingWorks:
    """Tests that player name matching works between PBP and roster."""

    @pytest.mark.asyncio
    async def test_exact_name_matching(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test exact name matches are found."""
        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        result = await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        # All 3 players should be matched
        assert result.records_updated == 3

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test name matching is case insensitive."""
        # Create player with different case
        player = Player(
            id=uuid4(),
            first_name="JOHN",
            last_name="SMITH",
            external_ids={},
        )
        test_db.add(player)
        test_db.flush()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
        )
        test_db.add(history)
        test_db.commit()

        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        test_db.refresh(player)
        # Should match despite case difference
        # Position property returns enum value (e.g., "G" for Guard)
        assert player.positions == [Position.GUARD]
        assert player.positions == [Position.GUARD]

    @pytest.mark.asyncio
    async def test_unmatched_players_not_updated(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test players not in roster are not updated."""
        # Create player not in roster
        player = Player(
            id=uuid4(),
            first_name="Unknown",
            last_name="Player",
            external_ids={},
        )
        test_db.add(player)
        test_db.flush()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
        )
        test_db.add(history)
        test_db.commit()

        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        test_db.refresh(player)
        # Should not have bio data
        assert player.positions == []
        assert player.height_cm is None


class TestNoDuplicatePlayers:
    """Tests that sync doesn't create duplicate players."""

    @pytest.mark.asyncio
    async def test_sync_does_not_create_new_players(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test sync only updates existing players, doesn't create new ones."""
        # Count players before sync
        player_count_before = test_db.scalar(select(func.count()).select_from(Player))

        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        # Count players after sync
        player_count_after = test_db.scalar(select(func.count()).select_from(Player))

        # Should not create any new players
        assert player_count_after == player_count_before

    @pytest.mark.asyncio
    async def test_resync_is_idempotent(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        players_without_bio: list[Player],
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test running sync twice doesn't duplicate data or overwrite."""
        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        # First sync
        result1 = await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        # Second sync
        result2 = await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        # First sync should update, second should skip (already has data)
        assert result1.records_updated == 3
        assert result2.records_updated == 0  # Already updated

    @pytest.mark.asyncio
    async def test_existing_bio_data_not_overwritten(
        self,
        test_db: Session,
        team: Team,
        team_season: TeamSeason,
        season: Season,
        mock_adapter: MagicMock,
        sync_config: SyncConfig,
    ) -> None:
        """Test existing bio data is not overwritten by sync."""
        # Create player with existing bio data
        player = Player(
            id=uuid4(),
            first_name="John",
            last_name="Smith",
            positions=[Position.FORWARD],  # Different from roster data
            height_cm=200,  # Different from roster data
            birth_date=date(1990, 1, 1),  # Different from roster data
            external_ids={},
        )
        test_db.add(player)
        test_db.flush()

        history = PlayerTeamHistory(
            player_id=player.id,
            team_id=team.id,
            season_id=season.id,
        )
        test_db.add(history)
        test_db.commit()

        manager = SyncManager(
            db=test_db,
            adapters={"winner": mock_adapter},
            config=sync_config,
        )

        await manager.sync_player_bio_from_roster(
            source="winner",
            team_id=team.id,
            team_external_id="100",
            season_id=season.id,
        )

        test_db.refresh(player)
        # Original values should be preserved
        assert player.positions == [Position.FORWARD]
        assert player.height_cm == 200
        assert player.birth_date == date(1990, 1, 1)
