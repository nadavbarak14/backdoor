"""
Base Model Tests

Tests for src/models/base.py covering:
- Base declarative base functionality
- UUIDMixin column generation
- TimestampMixin column generation
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import String, create_engine, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models import Base, TimestampMixin, UUIDMixin


# Test model that uses both mixins
class TestModel(UUIDMixin, TimestampMixin, Base):
    """Test model for validating mixins."""

    __tablename__ = "test_models"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class TestBase:
    """Tests for the Base declarative base."""

    def test_base_exists(self):
        """Base should be defined and accessible."""
        assert Base is not None

    def test_base_has_metadata(self):
        """Base should have metadata attribute."""
        assert hasattr(Base, "metadata")

    def test_base_has_registry(self):
        """Base should have registry attribute."""
        assert hasattr(Base, "registry")

    def test_model_can_inherit_from_base(self):
        """Models should be able to inherit from Base."""
        # TestModel already inherits from Base
        assert issubclass(TestModel, Base)

    def test_model_has_tablename(self):
        """Model should have __tablename__ accessible."""
        assert TestModel.__tablename__ == "test_models"


class TestUUIDMixin:
    """Tests for the UUIDMixin."""

    def test_mixin_adds_id_column(self):
        """UUIDMixin should add an id column."""
        mapper = inspect(TestModel)
        columns = [c.key for c in mapper.columns]
        assert "id" in columns

    def test_id_is_primary_key(self):
        """id column should be a primary key."""
        mapper = inspect(TestModel)
        primary_keys = [c.key for c in mapper.primary_key]
        assert "id" in primary_keys

    def test_id_generates_uuid(self, db_session: Session):
        """id should auto-generate a UUID on insert."""
        model = TestModel(name="Test")
        db_session.add(model)
        db_session.commit()

        assert model.id is not None
        assert isinstance(model.id, uuid.UUID)

    def test_id_generates_unique_uuids(self, db_session: Session):
        """Each model instance should get a unique UUID."""
        model1 = TestModel(name="Test 1")
        model2 = TestModel(name="Test 2")
        db_session.add_all([model1, model2])
        db_session.commit()

        assert model1.id != model2.id

    def test_id_is_uuid4_format(self, db_session: Session):
        """Generated UUID should be version 4."""
        model = TestModel(name="Test")
        db_session.add(model)
        db_session.commit()

        # UUID4 has version 4 in the version field
        assert model.id.version == 4


class TestTimestampMixin:
    """Tests for the TimestampMixin."""

    def test_mixin_adds_created_at_column(self):
        """TimestampMixin should add a created_at column."""
        mapper = inspect(TestModel)
        columns = [c.key for c in mapper.columns]
        assert "created_at" in columns

    def test_mixin_adds_updated_at_column(self):
        """TimestampMixin should add an updated_at column."""
        mapper = inspect(TestModel)
        columns = [c.key for c in mapper.columns]
        assert "updated_at" in columns

    def test_created_at_is_set_on_insert(self, db_session: Session):
        """created_at should be set automatically on insert."""
        model = TestModel(name="Test")
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        assert model.created_at is not None
        assert isinstance(model.created_at, datetime)

    def test_updated_at_is_set_on_insert(self, db_session: Session):
        """updated_at should be set automatically on insert."""
        model = TestModel(name="Test")
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        assert model.updated_at is not None
        assert isinstance(model.updated_at, datetime)

    def test_created_at_does_not_change_on_update(self, db_session: Session):
        """created_at should remain unchanged on update."""
        model = TestModel(name="Test")
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        original_created_at = model.created_at

        # Update the model
        model.name = "Updated Test"
        db_session.commit()
        db_session.refresh(model)

        assert model.created_at == original_created_at


class TestMixinCombination:
    """Tests for using both mixins together."""

    def test_model_has_all_mixin_columns(self):
        """Model with both mixins should have all expected columns."""
        mapper = inspect(TestModel)
        columns = [c.key for c in mapper.columns]

        assert "id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
        assert "name" in columns

    def test_full_model_lifecycle(self, db_session: Session):
        """Model should work correctly through full CRUD lifecycle."""
        # Create
        model = TestModel(name="Original")
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        model_id = model.id
        assert model.id is not None
        assert model.created_at is not None
        assert model.name == "Original"

        # Read
        fetched = db_session.get(TestModel, model_id)
        assert fetched is not None
        assert fetched.name == "Original"

        # Update
        fetched.name = "Updated"
        db_session.commit()
        db_session.refresh(fetched)
        assert fetched.name == "Updated"

        # Delete
        db_session.delete(fetched)
        db_session.commit()

        deleted = db_session.get(TestModel, model_id)
        assert deleted is None


class TestImports:
    """Tests for module imports."""

    def test_import_from_base(self):
        """Should be able to import from base module."""
        from src.models.base import Base, TimestampMixin, UUIDMixin

        assert Base is not None
        assert UUIDMixin is not None
        assert TimestampMixin is not None

    def test_import_from_models_package(self):
        """Should be able to import from models package."""
        from src.models import Base, TimestampMixin, UUIDMixin

        assert Base is not None
        assert UUIDMixin is not None
        assert TimestampMixin is not None
