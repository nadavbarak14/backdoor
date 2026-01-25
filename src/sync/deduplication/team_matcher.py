"""
Team Matcher Module

Provides functionality for matching and deduplicating teams across different
data sources (Winner League, Euroleague). Teams are matched by their external
IDs or by normalized name comparison.

When a team is found in multiple sources, their external_ids are merged into
a single team record. This allows tracking the same team across different
data providers.

Additionally supports competition-specific TeamSeason records, where each team's
participation in a season stores its own external_id. This allows the same team
(e.g., Maccabi Tel Aviv) to have different external_ids in different competitions
while remaining a single deduplicated entity.

Usage:
    from src.sync.deduplication.team_matcher import TeamMatcher
    from src.sync.types import RawTeam

    matcher = TeamMatcher(db_session)

    # Find or create a team from external data
    team = matcher.find_or_create_team(
        source="winner",
        external_id="team-123",
        team_data=RawTeam(external_id="team-123", name="Maccabi Tel Aviv")
    )

    # Find or create team with competition-specific TeamSeason
    team, team_season = matcher.find_or_create_team_season(
        source="winner",
        external_id="w-123",
        team_data=RawTeam(external_id="w-123", name="Maccabi Tel Aviv"),
        season_id=winner_season.id
    )

    # Merge an external ID into an existing team
    matcher.merge_external_id(team, "euroleague", "MAT")
"""

from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from src.models.team import Team, TeamSeason
from src.sync.deduplication.normalizer import normalize_name, team_names_match
from src.sync.types import RawTeam


