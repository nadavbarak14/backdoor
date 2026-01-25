"""
iBasketball Scraper Module

Provides the IBasketballScraper class for scraping data from iBasketball HTML pages.
Handles play-by-play data and player profiles that are not available via the REST API.

This module exports:
    - IBasketballScraper: HTML scraper for iBasketball data
    - PBPEvent: Dataclass for play-by-play event data
    - PlayerProfile: Dataclass for player profile data

Usage:
    from sqlalchemy.orm import Session
    from src.sync.ibasketball.scraper import IBasketballScraper

    db = SessionLocal()
    with IBasketballScraper(db) as scraper:
        pbp = scraper.fetch_game_pbp("team-a-vs-team-b")
        print(f"Found {len(pbp.events)} PBP events")
"""

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.models.sync_cache import SyncCache
from src.sync.ibasketball.config import IBasketballConfig
from src.sync.ibasketball.exceptions import (
    IBasketballAPIError,
    IBasketballParseError,
    IBasketballRateLimitError,
    IBasketballTimeoutError,
)
from src.sync.winner.rate_limiter import RateLimiter, calculate_backoff


@dataclass
class PBPEvent:
    """
    Play-by-play event data scraped from game page.

    Attributes:
        period: Period/quarter number.
        clock: Game clock time string.
        type: Event type (Hebrew or English).
        player: Player name if applicable.
        team_id: Team ID if applicable.
        team_name: Team name if applicable.
        success: Whether event was successful (for shots).
        description: Full event description.

    Example:
        >>> event = PBPEvent(
        ...     period=1,
        ...     clock="09:45",
        ...     type="קליעה",
        ...     player="John Smith",
        ...     team_name="Maccabi",
        ...     success=True
        ... )
    """

    period: int
    clock: str
    type: str
    player: str | None = None
    team_id: str | None = None
    team_name: str | None = None
    success: bool | None = None
    description: str | None = None


@dataclass
class GamePBP:
    """
    Full play-by-play data for a game.

    Attributes:
        event_slug: Event slug/ID.
        home_team: Home team name.
        away_team: Away team name.
        events: List of PBP events.
        raw_html: Original HTML for debugging.

    Example:
        >>> pbp = scraper.fetch_game_pbp("team-a-vs-team-b")
        >>> print(f"Found {len(pbp.events)} events")
    """

    event_slug: str
    home_team: str | None = None
    away_team: str | None = None
    events: list[PBPEvent] = field(default_factory=list)
    raw_html: str | None = field(default=None, repr=False)


@dataclass
class PlayerProfile:
    """
    Player profile data scraped from iBasketball.

    Attributes:
        player_slug: Player slug/ID from URL.
        name: Full player name.
        team_name: Current team name.
        position: Playing position.
        height_cm: Height in centimeters.
        birth_date: Date of birth if available.
        nationality: Country of origin.
        jersey_number: Current jersey number.
        raw_html: Original HTML for debugging.

    Example:
        >>> profile = scraper.fetch_player("john-smith")
        >>> print(f"{profile.name} - #{profile.jersey_number}")
    """

    player_slug: str
    name: str
    team_name: str | None = None
    position: str | None = None
    height_cm: int | None = None
    birth_date: datetime | None = None
    nationality: str | None = None
    jersey_number: str | None = None
    raw_html: str | None = field(default=None, repr=False)


