#!/usr/bin/env python3
"""
Player Duplicate Merger Script

Finds and merges duplicate player records that were created when syncing
players across multiple leagues (e.g., Winner League and Euroleague).

Identification criteria:
1. Same normalized name + same team in PlayerTeamHistory
2. Same normalized name + same birth_date

Merge strategy:
1. Keep player with more external_ids (primary)
2. Combine external_ids from both players
3. Reassign all related records to primary player
4. Delete duplicate player

Usage:
    python scripts/merge_duplicates.py --dry-run   # Preview without changes
    python scripts/merge_duplicates.py --execute   # Execute merges
    python scripts/merge_duplicates.py --report    # JSON report of duplicates

Examples:
    # See what duplicates exist
    python scripts/merge_duplicates.py --dry-run

    # Merge all duplicates
    python scripts/merge_duplicates.py --execute

    # Generate JSON report for analysis
    python scripts/merge_duplicates.py --report > duplicates.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.core.database import SessionLocal  # noqa: E402
from src.models.game import PlayerGameStats  # noqa: E402
from src.models.play_by_play import PlayByPlayEvent  # noqa: E402
from src.models.player import Player, PlayerTeamHistory  # noqa: E402
from src.models.stats import PlayerSeasonStats  # noqa: E402
from src.sync.deduplication.normalizer import normalize_name  # noqa: E402


@dataclass
class DuplicatePair:
    """Represents a pair of duplicate players."""

    primary: Player
    duplicate: Player
    reason: str
    confidence: str  # "high", "medium"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "primary": {
                "id": str(self.primary.id),
                "name": self.primary.full_name,
                "external_ids": self.primary.external_ids,
            },
            "duplicate": {
                "id": str(self.duplicate.id),
                "name": self.duplicate.full_name,
                "external_ids": self.duplicate.external_ids,
            },
            "reason": self.reason,
            "confidence": self.confidence,
        }


class DuplicateFinder:
    """Finds duplicate player records in the database."""

    def __init__(self, db: Session) -> None:
        """
        Initialize the duplicate finder.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def find_all_duplicates(self) -> list[DuplicatePair]:
        """
        Find all duplicate player pairs using multiple strategies.

        Returns:
            List of DuplicatePair objects representing duplicate players.
        """
        duplicates: list[DuplicatePair] = []
        seen_pairs: set[tuple[UUID, UUID]] = set()

        # Strategy 1: Same name + same team
        team_duplicates = self._find_same_team_duplicates()
        for pair in team_duplicates:
            pair_key = self._pair_key(pair.primary.id, pair.duplicate.id)
            if pair_key not in seen_pairs:
                duplicates.append(pair)
                seen_pairs.add(pair_key)

        # Strategy 2: Same name + same birth_date
        birth_duplicates = self._find_same_birthdate_duplicates()
        for pair in birth_duplicates:
            pair_key = self._pair_key(pair.primary.id, pair.duplicate.id)
            if pair_key not in seen_pairs:
                duplicates.append(pair)
                seen_pairs.add(pair_key)

        return duplicates

    def _pair_key(self, id1: UUID, id2: UUID) -> tuple[UUID, UUID]:
        """Create a consistent key for a pair of IDs."""
        return (min(id1, id2), max(id1, id2))

    def _find_same_team_duplicates(self) -> list[DuplicatePair]:
        """Find players with same normalized name on the same team."""
        duplicates: list[DuplicatePair] = []

        # Get all teams with multiple players
        team_ids = self.db.scalars(select(PlayerTeamHistory.team_id).distinct()).all()

        for team_id in team_ids:
            # Get all players on this team
            stmt = (
                select(Player)
                .join(PlayerTeamHistory)
                .where(PlayerTeamHistory.team_id == team_id)
                .distinct()
            )
            players = list(self.db.scalars(stmt).all())

            # Group by normalized name
            by_name: dict[str, list[Player]] = {}
            for player in players:
                norm_name = normalize_name(player.full_name)
                if norm_name not in by_name:
                    by_name[norm_name] = []
                by_name[norm_name].append(player)

            # Find duplicates
            for name, group in by_name.items():
                if len(group) > 1:
                    # Pick primary (most external_ids)
                    group.sort(key=lambda p: len(p.external_ids), reverse=True)
                    primary = group[0]
                    for dup in group[1:]:
                        duplicates.append(
                            DuplicatePair(
                                primary=primary,
                                duplicate=dup,
                                reason=f"Same name '{name}' on same team",
                                confidence="high",
                            )
                        )

        return duplicates

    def _find_same_birthdate_duplicates(self) -> list[DuplicatePair]:
        """Find players with same normalized name and birth_date."""
        duplicates: list[DuplicatePair] = []

        # Find duplicate name + birth_date combinations
        dup_query = (
            select(
                func.lower(Player.first_name).label("fn"),
                func.lower(Player.last_name).label("ln"),
                Player.birth_date.label("bd"),
            )
            .where(Player.birth_date.isnot(None))
            .group_by(
                func.lower(Player.first_name),
                func.lower(Player.last_name),
                Player.birth_date,
            )
            .having(func.count() > 1)
        )

        for row in self.db.execute(dup_query):
            # Get players with this name + birth_date
            players = list(
                self.db.scalars(
                    select(Player).where(
                        func.lower(Player.first_name) == row.fn,
                        func.lower(Player.last_name) == row.ln,
                        Player.birth_date == row.bd,
                    )
                ).all()
            )

            if len(players) > 1:
                # Pick primary (most external_ids)
                players.sort(key=lambda p: len(p.external_ids), reverse=True)
                primary = players[0]
                for dup in players[1:]:
                    duplicates.append(
                        DuplicatePair(
                            primary=primary,
                            duplicate=dup,
                            reason=f"Same name + birth_date ({row.bd})",
                            confidence="high",
                        )
                    )

        return duplicates


