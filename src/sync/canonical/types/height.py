"""
Height Type Module

Provides the Height dataclass and parse function for player heights.

This module exports:
    - Height: Validated height in centimeters
    - parse_height(): Parse height from various formats

Supported formats:
    - Integer cm: 198 -> Height(198)
    - String cm: "198", "198 cm" -> Height(198)
    - Meters: 1.98, "1.98", "1.98m" -> Height(198)
    - Feet/inches: "6'8", "6-8", "6ft 8in" -> Height(203)

Usage:
    from src.sync.canonical.types.height import Height, parse_height

    height = parse_height(198)  # Height(cm=198)
    height = parse_height("6'8\"")  # Height(cm=203)
    height = parse_height(1.98)  # Height(cm=198)
"""

import re
from dataclasses import dataclass

# Valid height range for basketball players
MIN_HEIGHT_CM = 150
MAX_HEIGHT_CM = 250


@dataclass(frozen=True)
class Height:
    """
    Validated height in centimeters.

    Attributes:
        cm: Height in centimeters (150-250 range)

    Example:
        >>> height = Height(cm=198)
        >>> print(height.cm)
        198
    """

    cm: int

    def __post_init__(self) -> None:
        """Validate height is within acceptable range."""
        if not MIN_HEIGHT_CM <= self.cm <= MAX_HEIGHT_CM:
            raise ValueError(
                f"Height {self.cm}cm outside valid range {MIN_HEIGHT_CM}-{MAX_HEIGHT_CM}"
            )


def _feet_inches_to_cm(feet: int, inches: int) -> int:
    """Convert feet and inches to centimeters."""
    total_inches = feet * 12 + inches
    return round(total_inches * 2.54)


def _parse_feet_inches(raw: str) -> int | None:
    """
    Parse feet/inches format to centimeters.

    Supports formats:
    - "6'8" or "6'8\""
    - "6-8"
    - "6ft 8in" or "6ft8in"
    - "6 ft 8 in"
    """
    # Pattern for 6'8 or 6'8"
    match = re.match(r"(\d+)['\u2019](\d+)[\"″]?$", raw)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        return _feet_inches_to_cm(feet, inches)

    # Pattern for 6-8
    match = re.match(r"(\d+)-(\d+)$", raw)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        # Only treat as feet-inches if feet is reasonable (4-7)
        if 4 <= feet <= 7 and 0 <= inches <= 11:
            return _feet_inches_to_cm(feet, inches)

    # Pattern for 6ft 8in or 6ft8in or 6 ft 8 in
    match = re.match(r"(\d+)\s*ft\s*(\d+)\s*in", raw, re.IGNORECASE)
    if match:
        feet = int(match.group(1))
        inches = int(match.group(2))
        return _feet_inches_to_cm(feet, inches)

    # Pattern for 6ft (no inches)
    match = re.match(r"(\d+)\s*ft$", raw, re.IGNORECASE)
    if match:
        feet = int(match.group(1))
        return _feet_inches_to_cm(feet, 0)

    return None


def parse_height(raw: str | int | float | None) -> Height | None:
    """
    Parse height from various formats.

    Supported formats:
    - Integer cm: 198 -> Height(198)
    - String cm: "198", "198 cm", "198cm" -> Height(198)
    - Meters: 1.98, "1.98", "1.98m" -> Height(198)
    - Feet/inches: "6'8", "6'8\"", "6-8", "6ft 8in" -> Height(203)

    Args:
        raw: Raw height value in any supported format, or None.

    Returns:
        Height dataclass with validated cm value, or None if:
        - Input is None or empty
        - Format cannot be parsed
        - Value is outside valid range (150-250 cm)

    Example:
        >>> parse_height(198)
        Height(cm=198)
        >>> parse_height("198 cm")
        Height(cm=198)
        >>> parse_height(1.98)
        Height(cm=198)
        >>> parse_height("6'8\"")
        Height(cm=203)
        >>> parse_height(100)  # Out of range
        None
        >>> parse_height("invalid")
        None
    """
    if raw is None:
        return None

    cm: int | None = None

    # Handle numeric types
    if isinstance(raw, int):
        # Integer is assumed to be cm if > 100, otherwise invalid
        if raw > 100:
            cm = raw
        elif raw > 3:
            # Could be meters without decimal (rare)
            cm = round(raw * 100)
        else:
            return None

    elif isinstance(raw, float):
        # Float: if < 3, assume meters; if > 100, assume cm
        if raw < 3:
            cm = round(raw * 100)
        elif raw > 100:
            cm = round(raw)
        else:
            return None

    elif isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None

        # Try feet/inches formats first
        ft_in_result = _parse_feet_inches(raw)
        if ft_in_result is not None:
            cm = ft_in_result
        else:
            # Try to parse as cm or meters
            # Remove common suffixes
            cleaned = re.sub(r"\s*(cm|m|centimeters?|meters?)\.?$", "", raw, flags=re.IGNORECASE)
            cleaned = cleaned.strip()

            try:
                value = float(cleaned)

                # Determine if cm or meters
                if value < 3:
                    # Likely meters
                    cm = round(value * 100)
                elif value > 100:
                    # Likely cm
                    cm = round(value)
                else:
                    # Ambiguous (3-100) - invalid
                    return None

            except ValueError:
                return None
    else:
        return None

    # Validate range
    if cm is None:
        return None

    if not MIN_HEIGHT_CM <= cm <= MAX_HEIGHT_CM:
        return None

    return Height(cm=cm)