class IBasketballScraper:
    """
    Scraper for iBasketball HTML pages.

    Provides methods for scraping play-by-play data and player profiles.
    All responses are cached in the database with checksum-based change detection.

    Attributes:
        db: SQLAlchemy database session.
        config: Configuration settings.
        rate_limiter: Token bucket rate limiter.
        _client: httpx HTTP client instance.

    Example:
        >>> db = SessionLocal()
        >>> with IBasketballScraper(db) as scraper:
        ...     pbp = scraper.fetch_game_pbp("team-a-vs-team-b")
        ...     print(f"Found {len(pbp.events)} events")
        ...
        ...     profile = scraper.fetch_player("john-smith")
        ...     print(f"Player: {profile.name}")
    """

    SOURCE = "ibasketball"

    def __init__(
        self,
        db: Session,
        config: IBasketballConfig | None = None,
    ) -> None:
        """
        Initialize IBasketballScraper.

        Args:
            db: SQLAlchemy database session for caching.
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> db = SessionLocal()
            >>> scraper = IBasketballScraper(db)
        """
        self.db = db
        self.config = config or IBasketballConfig()
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.scrape_requests_per_second,
            burst_size=self.config.scrape_burst_size,
        )
        self._client: httpx.Client | None = None

    def __enter__(self) -> "IBasketballScraper":
        """Context manager entry - create HTTP client."""
        self._client = httpx.Client(
            timeout=self.config.request_timeout,
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        """Get the HTTP client, creating one if needed."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.config.request_timeout,
                headers={"User-Agent": self.config.user_agent},
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def _compute_hash(self, html: str) -> str:
        """Compute SHA-256 hash of HTML content."""
        return hashlib.sha256(html.encode("utf-8")).hexdigest()

    def _get_cache(
        self,
        resource_type: str,
        resource_id: str,
    ) -> SyncCache | None:
        """Get cached entry from database."""
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
        html: str,
        http_status: int | None = None,
    ) -> tuple[SyncCache, bool]:
        """Save or update cache entry for HTML content."""
        content_hash = self._compute_hash(html)
        now = datetime.now(UTC)
        data = {"html": html}

        cache = self._get_cache(resource_type, resource_id)

        if cache:
            changed = cache.content_hash != content_hash

            if changed:
                cache.raw_data = data
                cache.content_hash = content_hash
                cache.fetched_at = now
                cache.http_status = http_status
                self.db.commit()
            else:
                cache.fetched_at = now
                self.db.commit()

            return cache, changed
        else:
            cache = SyncCache(
                source=self.SOURCE,
                resource_type=resource_type,
                resource_id=resource_id,
                raw_data=data,
                content_hash=content_hash,
                fetched_at=now,
                http_status=http_status,
            )
            self.db.add(cache)
            self.db.commit()
            self.db.refresh(cache)

            return cache, True

    def _fetch_html(
        self,
        url: str,
        resource_type: str,
        resource_id: str,  # noqa: ARG002
    ) -> str:
        """
        Fetch HTML from URL with rate limiting and retries.

        Args:
            url: URL to fetch.
            resource_type: Type of resource (for error messages).
            resource_id: Resource identifier (for error messages).

        Returns:
            str: HTML content.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballTimeoutError: On request timeout.
            IBasketballRateLimitError: On rate limit.
        """
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                self.rate_limiter.acquire()

                response = self.client.get(url)

                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", self.config.retry_base_delay
                        )
                    )
                    raise IBasketballRateLimitError(
                        f"Rate limited by server for {resource_type}",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    raise IBasketballAPIError(
                        f"HTTP {response.status_code} fetching {resource_type}",
                        status_code=response.status_code,
                        url=url,
                    )

                return response.text

            except httpx.TimeoutException as e:
                last_error = IBasketballTimeoutError(
                    f"Request timed out for {resource_type}",
                    timeout=self.config.request_timeout,
                    url=url,
                )
                if attempt < self.config.max_retries:
                    delay = calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error from e

            except IBasketballRateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = e.retry_after or calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise

            except httpx.RequestError as e:
                last_error = IBasketballAPIError(
                    f"Request failed for {resource_type}: {e}",
                    url=url,
                )
                if attempt < self.config.max_retries:
                    delay = calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error from e

        if last_error:
            raise last_error
        raise IBasketballAPIError(
            f"Failed to fetch {resource_type} after retries", url=url
        )

    def _parse_game_pbp(
        self,
        html: str,
        event_slug: str,
    ) -> GamePBP:
        """
        Parse play-by-play data from game HTML page.

        iBasketball uses SportsPress which may display PBP in various formats.
        This method attempts to extract events from tables or structured divs.

        Args:
            html: HTML content.
            event_slug: Event slug identifier.

        Returns:
            GamePBP: Parsed PBP data.

        Raises:
            IBasketballParseError: On parsing errors.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            pbp = GamePBP(
                event_slug=event_slug,
                raw_html=html,
            )

            # Try to extract team names from title or header
            title = soup.find("h1") or soup.find("title")
            if title:
                title_text = title.get_text(strip=True)
                # Common formats: "Team A vs Team B" or "Team A - Team B"
                match = re.search(r"(.+?)\s*(?:vs\.?|נגד|\-)\s*(.+)", title_text)
                if match:
                    pbp.home_team = match.group(1).strip()
                    pbp.away_team = match.group(2).strip()

            # Look for PBP table or timeline
            pbp_container = soup.find(
                class_=re.compile(r"(pbp|play-by-play|timeline|events)", re.I)
            )

            if pbp_container:
                # Try to parse rows/events
                rows = pbp_container.find_all(["tr", "div", "li"])
                current_period = 1

                for row in rows:
                    event = self._parse_pbp_row(row, current_period)
                    if event:
                        if event.period != current_period:
                            current_period = event.period
                        pbp.events.append(event)

            # Fallback: look for any table that might contain PBP
            if not pbp.events:
                for table in soup.find_all("table"):
                    for row in table.find_all("tr"):
                        event = self._parse_pbp_row(row, 1)
                        if event:
                            pbp.events.append(event)

            return pbp

        except Exception as e:
            raise IBasketballParseError(
                f"Failed to parse game PBP: {e}",
                resource_type="game_pbp",
                resource_id=event_slug,
                raw_data=html[:500] if html else None,
            ) from e

    def _parse_pbp_row(self, row, current_period: int) -> PBPEvent | None:
        """Parse a single PBP row/element."""
        try:
            # Get text content
            text = row.get_text(strip=True)
            if not text or len(text) < 3:
                return None

            # Check for period indicator
            period = current_period
            period_match = re.search(r"(?:רבע|quarter|period|Q)\s*(\d+)", text, re.I)
            if period_match:
                period = int(period_match.group(1))

            # Look for clock time (MM:SS format)
            clock_match = re.search(r"(\d{1,2}:\d{2})", text)
            clock = clock_match.group(1) if clock_match else ""

            # Skip if no clock (probably header or period row)
            if not clock and not period_match:
                return None

            # Determine event type and success
            event_type = ""
            success = None

            # Hebrew patterns
            if "קליעה" in text or "made" in text.lower():
                event_type = "קליעה"
                success = True
            elif "החטאה" in text or "missed" in text.lower():
                event_type = "החטאה"
                success = False
            elif "ריבאונד" in text or "rebound" in text.lower():
                event_type = "ריבאונד"
            elif "אסיסט" in text or "assist" in text.lower():
                event_type = "אסיסט"
            elif "חטיפה" in text or "steal" in text.lower():
                event_type = "חטיפה"
            elif "איבוד" in text or "turnover" in text.lower():
                event_type = "איבוד"
            elif "חסימה" in text or "block" in text.lower():
                event_type = "חסימה"
            elif "עבירה" in text or "foul" in text.lower():
                event_type = "עבירה"
            elif "עונשין" in text or "free throw" in text.lower():
                event_type = "עונשין"
                success = "קליעת" in text or "made" in text.lower()

            if not event_type:
                return None

            # Try to extract player name
            player_name = None
            # Look for links that might contain player name
            player_link = row.find("a", href=re.compile(r"/player/"))
            if player_link:
                player_name = player_link.get_text(strip=True)

            # Try to extract team
            team_name = None
            team_link = row.find("a", href=re.compile(r"/team/"))
            if team_link:
                team_name = team_link.get_text(strip=True)

            return PBPEvent(
                period=period,
                clock=clock,
                type=event_type,
                player=player_name,
                team_name=team_name,
                success=success,
                description=text,
            )

        except Exception:
            return None

    def _parse_player_profile(
        self,
        html: str,
        player_slug: str,
    ) -> PlayerProfile:
        """
        Parse player profile from HTML.

        Args:
            html: HTML content.
            player_slug: Player slug identifier.

        Returns:
            PlayerProfile: Parsed player data.

        Raises:
            IBasketballParseError: On parsing errors.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract player name
            name = ""
            name_element = soup.find("h1") or soup.find(class_="player-name")
            if name_element:
                name = name_element.get_text(strip=True)
                # Clean up title if it contains site name
                if " - " in name:
                    name = name.split(" - ")[0].strip()
                if " | " in name:
                    name = name.split(" | ")[0].strip()

            profile = PlayerProfile(
                player_slug=player_slug,
                name=name or f"Player {player_slug}",
                raw_html=html,
            )

            # Look for player details in various formats
            # SportsPress typically uses sp-player-details or similar classes
            details = soup.find(
                class_=re.compile(r"(player-details|sp-player|player-info)", re.I)
            )
            if not details:
                details = soup  # Search whole page

            # Extract from table rows or definition lists
            for item in details.find_all(["tr", "dt", "div"]):
                label = item.find(["th", "dt", "strong", "span"])
                value = item.find(["td", "dd"])

                if not (label and value):
                    continue

                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)

                # Match different fields
                if any(x in label_text for x in ["team", "קבוצה", "club"]):
                    profile.team_name = value_text
                elif any(x in label_text for x in ["number", "מספר", "jersey"]):
                    profile.jersey_number = value_text
                elif any(x in label_text for x in ["position", "עמדה", "תפקיד"]):
                    profile.position = value_text
                elif any(x in label_text for x in ["height", "גובה"]):
                    try:
                        height_str = "".join(c for c in value_text if c.isdigit())
                        if height_str:
                            profile.height_cm = int(height_str)
                    except ValueError:
                        pass
                elif any(x in label_text for x in ["nationality", "לאום", "country"]):
                    profile.nationality = value_text
                elif any(x in label_text for x in ["birth", "תאריך", "dob"]):
                    try:
                        # Try various date formats
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]:
                            try:
                                profile.birth_date = datetime.strptime(value_text, fmt)
                                break
                            except ValueError:
                                continue
                    except ValueError:
                        pass

            return profile

        except Exception as e:
            raise IBasketballParseError(
                f"Failed to parse player profile: {e}",
                resource_type="player_page",
                resource_id=player_slug,
                raw_data=html[:500] if html else None,
            ) from e

    def fetch_game_pbp(
        self,
        event_slug: str,
        force: bool = False,
    ) -> GamePBP:
        """
        Fetch and parse play-by-play data for a game.

        Args:
            event_slug: Event slug from the API.
            force: If True, bypass cache and fetch from source.

        Returns:
            GamePBP: Parsed PBP data.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On parsing errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> pbp = scraper.fetch_game_pbp("team-a-vs-team-b")
            >>> for event in pbp.events[:5]:
            ...     print(f"{event.clock} - {event.type}")
        """
        resource_type = "game_pbp"
        resource_id = event_slug

        # Check cache unless force refresh
        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")
                return self._parse_game_pbp(html, event_slug)

        # Fetch from source
        url = self.config.get_game_page_url(event_slug)
        html = self._fetch_html(url, resource_type, resource_id)

        # Save to cache
        self._save_cache(resource_type, resource_id, html, http_status=200)

        return self._parse_game_pbp(html, event_slug)

    def fetch_player(
        self,
        player_slug: str,
        force: bool = False,
    ) -> PlayerProfile:
        """
        Fetch and parse player profile.

        Args:
            player_slug: Player slug from the API.
            force: If True, bypass cache and fetch from source.

        Returns:
            PlayerProfile: Parsed player data.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On parsing errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> profile = scraper.fetch_player("john-smith")
            >>> print(f"{profile.name} - {profile.position}")
        """
        resource_type = "player_page"
        resource_id = player_slug

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")
                return self._parse_player_profile(html, player_slug)

        url = self.config.get_player_page_url(player_slug)
        html = self._fetch_html(url, resource_type, resource_id)

        self._save_cache(resource_type, resource_id, html, http_status=200)

        return self._parse_player_profile(html, player_slug)
