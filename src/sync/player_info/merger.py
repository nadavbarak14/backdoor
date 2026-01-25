"""
Player Info Merger Module

Provides merge logic for combining player biographical data from multiple
external sources. Handles conflicting data by applying priority rules.

The merge process:
1. Collect RawPlayerInfo from multiple sources
2. Apply priority rules for each field
3. Track which source provided each field value
4. Return a MergedPlayerInfo with consolidated data

Usage:
    from src.sync.player_info.merger import merge_player_info, MergedPlayerInfo
    from src.sync.types import RawPlayerInfo

    sources = [
        ("winner", winner_player_info),
        ("euroleague", euroleague_player_info),
    ]
    merged = merge_player_info(sources)
    print(f"{merged.first_name} {merged.last_name}")
    print(f"Height from: {merged.sources.get('height_cm')}")
"""

from dataclasses import dataclass, field
from datetime import date

from src.sync.types import RawPlayerInfo


@dataclass
class MergedPlayerInfo:
    """
    Result of merging player info from multiple sources.

    Contains consolidated player biographical data with tracking of
    which source provided each field value.

    Attributes:
        first_name: Player's first name
        last_name: Player's last name
        birth_date: Player's date of birth, if available
        height_cm: Player's height in centimeters, if available
        position: Player's position (PG, SG, SF, PF, C)
        sources: Mapping of field name to source that provided the value

    Example:
        >>> merged = MergedPlayerInfo(
        ...     first_name="LeBron",
        ...     last_name="James",
        ...     height_cm=206,
        ...     sources={"first_name": "winner", "height_cm": "euroleague"}
        ... )
        >>> print(merged.sources["height_cm"])
        euroleague
    """

    first_name: str
    last_name: str
    birth_date: date | None = None
    height_cm: int | None = None
    position: str | None = None
    sources: dict[str, str] = field(default_factory=dict)


def merge_player_info(
    sources: list[tuple[str, RawPlayerInfo]],
) -> MergedPlayerInfo:
    """
    Merge player info from multiple sources.

    Combines player biographical data from multiple sources, applying
    priority rules to resolve conflicts. Sources earlier in the list
    have higher priority.

    Priority rules:
    - first_name: First source with non-empty value
    - last_name: First source with non-empty value
    - height_cm: First source with non-null value
    - birth_date: First source with non-null value
    - position: First source with non-null value

    Args:
        sources: List of tuples containing (source_name, RawPlayerInfo).
            Sources are ordered by priority (first = highest priority).

    Returns:
        MergedPlayerInfo with consolidated data and source tracking.

    Raises:
        ValueError: If sources list is empty.

    Example:
        >>> from src.sync.types import RawPlayerInfo
        >>> winner_info = RawPlayerInfo(
        ...     external_id="w123",
        ...     first_name="LeBron",
        ...     last_name="James",
        ...     height_cm=206,
        ... )
        >>> euro_info = RawPlayerInfo(
        ...     external_id="e456",
        ...     first_name="Lebron",
        ...     last_name="James",
        ...     height_cm=205,
        ...     position="SF",
        ... )
        >>> merged = merge_player_info([("winner", winner_info), ("euroleague", euro_info)])
        >>> merged.height_cm
        206
        >>> merged.sources["height_cm"]
        'winner'
        >>> merged.position
        'SF'
        >>> merged.sources["position"]
        'euroleague'
    """
    if not sources:
        raise ValueError("Cannot merge empty sources list")

    # Initialize with first source's required fields
    first_source_name, first_info = sources[0]
    merged_sources: dict[str, str] = {}

    # Start with values from the first source
    first_name = first_info.first_name
    last_name = first_info.last_name
    birth_date: date | None = None
    height_cm: int | None = None
    position: str | None = None

    # Track sources for required fields
    if first_name:
        merged_sources["first_name"] = first_source_name
    if last_name:
        merged_sources["last_name"] = first_source_name

    # Process all sources for optional fields
    for source_name, info in sources:
        # Update first_name if not yet set (empty string)
        if not first_name and info.first_name:
            first_name = info.first_name
            merged_sources["first_name"] = source_name

        # Update last_name if not yet set (empty string)
        if not last_name and info.last_name:
            last_name = info.last_name
            merged_sources["last_name"] = source_name

        # Height: first non-null value wins
        if height_cm is None and info.height_cm is not None:
            height_cm = info.height_cm
            merged_sources["height_cm"] = source_name

        # Birth date: first non-null value wins
        if birth_date is None and info.birth_date is not None:
            birth_date = info.birth_date
            merged_sources["birth_date"] = source_name

        # Position: first non-null value wins
        if position is None and info.position is not None:
            position = info.position
            merged_sources["position"] = source_name

    return MergedPlayerInfo(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        height_cm=height_cm,
        position=position,
        sources=merged_sources,
    )
