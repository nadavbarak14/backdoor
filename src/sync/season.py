"""
Season Format Utilities Module

Provides centralized season name normalization to ensure all adapters
store seasons in the standardized YYYY-YY format (e.g., "2025-26").

This module exports:
    - normalize_season_name: Convert a year to standardized season format
    - parse_season_year: Extract the start year from a season name
    - validate_season_format: Check if a string matches the YYYY-YY format
    - SeasonFormatError: Exception for invalid season formats

Usage:
    from src.sync.season import normalize_season_name, parse_season_year

    # Convert year to season name
    name = normalize_season_name(2025)  # Returns "2025-26"

    # Parse season name back to year
    year = parse_season_year("2025-26")  # Returns 2025
"""

import re

from src.sync.exceptions import DataValidationError


class SeasonFormatError(DataValidationError):
    """
    Exception raised when a season name doesn't match the expected format.

    Attributes:
        value: The invalid season name that was provided.
        message: Explanation of the error.

    Example:
        >>> raise SeasonFormatError("E2025")
        SeasonFormatError: Invalid season format 'E2025'. Expected YYYY-YY format.
    """

    def __init__(self, value: str, message: str | None = None):
        if message is None:
            message = f"Invalid season format '{value}'. Expected YYYY-YY format (e.g., '2025-26')."
        super().__init__(message, field="name", value=value)


# Regex pattern for valid season format: YYYY-YY where YY = (YYYY + 1) % 100
SEASON_FORMAT_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")


def normalize_season_name(year: int) -> str:
    """
    Convert a start year to the standardized YYYY-YY season format.

    The season name represents a basketball season that spans two calendar
    years. For example, the 2025-26 season starts in fall 2025 and ends
    in spring 2026.

    Args:
        year: The start year of the season (e.g., 2025 for the 2025-26 season).

    Returns:
        Season name in YYYY-YY format (e.g., "2025-26").

    Raises:
        ValueError: If year is not a valid 4-digit year.

    Example:
        >>> normalize_season_name(2025)
        '2025-26'
        >>> normalize_season_name(2024)
        '2024-25'
        >>> normalize_season_name(1999)
        '1999-00'
    """
    if not isinstance(year, int) or year < 1900 or year > 2100:
        raise ValueError(
            f"Invalid year: {year}. Must be a 4-digit year between 1900 and 2100."
        )

    next_year_suffix = str((year + 1) % 100).zfill(2)
    return f"{year}-{next_year_suffix}"


def parse_season_year(season_name: str) -> int:
    """
    Extract the start year from a season name in YYYY-YY format.

    Args:
        season_name: Season name in YYYY-YY format (e.g., "2025-26").

    Returns:
        The start year of the season (e.g., 2025).

    Raises:
        SeasonFormatError: If the season name is not in valid YYYY-YY format.

    Example:
        >>> parse_season_year("2025-26")
        2025
        >>> parse_season_year("1999-00")
        1999
    """
    match = SEASON_FORMAT_PATTERN.match(season_name)
    if not match:
        raise SeasonFormatError(season_name)

    start_year = int(match.group(1))
    end_suffix = int(match.group(2))

    # Validate that the suffix is correct (next year's last 2 digits)
    expected_suffix = (start_year + 1) % 100
    if end_suffix != expected_suffix:
        raise SeasonFormatError(
            season_name,
            f"Invalid season format '{season_name}'. "
            f"Expected suffix '{expected_suffix:02d}' for year {start_year}.",
        )

    return start_year


def validate_season_format(season_name: str) -> bool:
    """
    Check if a string matches the valid YYYY-YY season format.

    This is a non-throwing validation that returns True/False.
    For validation that throws exceptions, use parse_season_year.

    Args:
        season_name: The season name to validate.

    Returns:
        True if the format is valid, False otherwise.

    Example:
        >>> validate_season_format("2025-26")
        True
        >>> validate_season_format("E2025")
        False
        >>> validate_season_format("2025-27")  # Wrong suffix
        False
    """
    try:
        parse_season_year(season_name)
        return True
    except SeasonFormatError:
        return False
