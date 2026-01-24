"""
Unit tests for BaseService.

Tests the generic CRUD operations provided by the base service class.
Uses League model as a concrete implementation for testing.
"""

import uuid

from sqlalchemy.orm import Session

from src.models.league import League
from src.services.base import BaseService


class TestBaseService:
    """Tests for BaseService CRUD operations."""

    def test_create_entity(self, test_db: Session):
        """Test creating a new entity."""
        service = BaseService[League](test_db, League)

        league = service.create(
            {
                "name": "National Basketball Association",
                "code": "NBA",
                "country": "USA",
            }
        )

        assert league.id is not None
        assert league.name == "National Basketball Association"
        assert league.code == "NBA"
        assert league.country == "USA"
        assert league.created_at is not None

    def test_get_by_id_existing(self, test_db: Session):
        """Test retrieving an existing entity by ID."""
        service = BaseService[League](test_db, League)
        created = service.create(
            {
                "name": "NBA",
                "code": "NBA",
                "country": "USA",
            }
        )

        result = service.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.name == "NBA"

    def test_get_by_id_not_found(self, test_db: Session):
        """Test retrieving a non-existent entity returns None."""
        service = BaseService[League](test_db, League)
        fake_id = uuid.uuid4()

        result = service.get_by_id(fake_id)

        assert result is None

    def test_get_all_empty(self, test_db: Session):
        """Test get_all returns empty list when no entities exist."""
        service = BaseService[League](test_db, League)

        result = service.get_all()

        assert result == []

    def test_get_all_with_entities(self, test_db: Session):
        """Test get_all returns all entities."""
        service = BaseService[League](test_db, League)
        service.create({"name": "NBA", "code": "NBA", "country": "USA"})
        service.create({"name": "EuroLeague", "code": "EL", "country": "Europe"})

        result = service.get_all()

        assert len(result) == 2

    def test_get_all_with_pagination(self, test_db: Session):
        """Test get_all respects skip and limit parameters."""
        service = BaseService[League](test_db, League)
        for i in range(5):
            service.create(
                {
                    "name": f"League {i}",
                    "code": f"L{i}",
                    "country": "Country",
                }
            )

        result = service.get_all(skip=2, limit=2)

        assert len(result) == 2

    def test_count_empty(self, test_db: Session):
        """Test count returns 0 when no entities exist."""
        service = BaseService[League](test_db, League)

        result = service.count()

        assert result == 0

    def test_count_with_entities(self, test_db: Session):
        """Test count returns correct number of entities."""
        service = BaseService[League](test_db, League)
        service.create({"name": "NBA", "code": "NBA", "country": "USA"})
        service.create({"name": "EuroLeague", "code": "EL", "country": "Europe"})
        service.create({"name": "ACB", "code": "ACB", "country": "Spain"})

        result = service.count()

        assert result == 3

    def test_update_existing(self, test_db: Session):
        """Test updating an existing entity."""
        service = BaseService[League](test_db, League)
        created = service.create(
            {
                "name": "NBA",
                "code": "NBA",
                "country": "USA",
            }
        )

        updated = service.update(created.id, {"name": "Updated NBA"})

        assert updated is not None
        assert updated.name == "Updated NBA"
        assert updated.code == "NBA"  # Unchanged

    def test_update_not_found(self, test_db: Session):
        """Test updating a non-existent entity returns None."""
        service = BaseService[League](test_db, League)
        fake_id = uuid.uuid4()

        result = service.update(fake_id, {"name": "New Name"})

        assert result is None

    def test_update_ignores_none_values(self, test_db: Session):
        """Test update ignores None values in data dict."""
        service = BaseService[League](test_db, League)
        created = service.create(
            {
                "name": "NBA",
                "code": "NBA",
                "country": "USA",
            }
        )

        updated = service.update(created.id, {"name": "Updated", "code": None})

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.code == "NBA"  # Should not be changed to None

    def test_delete_existing(self, test_db: Session):
        """Test deleting an existing entity."""
        service = BaseService[League](test_db, League)
        created = service.create(
            {
                "name": "NBA",
                "code": "NBA",
                "country": "USA",
            }
        )

        result = service.delete(created.id)

        assert result is True
        assert service.get_by_id(created.id) is None

    def test_delete_not_found(self, test_db: Session):
        """Test deleting a non-existent entity returns False."""
        service = BaseService[League](test_db, League)
        fake_id = uuid.uuid4()

        result = service.delete(fake_id)

        assert result is False
