"""
Player Info Module

Provides services for aggregating and merging player biographical data
from multiple external sources. Handles conflicting data using configurable
priority rules.

This module exports:
    - PlayerInfoService: Service that aggregates player info from multiple adapters
    - MergedPlayerInfo: Dataclass representing merged player info
    - merge_player_info: Function to merge RawPlayerInfo from multiple sources

Usage:
    from src.sync.player_info import PlayerInfoService, MergedPlayerInfo
    from src.sync.winner.adapter import WinnerAdapter
    from src.sync.euroleague.adapter import EuroleagueAdapter

    # Create adapters
    winner_adapter = WinnerAdapter(client, scraper, mapper)
    euroleague_adapter = EuroleagueAdapter(client, direct_client, mapper)

    # Create service with adapters ordered by priority
    service = PlayerInfoService([winner_adapter, euroleague_adapter])

    # Fetch and merge player info
    merged = await service.get_player_info({
        "winner": "w123",
        "euroleague": "e456",
    })
    print(f"{merged.first_name} {merged.last_name}")
"""

from src.sync.player_info.merger import MergedPlayerInfo, merge_player_info
from src.sync.player_info.service import PlayerInfoService

__all__ = [
    "PlayerInfoService",
    "MergedPlayerInfo",
    "merge_player_info",
]
