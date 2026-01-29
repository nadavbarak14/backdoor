"""
Player Info Service Module

Provides a service that aggregates player biographical data from multiple
adapter sources (Winner, Euroleague, etc.) with merge logic to handle
conflicting data.

The service:
1. Manages multiple BasePlayerInfoAdapter instances
2. Fetches player info from sources based on external_ids
3. Merges results using configurable priority rules
4. Provides search across all adapters

Usage:
    from src.sync.player_info import PlayerInfoService
    from src.sync.winner.adapter import WinnerAdapter
    from src.sync.euroleague.adapter import EuroleagueAdapter

    # Create adapters
    winner_adapter = WinnerAdapter(client, scraper, mapper)
    euroleague_adapter = EuroleagueAdapter(client, direct_client, mapper)

    # Create service with adapters ordered by priority
    service = PlayerInfoService([winner_adapter, euroleague_adapter])

    # Fetch player info from multiple sources
    merged = await service.get_player_info({
        "winner": "w123",
        "euroleague": "e456",
    })
"""

from typing import Any

from src.sync.adapters.base import BasePlayerInfoAdapter
from src.sync.player_info.merger import MergedPlayerInfo, merge_player_info
from src.sync.types import RawPlayerInfo


class PlayerInfoService:
    """
    Aggregates player info from multiple BasePlayerInfoAdapter sources.

    Manages a list of player info adapters and provides methods to fetch,
    merge, and search player biographical data across all sources.

    Attributes:
        adapters: List of player info adapters ordered by priority.
            Earlier adapters have higher priority when merging.

    Example:
        >>> winner_adapter = WinnerAdapter(client, scraper, mapper)
        >>> euroleague_adapter = EuroleagueAdapter(client, direct_client, mapper)
        >>> service = PlayerInfoService([winner_adapter, euroleague_adapter])
        >>>
        >>> # Fetch and merge player info
        >>> merged = await service.get_player_info({
        ...     "winner": "w123",
        ...     "euroleague": "e456",
        ... })
        >>> print(f"{merged.first_name} {merged.last_name}")
    """

    def __init__(self, adapters: list[BasePlayerInfoAdapter]) -> None:
        """
        Initialize PlayerInfoService.

        Args:
            adapters: List of BasePlayerInfoAdapter instances ordered by priority.
                Earlier adapters have higher priority when merging data.

        Example:
            >>> service = PlayerInfoService([winner_adapter, euroleague_adapter])
        """
        self.adapters = adapters
        self._adapter_map: dict[str, BasePlayerInfoAdapter] = {
            adapter.source_name: adapter for adapter in adapters
        }

    async def get_player_info(
        self,
        external_ids: dict[str, str],
    ) -> MergedPlayerInfo | None:
        """
        Fetch player info from all sources that have an external ID.

        Fetches player biographical data from each adapter that has a
        corresponding external_id, then merges the results using the
        adapter priority order.

        Args:
            external_ids: Mapping of source_name to external_id.
                Only sources with matching external_ids will be queried.

        Returns:
            MergedPlayerInfo with consolidated data from all sources,
            or None if no sources returned data.

        Example:
            >>> merged = await service.get_player_info({
            ...     "winner": "w123",
            ...     "euroleague": "e456",
            ... })
            >>> if merged:
            ...     print(f"{merged.first_name} {merged.last_name}")
            ...     print(f"Height source: {merged.sources.get('height_cm')}")
        """
        sources: list[tuple[str, RawPlayerInfo]] = []

        # Fetch from adapters in priority order
        for adapter in self.adapters:
            if adapter.source_name in external_ids:
                external_id = external_ids[adapter.source_name]
                try:
                    info = await adapter.get_player_info(external_id)
                    sources.append((adapter.source_name, info))
                except Exception:
                    # Skip sources that fail to fetch
                    continue

        if not sources:
            return None

        return merge_player_info(sources)

    async def get_player_info_from_source(
        self,
        source_name: str,
        external_id: str,
    ) -> RawPlayerInfo | None:
        """
        Fetch player info from a specific source.

        Args:
            source_name: Name of the source adapter (e.g., "winner", "euroleague").
            external_id: External player identifier for that source.

        Returns:
            RawPlayerInfo from the specified source, or None if the source
            doesn't exist or the fetch fails.

        Example:
            >>> info = await service.get_player_info_from_source("winner", "w123")
            >>> if info:
            ...     print(f"{info.first_name} {info.last_name}")
        """
        adapter = self._adapter_map.get(source_name)
        if adapter is None:
            return None

        try:
            return await adapter.get_player_info(external_id)
        except Exception:
            return None

    async def search_player(
        self,
        name: str,
        team: str | None = None,
    ) -> list[RawPlayerInfo]:
        """
        Search for players across all adapters.

        Searches each adapter for players matching the name and optional
        team filter. Results are combined from all sources.

        Args:
            name: Player name to search for (partial match supported).
            team: Optional team external ID to filter results.

        Returns:
            List of RawPlayerInfo matching the search criteria from all sources.
            Note: Duplicates may exist if the same player appears in multiple sources.

        Example:
            >>> results = await service.search_player("James")
            >>> for player in results:
            ...     print(f"{player.first_name} {player.last_name}")
        """
        all_results: list[RawPlayerInfo] = []

        for adapter in self.adapters:
            try:
                results = await adapter.search_player(name, team)
                all_results.extend(results)
            except Exception:
                # Skip sources that fail to search
                continue

        return all_results

    async def update_player_from_sources(
        self,
        player: Any,
    ) -> dict[str, Any]:
        """
        Fetch latest info from all sources for a player.

        Uses the player's external_ids attribute to query each source
        and returns a dict of fields that can be used to update the player.

        Args:
            player: Player model instance with an external_ids attribute
                that maps source_name to external_id.

        Returns:
            Dict of field names to updated values. Only includes fields
            that have non-None values from the merged sources.

        Example:
            >>> from src.models.player import Player
            >>> player = session.query(Player).get(player_id)
            >>> updates = await service.update_player_from_sources(player)
            >>> for field, value in updates.items():
            ...     setattr(player, field, value)
            >>> session.commit()
        """
        external_ids = getattr(player, "external_ids", {})
        if not external_ids:
            return {}

        merged = await self.get_player_info(external_ids)
        if merged is None:
            return {}

        updates: dict[str, Any] = {}

        if merged.first_name:
            updates["first_name"] = merged.first_name
        if merged.last_name:
            updates["last_name"] = merged.last_name
        if merged.birth_date is not None:
            updates["birth_date"] = merged.birth_date
        if merged.height_cm is not None:
            updates["height_cm"] = merged.height_cm
        if merged.positions:
            updates["positions"] = merged.positions

        return updates

    def get_adapter(self, source_name: str) -> BasePlayerInfoAdapter | None:
        """
        Get an adapter by source name.

        Args:
            source_name: Name of the source adapter.

        Returns:
            The adapter instance, or None if not found.

        Example:
            >>> adapter = service.get_adapter("winner")
            >>> if adapter:
            ...     info = await adapter.get_player_info("w123")
        """
        return self._adapter_map.get(source_name)

    @property
    def source_names(self) -> list[str]:
        """
        Get list of available source names.

        Returns:
            List of source names in priority order.

        Example:
            >>> print(service.source_names)
            ['winner', 'euroleague']
        """
        return [adapter.source_name for adapter in self.adapters]
