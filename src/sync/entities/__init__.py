"""
Entity Syncers Package

Provides syncer classes for importing individual entity types from external
data sources into the database. These syncers handle the transformation from
raw data types to database models, leveraging deduplication services.

Entity Syncers:
    - PlayerSyncer: Syncs player data using PlayerDeduplicator
    - TeamSyncer: Syncs team and roster data using TeamMatcher
    - GameSyncer: Syncs games, box scores, and play-by-play data

Usage:
    from src.sync.entities import PlayerSyncer, TeamSyncer, GameSyncer

    player_syncer = PlayerSyncer(db, player_deduplicator)
    team_syncer = TeamSyncer(db, team_matcher, player_deduplicator)
    game_syncer = GameSyncer(db, team_matcher, player_deduplicator)

    # Sync a player
    player = player_syncer.sync_player(raw_player_info, team_id, source)

    # Sync a game with box score
    game = game_syncer.sync_game(raw_game, season_id, source)
    game_syncer.sync_boxscore(raw_boxscore, game)
"""

from src.sync.entities.game import GameSyncer
from src.sync.entities.player import PlayerSyncer
from src.sync.entities.team import TeamSyncer

__all__ = [
    "PlayerSyncer",
    "TeamSyncer",
    "GameSyncer",
]