class TeamMatcher:
    """
    Service for matching and deduplicating teams across data sources.

    Provides methods to find existing teams by external ID or name,
    create new teams when no match is found, and merge external IDs
    when teams are matched across sources.

    Attributes:
        db: SQLAlchemy Session for database operations.

    Example:
        >>> matcher = TeamMatcher(db_session)
        >>> team = matcher.find_or_create_team(
        ...     source="winner",
        ...     external_id="123",
        ...     team_data=RawTeam(
        ...         external_id="123",
        ...         name="Maccabi Tel Aviv",
        ...         short_name="MTA"
        ...     )
        ... )
        >>> print(team.external_ids)
        {'winner': '123'}
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the team matcher.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> matcher = TeamMatcher(db_session)
        """
        self.db = db

    def find_or_create_team(
        self,
        source: str,
        external_id: str,
        team_data: RawTeam,
    ) -> Team:
        """
        Find an existing team or create a new one from external data.

        This method follows a three-step matching process:
        1. Check if a team exists with this external_id for this source
        2. If not, try to match by normalized team name
        3. If a match is found, merge the external_id; otherwise create new

        Args:
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID from the data source.
            team_data: Raw team data containing name and other attributes.

        Returns:
            The matched or newly created Team entity.

        Example:
            >>> team = matcher.find_or_create_team(
            ...     source="winner",
            ...     external_id="team-123",
            ...     team_data=RawTeam(
            ...         external_id="team-123",
            ...         name="Maccabi Tel Aviv",
            ...         short_name="MTA"
            ...     )
            ... )
        """
        # Step 1: Check by external_id for this source
        existing = self.get_by_external_id(source, external_id)
        if existing:
            return existing

        # Step 2: Try to match by name
        city = self._extract_city_from_name(team_data.name)
        matched = self.match_team_across_sources(team_data.name, city)

        if matched:
            # Step 3a: Merge external_id into existing team
            return self.merge_external_id(matched, source, external_id)

        # Step 3b: Create new team
        return self._create_team(source, external_id, team_data)

    def find_or_create_team_season(
        self,
        source: str,
        external_id: str,
        team_data: RawTeam,
        season_id: UUID,
    ) -> tuple[Team, TeamSeason]:
        """
        Find or create both Team and TeamSeason records.

        Creates a deduplicated Team record (or finds an existing one by external_id
        or name match), then creates or finds a TeamSeason record for the specific
        season with the competition-specific external_id.

        This supports scenarios where the same team participates in multiple
        competitions (e.g., Maccabi Tel Aviv in Winner League AND Euroleague),
        each with its own TeamSeason record containing the competition-specific
        external_id.

        Args:
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID from the data source.
            team_data: Raw team data containing name and other attributes.
            season_id: The UUID of the season this team is participating in.

        Returns:
            Tuple of (Team, TeamSeason) where:
            - Team is the deduplicated team entity
            - TeamSeason is the competition-specific season record

        Example:
            >>> team, team_season = matcher.find_or_create_team_season(
            ...     source="winner",
            ...     external_id="w-123",
            ...     team_data=RawTeam(
            ...         external_id="w-123",
            ...         name="Maccabi Tel Aviv",
            ...         short_name="MTA"
            ...     ),
            ...     season_id=winner_season.id
            ... )
            >>> print(team_season.external_id)
            'w-123'
        """
        # Step 1: Find or create the deduplicated Team
        team = self.find_or_create_team(source, external_id, team_data)

        # Step 2: Find or create TeamSeason with external_id
        team_season = self._find_or_create_team_season(
            team_id=team.id,
            season_id=season_id,
            external_id=external_id,
        )

        return team, team_season

    def get_team_season_by_external_id(
        self,
        season_id: UUID,
        external_id: str,
    ) -> TeamSeason | None:
        """
        Find a TeamSeason by its external_id within a specific season.

        Useful for looking up a team's season record when you only have
        the competition-specific external_id.

        Args:
            season_id: The UUID of the season to search within.
            external_id: The external ID to search for.

        Returns:
            The TeamSeason if found, None otherwise.

        Example:
            >>> team_season = matcher.get_team_season_by_external_id(
            ...     season_id=winner_season.id,
            ...     external_id="w-123"
            ... )
            >>> if team_season:
            ...     print(team_season.team.name)
        """
        stmt = select(TeamSeason).where(
            TeamSeason.season_id == season_id,
            TeamSeason.external_id == external_id,
        )
        return self.db.scalars(stmt).first()

    def _find_or_create_team_season(
        self,
        team_id: UUID,
        season_id: UUID,
        external_id: str,
    ) -> TeamSeason:
        """
        Find an existing TeamSeason or create a new one.

        If a TeamSeason already exists for this team-season combination,
        updates the external_id if it was not set. Otherwise, creates a new
        TeamSeason record.

        Args:
            team_id: The UUID of the team.
            season_id: The UUID of the season.
            external_id: The competition-specific external ID.

        Returns:
            The found or created TeamSeason entity.
        """
        # Try to find existing TeamSeason
        stmt = select(TeamSeason).where(
            TeamSeason.team_id == team_id,
            TeamSeason.season_id == season_id,
        )
        team_season = self.db.scalars(stmt).first()

        if team_season:
            # Update external_id if not set
            if team_season.external_id is None:
                team_season.external_id = external_id
                self.db.commit()
                self.db.refresh(team_season)
            return team_season

        # Create new TeamSeason
        team_season = TeamSeason(
            team_id=team_id,
            season_id=season_id,
            external_id=external_id,
        )
        self.db.add(team_season)
        self.db.commit()
        self.db.refresh(team_season)
        return team_season

    def get_by_external_id(self, source: str, external_id: str) -> Team | None:
        """
        Find a team by its external ID for a specific source.

        Uses JSON field query to match the external_id stored in the
        team's external_ids column.

        Args:
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID from the data source.

        Returns:
            The Team if found, None otherwise.

        Example:
            >>> team = matcher.get_by_external_id("winner", "123")
            >>> if team:
            ...     print(team.name)
        """
        stmt = select(Team).where(
            cast(func.json_extract(Team.external_ids, f"$.{source}"), String)
            == external_id
        )
        return self.db.scalars(stmt).first()

    def match_team_across_sources(
        self,
        team_name: str,
        city: str | None = None,
    ) -> Team | None:
        """
        Find a team by normalized name match.

        Searches for teams where the normalized name matches. If a city
        is provided, it can help distinguish teams with similar names.

        Args:
            team_name: The team name to search for.
            city: Optional city name for additional matching criteria.

        Returns:
            The matched Team if found, None otherwise.

        Example:
            >>> team = matcher.match_team_across_sources(
            ...     "Maccabi Tel Aviv",
            ...     city="Tel Aviv"
            ... )
        """
        # Get all teams and compare using fuzzy team name matching
        # This is a simple approach; for large datasets, consider
        # storing normalized names as a column
        stmt = select(Team)
        teams = self.db.scalars(stmt).all()

        for team in teams:
            # Use fuzzy team name matching (handles sponsor variations)
            if team_names_match(team.name, team_name):
                return team

            # Also check if city matches for additional confidence
            if (
                city
                and normalize_name(team.city) == normalize_name(city)
                and team_names_match(team.name, team_name)
            ):
                return team

        return None

    def merge_external_id(self, team: Team, source: str, external_id: str) -> Team:
        """
        Add an external ID from a source to an existing team.

        Creates a new dict to ensure SQLAlchemy detects the change.
        If the source already has an external_id, it will be overwritten.

        Args:
            team: The Team entity to update.
            source: The data source name (e.g., "winner", "euroleague").
            external_id: The external ID to add.

        Returns:
            The updated Team entity.

        Example:
            >>> team = matcher.merge_external_id(team, "euroleague", "MAT")
            >>> print(team.external_ids)
            {'winner': '123', 'euroleague': 'MAT'}
        """
        # Create new dict to trigger SQLAlchemy change detection
        new_external_ids = dict(team.external_ids)
        new_external_ids[source] = external_id
        team.external_ids = new_external_ids

        self.db.commit()
        self.db.refresh(team)
        return team

    def _create_team(
        self,
        source: str,
        external_id: str,
        team_data: RawTeam,
    ) -> Team:
        """
        Create a new team from external data.

        Args:
            source: The data source name.
            external_id: The external ID from the data source.
            team_data: Raw team data.

        Returns:
            The newly created Team entity.
        """
        city = self._extract_city_from_name(team_data.name)

        team = Team(
            name=team_data.name,
            short_name=team_data.short_name
            or self._generate_short_name(team_data.name),
            city=city,
            country=self._infer_country_from_source(source),
            external_ids={source: external_id},
        )

        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        return team

    def _extract_city_from_name(self, team_name: str) -> str:
        """
        Extract city name from team name.

        Common patterns:
        - "Maccabi Tel Aviv" -> "Tel Aviv"
        - "Hapoel Jerusalem" -> "Jerusalem"

        Args:
            team_name: Full team name.

        Returns:
            Extracted city name, or the full name if no pattern matches.
        """
        parts = team_name.split()

        # Common Israeli team prefixes to remove
        prefixes = {"maccabi", "hapoel", "bnei", "ironi", "elitzur", "bc"}

        # If first word is a known prefix, use the rest as city
        if len(parts) > 1 and parts[0].lower() in prefixes:
            return " ".join(parts[1:])

        # Default: use the full name as city
        return team_name

    def _generate_short_name(self, team_name: str) -> str:
        """
        Generate a short name from the full team name.

        Takes the first 3 characters of each significant word
        and combines them (max 5 characters).

        Args:
            team_name: Full team name.

        Returns:
            Generated short name.
        """
        parts = team_name.split()
        if not parts:
            return "UNK"

        # If single word, take first 3 chars uppercase
        if len(parts) == 1:
            return parts[0][:3].upper()

        # Take first letter of each word
        initials = "".join(word[0] for word in parts if word)
        return initials[:5].upper()

    def _infer_country_from_source(self, source: str) -> str:
        """
        Infer country from the data source.

        Args:
            source: The data source name.

        Returns:
            Country name based on source.
        """
        source_countries = {
            "winner": "Israel",
            "euroleague": "Europe",
            "nba": "USA",
        }
        return source_countries.get(source, "Unknown")
