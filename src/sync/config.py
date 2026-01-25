"""
Sync Configuration Module

Provides configuration classes for sync sources in the Basketball Analytics
Platform. Supports enabling/disabling sources and configuring future
automatic sync scheduling.

Usage:
    from src.sync.config import SyncConfig, SyncSourceConfig

    # Load from settings
    config = SyncConfig.from_settings()

    # Check if a source is enabled
    if config.is_source_enabled("winner"):
        sync_winner_data()

    # Get source config
    source_config = config.get_source_config("euroleague")
    print(source_config.sync_interval_minutes)
"""

from dataclasses import dataclass, field


@dataclass
class SyncSourceConfig:
    """
    Configuration for a single sync source.

    Each sync source (winner, euroleague, etc.) has its own configuration
    that controls whether it's enabled and how automatic sync should behave.

    Attributes:
        source_name: Unique identifier for the source (e.g., "winner")
        enabled: Whether this source is enabled for syncing
        auto_sync_enabled: Whether automatic sync is enabled (future scheduler)
        sync_interval_minutes: Minutes between automatic syncs (future scheduler)

    Example:
        >>> config = SyncSourceConfig(
        ...     source_name="winner",
        ...     enabled=True,
        ...     auto_sync_enabled=False,
        ...     sync_interval_minutes=60
        ... )
    """

    source_name: str
    enabled: bool = True
    auto_sync_enabled: bool = False
    sync_interval_minutes: int = 60

    def __post_init__(self) -> None:
        """
        Validate configuration values after initialization.

        Raises:
            ValueError: If sync_interval_minutes is not positive
        """
        if self.sync_interval_minutes <= 0:
            raise ValueError("sync_interval_minutes must be positive")


@dataclass
class SyncConfig:
    """
    Global sync configuration containing all source configurations.

    This is the main configuration object that manages all sync sources.
    It can be loaded from application settings or created manually.

    Attributes:
        sources: Dictionary mapping source names to their configurations

    Example:
        >>> config = SyncConfig(sources={
        ...     "winner": SyncSourceConfig(source_name="winner", enabled=True),
        ...     "euroleague": SyncSourceConfig(source_name="euroleague", enabled=True)
        ... })
        >>> config.is_source_enabled("winner")
        True
    """

    sources: dict[str, SyncSourceConfig] = field(default_factory=dict)

    def is_source_enabled(self, source_name: str) -> bool:
        """
        Check if a sync source is enabled.

        Args:
            source_name: Name of the source to check

        Returns:
            True if the source exists and is enabled, False otherwise

        Example:
            >>> config = SyncConfig.from_settings()
            >>> config.is_source_enabled("winner")
            True
        """
        source = self.sources.get(source_name)
        return source is not None and source.enabled

    def get_source_config(self, source_name: str) -> SyncSourceConfig | None:
        """
        Get configuration for a specific source.

        Args:
            source_name: Name of the source

        Returns:
            SyncSourceConfig if found, None otherwise

        Example:
            >>> config = SyncConfig.from_settings()
            >>> source = config.get_source_config("euroleague")
            >>> source.sync_interval_minutes
            60
        """
        return self.sources.get(source_name)

    def get_enabled_sources(self) -> list[str]:
        """
        Get list of all enabled source names.

        Returns:
            List of enabled source names

        Example:
            >>> config = SyncConfig.from_settings()
            >>> config.get_enabled_sources()
            ['winner', 'euroleague']
        """
        return [name for name, source in self.sources.items() if source.enabled]

    def get_auto_sync_sources(self) -> list[str]:
        """
        Get list of sources with auto-sync enabled.

        Returns:
            List of source names with auto_sync_enabled=True

        Example:
            >>> config = SyncConfig.from_settings()
            >>> config.get_auto_sync_sources()
            ['euroleague']
        """
        return [
            name
            for name, source in self.sources.items()
            if source.enabled and source.auto_sync_enabled
        ]

    def register_source(self, source_config: SyncSourceConfig) -> None:
        """
        Register a new sync source configuration.

        Args:
            source_config: Configuration for the source

        Example:
            >>> config = SyncConfig()
            >>> config.register_source(SyncSourceConfig(source_name="nba"))
            >>> config.is_source_enabled("nba")
            True
        """
        self.sources[source_config.source_name] = source_config

    @classmethod
    def from_settings(cls) -> "SyncConfig":
        """
        Create SyncConfig from application settings.

        Loads sync configuration from the application settings module.
        Currently provides default configurations for known sources.
        Future versions will load from environment variables or config files.

        Returns:
            SyncConfig instance with loaded settings

        Example:
            >>> config = SyncConfig.from_settings()
            >>> config.get_enabled_sources()
            ['winner', 'euroleague']
        """
        return cls(
            sources={
                "winner": SyncSourceConfig(
                    source_name="winner",
                    enabled=True,
                    auto_sync_enabled=False,
                    sync_interval_minutes=60,
                ),
                "euroleague": SyncSourceConfig(
                    source_name="euroleague",
                    enabled=True,
                    auto_sync_enabled=False,
                    sync_interval_minutes=30,
                ),
            }
        )

    @classmethod
    def create_disabled(cls) -> "SyncConfig":
        """
        Create SyncConfig with all sources disabled.

        Useful for testing or when sync should be completely disabled.

        Returns:
            SyncConfig instance with no enabled sources

        Example:
            >>> config = SyncConfig.create_disabled()
            >>> config.get_enabled_sources()
            []
        """
        return cls(sources={})
