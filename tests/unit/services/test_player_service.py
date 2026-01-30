"""
Unit tests for PlayerService.

Tests player business logic including filtering, external ID lookup,
team history, and player-team associations.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.team import Team
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.player import PlayerCreate, PlayerFilter, PlayerUpdate
from src.schemas.team import TeamCreate
from src.services.league import LeagueService, SeasonService
from src.services.player import PlayerService
from src.services.team import TeamService
from src.schemas.enums import Position


class TestPlayerService:
    """Tests for PlayerService operations."""

    @pytest.fixture
    def nba_league(self, test_db: Session) -> League:
        """Create an NBA league for testing."""
        service = LeagueService(test_db)
        return service.create_league(
            LeagueCreate(
                name="NBA",
                code="NBA",
                country="USA",
            )
        )

    @pytest.fixture
    def nba_season(self, test_db: Session, nba_league: League) -> Season:
        """Create an NBA season for testing."""
        service = SeasonService(test_db)
        return service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2023-24",
                start_date=date(2023, 10, 24),
                end_date=date(2024, 6, 17),
                is_current=True,
            )
        )

    @pytest.fixture
    def lakers(self, test_db: Session) -> Team:
        """Create a Lakers team for testing."""
        service = TeamService(test_db)
        return service.create_team(
            TeamCreate(
                name="Los Angeles Lakers",
                short_name="LAL",
                city="Los Angeles",
                country="USA",
            )
        )

    def test_create_player(self, test_db: Session):
        """Test creating a player from Pydantic schema."""
        service = PlayerService(test_db)
        data = PlayerCreate(
            first_name="LeBron",
            last_name="James",
            birth_date=date(1984, 12, 30),
            nationality="USA",
            height_cm=206,
            positions=["SF"],
            external_ids={"nba": "2544"},
        )

        player = service.create_player(data)

        assert player.id is not None
        assert player.first_name == "LeBron"
        assert player.last_name == "James"
        assert player.full_name == "LeBron James"
        assert player.external_ids == {"nba": "2544"}

    def test_create_player_without_external_ids(self, test_db: Session):
        """Test creating a player without external_ids defaults to empty dict."""
        service = PlayerService(test_db)
        data = PlayerCreate(
            first_name="Test",
            last_name="Player",
        )

        player = service.create_player(data)

        assert player.external_ids == {}

    def test_update_player(self, test_db: Session):
        """Test updating a player from Pydantic schema."""
        service = PlayerService(test_db)
        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                positions=["SF"],
            )
        )

        updated = service.update_player(player.id, PlayerUpdate(positions=["PF"]))

        assert updated is not None
        assert updated.positions == [Position.POWER_FORWARD]
        assert updated.first_name == "LeBron"  # Unchanged

    def test_get_by_external_id_found(self, test_db: Session):
        """Test finding a player by external ID."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                external_ids={"nba": "2544", "espn": "1966"},
            )
        )

        result = service.get_by_external_id("nba", "2544")

        assert result is not None
        assert result.full_name == "LeBron James"

    def test_get_by_external_id_not_found(self, test_db: Session):
        """Test get_by_external_id returns None for non-existent ID."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                external_ids={"nba": "2544"},
            )
        )

        result = service.get_by_external_id("nba", "999999")

        assert result is None

    def test_get_by_external_id_wrong_source(self, test_db: Session):
        """Test get_by_external_id returns None for wrong source."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                external_ids={"nba": "2544"},
            )
        )

        result = service.get_by_external_id("espn", "2544")

        assert result is None

    def test_get_filtered_by_position(self, test_db: Session):
        """Test filtering players by position."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                positions=["SF"],
            )
        )
        service.create_player(
            PlayerCreate(
                first_name="Stephen",
                last_name="Curry",
                positions=["PG"],
            )
        )

        players, total = service.get_filtered(PlayerFilter(position="PG"))

        assert total == 1
        assert len(players) == 1
        assert players[0].full_name == "Stephen Curry"

    def test_get_filtered_by_nationality(self, test_db: Session):
        """Test filtering players by nationality."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
                nationality="USA",
            )
        )
        service.create_player(
            PlayerCreate(
                first_name="Luka",
                last_name="Doncic",
                nationality="Slovenia",
            )
        )

        players, total = service.get_filtered(PlayerFilter(nationality="Slovenia"))

        assert total == 1
        assert players[0].full_name == "Luka Doncic"

    def test_get_filtered_by_name_search(self, test_db: Session):
        """Test filtering players by name search."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        service.create_player(
            PlayerCreate(
                first_name="Stephen",
                last_name="Curry",
            )
        )

        players, total = service.get_filtered(PlayerFilter(search="Curry"))

        assert total == 1
        assert players[0].last_name == "Curry"

    def test_get_filtered_by_first_name_search(self, test_db: Session):
        """Test filtering players by first name search."""
        service = PlayerService(test_db)
        service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        service.create_player(
            PlayerCreate(
                first_name="Stephen",
                last_name="Curry",
            )
        )

        players, total = service.get_filtered(PlayerFilter(search="LeBron"))

        assert total == 1
        assert players[0].first_name == "LeBron"

    def test_get_filtered_by_team(
        self, test_db: Session, nba_season: Season, lakers: Team
    ):
        """Test filtering players by team."""
        service = PlayerService(test_db)
        lebron = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        service.create_player(
            PlayerCreate(
                first_name="Stephen",
                last_name="Curry",
            )
        )
        service.add_to_team(lebron.id, lakers.id, nba_season.id)

        players, total = service.get_filtered(PlayerFilter(team_id=lakers.id))

        assert total == 1
        assert players[0].full_name == "LeBron James"

    def test_get_filtered_by_season(
        self, test_db: Session, nba_league: League, nba_season: Season, lakers: Team
    ):
        """Test filtering players by season."""
        service = PlayerService(test_db)
        season_service = SeasonService(test_db)

        old_season = season_service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )

        lebron = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        curry = service.create_player(
            PlayerCreate(
                first_name="Stephen",
                last_name="Curry",
            )
        )
        service.add_to_team(lebron.id, lakers.id, nba_season.id)
        service.add_to_team(curry.id, lakers.id, old_season.id)

        players, total = service.get_filtered(PlayerFilter(season_id=nba_season.id))

        assert total == 1
        assert players[0].full_name == "LeBron James"

    def test_get_filtered_pagination(self, test_db: Session):
        """Test filtered results respect pagination."""
        service = PlayerService(test_db)
        for i in range(5):
            service.create_player(
                PlayerCreate(
                    first_name="Player",
                    last_name=f"Number{i}",
                )
            )

        players, total = service.get_filtered(PlayerFilter(), skip=2, limit=2)

        assert total == 5
        assert len(players) == 2

    def test_add_to_team(self, test_db: Session, nba_season: Season, lakers: Team):
        """Test adding a player to a team."""
        service = PlayerService(test_db)
        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )

        result = service.add_to_team(
            player.id, lakers.id, nba_season.id, jersey_number=23, position="SF"
        )

        assert result is not None
        assert result.player_id == player.id
        assert result.team_id == lakers.id
        assert result.season_id == nba_season.id
        assert result.jersey_number == 23
        assert result.positions == [Position.SMALL_FORWARD]

    def test_add_to_team_already_exists(
        self, test_db: Session, nba_season: Season, lakers: Team
    ):
        """Test add_to_team returns existing entry if already exists."""
        service = PlayerService(test_db)
        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        first = service.add_to_team(
            player.id, lakers.id, nba_season.id, jersey_number=23
        )

        second = service.add_to_team(
            player.id,
            lakers.id,
            nba_season.id,
            jersey_number=6,  # Different jersey, but same player/team/season
        )

        assert second is not None
        assert second.id == first.id
        assert second.jersey_number == 23  # Original value, not updated

    def test_add_to_team_player_not_found(
        self, test_db: Session, nba_season: Season, lakers: Team
    ):
        """Test add_to_team returns None for non-existent player."""
        service = PlayerService(test_db)
        fake_player_id = uuid.uuid4()

        result = service.add_to_team(fake_player_id, lakers.id, nba_season.id)

        assert result is None

    def test_add_to_team_team_not_found(self, test_db: Session, nba_season: Season):
        """Test add_to_team returns None for non-existent team."""
        service = PlayerService(test_db)
        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        fake_team_id = uuid.uuid4()

        result = service.add_to_team(player.id, fake_team_id, nba_season.id)

        assert result is None

    def test_add_to_team_season_not_found(self, test_db: Session, lakers: Team):
        """Test add_to_team returns None for non-existent season."""
        service = PlayerService(test_db)
        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        fake_season_id = uuid.uuid4()

        result = service.add_to_team(player.id, lakers.id, fake_season_id)

        assert result is None

    def test_get_with_history(
        self, test_db: Session, nba_league: League, nba_season: Season, lakers: Team
    ):
        """Test retrieving a player with team history loaded."""
        service = PlayerService(test_db)
        season_service = SeasonService(test_db)
        team_service = TeamService(test_db)

        old_season = season_service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )
        heat = team_service.create_team(
            TeamCreate(
                name="Miami Heat",
                short_name="MIA",
                city="Miami",
                country="USA",
            )
        )

        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        service.add_to_team(player.id, heat.id, old_season.id, jersey_number=6)
        service.add_to_team(player.id, lakers.id, nba_season.id, jersey_number=23)

        result = service.get_with_history(player.id)

        assert result is not None
        assert result.full_name == "LeBron James"
        assert len(result.team_histories) == 2

        team_names = [h.team.name for h in result.team_histories]
        assert "Los Angeles Lakers" in team_names
        assert "Miami Heat" in team_names

    def test_get_with_history_not_found(self, test_db: Session):
        """Test get_with_history returns None for non-existent player."""
        service = PlayerService(test_db)
        fake_id = uuid.uuid4()

        result = service.get_with_history(fake_id)

        assert result is None

    def test_get_team_history(
        self, test_db: Session, nba_league: League, nba_season: Season, lakers: Team
    ):
        """Test retrieving all team history entries for a player."""
        service = PlayerService(test_db)
        season_service = SeasonService(test_db)
        team_service = TeamService(test_db)

        old_season = season_service.create_season(
            SeasonCreate(
                league_id=nba_league.id,
                name="2022-23",
                start_date=date(2022, 10, 18),
                end_date=date(2023, 6, 12),
            )
        )
        heat = team_service.create_team(
            TeamCreate(
                name="Miami Heat",
                short_name="MIA",
                city="Miami",
                country="USA",
            )
        )

        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )
        service.add_to_team(player.id, heat.id, old_season.id, jersey_number=6)
        service.add_to_team(player.id, lakers.id, nba_season.id, jersey_number=23)

        history = service.get_team_history(player.id)

        assert len(history) == 2
        for entry in history:
            assert entry.team is not None
            assert entry.season is not None

        seasons = [h.season.name for h in history]
        assert "2022-23" in seasons
        assert "2023-24" in seasons

    def test_get_team_history_empty(self, test_db: Session):
        """Test get_team_history returns empty list for player with no history."""
        service = PlayerService(test_db)
        player = service.create_player(
            PlayerCreate(
                first_name="LeBron",
                last_name="James",
            )
        )

        history = service.get_team_history(player.id)

        assert history == []
