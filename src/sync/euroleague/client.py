"""
Euroleague Client Module

Provides the EuroleagueClient class for fetching data using the euroleague-api package.
Wraps the package with caching layer for efficient data retrieval and change detection.

This module exports:
    - EuroleagueClient: Client for Euroleague data with caching
    - CacheResult: Dataclass for fetch results with caching metadata

Usage:
    from sqlalchemy.orm import Session
    from src.sync.euroleague.client import EuroleagueClient

    db = SessionLocal()
    with EuroleagueClient(db) as client:
        result = client.fetch_season_games(2024)
        print(f"Fetched {len(result.data)} games")
        print(f"Changed: {result.changed}")
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from euroleague_api.boxscore_data import BoxScoreData
from euroleague_api.game_metadata import GameMetadata
from euroleague_api.play_by_play_data import PlayByPlay
from euroleague_api.player_stats import PlayerStats
from euroleague_api.shot_data import ShotData
from euroleague_api.standings import Standings
from sqlalchemy.orm import Session

from src.models.sync_cache import SyncCache
from src.sync.euroleague.config import EuroleagueConfig


@dataclass
class CacheResult:
    """
    Result from a cached fetch operation.

    Contains the fetched data along with caching metadata to indicate
    whether the data is new or unchanged from the previous fetch.

    Attributes:
        data: The fetched data (dict or list of dicts from DataFrame).
        changed: True if data differs from cached version.
        fetched_at: Timestamp when data was fetched.
        cache_id: UUID of the cache entry.
        from_cache: True if data was served from cache without API request.

    Example:
        >>> result = client.fetch_game_boxscore(2024, 1)
        >>> if result.changed:
        ...     print("New data available!")
        ...     process_boxscore(result.data)
    """

    data: dict | list
    changed: bool
    fetched_at: datetime
    cache_id: str
    from_cache: bool = False


class EuroleagueClient:
    """
    Client for fetching Euroleague data using the euroleague-api package.

    Wraps the euroleague-api package with caching layer. All responses are
    cached in the database with checksum-based change detection.

    Attributes:
        db: SQLAlchemy database session.
        config: Configuration settings.
        _game_metadata: GameMetadata instance from euroleague-api.
        _boxscore: BoxScoreData instance from euroleague-api.
        _pbp: PlayByPlay instance from euroleague-api.
        _shot_data: ShotData instance from euroleague-api.
        _standings: Standings instance from euroleague-api.
        _player_stats: PlayerStats instance from euroleague-api.

    Example:
        >>> db = SessionLocal()
        >>> with EuroleagueClient(db) as client:
        ...     # Fetch season games
        ...     games = client.fetch_season_games(2024)
        ...     print(f"Games: {len(games.data)}")
        ...
        ...     # Fetch specific game boxscore
        ...     boxscore = client.fetch_game_boxscore(2024, 1)
        ...     print(f"Players: {len(boxscore.data)}")
    """

    SOURCE = "euroleague"

    def __init__(
        self,
        db: Session,
        config: EuroleagueConfig | None = None,
    ) -> None:
        """
        Initialize EuroleagueClient.

        Args:
            db: SQLAlchemy database session for caching.
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> db = SessionLocal()
            >>> client = EuroleagueClient(db)
            >>> # Or with EuroCup
            >>> config = EuroleagueConfig(competition='U')
            >>> client = EuroleagueClient(db, config=config)
        """
        self.db = db
        self.config = config or EuroleagueConfig()

        # Initialize euroleague-api instances
        self._game_metadata: GameMetadata | None = None
        self._boxscore: BoxScoreData | None = None
        self._pbp: PlayByPlay | None = None
        self._shot_data: ShotData | None = None
        self._standings: Standings | None = None
        self._player_stats: PlayerStats | None = None

    def __enter__(self) -> "EuroleagueClient":
        """
        Context manager entry - initialize API clients.

        Returns:
            EuroleagueClient: Self for method chaining.
        """
        self._init_clients()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit - cleanup.

        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.
        """
        # euroleague-api clients don't need explicit cleanup
        pass

    def _init_clients(self) -> None:
        """Initialize euroleague-api client instances."""
        competition = self.config.competition
        self._game_metadata = GameMetadata(competition=competition)
        self._boxscore = BoxScoreData(competition=competition)
        self._pbp = PlayByPlay(competition=competition)
        self._shot_data = ShotData(competition=competition)
        self._standings = Standings(competition=competition)
        self._player_stats = PlayerStats(competition=competition)

    @property
    def game_metadata(self) -> GameMetadata:
        """Get GameMetadata client, initializing if needed."""
        if self._game_metadata is None:
            self._init_clients()
        return self._game_metadata  # type: ignore

    @property
    def boxscore(self) -> BoxScoreData:
        """Get BoxScoreData client, initializing if needed."""
        if self._boxscore is None:
            self._init_clients()
        return self._boxscore  # type: ignore

    @property
    def pbp(self) -> PlayByPlay:
        """Get PlayByPlay client, initializing if needed."""
        if self._pbp is None:
            self._init_clients()
        return self._pbp  # type: ignore

    @property
    def shot_data(self) -> ShotData:
        """Get ShotData client, initializing if needed."""
        if self._shot_data is None:
            self._init_clients()
        return self._shot_data  # type: ignore

    @property
    def standings(self) -> Standings:
        """Get Standings client, initializing if needed."""
        if self._standings is None:
            self._init_clients()
        return self._standings  # type: ignore

    @property
    def player_stats(self) -> PlayerStats:
        """Get PlayerStats client, initializing if needed."""
        if self._player_stats is None:
            self._init_clients()
        return self._player_stats  # type: ignore

    def _compute_hash(self, data: dict | list) -> str:
        """
        Compute SHA-256 hash of data for change detection.

        Args:
            data: Dictionary or list to hash.

        Returns:
            str: Hex-encoded SHA-256 hash.
        """
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _dataframe_to_dict(self, df: pd.DataFrame) -> list[dict]:
        """
        Convert pandas DataFrame to list of dicts for caching.

        Args:
            df: pandas DataFrame.

        Returns:
            list[dict]: List of row dictionaries.
        """
        return df.to_dict(orient="records")

    def _get_cache(
        self,
        resource_type: str,
        resource_id: str,
    ) -> SyncCache | None:
        """
        Get cached entry from database.

        Args:
            resource_type: Type of resource (e.g., "season_games", "boxscore").
            resource_id: Resource identifier.

        Returns:
            SyncCache if found, None otherwise.
        """
        return (
            self.db.query(SyncCache)
            .filter(
                SyncCache.source == self.SOURCE,
                SyncCache.resource_type == resource_type,
                SyncCache.resource_id == resource_id,
            )
            .first()
        )

    def _save_cache(
        self,
        resource_type: str,
        resource_id: str,
        data: dict | list,
    ) -> tuple[SyncCache, bool]:
        """
        Save or update cache entry.

        Args:
            resource_type: Type of resource.
            resource_id: Resource identifier.
            data: Data to cache.

        Returns:
            Tuple of (cache entry, changed flag).
        """
        content_hash = self._compute_hash(data)
        now = datetime.now(UTC)

        cache = self._get_cache(resource_type, resource_id)

        if cache:
            # Check if data changed
            changed = cache.content_hash != content_hash

            if changed:
                cache.raw_data = data
                cache.content_hash = content_hash
                cache.fetched_at = now
                self.db.commit()
            else:
                # Update fetched_at even if data unchanged
                cache.fetched_at = now
                self.db.commit()

            return cache, changed
        else:
            # Create new cache entry
            cache = SyncCache(
                source=self.SOURCE,
                resource_type=resource_type,
                resource_id=resource_id,
                raw_data=data,
                content_hash=content_hash,
                fetched_at=now,
            )
            self.db.add(cache)
            self.db.commit()
            self.db.refresh(cache)

            return cache, True

    def fetch_season_games(self, season: int, force: bool = False) -> CacheResult:
        """
        Fetch all games for a season.

        Uses GameMetadata.get_gamecodes_season() to retrieve all games
        including dates, teams, and scores.

        Args:
            season: The season year (e.g., 2024).
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of game dictionaries with caching metadata.

        Example:
            >>> result = client.fetch_season_games(2024)
            >>> print(f"Found {len(result.data)} games")
            >>> for game in result.data[:3]:
            ...     print(f"{game['hometeam']} vs {game['awayteam']}")
        """
        resource_type = "season_games"
        resource_id = f"{self.config.competition}{season}"

        # Check cache unless force refresh
        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        # Fetch from API
        df = self.game_metadata.get_gamecodes_season(season)
        data = self._dataframe_to_dict(df)

        # Save to cache
        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_game_metadata(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch metadata for a specific game.

        Uses GameMetadata.get_game_metadata() to retrieve detailed game info
        including stadium, coaches, referees, and quarter scores.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Game metadata dictionary.

        Example:
            >>> result = client.fetch_game_metadata(2024, 1)
            >>> print(f"Stadium: {result.data[0]['Stadium']}")
            >>> print(f"Score: {result.data[0]['ScoreA']} - {result.data[0]['ScoreB']}")
        """
        resource_type = "game_metadata"
        resource_id = f"{self.config.competition}{season}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.game_metadata.get_game_metadata(season=season, gamecode=gamecode)
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_game_boxscore(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch boxscore for a specific game.

        Uses BoxScoreData.get_player_boxscore_stats_data() to retrieve
        player statistics for a game.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of player stats dictionaries.

        Example:
            >>> result = client.fetch_game_boxscore(2024, 1)
            >>> for player in result.data[:3]:
            ...     print(f"{player['Player']}: {player['Points']} pts")
        """
        resource_type = "boxscore"
        resource_id = f"{self.config.competition}{season}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.boxscore.get_player_boxscore_stats_data(
            season=season, gamecode=gamecode
        )
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_game_pbp(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch play-by-play data for a specific game.

        Uses PlayByPlay.get_game_play_by_play_data() to retrieve
        all play-by-play events.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of play-by-play event dictionaries.

        Example:
            >>> result = client.fetch_game_pbp(2024, 1)
            >>> print(f"Found {len(result.data)} events")
        """
        resource_type = "pbp"
        resource_id = f"{self.config.competition}{season}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.pbp.get_game_play_by_play_data(season=season, gamecode=gamecode)
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_game_pbp_with_lineups(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch play-by-play data with lineups for a specific game.

        Uses PlayByPlay.get_pbp_data_with_lineups() to retrieve
        play-by-play events with on-court lineup tracking.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of play-by-play events with lineup data.

        Example:
            >>> result = client.fetch_game_pbp_with_lineups(2024, 1)
            >>> event = result.data[0]
            >>> print(f"Home lineup: {event['Lineup_A']}")
        """
        resource_type = "pbp_lineups"
        resource_id = f"{self.config.competition}{season}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.pbp.get_pbp_data_with_lineups(season=season, gamecode=gamecode)
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_game_shots(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch shot data for a specific game.

        Uses ShotData.get_game_shot_data() to retrieve shot locations,
        zones, and contextual information.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of shot dictionaries with coordinates.

        Example:
            >>> result = client.fetch_game_shots(2024, 1)
            >>> for shot in result.data[:3]:
            ...     print(f"{shot['PLAYER']}: ({shot['COORD_X']}, {shot['COORD_Y']})")
        """
        resource_type = "shots"
        resource_id = f"{self.config.competition}{season}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.shot_data.get_game_shot_data(season=season, gamecode=gamecode)
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_standings(
        self, season: int, round_number: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch standings for a specific round.

        Uses Standings.get_standings() to retrieve team standings
        including records and positions.

        Args:
            season: The season year.
            round_number: The round number.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of team standings dictionaries.

        Example:
            >>> result = client.fetch_standings(2024, 10)
            >>> for team in result.data[:3]:
            ...     print(f"{team['club.name']}: {team['gamesWon']}-{team['gamesLost']}")
        """
        resource_type = "standings"
        resource_id = f"{self.config.competition}{season}_r{round_number}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.standings.get_standings(season=season, round_number=round_number)
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_player_leaders(
        self,
        season: int,
        stat_category: str = "Score",
        top_n: int = 50,
        force: bool = False,
    ) -> CacheResult:
        """
        Fetch player stat leaders for a season.

        Uses PlayerStats.get_player_stats_leaders_single_season() to retrieve
        top players in a statistical category.

        Args:
            season: The season year.
            stat_category: Stat category ('Score', 'Assistances', 'TotalRebounds', etc.).
            top_n: Number of players to return.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of player stat dictionaries.

        Example:
            >>> result = client.fetch_player_leaders(2024, 'Score', 10)
            >>> for player in result.data:
            ...     print(f"{player['playerName']}: {player['averagePerGame']} ppg")
        """
        resource_type = "player_leaders"
        resource_id = f"{self.config.competition}{season}_{stat_category}_{top_n}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        df = self.player_stats.get_player_stats_leaders_single_season(
            season=season, stat_category=stat_category, top_n=top_n
        )
        data = self._dataframe_to_dict(df)

        cache, changed = self._save_cache(resource_type, resource_id, data)

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_multiple_boxscores(
        self,
        season: int,
        gamecodes: list[int],
        force: bool = False,
    ) -> dict[int, CacheResult]:
        """
        Fetch boxscores for multiple games.

        Convenience method for fetching multiple boxscores sequentially.

        Args:
            season: The season year.
            gamecodes: List of game codes.
            force: If True, bypass cache and fetch from API.

        Returns:
            Dict mapping gamecode to CacheResult.

        Example:
            >>> results = client.fetch_multiple_boxscores(2024, [1, 2, 3])
            >>> for gamecode, result in results.items():
            ...     print(f"Game {gamecode}: {len(result.data)} players")
        """
        results = {}
        for gamecode in gamecodes:
            results[gamecode] = self.fetch_game_boxscore(season, gamecode, force=force)
        return results
