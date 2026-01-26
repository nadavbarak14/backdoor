"""
Name Normalization Module

Provides utilities for normalizing and comparing player and team names
across different data sources. This is essential for deduplication when
matching entities between Winner League and Euroleague data.

The normalization process:
1. Converts to lowercase
2. Removes diacritics/accents (e.g., Doncic -> doncic)
3. Strips leading/trailing whitespace
4. Normalizes internal whitespace

Usage:
    from src.sync.deduplication.normalizer import normalize_name, names_match

    # Normalize a single name
    normalized = normalize_name("Luka Doncic")  # "luka doncic"

    # Compare two names
    if names_match("Doncic", "DONCIC"):
        print("Same player!")

    # Parse full name into components
    first, last = parse_full_name("Scottie Wilbekin")  # ("Scottie", "Wilbekin")
"""

import re
import unicodedata

# Common suffixes to strip from last names (Jr., Sr., III, IV, etc.)
NAME_SUFFIXES = {
    "jr",
    "jr.",
    "junior",
    "sr",
    "sr.",
    "senior",
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "1st",
    "2nd",
    "3rd",
    "4th",
    "5th",
}


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison across data sources.

    Applies the following transformations:
    1. Strip leading/trailing whitespace
    2. Remove diacritics/accents using Unicode normalization (NFD + ASCII filter)
    3. Convert to lowercase
    4. Normalize internal whitespace (multiple spaces -> single space)

    Args:
        name: The name to normalize.

    Returns:
        The normalized name string.

    Example:
        >>> normalize_name("Luka Doncic")
        'luka doncic'
        >>> normalize_name("  LEBRON   JAMES  ")
        'lebron james'
        >>> normalize_name("Doncic")
        'doncic'
    """
    if not name:
        return ""

    # Strip whitespace
    name = name.strip()

    # Remove diacritics using Unicode normalization
    # NFD decomposes characters (e -> e + combining accent)
    # Then we filter out combining marks (category 'Mn')
    normalized = unicodedata.normalize("NFD", name)
    name = "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    # Convert to lowercase
    name = name.lower()

    # Replace hyphens and underscores with spaces (e.g., "Tel-Aviv" -> "Tel Aviv")
    name = name.replace("-", " ").replace("_", " ")

    # Normalize internal whitespace
    name = re.sub(r"\s+", " ", name)

    return name


def strip_name_suffix(name: str) -> str:
    """
    Remove common suffixes from a name (Jr., Sr., III, IV, etc.).

    Args:
        name: The name to strip suffixes from.

    Returns:
        The name with suffixes removed.

    Example:
        >>> strip_name_suffix("Baldwin IV")
        'Baldwin'
        >>> strip_name_suffix("Smith Jr.")
        'Smith'
        >>> strip_name_suffix("Johnson")
        'Johnson'
    """
    if not name:
        return ""

    parts = name.strip().split()
    if not parts:
        return ""

    # Check if last part is a suffix
    while parts and parts[-1].lower().rstrip(".") in NAME_SUFFIXES:
        parts.pop()

    return " ".join(parts) if parts else name


def names_match(name1: str, name2: str) -> bool:
    """
    Check if two names match after normalization.

    Compares two names using normalized comparison, which handles
    differences in case, accents, and whitespace.

    Args:
        name1: First name to compare.
        name2: Second name to compare.

    Returns:
        True if the normalized names are equal, False otherwise.

    Example:
        >>> names_match("Luka Doncic", "luka doncic")
        True
        >>> names_match("Doncic", "DONCIC")
        True
        >>> names_match("Doncic", "Doncic ")
        True
        >>> names_match("LeBron", "Luka")
        False
    """
    return normalize_name(name1) == normalize_name(name2)


def names_match_fuzzy(name1: str, name2: str) -> bool:
    """
    Check if two names match, handling suffixes like Jr., III, IV.

    More lenient than names_match - also strips common suffixes
    before comparing.

    Args:
        name1: First name to compare.
        name2: Second name to compare.

    Returns:
        True if the names match (with or without suffixes), False otherwise.

    Example:
        >>> names_match_fuzzy("Baldwin IV", "Baldwin")
        True
        >>> names_match_fuzzy("Smith Jr.", "Smith")
        True
        >>> names_match_fuzzy("Johnson", "Johnson")
        True
    """
    # First try exact match
    if normalize_name(name1) == normalize_name(name2):
        return True

    # Try with suffixes stripped
    stripped1 = normalize_name(strip_name_suffix(name1))
    stripped2 = normalize_name(strip_name_suffix(name2))

    return stripped1 == stripped2


def team_names_match(name1: str, name2: str) -> bool:
    """
    Check if two team names match, handling sponsor variations.

    Handles common cases like:
    - "Maccabi Tel Aviv" vs "Maccabi Playtika Tel Aviv" (sponsor)
    - Case and accent differences

    Args:
        name1: First team name.
        name2: Second team name.

    Returns:
        True if the team names likely refer to the same team.

    Example:
        >>> team_names_match("Maccabi Tel Aviv", "Maccabi Playtika Tel Aviv")
        True
        >>> team_names_match("Hapoel Jerusalem", "Maccabi Tel Aviv")
        False
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Exact match
    if norm1 == norm2:
        return True

    # Check if one contains the other (for sponsor names)
    # "maccabi tel aviv" in "maccabi playtika tel aviv"
    if norm1 in norm2 or norm2 in norm1:
        return True

    # Check if they share the same core name (first and last words)
    parts1 = norm1.split()
    parts2 = norm2.split()

    # Same first word (team type) and last word (city)
    return (
        len(parts1) >= 2
        and len(parts2) >= 2
        and parts1[0] == parts2[0]
        and parts1[-1] == parts2[-1]
    )


def parse_full_name(full_name: str) -> tuple[str, str]:
    """
    Parse a full name into first and last name components.

    Handles common name formats:
    - "First Last" -> ("First", "Last")
    - "First Middle Last" -> ("First", "Middle Last")
    - "First" -> ("First", "")

    The first word is treated as the first name, and all remaining
    words are combined as the last name.

    Args:
        full_name: The full name to parse.

    Returns:
        A tuple of (first_name, last_name). If only one word is provided,
        last_name will be an empty string.

    Example:
        >>> parse_full_name("Scottie Wilbekin")
        ('Scottie', 'Wilbekin')
        >>> parse_full_name("LeBron Raymone James")
        ('LeBron', 'Raymone James')
        >>> parse_full_name("Madonna")
        ('Madonna', '')
        >>> parse_full_name("  John   Doe  ")
        ('John', 'Doe')
    """
    if not full_name:
        return ("", "")

    # Normalize whitespace and split
    parts = full_name.strip().split()

    if not parts:
        return ("", "")

    if len(parts) == 1:
        return (parts[0], "")

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    return (first_name, last_name)
