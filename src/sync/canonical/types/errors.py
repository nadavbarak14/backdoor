"""
Custom Exceptions Module

Provides custom exceptions for the canonical types layer.

This module exports:
    - ValidationError: Raised when data fails validation
    - ConversionError: Raised when data cannot be converted

Usage:
    from src.sync.canonical.types.errors import ValidationError, ConversionError

    if height < 150 or height > 250:
        raise ValidationError(f"Height {height} outside valid range 150-250")
"""


class ValidationError(Exception):
    """
    Raised when data fails validation.

    Use this exception when data is in the correct format but fails
    business rule validation (e.g., height outside valid range).

    Example:
        >>> raise ValidationError("Height must be between 150-250 cm")
        ValidationError: Height must be between 150-250 cm
    """

    pass


class ConversionError(Exception):
    """
    Raised when data cannot be converted to canonical format.

    Use this exception when data format is unrecognized or cannot
    be parsed (e.g., invalid date string format).

    Example:
        >>> raise ConversionError("Cannot parse date: 'not-a-date'")
        ConversionError: Cannot parse date: 'not-a-date'
    """

    pass
