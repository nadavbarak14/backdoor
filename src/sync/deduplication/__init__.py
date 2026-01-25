"""
Deduplication Package

Provides functionality for deduplicating players and teams across multiple
data sources (Winner League, Euroleague). Uses team-based matching to identify
the same entities appearing in different leagues.

Key components:
- normalizer: Name normalization utilities for matching
- team_matcher: Team matching and merging across sources
- player: Player deduplication using team rosters

Usage:
    from src.sync.deduplication import (
        PlayerDeduplicator,
        TeamMatcher,
        normalize_name,
        names_match,
        parse_full_name,
    )

    # Normalize names for comparison
    normalized = normalize_name("Luka Doncic")

    # Match teams across sources
    matcher = TeamMatcher(db_session)
    team = matcher.find_or_create_team("winner", "123", raw_team_data)

    # Deduplicate players
    dedup = PlayerDeduplicator(db_session)
    player = dedup.find_or_create_player("winner", "456", raw_player_info, team.id)
"""

from src.sync.deduplication.normalizer import (
    names_match,
    names_match_fuzzy,
    normalize_name,
    parse_full_name,
    strip_name_suffix,
    team_names_match,
)
from src.sync.deduplication.player import PlayerDeduplicator
from src.sync.deduplication.team_matcher import TeamMatcher

__all__ = [
    # Normalizer functions
    "normalize_name",
    "names_match",
    "names_match_fuzzy",
    "parse_full_name",
    "strip_name_suffix",
    "team_names_match",
    # Team matching
    "TeamMatcher",
    # Player deduplication
    "PlayerDeduplicator",
]
