"""
Player Deduplication Module

Provides functionality for deduplicating players across different data sources
(Winner League, Euroleague). Players are matched using multiple strategies:

1. External ID match - exact match by source-specific ID
2. Team roster match - same team, same normalized name
3. Global match - name + biographical data (birth_date, height)

This handles cases where:
- Players appear on the same team in multiple leagues
- Players transfer between teams but appear in multiple sources
- Names are consistent but may have minor variations (accents, transliterations)

Usage:
    from src.sync.deduplication.player import PlayerDeduplicator
    from src.sync.types import RawPlayerInfo

    dedup = PlayerDeduplicator(db_session)

    # Find or create a player
    player = dedup.find_or_create_player(
        source="winner",
        external_id="player-123",
        player_data=RawPlayerInfo(
            external_id="player-123",
            first_name="Scottie",
            last_name="Wilbekin",
            birth_date=date(1993, 7, 19)
        ),
        team_id=team_uuid
    )
"""

from datetime import date
from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from src.models.player import Player, PlayerTeamHistory
from src.sync.deduplication.normalizer import (
    names_match,
    names_match_fuzzy,
    normalize_name,
    strip_name_suffix,
)
from src.sync.types import RawPlayerInfo


class PlayerDeduplicator:
    """
    Service for deduplicating players across data sources.

    Uses a multi-tier matching strategy:
    1. External ID - exact match for known mappings
    2. Team roster - players on the same team with matching names
    3. Global bio match - name + birth_date or height for transferred players

    Attributes:
        db: SQLAlchemy Session for database operations.

    Example:
        >>> dedup = PlayerDeduplicator(db_session)
        >>> player = dedup.find_or_create_player(
        ...     source="winner",
        ...     external_id="123",
        ...     player_data=RawPlayerInfo(
        ...         external_id="123",
        ...         first_name="Scottie",
        ...         last_name="Wilbekin"
        ...     ),
        ...     team_id=team.id
        ... )
    """

    # Height tolerance for matching (in cm)
    HEIGHT_TOLERANCE_CM = 3

    def __init__(self, db: Session) -> None:
        """
        Initialize the player deduplicator.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> dedup = PlayerDeduplicator(db_session)
        """
        self.db = db

    def find_or_create_player(
        self,
        source: str,
        external_id: str,
        player_data: RawPlayerInfo,
        team_id: UUID | None = None,
        season_id: UUID | None = None,
        jersey_number: str | None = None,
    ) -> Player:
        """
        Find an existing player or create a new one from external data.

        This method follows a multi-tier matching process:
        1. Check if a player exists with this external_id for this source
        2. If team_id + season_id + jersey_number provided, match by jersey
        3. If team_id provided, check team roster for name match
        4. Try global match using name + bio data (birth_date, height)
        5. If no match found, create new player

        Args:
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID from the data source.
            player_data: Raw player info containing name and bio data.
            team_id: Optional UUID of the team this player belongs to.
            season_id: Optional UUID of the season (for jersey matching).
            jersey_number: Optional jersey number (for matching with roster).

        Returns:
            The matched or newly created Player entity.

        Example:
            >>> from src.schemas.enums import Position
            >>> player = dedup.find_or_create_player(
            ...     source="winner",
            ...     external_id="player-123",
            ...     player_data=RawPlayerInfo(
            ...         external_id="player-123",
            ...         first_name="LeBron",
            ...         last_name="James",
            ...         birth_date=date(1984, 12, 30),
            ...         positions=[Position.SMALL_FORWARD]
            ...     ),
            ...     team_id=team.id
            ... )
        """
        # Step 1: Check by external_id for this source
        existing = self.get_by_external_id(source, external_id)
        if existing:
            # Fill in missing data from player_data
            return self._update_missing_data(existing, player_data)

        player_name = f"{player_data.first_name} {player_data.last_name}"

        # Step 2: Try to match by jersey number on the same team/season
        if team_id and season_id and jersey_number:
            matched = self.match_player_by_jersey(
                team_id, season_id, jersey_number, source
            )
            if matched:
                return self.merge_external_id(matched, source, external_id, player_data)

        # Step 3: Try to match by name on the same team (if team provided)
        if team_id:
            matched = self.match_player_on_team(team_id, player_name, source)
            if matched:
                return self.merge_external_id(matched, source, external_id, player_data)

        # Step 4: Try global match using bio data
        matched = self.match_player_globally(
            player_name=player_name,
            source=source,
            birth_date=player_data.birth_date,
            height_cm=player_data.height_cm,
        )
        if matched:
            return self.merge_external_id(matched, source, external_id, player_data)

        # Step 5: Create new player
        return self._create_player(source, external_id, player_data)

    def match_player_by_jersey(
        self,
        team_id: UUID,
        season_id: UUID,
        jersey_number: str,
    ) -> Player | None:
        """
        Find a roster player by jersey number.

        Args:
            team_id: UUID of the team.
            season_id: UUID of the season.
            jersey_number: Jersey number to match.

        Returns:
            The matched Player if found, None otherwise.
        """
        try:
            jersey_int = int(jersey_number)
        except (ValueError, TypeError):
            return None

        stmt = (
            select(Player)
            .join(PlayerTeamHistory, Player.id == PlayerTeamHistory.player_id)
            .where(
                PlayerTeamHistory.team_id == team_id,
                PlayerTeamHistory.season_id == season_id,
                PlayerTeamHistory.jersey_number == jersey_int,
            )
        )
        return self.db.scalars(stmt).first()

    def get_by_external_id(self, source: str, external_id: str) -> Player | None:
        """
        Find a player by their external ID for a specific source.

        Uses JSON field query to match the external_id stored in the
        player's external_ids column.

        Args:
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID from the data source.

        Returns:
            The Player if found, None otherwise.

        Example:
            >>> player = dedup.get_by_external_id("winner", "123")
            >>> if player:
            ...     print(player.full_name)
        """
        stmt = select(Player).where(
            cast(func.json_extract(Player.external_ids, f"$.{source}"), String)
            == external_id
        )
        return self.db.scalars(stmt).first()

    def match_player_on_team(
        self,
        team_id: UUID,
        player_name: str,
        source: str,
    ) -> Player | None:
        """
        Find a player on a team with a matching normalized name.

        Searches players who have a team history entry for the given team
        and compares their full name using normalized comparison.

        Note: Only matches players that DON'T already have an external_id
        for the given source, to avoid false matches.

        Args:
            team_id: UUID of the team to search within.
            player_name: Full name of the player to match.
            source: The data source (used to exclude already-mapped players).

        Returns:
            The matched Player if found, None otherwise.

        Example:
            >>> player = dedup.match_player_on_team(
            ...     team_id=maccabi.id,
            ...     player_name="Scottie Wilbekin",
            ...     source="euroleague"
            ... )
        """
        # Get all players on this team
        stmt = (
            select(Player)
            .join(PlayerTeamHistory)
            .where(PlayerTeamHistory.team_id == team_id)
            .distinct()
        )
        team_players = self.db.scalars(stmt).all()

        return self._find_name_match(team_players, player_name, source)

    def match_player_globally(
        self,
        player_name: str,
        source: str,
        birth_date: date | None = None,
        height_cm: int | None = None,
    ) -> Player | None:
        """
        Find a player globally using name and biographical data.

        This is used to match players who have transferred between teams.
        Uses indexed database queries to efficiently find candidates by last name,
        then applies finer matching logic.

        Matching priority:
        1. Name + birth_date (high confidence - birth dates are unique)
        2. Name + height within tolerance (medium confidence)

        Args:
            player_name: Full name of the player to match.
            source: The data source (used to exclude already-mapped players).
            birth_date: Player's birth date for additional matching.
            height_cm: Player's height in cm for additional matching.

        Returns:
            The matched Player if found with sufficient confidence, None otherwise.

        Example:
            >>> player = dedup.match_player_globally(
            ...     player_name="Scottie Wilbekin",
            ...     source="euroleague",
            ...     birth_date=date(1993, 7, 19)
            ... )
        """
        normalized_search = normalize_name(player_name)

        # Parse name parts, handling suffixes like "Jr.", "III", "IV"
        name_parts = player_name.split()
        if not name_parts:
            return None

        first_name = name_parts[0] if name_parts else ""

        # Extract last name, handling suffixes
        # "Wade Baldwin IV" -> last_name should be "Baldwin IV" or "Baldwin"
        if len(name_parts) > 1:
            # Join all parts after first name, then strip suffix for search
            last_name_full = " ".join(name_parts[1:])
            last_name = strip_name_suffix(last_name_full) or last_name_full
        else:
            last_name = name_parts[0]

        # Use database query to find candidates by last name (uses index)
        # This reduces O(n) full scan to O(log n) index lookup + small result set
        candidates = self._find_candidates_by_last_name(last_name, source)

        # Find name matches from candidates
        name_matches: list[Player] = []
        for player in candidates:
            # Match by full name (with fuzzy suffix handling)
            full_name_match = normalize_name(player.full_name) == normalized_search
            fuzzy_full_match = names_match_fuzzy(player.full_name, player_name)

            # Match by last name (fuzzy) + first initial
            last_name_match = names_match_fuzzy(player.last_name, last_name)
            first_initial_match = (
                first_name
                and player.first_name
                and normalize_name(first_name[0])
                == normalize_name(player.first_name[0])
            )

            if (
                full_name_match
                or fuzzy_full_match
                or (last_name_match and first_initial_match)
            ):
                name_matches.append(player)

        if not name_matches:
            return None

        # Priority 1: Match by birth_date (highest confidence)
        if birth_date:
            for player in name_matches:
                if player.birth_date == birth_date:
                    return player

        # Priority 2: Match by height within tolerance
        if height_cm:
            for player in name_matches:
                if (
                    player.height_cm
                    and abs(player.height_cm - height_cm) <= self.HEIGHT_TOLERANCE_CM
                ):
                    return player

        # If only one name match, consider returning it if bio data doesn't contradict
        if len(name_matches) == 1:
            candidate = name_matches[0]

            # Check if any provided bio data contradicts the candidate
            has_contradiction = False

            if (
                birth_date
                and candidate.birth_date
                and birth_date != candidate.birth_date
            ):
                has_contradiction = True

            if (
                height_cm
                and candidate.height_cm
                and abs(candidate.height_cm - height_cm) > self.HEIGHT_TOLERANCE_CM
            ):
                has_contradiction = True

            # Only return if:
            # 1. We have bio data provided AND
            # 2. There's no contradiction (either DB has no data or it matches)
            if (birth_date or height_cm) and not has_contradiction:
                return candidate

        return None

    def merge_external_id(
        self,
        player: Player,
        source: str,
        external_id: str,
        player_data: RawPlayerInfo | None = None,
    ) -> Player:
        """
        Add an external ID from a source to an existing player.

        Creates a new dict to ensure SQLAlchemy detects the change.
        If the source already has an external_id, it will be overwritten.

        Also fills in missing player data (positions, height, birth_date)
        from the new source if provided.

        Args:
            player: The Player entity to update.
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID to add.
            player_data: Optional player info to fill in missing fields.

        Returns:
            The updated Player entity.

        Example:
            >>> player = dedup.merge_external_id(player, "euroleague", "PWB")
            >>> print(player.external_ids)
            {'winner': '123', 'euroleague': 'PWB'}
        """
        # Create new dict to trigger SQLAlchemy change detection
        new_external_ids = dict(player.external_ids)
        new_external_ids[source] = external_id
        player.external_ids = new_external_ids

        # Fill in missing data from new source
        if player_data:
            if not player.positions and player_data.positions:
                player.positions = player_data.positions
            if not player.height_cm and player_data.height_cm:
                player.height_cm = player_data.height_cm
            if not player.birth_date and player_data.birth_date:
                player.birth_date = player_data.birth_date

        self.db.commit()
        self.db.refresh(player)
        return player

    def _update_missing_data(
        self, player: Player, player_data: RawPlayerInfo
    ) -> Player:
        """
        Update player with missing data from new source.

        Only fills in fields that are currently empty/null.
        Commits changes if any updates were made.

        Args:
            player: The Player entity to update.
            player_data: Raw player info with potential new data.

        Returns:
            The updated Player entity.
        """
        updated = False

        if not player.positions and player_data.positions:
            player.positions = player_data.positions
            updated = True
        if not player.height_cm and player_data.height_cm:
            player.height_cm = player_data.height_cm
            updated = True
        if not player.birth_date and player_data.birth_date:
            player.birth_date = player_data.birth_date
            updated = True

        if updated:
            self.db.commit()
            self.db.refresh(player)

        return player

    def _find_name_match(
        self,
        players: list[Player],
        player_name: str,
        source: str,
    ) -> Player | None:
        """
        Find a player with matching name from a list of candidates.

        Args:
            players: List of Player entities to search.
            player_name: Full name to match.
            source: Data source (to exclude already-mapped players).

        Returns:
            Matched Player or None.
        """
        normalized_search = normalize_name(player_name)
        name_parts = player_name.split()

        for player in players:
            # Skip if player already has an external_id for this source
            if source in player.external_ids:
                continue

            # Exact normalized name match
            if normalize_name(player.full_name) == normalized_search:
                return player

            # Last name + first initial match (handles nickname variations)
            if name_parts:
                last_name = name_parts[-1] if len(name_parts) > 1 else name_parts[0]
                if names_match(player.last_name, last_name):
                    first_name = name_parts[0] if name_parts else ""
                    if (
                        first_name
                        and player.first_name
                        and normalize_name(first_name[0])
                        == normalize_name(player.first_name[0])
                    ):
                        return player

        return None

    def _find_candidates_by_last_name(
        self,
        last_name: str,
        source: str,
    ) -> list[Player]:
        """
        Find player candidates by last name using database query.

        Uses case-insensitive LIKE query to efficiently find candidates
        without loading all players into memory. The database index on
        last_name column makes this O(log n) instead of O(n).

        Also handles name suffixes (Jr., III, IV, etc.) by searching for
        both the full name and the stripped version.

        Args:
            last_name: Last name to search for.
            source: Data source (to exclude already-mapped players).

        Returns:
            List of Player candidates with matching last name.
        """
        normalized_last = normalize_name(last_name)
        stripped_last = normalize_name(strip_name_suffix(last_name))

        # Search for both full and stripped last names
        # This handles "Baldwin IV" matching "Baldwin"
        search_names = {normalized_last}
        if stripped_last and stripped_last != normalized_last:
            search_names.add(stripped_last)

        candidates = []
        for search_name in search_names:
            stmt = select(Player).where(func.lower(Player.last_name) == search_name)
            candidates.extend(self.db.scalars(stmt).all())

        # Also search for players whose last name (stripped) matches our search
        # This handles "Baldwin" in DB matching search for "Baldwin IV"
        stmt = select(Player)
        all_players = self.db.scalars(stmt).all()
        for player in all_players:
            player_stripped = normalize_name(strip_name_suffix(player.last_name))
            if player_stripped in search_names and player not in candidates:
                candidates.append(player)

        # Filter out players already mapped to this source
        return [p for p in candidates if source not in p.external_ids]

    def _create_player(
        self,
        source: str,
        external_id: str,
        player_data: RawPlayerInfo,
    ) -> Player:
        """
        Create a new player from external data.

        Args:
            source: The data source name.
            external_id: The external ID from the data source.
            player_data: Raw player info.

        Returns:
            The newly created Player entity.
        """
        player = Player(
            first_name=player_data.first_name,
            last_name=player_data.last_name,
            birth_date=player_data.birth_date,
            height_cm=player_data.height_cm,
            positions=player_data.positions,
            external_ids={source: external_id},
        )

        self.db.add(player)
        self.db.commit()
        self.db.refresh(player)
        return player

    def find_all_by_team(self, team_id: UUID) -> list[Player]:
        """
        Get all players who have played for a given team.

        Args:
            team_id: UUID of the team.

        Returns:
            List of Player entities who have team history with this team.

        Example:
            >>> players = dedup.find_all_by_team(maccabi.id)
            >>> for p in players:
            ...     print(p.full_name)
        """
        stmt = (
            select(Player)
            .join(PlayerTeamHistory)
            .where(PlayerTeamHistory.team_id == team_id)
            .distinct()
        )
        return list(self.db.scalars(stmt).all())

    def find_potential_duplicates(self) -> list[tuple[Player, Player]]:
        """
        Find potential duplicate players in the database.

        Uses database-level grouping queries for efficiency - only fetches
        players that actually have duplicates, not all players.

        Complexity: O(d) where d = number of duplicate pairs (typically << n)
        The database handles grouping with indexes.

        Returns:
            List of (player1, player2) tuples that may be duplicates.

        Example:
            >>> duplicates = dedup.find_potential_duplicates()
            >>> for p1, p2 in duplicates:
            ...     print(f"Possible match: {p1.full_name} vs {p2.full_name}")
        """
        duplicates: list[tuple[Player, Player]] = []
        seen_pairs: set[tuple[UUID, UUID]] = set()

        # Query 1: Find duplicate names using database grouping
        # Uses index on (first_name, last_name) if available
        dup_names_query = (
            select(
                func.lower(Player.first_name).label("fn"),
                func.lower(Player.last_name).label("ln"),
            )
            .group_by(func.lower(Player.first_name), func.lower(Player.last_name))
            .having(func.count() > 1)
        )

        for row in self.db.execute(dup_names_query):
            # Fetch only players with this duplicate name
            players = list(
                self.db.scalars(
                    select(Player).where(
                        func.lower(Player.first_name) == row.fn,
                        func.lower(Player.last_name) == row.ln,
                    )
                ).all()
            )
            for i, p1 in enumerate(players):
                for p2 in players[i + 1 :]:
                    pair_key = (min(p1.id, p2.id), max(p1.id, p2.id))
                    if pair_key not in seen_pairs:
                        duplicates.append((p1, p2))
                        seen_pairs.add(pair_key)

        # Query 2: Find players with same last_name + birth_date
        dup_birth_query = (
            select(
                func.lower(Player.last_name).label("ln"),
                Player.birth_date.label("bd"),
            )
            .where(Player.birth_date.isnot(None))
            .group_by(func.lower(Player.last_name), Player.birth_date)
            .having(func.count() > 1)
        )

        for row in self.db.execute(dup_birth_query):
            players = list(
                self.db.scalars(
                    select(Player).where(
                        func.lower(Player.last_name) == row.ln,
                        Player.birth_date == row.bd,
                    )
                ).all()
            )
            for i, p1 in enumerate(players):
                for p2 in players[i + 1 :]:
                    pair_key = (min(p1.id, p2.id), max(p1.id, p2.id))
                    if pair_key not in seen_pairs:
                        duplicates.append((p1, p2))
                        seen_pairs.add(pair_key)

        return duplicates
