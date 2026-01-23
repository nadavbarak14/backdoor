"""
Tests for Core Configuration Module

Tests that settings load correctly from environment variables,
defaults work as expected, and the Settings class behaves properly.
"""

import os
from unittest.mock import patch

from src.core.config import Settings


class TestSettingsDefaults:
    """Test that default values are set correctly."""

    def test_project_name_default(self) -> None:
        """PROJECT_NAME should default to 'Basketball Analytics'."""
        settings = Settings()
        assert settings.PROJECT_NAME == "Basketball Analytics"

    def test_debug_default(self) -> None:
        """DEBUG should default to False."""
        settings = Settings()
        assert settings.DEBUG is False

    def test_database_url_default(self) -> None:
        """DATABASE_URL should default to SQLite file."""
        settings = Settings()
        assert settings.DATABASE_URL == "sqlite:///./basketball.db"

    def test_test_database_url_default(self) -> None:
        """TEST_DATABASE_URL should default to in-memory SQLite."""
        settings = Settings()
        assert settings.TEST_DATABASE_URL == "sqlite:///:memory:"

    def test_api_prefix_default(self) -> None:
        """API_PREFIX should default to '/api/v1'."""
        settings = Settings()
        assert settings.API_PREFIX == "/api/v1"


class TestSettingsFromEnvironment:
    """Test that settings load from environment variables."""

    def test_project_name_from_env(self) -> None:
        """PROJECT_NAME should be overridable via environment."""
        with patch.dict(os.environ, {"PROJECT_NAME": "Test App"}):
            settings = Settings()
            assert settings.PROJECT_NAME == "Test App"

    def test_debug_from_env_true(self) -> None:
        """DEBUG should parse 'true' as True."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            settings = Settings()
            assert settings.DEBUG is True

    def test_debug_from_env_false(self) -> None:
        """DEBUG should parse 'false' as False."""
        with patch.dict(os.environ, {"DEBUG": "false"}):
            settings = Settings()
            assert settings.DEBUG is False

    def test_debug_from_env_numeric(self) -> None:
        """DEBUG should parse '1' as True."""
        with patch.dict(os.environ, {"DEBUG": "1"}):
            settings = Settings()
            assert settings.DEBUG is True

    def test_database_url_from_env(self) -> None:
        """DATABASE_URL should be overridable via environment."""
        expected_url = "postgresql://user:pass@localhost/testdb"
        with patch.dict(os.environ, {"DATABASE_URL": expected_url}):
            settings = Settings()
            assert settings.DATABASE_URL == expected_url

    def test_api_prefix_from_env(self) -> None:
        """API_PREFIX should be overridable via environment."""
        with patch.dict(os.environ, {"API_PREFIX": "/api/v2"}):
            settings = Settings()
            assert settings.API_PREFIX == "/api/v2"


class TestSettingsImport:
    """Test that settings can be imported correctly."""

    def test_import_settings_singleton(self) -> None:
        """Should be able to import settings singleton from src.core."""
        from src.core import settings

        assert settings is not None
        assert isinstance(settings, Settings)

    def test_import_settings_class(self) -> None:
        """Should be able to import Settings class from src.core."""
        from src.core import Settings as SettingsClass

        assert SettingsClass is Settings

    def test_import_get_settings(self) -> None:
        """Should be able to import get_settings from src.core."""
        from src.core import get_settings

        result = get_settings()
        assert isinstance(result, Settings)


class TestSettingsTypes:
    """Test that settings have correct types."""

    def test_project_name_is_string(self) -> None:
        """PROJECT_NAME should be a string."""
        settings = Settings()
        assert isinstance(settings.PROJECT_NAME, str)

    def test_debug_is_bool(self) -> None:
        """DEBUG should be a boolean."""
        settings = Settings()
        assert isinstance(settings.DEBUG, bool)

    def test_database_url_is_string(self) -> None:
        """DATABASE_URL should be a string."""
        settings = Settings()
        assert isinstance(settings.DATABASE_URL, str)

    def test_api_prefix_is_string(self) -> None:
        """API_PREFIX should be a string."""
        settings = Settings()
        assert isinstance(settings.API_PREFIX, str)
