"""
Unit tests for LeagueService and SeasonService.

Tests league and season business logic including code lookup,
season counting, and current season management.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models.league import League
from src.schemas.league import LeagueCreate, LeagueUpdate, SeasonCreate, SeasonUpdate
from src.services.league import LeagueService, SeasonService


class TestLeagueService:
    """Tests for LeagueService operations."""

    def test_get_by_code_existing(self, test_db: Session):
        """Test finding a league by its unique code."""
        service = LeagueService(test_db)
        service.create_league(LeagueCreate(
            name="National Basketball Association",
            code="NBA",
            country="USA",
        ))

        result = service.get_by_code("NBA")

        assert result is not None
        assert result.code == "NBA"
        assert result.name == "National Basketball Association"

    def test_get_by_code_not_found(self, test_db: Session):
        """Test get_by_code returns None for non-existent code."""
        service = LeagueService(test_db)

        result = service.get_by_code("NONEXISTENT")

        assert result is None

    def test_get_with_season_count_no_seasons(self, test_db: Session):
        """Test get_with_season_count returns 0 when league has no seasons."""
        service = LeagueService(test_db)
        league = service.create_league(LeagueCreate(
            name="NBA",
            code="NBA",
            country="USA",
        ))

        result_league, count = service.get_with_season_count(league.id)

        assert result_league is not None
        assert result_league.id == league.id
        assert count == 0

    def test_get_with_season_count_with_seasons(self, test_db: Session):
        """Test get_with_season_count returns correct count."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)

        league = league_service.create_league(LeagueCreate(
            name="NBA",
            code="NBA",
            country="USA",
        ))
        season_service.create_season(SeasonCreate(
            league_id=league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
        ))
        season_service.create_season(SeasonCreate(
            league_id=league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
        ))

        result_league, count = league_service.get_with_season_count(league.id)

        assert result_league is not None
        assert count == 2

    def test_get_with_season_count_not_found(self, test_db: Session):
        """Test get_with_season_count returns None, 0 for non-existent league."""
        service = LeagueService(test_db)
        fake_id = uuid.uuid4()

        result_league, count = service.get_with_season_count(fake_id)

        assert result_league is None
        assert count == 0

    def test_get_all_with_season_counts(self, test_db: Session):
        """Test get_all_with_season_counts returns leagues with counts."""
        league_service = LeagueService(test_db)
        season_service = SeasonService(test_db)

        nba = league_service.create_league(LeagueCreate(
            name="NBA",
            code="NBA",
            country="USA",
        ))
        league_service.create_league(LeagueCreate(
            name="EuroLeague",
            code="EL",
            country="Europe",
        ))

        season_service.create_season(SeasonCreate(
            league_id=nba.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
        ))
        season_service.create_season(SeasonCreate(
            league_id=nba.id,
            name="2024-25",
            start_date=date(2024, 10, 22),
            end_date=date(2025, 6, 15),
        ))

        results = league_service.get_all_with_season_counts()

        assert len(results) == 2
        nba_result = next(
            (league, count) for league, count in results if league.code == "NBA"
        )
        el_result = next(
            (league, count) for league, count in results if league.code == "EL"
        )
        assert nba_result[1] == 2
        assert el_result[1] == 0

    def test_create_league(self, test_db: Session):
        """Test creating a league from Pydantic schema."""
        service = LeagueService(test_db)
        data = LeagueCreate(
            name="National Basketball Association",
            code="NBA",
            country="United States",
        )

        league = service.create_league(data)

        assert league.id is not None
        assert league.name == "National Basketball Association"
        assert league.code == "NBA"
        assert league.country == "United States"

    def test_update_league(self, test_db: Session):
        """Test updating a league from Pydantic schema."""
        service = LeagueService(test_db)
        league = service.create_league(LeagueCreate(
            name="NBA",
            code="NBA",
            country="USA",
        ))

        updated = service.update_league(
            league.id,
            LeagueUpdate(name="National Basketball Association")
        )

        assert updated is not None
        assert updated.name == "National Basketball Association"
        assert updated.code == "NBA"  # Unchanged

    def test_update_league_not_found(self, test_db: Session):
        """Test updating non-existent league returns None."""
        service = LeagueService(test_db)
        fake_id = uuid.uuid4()

        result = service.update_league(fake_id, LeagueUpdate(name="New"))

        assert result is None


