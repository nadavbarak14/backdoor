"""
Unit tests for TeamService.

Tests team business logic including filtering, external ID lookup,
roster retrieval, and season associations.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.schemas.league import LeagueCreate, SeasonCreate
from src.schemas.team import TeamCreate, TeamFilter, TeamUpdate
from src.services.league import LeagueService, SeasonService
from src.services.team import TeamService


class TestTeamService:
    """Tests for TeamService operations."""

    @pytest.fixture
    def nba_league(self, test_db: Session) -> League:
        """Create an NBA league for testing."""
        service = LeagueService(test_db)
        return service.create_league(LeagueCreate(
            name="NBA",
            code="NBA",
            country="USA",
        ))

    @pytest.fixture
    def nba_season(self, test_db: Session, nba_league: League) -> Season:
        """Create an NBA season for testing."""
        service = SeasonService(test_db)
        return service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=True,
        ))

    def test_create_team(self, test_db: Session):
        """Test creating a team from Pydantic schema."""
        service = TeamService(test_db)
        data = TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={"nba": "1610612747"},
        )

        team = service.create_team(data)

        assert team.id is not None
        assert team.name == "Los Angeles Lakers"
        assert team.short_name == "LAL"
        assert team.external_ids == {"nba": "1610612747"}

    def test_create_team_without_external_ids(self, test_db: Session):
        """Test creating a team without external_ids defaults to empty dict."""
        service = TeamService(test_db)
        data = TeamCreate(
            name="New Team",
            short_name="NT",
            city="City",
            country="Country",
        )

        team = service.create_team(data)

        assert team.external_ids == {}

    def test_update_team(self, test_db: Session):
        """Test updating a team from Pydantic schema."""
        service = TeamService(test_db)
        team = service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))

        updated = service.update_team(team.id, TeamUpdate(city="Hollywood"))

        assert updated is not None
        assert updated.city == "Hollywood"
        assert updated.name == "Los Angeles Lakers"  # Unchanged

    def test_get_by_external_id_found(self, test_db: Session):
        """Test finding a team by external ID."""
        service = TeamService(test_db)
        service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={"nba": "1610612747", "espn": "13"},
        ))

        result = service.get_by_external_id("nba", "1610612747")

        assert result is not None
        assert result.name == "Los Angeles Lakers"

    def test_get_by_external_id_not_found(self, test_db: Session):
        """Test get_by_external_id returns None for non-existent ID."""
        service = TeamService(test_db)
        service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={"nba": "1610612747"},
        ))

        result = service.get_by_external_id("nba", "999999")

        assert result is None

    def test_get_by_external_id_wrong_source(self, test_db: Session):
        """Test get_by_external_id returns None for wrong source."""
        service = TeamService(test_db)
        service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
            external_ids={"nba": "1610612747"},
        ))

        result = service.get_by_external_id("espn", "1610612747")

        assert result is None

    def test_get_filtered_by_country(self, test_db: Session):
        """Test filtering teams by country."""
        service = TeamService(test_db)
        service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        service.create_team(TeamCreate(
            name="Real Madrid",
            short_name="RMD",
            city="Madrid",
            country="Spain",
        ))

        teams, total = service.get_filtered(TeamFilter(country="USA"))

        assert total == 1
        assert len(teams) == 1
        assert teams[0].name == "Los Angeles Lakers"

    def test_get_filtered_by_search(self, test_db: Session):
        """Test filtering teams by name search."""
        service = TeamService(test_db)
        service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        service.create_team(TeamCreate(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        ))

        teams, total = service.get_filtered(TeamFilter(search="Lakers"))

        assert total == 1
        assert teams[0].name == "Los Angeles Lakers"

    def test_get_filtered_by_short_name_search(self, test_db: Session):
        """Test filtering teams by short name search."""
        service = TeamService(test_db)
        service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        service.create_team(TeamCreate(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        ))

        teams, total = service.get_filtered(TeamFilter(search="LAL"))

        assert total == 1
        assert teams[0].short_name == "LAL"

    def test_get_filtered_by_season(
        self, test_db: Session, nba_league: League, nba_season: Season
    ):
        """Test filtering teams by season."""
        service = TeamService(test_db)
        lakers = service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        service.create_team(TeamCreate(
            name="Boston Celtics",
            short_name="BOS",
            city="Boston",
            country="USA",
        ))
        service.add_to_season(lakers.id, nba_season.id)

        teams, total = service.get_filtered(TeamFilter(season_id=nba_season.id))

        assert total == 1
        assert teams[0].name == "Los Angeles Lakers"

    def test_get_filtered_pagination(self, test_db: Session):
        """Test filtered results respect pagination."""
        service = TeamService(test_db)
        for i in range(5):
            service.create_team(TeamCreate(
                name=f"Team {i}",
                short_name=f"T{i}",
                city="City",
                country="USA",
            ))

        teams, total = service.get_filtered(TeamFilter(country="USA"), skip=2, limit=2)

        assert total == 5
        assert len(teams) == 2

    def test_add_to_season(
        self, test_db: Session, nba_league: League, nba_season: Season
    ):
        """Test adding a team to a season."""
        service = TeamService(test_db)
        team = service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))

        result = service.add_to_season(team.id, nba_season.id)

        assert result is not None
        assert result.team_id == team.id
        assert result.season_id == nba_season.id

    def test_add_to_season_already_exists(
        self, test_db: Session, nba_league: League, nba_season: Season
    ):
        """Test adding a team to season when already exists returns existing."""
        service = TeamService(test_db)
        team = service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        first = service.add_to_season(team.id, nba_season.id)

        second = service.add_to_season(team.id, nba_season.id)

        assert second is not None
        assert second.team_id == first.team_id
        assert second.season_id == first.season_id

    def test_add_to_season_team_not_found(self, test_db: Session, nba_season: Season):
        """Test add_to_season returns None for non-existent team."""
        service = TeamService(test_db)
        fake_team_id = uuid.uuid4()

        result = service.add_to_season(fake_team_id, nba_season.id)

        assert result is None

    def test_add_to_season_season_not_found(self, test_db: Session):
        """Test add_to_season returns None for non-existent season."""
        service = TeamService(test_db)
        team = service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        fake_season_id = uuid.uuid4()

        result = service.add_to_season(team.id, fake_season_id)

        assert result is None

    def test_get_roster(
        self, test_db: Session, nba_league: League, nba_season: Season
    ):
        """Test retrieving a team's roster for a season."""
        team_service = TeamService(test_db)
        team = team_service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))
        team_service.add_to_season(team.id, nba_season.id)

        player1 = Player(
            first_name="LeBron",
            last_name="James",
            position="SF",
            external_ids={},
        )
        player2 = Player(
            first_name="Anthony",
            last_name="Davis",
            position="PF",
            external_ids={},
        )
        test_db.add_all([player1, player2])
        test_db.commit()

        history1 = PlayerTeamHistory(
            player_id=player1.id,
            team_id=team.id,
            season_id=nba_season.id,
            jersey_number=23,
            position="SF",
        )
        history2 = PlayerTeamHistory(
            player_id=player2.id,
            team_id=team.id,
            season_id=nba_season.id,
            jersey_number=3,
            position="PF",
        )
        test_db.add_all([history1, history2])
        test_db.commit()

        roster = team_service.get_roster(team.id, nba_season.id)

        assert len(roster) == 2
        player_names = [entry.player.full_name for entry in roster]
        assert "LeBron James" in player_names
        assert "Anthony Davis" in player_names

    def test_get_roster_empty(
        self, test_db: Session, nba_league: League, nba_season: Season
    ):
        """Test get_roster returns empty list for team with no players."""
        team_service = TeamService(test_db)
        team = team_service.create_team(TeamCreate(
            name="Los Angeles Lakers",
            short_name="LAL",
            city="Los Angeles",
            country="USA",
        ))

        roster = team_service.get_roster(team.id, nba_season.id)

        assert roster == []