class DuplicateMerger:
    """Merges duplicate player records."""

    def __init__(self, db: Session) -> None:
        """
        Initialize the duplicate merger.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def merge(self, pair: DuplicatePair, dry_run: bool = True) -> dict:
        """
        Merge a duplicate player into the primary player.

        Args:
            pair: The duplicate pair to merge.
            dry_run: If True, don't commit changes.

        Returns:
            Dictionary with merge statistics.
        """
        primary = pair.primary
        duplicate = pair.duplicate

        stats = {
            "primary_id": str(primary.id),
            "duplicate_id": str(duplicate.id),
            "game_stats_moved": 0,
            "team_histories_moved": 0,
            "pbp_events_moved": 0,
            "season_stats_moved": 0,
            "external_ids_merged": [],
        }

        # 1. Merge external_ids
        new_external_ids = dict(primary.external_ids)
        for source, ext_id in duplicate.external_ids.items():
            if source not in new_external_ids:
                new_external_ids[source] = ext_id
                stats["external_ids_merged"].append(f"{source}:{ext_id}")

        if not dry_run:
            primary.external_ids = new_external_ids

        # 2. Move PlayerGameStats
        game_stats = self.db.scalars(
            select(PlayerGameStats).where(PlayerGameStats.player_id == duplicate.id)
        ).all()
        stats["game_stats_moved"] = len(game_stats)
        if not dry_run:
            for gs in game_stats:
                gs.player_id = primary.id

        # 3. Move PlayerTeamHistory (handle unique constraint)
        team_histories = self.db.scalars(
            select(PlayerTeamHistory).where(PlayerTeamHistory.player_id == duplicate.id)
        ).all()

        # Get existing team/season combos for primary
        existing_combos = set()
        primary_histories = self.db.scalars(
            select(PlayerTeamHistory).where(PlayerTeamHistory.player_id == primary.id)
        ).all()
        for h in primary_histories:
            existing_combos.add((h.team_id, h.season_id))

        moved_histories = 0
        for th in team_histories:
            combo = (th.team_id, th.season_id)
            if combo not in existing_combos:
                if not dry_run:
                    th.player_id = primary.id
                moved_histories += 1
                existing_combos.add(combo)
            else:
                # Delete duplicate history entry
                if not dry_run:
                    self.db.delete(th)

        stats["team_histories_moved"] = moved_histories

        # 4. Move PlayByPlayEvent
        pbp_events = self.db.scalars(
            select(PlayByPlayEvent).where(PlayByPlayEvent.player_id == duplicate.id)
        ).all()
        stats["pbp_events_moved"] = len(pbp_events)
        if not dry_run:
            for event in pbp_events:
                event.player_id = primary.id

        # 5. Move PlayerSeasonStats (handle unique constraint)
        season_stats = self.db.scalars(
            select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == duplicate.id)
        ).all()

        # Get existing season combos for primary
        existing_season_combos = set()
        primary_season_stats = self.db.scalars(
            select(PlayerSeasonStats).where(PlayerSeasonStats.player_id == primary.id)
        ).all()
        for ss in primary_season_stats:
            existing_season_combos.add((ss.team_id, ss.season_id))

        moved_season_stats = 0
        for ss in season_stats:
            combo = (ss.team_id, ss.season_id)
            if combo not in existing_season_combos:
                if not dry_run:
                    ss.player_id = primary.id
                moved_season_stats += 1
                existing_season_combos.add(combo)
            else:
                # Delete duplicate season stats
                if not dry_run:
                    self.db.delete(ss)

        stats["season_stats_moved"] = moved_season_stats

        # 6. Delete duplicate player
        if not dry_run:
            self.db.delete(duplicate)
            self.db.commit()

        return stats


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Find and merge duplicate player records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview duplicate merges without making changes",
    )
    mode_group.add_argument(
        "--execute",
        action="store_true",
        help="Execute duplicate merges",
    )
    mode_group.add_argument(
        "--report",
        action="store_true",
        help="Output JSON report of duplicates",
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        finder = DuplicateFinder(db)
        duplicates = finder.find_all_duplicates()

        if args.report:
            # Output JSON report
            report = {
                "total_duplicates": len(duplicates),
                "duplicates": [d.to_dict() for d in duplicates],
            }
            print(json.dumps(report, indent=2))
            return

        if not duplicates:
            print("No duplicate players found.")
            return

        print(f"Found {len(duplicates)} duplicate player pair(s)")
        print("=" * 60)

        merger = DuplicateMerger(db)

        for i, pair in enumerate(duplicates, 1):
            print(f"\n[{i}/{len(duplicates)}] {pair.reason}")
            print(f"  Primary:   {pair.primary.full_name} (id={pair.primary.id})")
            print(f"             external_ids={pair.primary.external_ids}")
            print(f"  Duplicate: {pair.duplicate.full_name} (id={pair.duplicate.id})")
            print(f"             external_ids={pair.duplicate.external_ids}")
            print(f"  Confidence: {pair.confidence}")

            stats = merger.merge(pair, dry_run=not args.execute)

            print("  Actions:")
            print(f"    - Game stats to move: {stats['game_stats_moved']}")
            print(f"    - Team histories to move: {stats['team_histories_moved']}")
            print(f"    - PBP events to move: {stats['pbp_events_moved']}")
            print(f"    - Season stats to move: {stats['season_stats_moved']}")
            if stats["external_ids_merged"]:
                print(f"    - External IDs to merge: {stats['external_ids_merged']}")

            if args.execute:
                print("  Status: MERGED")
            else:
                print("  Status: DRY RUN (no changes made)")

        print("\n" + "=" * 60)
        if args.execute:
            print(f"Merged {len(duplicates)} duplicate player(s)")
        else:
            print(f"Would merge {len(duplicates)} duplicate player(s)")
            print("Run with --execute to apply changes")

    finally:
        db.close()


if __name__ == "__main__":
    main()
