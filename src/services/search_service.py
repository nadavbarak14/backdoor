"""
Search Service Module

Provides fast autocomplete and hierarchical browse functionality
for the @-mention feature in the chat UI.

This service handles:
    - Unified search across players, teams, seasons, and leagues
    - Hierarchical browse navigation (League -> Season -> Team -> Player)
    - Optimized queries for fast typeahead response

Usage:
    from src.services.search_service import SearchService

    service = SearchService(db_session)
    results = service.autocomplete("mac", limit=10)
"""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models import League, Player, Season, Team, TeamSeason
from src.schemas.search import (
    AutocompleteResponse,
    BrowseItem,
    BrowseParent,
    BrowseResponse,
    EntityType,
    SearchResult,
)


class SearchService:
    """
    Service for entity search and hierarchical browsing.

    Provides optimized search across all mentionable entities
    and hierarchical navigation for the browse UI.

    Attributes:
        db: SQLAlchemy database session

    Example:
        >>> service = SearchService(db)
        >>> results = service.autocomplete("curry")
        >>> print(results.results[0].name)
        Stephen Curry
    """

    def __init__(self, db: Session):
        """
        Initialize the search service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def autocomplete(self, query: str, limit: int = 10) -> AutocompleteResponse:
        """
        Search across all entity types for autocomplete.

        Searches players (first name, last name), teams, seasons,
        and leagues. Returns results ordered by relevance with
        exact prefix matches prioritized.

        Args:
            query: Search query string (minimum 1 character)
            limit: Maximum number of results (default 10, max 20)

        Returns:
            AutocompleteResponse with matching entities

        Example:
            >>> results = service.autocomplete("mac")
            >>> for r in results.results:
            ...     print(f"{r.type}: {r.name}")
            player: Mac McClung
            team: Maccabi Tel Aviv
        """
        if not query or len(query.strip()) == 0:
            return AutocompleteResponse(results=[])

        query = query.strip().lower()
        limit = min(limit, 20)  # Cap at 20 results

        results: list[SearchResult] = []

        # Search players (first name, last name, or full name)
        players = self._search_players(query, limit)
        results.extend(players)

        # Search teams
        teams = self._search_teams(query, limit)
        results.extend(teams)

        # Search seasons
        seasons = self._search_seasons(query, limit)
        results.extend(seasons)

        # Search leagues
        leagues = self._search_leagues(query, limit)
        results.extend(leagues)

        # Sort by relevance (exact prefix match first, then by name length)
        def relevance_key(r: SearchResult) -> tuple:
            name_lower = r.name.lower()
            # Priority: 0 = starts with query, 1 = contains query
            starts_with = 0 if name_lower.startswith(query) else 1
            return (starts_with, len(r.name), r.name)

        results.sort(key=relevance_key)

        return AutocompleteResponse(results=results[:limit])

    def _search_players(self, query: str, limit: int) -> list[SearchResult]:
        """
        Search players by first name, last name, or full name.

        Args:
            query: Lowercased search query
            limit: Maximum results

        Returns:
            List of SearchResult for matching players
        """
        # Build search conditions
        first_name_match = func.lower(Player.first_name).like(f"%{query}%")
        last_name_match = func.lower(Player.last_name).like(f"%{query}%")
        full_name_match = func.lower(Player.first_name + " " + Player.last_name).like(
            f"%{query}%"
        )

        stmt = (
            select(Player)
            .where(or_(first_name_match, last_name_match, full_name_match))
            .limit(limit)
        )

        players = self.db.execute(stmt).scalars().all()

        results = []
        for player in players:
            # Get current team for context
            context = self._get_player_team_context(player)
            results.append(
                SearchResult(
                    id=player.id,
                    type=EntityType.PLAYER,
                    name=player.full_name,
                    context=context,
                )
            )

        return results

    def _get_player_team_context(self, player: Player) -> str | None:
        """
        Get the player's current team name for context display.

        Args:
            player: Player model instance

        Returns:
            Team name or None if no current team
        """
        if player.team_histories:
            # Get most recent team history
            latest = max(player.team_histories, key=lambda h: h.created_at)
            return latest.team.name
        return None

    def _search_teams(self, query: str, limit: int) -> list[SearchResult]:
        """
        Search teams by name or short name.

        Args:
            query: Lowercased search query
            limit: Maximum results

        Returns:
            List of SearchResult for matching teams
        """
        name_match = func.lower(Team.name).like(f"%{query}%")
        short_name_match = func.lower(Team.short_name).like(f"%{query}%")

        stmt = select(Team).where(or_(name_match, short_name_match)).limit(limit)

        teams = self.db.execute(stmt).scalars().all()

        results = []
        for team in teams:
            # Get league for context
            context = self._get_team_league_context(team)
            results.append(
                SearchResult(
                    id=team.id,
                    type=EntityType.TEAM,
                    name=team.name,
                    context=context,
                )
            )

        return results

    def _get_team_league_context(self, team: Team) -> str | None:
        """
        Get the team's league name for context display.

        Args:
            team: Team model instance

        Returns:
            League name or None if no league association
        """
        if team.team_seasons:
            # Get most recent season association
            latest = max(team.team_seasons, key=lambda ts: ts.created_at)
            return latest.season.league.name
        return None

    def _search_seasons(self, query: str, limit: int) -> list[SearchResult]:
        """
        Search seasons by name.

        Args:
            query: Lowercased search query
            limit: Maximum results

        Returns:
            List of SearchResult for matching seasons
        """
        stmt = (
            select(Season)
            .where(func.lower(Season.name).like(f"%{query}%"))
            .limit(limit)
        )

        seasons = self.db.execute(stmt).scalars().all()

        results = []
        for season in seasons:
            results.append(
                SearchResult(
                    id=season.id,
                    type=EntityType.SEASON,
                    name=season.name,
                    context=season.league.name,
                )
            )

        return results

    def _search_leagues(self, query: str, limit: int) -> list[SearchResult]:
        """
        Search leagues by name or code.

        Args:
            query: Lowercased search query
            limit: Maximum results

        Returns:
            List of SearchResult for matching leagues
        """
        name_match = func.lower(League.name).like(f"%{query}%")
        code_match = func.lower(League.code).like(f"%{query}%")

        stmt = select(League).where(or_(name_match, code_match)).limit(limit)

        leagues = self.db.execute(stmt).scalars().all()

        results = []
        for league in leagues:
            results.append(
                SearchResult(
                    id=league.id,
                    type=EntityType.LEAGUE,
                    name=league.name,
                    context=league.country,
                )
            )

        return results

    # -------------------------------------------------------------------------
    # Browse Methods (Hierarchical Navigation)
    # -------------------------------------------------------------------------

    def browse_leagues(self) -> BrowseResponse:
        """
        Get all leagues for the root browse level.

        Returns:
            BrowseResponse with all leagues

        Example:
            >>> response = service.browse_leagues()
            >>> for item in response.items:
            ...     print(item.name)
            Israeli Basketball League
        """
        stmt = select(League).order_by(League.name)
        leagues = self.db.execute(stmt).scalars().all()

        items = [
            BrowseItem(
                id=league.id,
                type=EntityType.LEAGUE,
                name=league.name,
                has_children=True,
            )
            for league in leagues
        ]

        return BrowseResponse(items=items, parent=None)

    def browse_seasons(self, league_id: UUID) -> BrowseResponse:
        """
        Get seasons for a specific league.

        Args:
            league_id: UUID of the parent league

        Returns:
            BrowseResponse with seasons and league as parent

        Raises:
            ValueError: If league_id doesn't exist
        """
        league = self.db.get(League, league_id)
        if not league:
            raise ValueError(f"League not found: {league_id}")

        stmt = (
            select(Season)
            .where(Season.league_id == league_id)
            .order_by(Season.name.desc())  # Most recent first
        )
        seasons = self.db.execute(stmt).scalars().all()

        items = [
            BrowseItem(
                id=season.id,
                type=EntityType.SEASON,
                name=season.name,
                has_children=True,
            )
            for season in seasons
        ]

        parent = BrowseParent(
            id=league.id,
            type=EntityType.LEAGUE,
            name=league.name,
        )

        return BrowseResponse(items=items, parent=parent)

    def browse_teams(self, season_id: UUID) -> BrowseResponse:
        """
        Get teams for a specific season.

        Args:
            season_id: UUID of the parent season

        Returns:
            BrowseResponse with teams and season as parent

        Raises:
            ValueError: If season_id doesn't exist
        """
        season = self.db.get(Season, season_id)
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        stmt = (
            select(Team)
            .join(TeamSeason, Team.id == TeamSeason.team_id)
            .where(TeamSeason.season_id == season_id)
            .order_by(Team.name)
        )
        teams = self.db.execute(stmt).scalars().all()

        items = [
            BrowseItem(
                id=team.id,
                type=EntityType.TEAM,
                name=team.name,
                has_children=True,
            )
            for team in teams
        ]

        parent = BrowseParent(
            id=season.id,
            type=EntityType.SEASON,
            name=season.name,
        )

        return BrowseResponse(items=items, parent=parent)

    def browse_players(
        self, team_id: UUID, season_id: UUID | None = None
    ) -> BrowseResponse:
        """
        Get players for a specific team.

        Args:
            team_id: UUID of the parent team
            season_id: Optional season filter for roster

        Returns:
            BrowseResponse with players and team as parent

        Raises:
            ValueError: If team_id doesn't exist
        """
        team = self.db.get(Team, team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        # Get players from team histories
        from src.models import PlayerTeamHistory

        stmt = (
            select(Player)
            .join(PlayerTeamHistory, Player.id == PlayerTeamHistory.player_id)
            .where(PlayerTeamHistory.team_id == team_id)
        )

        if season_id:
            stmt = stmt.where(PlayerTeamHistory.season_id == season_id)

        stmt = stmt.distinct().order_by(Player.last_name, Player.first_name)
        players = self.db.execute(stmt).scalars().all()

        items = [
            BrowseItem(
                id=player.id,
                type=EntityType.PLAYER,
                name=player.full_name,
                has_children=False,  # Players are leaf nodes
            )
            for player in players
        ]

        parent = BrowseParent(
            id=team.id,
            type=EntityType.TEAM,
            name=team.name,
        )

        return BrowseResponse(items=items, parent=parent)