class TestSeasonService:
    """Tests for SeasonService operations."""

    @pytest.fixture
    def nba_league(self, test_db: Session) -> League:
        """Create an NBA league for testing."""
        service = LeagueService(test_db)
        return service.create_league(LeagueCreate(
            name="NBA",
            code="NBA",
            country="USA",
        ))

    def test_get_by_league(self, test_db: Session, nba_league: League):
        """Test retrieving seasons for a specific league."""
        service = SeasonService(test_db)
        service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
        ))
        service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
        ))

        seasons = service.get_by_league(nba_league.id)

        assert len(seasons) == 2
        assert all(s.league_id == nba_league.id for s in seasons)

    def test_get_by_league_empty(self, test_db: Session, nba_league: League):
        """Test get_by_league returns empty list for league with no seasons."""
        service = SeasonService(test_db)

        seasons = service.get_by_league(nba_league.id)

        assert seasons == []

    def test_get_current_with_league(self, test_db: Session, nba_league: League):
        """Test get_current returns current season for a league."""
        service = SeasonService(test_db)
        service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
            is_current=False,
        ))
        service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=True,
        ))

        current = service.get_current(nba_league.id)

        assert current is not None
        assert current.name == "2023-24"
        assert current.is_current is True

    def test_get_current_no_current_season(self, test_db: Session, nba_league: League):
        """Test get_current returns None when no current season exists."""
        service = SeasonService(test_db)
        service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=False,
        ))

        current = service.get_current(nba_league.id)

        assert current is None

    def test_get_current_any_league(self, test_db: Session, nba_league: League):
        """Test get_current without league_id returns any current season."""
        service = SeasonService(test_db)
        service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=True,
        ))

        current = service.get_current()

        assert current is not None
        assert current.is_current is True

    def test_create_season_sets_current(self, test_db: Session, nba_league: League):
        """Test creating a current season unsets other current seasons."""
        service = SeasonService(test_db)
        first = service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
            is_current=True,
        ))

        second = service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=True,
        ))

        test_db.refresh(first)
        assert first.is_current is False
        assert second.is_current is True

    def test_set_current(self, test_db: Session, nba_league: League):
        """Test set_current marks a season as current and unsets others."""
        service = SeasonService(test_db)
        first = service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
            is_current=True,
        ))
        second = service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=False,
        ))

        result = service.set_current(second.id)

        test_db.refresh(first)
        assert result is not None
        assert result.is_current is True
        assert first.is_current is False

    def test_set_current_not_found(self, test_db: Session):
        """Test set_current returns None for non-existent season."""
        service = SeasonService(test_db)
        fake_id = uuid.uuid4()

        result = service.set_current(fake_id)

        assert result is None

    def test_update_season_is_current(self, test_db: Session, nba_league: League):
        """Test updating is_current unsets other seasons in league."""
        service = SeasonService(test_db)
        first = service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2022-23",
            start_date=date(2022, 10, 18),
            end_date=date(2023, 6, 12),
            is_current=True,
        ))
        second = service.create_season(SeasonCreate(
            league_id=nba_league.id,
            name="2023-24",
            start_date=date(2023, 10, 24),
            end_date=date(2024, 6, 17),
            is_current=False,
        ))

        service.update_season(second.id, SeasonUpdate(is_current=True))

        test_db.refresh(first)
        test_db.refresh(second)
        assert first.is_current is False
        assert second.is_current is True
