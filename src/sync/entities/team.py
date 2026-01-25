"""
Team Syncer Module

Provides functionality to sync team and roster data from external sources
to the database. Uses TeamMatcher for team deduplication and PlayerSyncer
for roster synchronization.

Usage:
    from src.sync.entities.team import TeamSyncer
    from src.sync.deduplication import TeamMatcher, PlayerDeduplicator

    team_matcher = TeamMatcher(db_session)
    player_deduplicator = PlayerDeduplicator(db_session)
    syncer = TeamSyncer(db_session, team_matcher, player_deduplicator)

    # Sync a team
    team = syncer.sync_team(raw_team, source)

    # Sync with season-specific record
    team, team_season = syncer.sync_team_season(raw_team, season_id, source)

    # Sync roster for a team
    syncer.sync_roster(player_stats, team, season, source)
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.league import Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team, TeamSeason
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities.player import PlayerSyncer
from src.sync.types import RawPlayerStats, RawTeam


class TeamSyncer:
    """
    Syncs team and roster data from external sources to the database.

    Uses TeamMatcher for team deduplication and PlayerDeduplicator
    for player matching when syncing rosters.

    Attributes:
        db: SQLAlchemy Session for database operations.
        team_matcher: TeamMatcher for team deduplication.
        player_syncer: PlayerSyncer for roster synchronization.

    Example:
        >>> syncer = TeamSyncer(db, team_matcher, player_deduplicator)
        >>> team = syncer.sync_team(raw_team, "winner")
        >>> syncer.sync_roster(player_stats, team, season, "winner")
    """

    def __init__(
        self,
        db: Session,
        team_matcher: TeamMatcher,
        player_deduplicator: PlayerDeduplicator,
    ) -> None:
        """
        Initialize the team syncer.

        Args:
            db: SQLAlchemy database session.
            team_matcher: TeamMatcher instance for team deduplication.
            player_deduplicator: PlayerDeduplicator for player matching.

        Example:
            >>> syncer = TeamSyncer(db_session, team_matcher, player_deduplicator)
        """
        self.db = db
        self.team_matcher = team_matcher
        self.player_syncer = PlayerSyncer(db, player_deduplicator)

    def sync_team(self, raw: RawTeam, source: str) -> Team:
        """
        Sync a team from raw data to the database.

        Uses TeamMatcher to find an existing team or create a new one.
        Handles matching by external ID or name.

        Args:
            raw: Raw team data from external source.
            source: The data source name (e.g., "winner", "euroleague").

        Returns:
            The found or created Team entity.

        Example:
            >>> team = syncer.sync_team(
            ...     raw=RawTeam(
            ...         external_id="t123",
            ...         name="Maccabi Tel Aviv",
            ...         short_name="MTA"
            ...     ),
            ...     source="winner"
            ... )
        """
        return self.team_matcher.find_or_create_team(
            source=source,
            external_id=raw.external_id,
            team_data=raw,
        )

    def sync_team_season(
        self,
        raw: RawTeam,
        season_id: UUID,
        source: str,
    ) -> tuple[Team, TeamSeason]:
        """
        Sync a team with its season-specific record.

        Creates or finds both the deduplicated Team and the TeamSeason
        record for this specific competition.

        Args:
            raw: Raw team data from external source.
            season_id: UUID of the season.
            source: The data source name.

        Returns:
            Tuple of (Team, TeamSeason) entities.

        Example:
            >>> team, team_season = syncer.sync_team_season(
            ...     raw_team, season.id, "winner"
            ... )
        """
        return self.team_matcher.find_or_create_team_season(
            source=source,
            external_id=raw.external_id,
            team_data=raw,
            season_id=season_id,
        )

    def sync_roster(
        self,
        players: list[RawPlayerStats],
        team: Team,
        season: Season,
        source: str,
    ) -> list[Player]:
        """
        Sync roster entries for a team from player stats.

        Creates or updates PlayerTeamHistory records linking players
        to the team for the given season.

        Args:
            players: List of raw player stats (from box score).
            team: The Team entity.
            season: The Season entity.
            source: The data source name.

        Returns:
            List of synced Player entities.

        Example:
            >>> players = syncer.sync_roster(
            ...     boxscore.home_players, home_team, season, "winner"
            ... )
        """
        synced_players: list[Player] = []

        for raw_stats in players:
            # Find or create player
            player = self.player_syncer.sync_player_from_stats(
                raw=raw_stats,
                team_id=team.id,
                source=source,
            )

            # Create PlayerTeamHistory if not exists
            self._ensure_team_history(
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
            )

            synced_players.append(player)

        return synced_players

    def get_by_external_id(self, source: str, external_id: str) -> Team | None:
        """
        Get a team by its external ID for a specific source.

        Args:
            source: The data source name.
            external_id: The external ID from the source.

        Returns:
            The Team if found, None otherwise.

        Example:
            >>> team = syncer.get_by_external_id("winner", "t123")
        """
        return self.team_matcher.get_by_external_id(source, external_id)

    def get_team_season(
        self,
        season_id: UUID,
        external_id: str,
    ) -> TeamSeason | None:
        """
        Get a TeamSeason by external ID within a season.

        Args:
            season_id: UUID of the season.
            external_id: The external ID to search for.

        Returns:
            The TeamSeason if found, None otherwise.

        Example:
            >>> ts = syncer.get_team_season(season.id, "t123")
        """
        return self.team_matcher.get_team_season_by_external_id(
            season_id=season_id,
            external_id=external_id,
        )

    def _ensure_team_history(
        self,
        player_id: UUID,
        team_id: UUID,
        season_id: UUID,
    ) -> PlayerTeamHistory:
        """
        Ensure a PlayerTeamHistory record exists.

        Creates the record if it doesn't exist, otherwise returns existing.

        Args:
            player_id: UUID of the player.
            team_id: UUID of the team.
            season_id: UUID of the season.

        Returns:
            The found or created PlayerTeamHistory.
        """
        stmt = select(PlayerTeamHistory).where(
            PlayerTeamHistory.player_id == player_id,
            PlayerTeamHistory.team_id == team_id,
            PlayerTeamHistory.season_id == season_id,
        )
        history = self.db.scalars(stmt).first()

        if history:
            return history

        history = PlayerTeamHistory(
            player_id=player_id,
            team_id=team_id,
            season_id=season_id,
        )
        self.db.add(history)
        self.db.flush()
        return history
