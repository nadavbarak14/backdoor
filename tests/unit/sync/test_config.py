"""
Tests for the sync configuration module.

Tests cover:
- SyncSourceConfig initialization and validation
- SyncConfig source management
- Loading config from settings
"""

import pytest

from src.sync.config import SyncConfig, SyncSourceConfig


class TestSyncSourceConfig:
    """Tests for SyncSourceConfig dataclass."""

    def test_creates_with_defaults(self) -> None:
        """Should create config with default values."""
        config = SyncSourceConfig(source_name="test")

        assert config.source_name == "test"
        assert config.enabled is True
        assert config.auto_sync_enabled is False
        assert config.sync_interval_minutes == 60

    def test_creates_with_custom_values(self) -> None:
        """Should create config with custom values."""
        config = SyncSourceConfig(
            source_name="custom",
            enabled=False,
            auto_sync_enabled=True,
            sync_interval_minutes=30,
        )

        assert config.source_name == "custom"
        assert config.enabled is False
        assert config.auto_sync_enabled is True
        assert config.sync_interval_minutes == 30

    def test_raises_for_invalid_interval(self) -> None:
        """Should raise ValueError for non-positive sync interval."""
        with pytest.raises(ValueError, match="sync_interval_minutes must be positive"):
            SyncSourceConfig(source_name="test", sync_interval_minutes=0)

        with pytest.raises(ValueError, match="sync_interval_minutes must be positive"):
            SyncSourceConfig(source_name="test", sync_interval_minutes=-1)


class TestSyncConfigIsSourceEnabled:
    """Tests for SyncConfig.is_source_enabled method."""

    def test_returns_true_for_enabled_source(self) -> None:
        """Should return True when source exists and is enabled."""
        config = SyncConfig(
            sources={"winner": SyncSourceConfig(source_name="winner", enabled=True)}
        )

        assert config.is_source_enabled("winner") is True

    def test_returns_false_for_disabled_source(self) -> None:
        """Should return False when source exists but is disabled."""
        config = SyncConfig(
            sources={"winner": SyncSourceConfig(source_name="winner", enabled=False)}
        )

        assert config.is_source_enabled("winner") is False

    def test_returns_false_for_unknown_source(self) -> None:
        """Should return False when source doesn't exist."""
        config = SyncConfig(sources={})

        assert config.is_source_enabled("unknown") is False


class TestSyncConfigGetSourceConfig:
    """Tests for SyncConfig.get_source_config method."""

    def test_returns_config_when_exists(self) -> None:
        """Should return source config when it exists."""
        source_config = SyncSourceConfig(source_name="winner")
        config = SyncConfig(sources={"winner": source_config})

        result = config.get_source_config("winner")

        assert result is source_config

    def test_returns_none_when_not_exists(self) -> None:
        """Should return None when source doesn't exist."""
        config = SyncConfig(sources={})

        result = config.get_source_config("unknown")

        assert result is None


class TestSyncConfigGetEnabledSources:
    """Tests for SyncConfig.get_enabled_sources method."""

    def test_returns_only_enabled_sources(self) -> None:
        """Should return only enabled source names."""
        config = SyncConfig(
            sources={
                "winner": SyncSourceConfig(source_name="winner", enabled=True),
                "euroleague": SyncSourceConfig(source_name="euroleague", enabled=True),
                "disabled": SyncSourceConfig(source_name="disabled", enabled=False),
            }
        )

        result = config.get_enabled_sources()

        assert "winner" in result
        assert "euroleague" in result
        assert "disabled" not in result

    def test_returns_empty_when_none_enabled(self) -> None:
        """Should return empty list when no sources are enabled."""
        config = SyncConfig(
            sources={
                "source1": SyncSourceConfig(source_name="source1", enabled=False),
                "source2": SyncSourceConfig(source_name="source2", enabled=False),
            }
        )

        result = config.get_enabled_sources()

        assert result == []

    def test_returns_empty_when_no_sources(self) -> None:
        """Should return empty list when no sources configured."""
        config = SyncConfig(sources={})

        result = config.get_enabled_sources()

        assert result == []


class TestSyncConfigGetAutoSyncSources:
    """Tests for SyncConfig.get_auto_sync_sources method."""

    def test_returns_auto_sync_enabled_sources(self) -> None:
        """Should return only sources with auto_sync_enabled."""
        config = SyncConfig(
            sources={
                "auto": SyncSourceConfig(
                    source_name="auto", enabled=True, auto_sync_enabled=True
                ),
                "manual": SyncSourceConfig(
                    source_name="manual", enabled=True, auto_sync_enabled=False
                ),
            }
        )

        result = config.get_auto_sync_sources()

        assert "auto" in result
        assert "manual" not in result

    def test_excludes_disabled_sources(self) -> None:
        """Should exclude disabled sources even if auto_sync_enabled."""
        config = SyncConfig(
            sources={
                "disabled_auto": SyncSourceConfig(
                    source_name="disabled_auto", enabled=False, auto_sync_enabled=True
                ),
            }
        )

        result = config.get_auto_sync_sources()

        assert "disabled_auto" not in result


class TestSyncConfigRegisterSource:
    """Tests for SyncConfig.register_source method."""

    def test_adds_new_source(self) -> None:
        """Should add new source configuration."""
        config = SyncConfig(sources={})
        source_config = SyncSourceConfig(source_name="new_source")

        config.register_source(source_config)

        assert config.is_source_enabled("new_source") is True
        assert config.get_source_config("new_source") is source_config

    def test_overwrites_existing_source(self) -> None:
        """Should overwrite existing source configuration."""
        old_config = SyncSourceConfig(source_name="test", enabled=True)
        new_config = SyncSourceConfig(source_name="test", enabled=False)
        config = SyncConfig(sources={"test": old_config})

        config.register_source(new_config)

        assert config.is_source_enabled("test") is False
        assert config.get_source_config("test") is new_config


class TestSyncConfigFromSettings:
    """Tests for SyncConfig.from_settings class method."""

    def test_loads_default_sources(self) -> None:
        """Should load default source configurations."""
        config = SyncConfig.from_settings()

        # Should have winner and euroleague
        assert config.is_source_enabled("winner") is True
        assert config.is_source_enabled("euroleague") is True

    def test_winner_config_values(self) -> None:
        """Should have correct winner config values."""
        config = SyncConfig.from_settings()
        winner = config.get_source_config("winner")

        assert winner is not None
        assert winner.source_name == "winner"
        assert winner.enabled is True
        assert winner.auto_sync_enabled is False
        assert winner.sync_interval_minutes == 60

    def test_euroleague_config_values(self) -> None:
        """Should have correct euroleague config values."""
        config = SyncConfig.from_settings()
        euroleague = config.get_source_config("euroleague")

        assert euroleague is not None
        assert euroleague.source_name == "euroleague"
        assert euroleague.enabled is True
        assert euroleague.auto_sync_enabled is False
        assert euroleague.sync_interval_minutes == 30


class TestSyncConfigCreateDisabled:
    """Tests for SyncConfig.create_disabled class method."""

    def test_creates_empty_config(self) -> None:
        """Should create config with no sources."""
        config = SyncConfig.create_disabled()

        assert config.get_enabled_sources() == []
        assert config.sources == {}

    def test_no_sources_enabled(self) -> None:
        """Should have no enabled sources."""
        config = SyncConfig.create_disabled()

        assert config.is_source_enabled("winner") is False
        assert config.is_source_enabled("euroleague") is False
