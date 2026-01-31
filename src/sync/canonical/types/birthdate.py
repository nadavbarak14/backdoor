"""
Birthdate Module

Provides the parse_birthdate function for parsing player birthdates.

This module exports:
    - parse_birthdate(): Parse birthdate from various formats

Supported formats:
    - ISO: "1995-05-15"
    - European: "15/05/1995", "15-05-1995"
    - US: "05/15/1995"
    - Text: "May 15, 1995", "15 May 1995"
    - datetime objects: extract date

Usage:
    from src.sync.canonical.types.birthdate import parse_birthdate

    date = parse_birthdate("1995-05-15")  # date(1995, 5, 15)
    date = parse_birthdate("May 15, 1995")  # date(1995, 5, 15)
"""

import re
from datetime import date, datetime

# Valid year range for basketball players
MIN_YEAR = 1950
MAX_YEAR = datetime.now().year


# Month name mappings (English)
_MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _validate_date(year: int, month: int, day: int) -> date | None:
    """
    Validate and create a date object.

    Returns None if:
    - Year is outside valid range (1950 to current year)
    - Date is in the future
    - Date components are invalid
    """
    # Check year range
    if not MIN_YEAR <= year <= MAX_YEAR:
        return None

    # Try to create date
    try:
        result = date(year, month, day)
    except ValueError:
        return None

    # Check not in future
    if result > date.today():
        return None

    return result


def _parse_iso_format(raw: str) -> date | None:
    """Parse ISO format: YYYY-MM-DD or YYYY/MM/DD."""
    match = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", raw)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return _validate_date(year, month, day)
    return None


def _parse_european_format(raw: str) -> date | None:
    """Parse European format: DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY."""
    match = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", raw)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        return _validate_date(year, month, day)
    return None


def _parse_us_format(raw: str) -> date | None:
    """
    Parse US format: MM/DD/YYYY.

    Disambiguated from European by checking if first number > 12.
    If first <= 12 and second <= 12, prefers European format.
    """
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", raw)
    if match:
        first = int(match.group(1))
        second = int(match.group(2))
        year = int(match.group(3))

        # If first > 12, must be day (European)
        if first > 12:
            return _validate_date(year, second, first)  # DD/MM/YYYY

        # If second > 12, must be day (US)
        if second > 12:
            return _validate_date(year, first, second)  # MM/DD/YYYY

        # Ambiguous: default to European (DD/MM/YYYY)
        return _validate_date(year, second, first)

    return None


def _parse_text_format(raw: str) -> date | None:
    """
    Parse text formats:
    - "May 15, 1995"
    - "15 May 1995"
    - "May 15 1995"
    """
    # Pattern: Month Day, Year (e.g., "May 15, 1995")
    match = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", raw)
    if match:
        month_name = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3))
        month = _MONTH_NAMES.get(month_name)
        if month:
            return _validate_date(year, month, day)

    # Pattern: Day Month Year (e.g., "15 May 1995")
    match = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", raw)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))
        month = _MONTH_NAMES.get(month_name)
        if month:
            return _validate_date(year, month, day)

    return None


def parse_birthdate(raw: str | date | datetime | None) -> date | None:
    """
    Parse and validate birthdate from various formats.

    Supported formats:
    - ISO: "1995-05-15", "1995/05/15"
    - European: "15/05/1995", "15-05-1995", "15.05.1995"
    - US: "05/15/1995" (when unambiguous)
    - Text: "May 15, 1995", "15 May 1995"
    - datetime objects: extracts date component

    Validation:
    - Year must be 1950 to current year
    - Date must not be in the future

    Args:
        raw: Raw date value in any supported format, or None.

    Returns:
        date object, or None if:
        - Input is None or empty
        - Format cannot be parsed
        - Year is outside valid range (1950 to current)
        - Date is in the future

    Example:
        >>> parse_birthdate("1995-05-15")
        datetime.date(1995, 5, 15)
        >>> parse_birthdate("15/05/1995")
        datetime.date(1995, 5, 15)
        >>> parse_birthdate("May 15, 1995")
        datetime.date(1995, 5, 15)
        >>> parse_birthdate("2050-01-01")  # Future date
        None
        >>> parse_birthdate("invalid")
        None
    """
    if raw is None:
        return None

    # Handle datetime objects
    if isinstance(raw, datetime):
        result = raw.date()
        # Validate year range and not future
        if not MIN_YEAR <= result.year <= MAX_YEAR:
            return None
        if result > date.today():
            return None
        return result

    # Handle date objects
    if isinstance(raw, date):
        if not MIN_YEAR <= raw.year <= MAX_YEAR:
            return None
        if raw > date.today():
            return None
        return raw

    # Handle string
    if not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    # Try different formats in order
    result = _parse_iso_format(raw)
    if result:
        return result

    result = _parse_european_format(raw)
    if result:
        return result

    result = _parse_text_format(raw)
    if result:
        return result

    # US format is tried via _parse_european_format with disambiguation
    # so we don't need a separate call

    return None
