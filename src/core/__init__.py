"""
Core Module

Contains core application infrastructure including configuration,
database setup, and shared utilities.

Exports:
    settings: Application settings singleton
    Settings: Settings class for type hints and testing
    get_settings: Factory function for settings (useful for dependency injection)
"""

from src.core.config import Settings, get_settings, settings

__all__ = ["Settings", "get_settings", "settings"]
