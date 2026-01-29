#!/usr/bin/env python3
"""
Sync script for running data synchronization from command line.

Usage:
    python scripts/run_sync.py winner 2025-26 [--include-pbp]

This script is designed to be run as a subprocess so progress can be
monitored in real-time via stdout.
"""

import argparse
import asyncio
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, "/root/projects/backdoor")

from src.core.database import SessionLocal
from src.sync import SyncConfig
from src.sync.euroleague import (
    EuroleagueAdapter,
    EuroleagueClient,
    EuroleagueDirectClient,
    EuroleagueMapper,
)
from src.sync.manager import SyncManager
from src.sync.winner import WinnerClient, WinnerScraper
from src.sync.winner.adapter import WinnerAdapter
from src.sync.winner.mapper import WinnerMapper


def log(msg: str):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def get_sync_manager(db, sources: list[str] | None = None):
    """Create a SyncManager with configured adapters."""
    adapters = {}

    if sources is None:
        sources = ["winner", "euroleague"]

    if "winner" in sources:
        log("Initializing Winner adapter...")
        client = WinnerClient(db)
        scraper = WinnerScraper(db)
        mapper = WinnerMapper()
        winner_adapter = WinnerAdapter(client, scraper, mapper)
        adapters["winner"] = winner_adapter

    if "euroleague" in sources:
        log("Initializing Euroleague adapter...")
        euro_client = EuroleagueClient(db)
        euro_direct_client = EuroleagueDirectClient(db)
        euro_mapper = EuroleagueMapper()
        euro_adapter = EuroleagueAdapter(euro_client, euro_direct_client, euro_mapper)
        adapters["euroleague"] = euro_adapter

    config = SyncConfig.from_settings()

    return SyncManager(
        db=db,
        adapters=adapters,
        config=config,
    )


async def run_sync(source: str, season_id: str, include_pbp: bool):
    """Run the sync operation."""
    log(f"Starting sync: source={source}, season={season_id}, pbp={include_pbp}")

    db = SessionLocal()
    try:
        manager = get_sync_manager(db, sources=[source])

        log("Fetching games from external API...")
        sync_log = await manager.sync_season(
            source=source,
            season_external_id=season_id,
            include_pbp=include_pbp,
        )

        log("Sync completed!")
        log(f"  Status: {sync_log.status}")
        log(f"  Records processed: {sync_log.records_processed}")
        log(f"  Records created: {sync_log.records_created}")
        log(f"  Records updated: {sync_log.records_updated}")
        log(f"  Records skipped: {sync_log.records_skipped}")

        if sync_log.error_message:
            log(f"  Error: {sync_log.error_message}")

        return sync_log.status == "COMPLETED"

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Run data sync")
    parser.add_argument("source", choices=["winner", "euroleague"], help="Data source")
    parser.add_argument("season", help="Season ID (e.g., 2025-26)")
    parser.add_argument(
        "--include-pbp", action="store_true", help="Include play-by-play"
    )

    args = parser.parse_args()

    log("=" * 50)
    log(f"SYNC: {args.source} - {args.season}")
    log("=" * 50)

    success = asyncio.run(run_sync(args.source, args.season, args.include_pbp))

    log("=" * 50)
    if success:
        log("SYNC COMPLETED SUCCESSFULLY")
    else:
        log("SYNC FAILED")
    log("=" * 50)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
