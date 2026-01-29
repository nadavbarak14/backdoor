"""
Winner League Scraper Module

Provides the WinnerScraper class for scraping data from Winner League HTML pages.
Handles player profiles, team rosters, and historical results with automatic
caching and rate limiting.

This module exports:
    - WinnerScraper: HTML scraper for Winner League data
    - PlayerProfile: Dataclass for player profile data
    - TeamRoster: Dataclass for team roster data
    - HistoricalResults: Dataclass for historical game results

Usage:
    from sqlalchemy.orm import Session
    from src.sync.winner.scraper import WinnerScraper

    db = SessionLocal()
    with WinnerScraper(db) as scraper:
        profile = scraper.fetch_player("12345")
        print(f"Player: {profile.name}")
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.models.sync_cache import SyncCache
from src.sync.winner.config import WinnerConfig
from src.sync.winner.exceptions import (
    WinnerAPIError,
    WinnerParseError,
    WinnerRateLimitError,
    WinnerTimeoutError,
)
from src.sync.winner.rate_limiter import RateLimiter, calculate_backoff


@dataclass
class PlayerProfile:
    """
    Player profile data scraped from basket.co.il.

    Contains biographical and career information for a player.

    Attributes:
        player_id: Player identifier from source.
        name: Full player name.
        name_hebrew: Hebrew name if available.
        team_id: Current team identifier.
        team_name: Current team name.
        jersey_number: Current jersey number.
        position: Playing position.
        height_cm: Height in centimeters.
        birth_date: Date of birth if available.
        nationality: Country of origin.
        raw_html: Original HTML for debugging.

    Example:
        >>> profile = scraper.fetch_player("12345")
        >>> print(f"{profile.name} - #{profile.jersey_number}")
    """

    player_id: str
    name: str
    name_hebrew: str | None = None
    team_id: str | None = None
    team_name: str | None = None
    jersey_number: str | None = None
    position: str | None = None
    height_cm: int | None = None
    birth_date: datetime | None = None
    nationality: str | None = None
    raw_html: str | None = field(default=None, repr=False)


@dataclass
class RosterPlayer:
    """
    Player entry in a team roster.

    Attributes:
        player_id: Player identifier.
        name: Player name.
        jersey_number: Jersey number.
        position: Playing position.

    Example:
        >>> for player in roster.players:
        ...     print(f"#{player.jersey_number}: {player.name}")
    """

    player_id: str
    name: str
    jersey_number: str | None = None
    position: str | None = None


@dataclass
class TeamRoster:
    """
    Team roster data scraped from basket.co.il.

    Contains the list of players on a team's roster.

    Attributes:
        team_id: Team identifier.
        team_name: Team name.
        players: List of roster players.
        raw_html: Original HTML for debugging.

    Example:
        >>> roster = scraper.fetch_team_roster("100")
        >>> print(f"{roster.team_name}: {len(roster.players)} players")
    """

    team_id: str
    team_name: str | None = None
    players: list[RosterPlayer] = field(default_factory=list)
    raw_html: str | None = field(default=None, repr=False)


@dataclass
class GameResult:
    """
    Historical game result.

    Attributes:
        game_id: Game identifier if available.
        date: Game date.
        home_team: Home team name.
        away_team: Away team name.
        home_score: Home team score.
        away_score: Away team score.

    Example:
        >>> for game in results.games:
        ...     print(f"{game.home_team} {game.home_score} - {game.away_score} {game.away_team}")
    """

    game_id: str | None
    date: datetime | None
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None


@dataclass
class HistoricalResults:
    """
    Historical game results for a season.

    Attributes:
        year: Season year.
        games: List of game results.
        raw_html: Original HTML for debugging.

    Example:
        >>> results = scraper.fetch_historical_results(2024)
        >>> print(f"{results.year}: {len(results.games)} games")
    """

    year: int
    games: list[GameResult] = field(default_factory=list)
    raw_html: str | None = field(default=None, repr=False)


class WinnerScraper:
    """
    Scraper for Winner League HTML pages.

    Provides methods for scraping player profiles, team rosters, and
    historical results. All responses are cached in the database with
    checksum-based change detection.

    Attributes:
        db: SQLAlchemy database session.
        config: Configuration settings.
        rate_limiter: Token bucket rate limiter.
        _client: httpx HTTP client instance.

    Example:
        >>> db = SessionLocal()
        >>> with WinnerScraper(db) as scraper:
        ...     profile = scraper.fetch_player("12345")
        ...     print(f"Player: {profile.name}")
        ...
        ...     roster = scraper.fetch_team_roster("100")
        ...     print(f"Team: {roster.team_name}")
    """

    SOURCE = "winner"

    def __init__(
        self,
        db: Session,
        config: WinnerConfig | None = None,
    ) -> None:
        """
        Initialize WinnerScraper.

        Args:
            db: SQLAlchemy database session for caching.
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> db = SessionLocal()
            >>> scraper = WinnerScraper(db)
        """
        self.db = db
        self.config = config or WinnerConfig()
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.scrape_requests_per_second,
            burst_size=self.config.scrape_burst_size,
        )
        self._client: httpx.Client | None = None

    def __enter__(self) -> "WinnerScraper":
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
        _resource_id: str,
    ) -> str:
        """
        Fetch HTML from URL with rate limiting and retries.

        Args:
            url: URL to fetch.
            resource_type: Type of resource (for error messages).
            _resource_id: Resource identifier (unused, kept for API consistency).

        Returns:
            str: HTML content.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerTimeoutError: On request timeout.
            WinnerRateLimitError: On rate limit.
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
                    raise WinnerRateLimitError(
                        f"Rate limited by server for {resource_type}",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    raise WinnerAPIError(
                        f"HTTP {response.status_code} fetching {resource_type}",
                        status_code=response.status_code,
                        url=url,
                    )

                # Detect encoding (basket.co.il uses windows-1255 for Hebrew)
                content = response.text
                return content

            except httpx.TimeoutException as e:
                last_error = WinnerTimeoutError(
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

            except WinnerRateLimitError as e:
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
                last_error = WinnerAPIError(
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
        raise WinnerAPIError(f"Failed to fetch {resource_type} after retries", url=url)

    def _parse_player_profile(
        self,
        html: str,
        player_id: str,
    ) -> PlayerProfile:
        """
        Parse player profile from HTML.

        Args:
            html: HTML content.
            player_id: Player identifier.

        Returns:
            PlayerProfile: Parsed player data.

        Raises:
            WinnerParseError: On parsing errors.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract player name from p_name class (most reliable)
            name = ""
            p_name_el = soup.find(class_="p_name")
            if p_name_el:
                name = p_name_el.get_text(strip=True)
                # Fix missing space (e.g., "JaylenHoard" -> "Jaylen Hoard")
                import re as _re

                name = _re.sub(r"([a-z])([A-Z])", r"\1 \2", name)

            # Fallback: extract from title (last pipe-separated segment)
            if not name:
                title_el = soup.find("title")
                if title_el:
                    title_text = title_el.get_text(strip=True)
                    parts = title_text.split("|")
                    if parts:
                        name = parts[-1].strip()

            # Try to find player info table/div
            profile = PlayerProfile(
                player_id=player_id,
                name=name or f"Player {player_id}",
                raw_html=html,
            )

            # Parse player info from <div class="p_info"> with span labels
            p_info_div = soup.find("div", class_="p_info")
            if p_info_div:
                for span in p_info_div.find_all("span", class_="p_info_title"):
                    label = span.get_text(strip=True).lower().rstrip(":")
                    # Get the text node immediately after the span (before <br/>)
                    value = ""
                    sibling = span.next_sibling
                    while sibling:
                        if getattr(sibling, "name", None) == "br":
                            break
                        if isinstance(sibling, str):
                            value += sibling.strip()
                        elif getattr(sibling, "name", None) == "a":
                            value += sibling.get_text(strip=True)
                        sibling = sibling.next_sibling
                    value = value.strip()

                    if not value:
                        continue

                    if "team" in label or "קבוצה" in label:
                        profile.team_name = value
                    elif "number" in label or "מספר" in label:
                        profile.jersey_number = value
                    elif "position" in label or "עמדה" in label:
                        profile.position = value
                    elif "height" in label or "גובה" in label:
                        try:
                            # Height may be "2.03" (meters) or "203" (cm)
                            if "." in value:
                                profile.height_cm = int(float(value) * 100)
                            else:
                                height_str = "".join(c for c in value if c.isdigit())
                                if height_str:
                                    profile.height_cm = int(height_str)
                        except ValueError:
                            pass
                    elif "nationality" in label or "לאום" in label:
                        profile.nationality = value
                    elif "birth" in label or "תאריך" in label or "dob" in label:
                        try:
                            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]:
                                try:
                                    profile.birth_date = datetime.strptime(value, fmt)
                                    break
                                except ValueError:
                                    continue
                        except ValueError:
                            pass

            # Fallback: look for info in table rows
            if not profile.birth_date or not profile.position:
                info_tables = soup.find_all("table")
                for table in info_tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)

                            if "team" in label and not profile.team_name:
                                profile.team_name = value
                            elif "number" in label and not profile.jersey_number:
                                profile.jersey_number = value
                            elif "position" in label and not profile.position:
                                profile.position = value
                            elif "height" in label and not profile.height_cm:
                                try:
                                    height_str = "".join(
                                        c for c in value if c.isdigit()
                                    )
                                    if height_str:
                                        profile.height_cm = int(height_str)
                                except ValueError:
                                    pass
                            elif "nationality" in label and not profile.nationality:
                                profile.nationality = value
                            elif (
                                "birth" in label or "dob" in label
                            ) and not profile.birth_date:
                                try:
                                    for fmt in [
                                        "%Y-%m-%d",
                                        "%d/%m/%Y",
                                        "%d.%m.%Y",
                                    ]:
                                        try:
                                            profile.birth_date = datetime.strptime(
                                                value, fmt
                                            )
                                            break
                                        except ValueError:
                                            continue
                                except ValueError:
                                    pass

            return profile

        except Exception as e:
            raise WinnerParseError(
                f"Failed to parse player profile: {e}",
                resource_type="player_page",
                resource_id=player_id,
                raw_data=html[:500] if html else None,
            ) from e

    def _parse_team_roster(
        self,
        html: str,
        team_id: str,
    ) -> TeamRoster:
        """
        Parse team roster from HTML.

        Handles two HTML structures:
        1. Card-based layout (real basket.co.il): div.box_role with role_name, role_num
        2. Table-based layout (legacy/test fixtures): table rows with player links

        Args:
            html: HTML content.
            team_id: Team identifier.

        Returns:
            TeamRoster: Parsed roster data.

        Raises:
            WinnerParseError: On parsing errors.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract team name
            team_name = None
            name_element = soup.find("h1") or soup.find("title")
            if name_element:
                team_name = name_element.get_text(strip=True)
                if " - " in team_name:
                    team_name = team_name.split(" - ")[0].strip()

            roster = TeamRoster(
                team_id=team_id,
                team_name=team_name,
                raw_html=html,
            )

            # Try card-based layout first (real basket.co.il structure)
            player_boxes = soup.find_all("div", class_="box_role")
            for box in player_boxes:
                link = box.find("a", href=lambda x: x and "PlayerId" in str(x))
                if not link:
                    continue  # Skip non-player boxes (coaches, etc.)

                href = link.get("href", "")
                player_id = href.split("PlayerId=")[-1].split("&")[0]

                # Extract name from role_name div
                name_div = box.find("div", class_="role_name")
                if name_div:
                    # Name has <br> between first/last - use separator to join
                    player_name = " ".join(name_div.get_text(separator=" ").split())
                else:
                    player_name = f"Player {player_id}"

                # Extract jersey number from role_num div
                num_div = box.find("div", class_="role_num")
                jersey_number = num_div.get_text(strip=True) if num_div else None

                # Extract position from role_desc div
                position = None
                desc_div = box.find("div", class_="role_desc")
                if desc_div:
                    strong = desc_div.find("strong")
                    if strong:
                        pos_height = strong.get_text(strip=True)
                        if "|" in pos_height:
                            position = pos_height.split("|")[0].strip()

                roster.players.append(
                    RosterPlayer(
                        player_id=player_id,
                        name=player_name,
                        jersey_number=jersey_number,
                        position=position,
                    )
                )

            # If no players found with card layout, try table-based layout
            if not roster.players:
                player_links = soup.find_all(
                    "a", href=lambda x: x and "PlayerId" in str(x)
                )
                for link in player_links:
                    href = link.get("href", "")
                    player_name = link.get_text(strip=True)

                    player_id_match = None
                    if "PlayerId=" in href:
                        player_id_match = href.split("PlayerId=")[-1].split("&")[0]

                    if player_id_match and player_name:
                        parent_row = link.find_parent("tr")
                        jersey_number = None
                        position = None

                        if parent_row:
                            cells = parent_row.find_all("td")
                            for cell in cells:
                                text = cell.get_text(strip=True)
                                if text.isdigit() and not jersey_number:
                                    jersey_number = text
                                elif text in ["G", "F", "C", "PG", "SG", "SF", "PF"]:
                                    position = text

                        roster.players.append(
                            RosterPlayer(
                                player_id=player_id_match,
                                name=player_name,
                                jersey_number=jersey_number,
                                position=position,
                            )
                        )

            return roster

        except Exception as e:
            raise WinnerParseError(
                f"Failed to parse team roster: {e}",
                resource_type="team_page",
                resource_id=team_id,
                raw_data=html[:500] if html else None,
            ) from e

    def _parse_historical_results(
        self,
        html: str,
        year: int,
    ) -> HistoricalResults:
        """
        Parse historical results from HTML.

        Args:
            html: HTML content.
            year: Season year.

        Returns:
            HistoricalResults: Parsed results data.

        Raises:
            WinnerParseError: On parsing errors.
        """
        try:
            soup = BeautifulSoup(html, "html.parser")

            results = HistoricalResults(
                year=year,
                raw_html=html,
            )

            # Look for game result rows in tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        # Try to extract game data
                        # Format varies but typically: date, home, score, away
                        texts = [c.get_text(strip=True) for c in cells]

                        # Look for score pattern (e.g., "85 - 78" or "85-78")
                        score_idx = None
                        for i, text in enumerate(texts):
                            if "-" in text and any(c.isdigit() for c in text):
                                score_idx = i
                                break

                        if score_idx is not None and score_idx >= 1:
                            try:
                                score_parts = (
                                    texts[score_idx].replace(" ", "").split("-")
                                )
                                if len(score_parts) == 2:
                                    home_score = int(score_parts[0])
                                    away_score = int(score_parts[1])

                                    home_team = (
                                        texts[score_idx - 1]
                                        if score_idx > 0
                                        else "Unknown"
                                    )
                                    away_team = (
                                        texts[score_idx + 1]
                                        if score_idx + 1 < len(texts)
                                        else "Unknown"
                                    )

                                    # Look for game link for ID
                                    game_id = None
                                    game_link = row.find(
                                        "a", href=lambda x: x and "GameId" in str(x)
                                    )
                                    if game_link:
                                        href = game_link.get("href", "")
                                        if "GameId=" in href:
                                            game_id = href.split("GameId=")[-1].split(
                                                "&"
                                            )[0]

                                    results.games.append(
                                        GameResult(
                                            game_id=game_id,
                                            date=None,  # Date parsing can be added
                                            home_team=home_team,
                                            away_team=away_team,
                                            home_score=home_score,
                                            away_score=away_score,
                                        )
                                    )
                            except (ValueError, IndexError):
                                continue

            return results

        except Exception as e:
            raise WinnerParseError(
                f"Failed to parse historical results: {e}",
                resource_type="results_page",
                resource_id=str(year),
                raw_data=html[:500] if html else None,
            ) from e

    def fetch_player(
        self,
        player_id: str,
        force: bool = False,
    ) -> PlayerProfile:
        """
        Fetch and parse player profile.

        Args:
            player_id: The player identifier.
            force: If True, bypass cache and fetch from source.

        Returns:
            PlayerProfile: Parsed player data.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On parsing errors.
            WinnerTimeoutError: On request timeout.

        Example:
            >>> profile = scraper.fetch_player("12345")
            >>> print(f"{profile.name} - #{profile.jersey_number}")
        """
        resource_type = "player_page"
        resource_id = player_id

        # Check cache unless force refresh
        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")
                return self._parse_player_profile(html, player_id)

        # Fetch from source
        url = self.config.get_player_url(player_id)
        html = self._fetch_html(url, resource_type, resource_id)

        # Save to cache
        self._save_cache(resource_type, resource_id, html, http_status=200)

        return self._parse_player_profile(html, player_id)

    def fetch_team_roster(
        self,
        team_id: str,
        force: bool = False,
    ) -> TeamRoster:
        """
        Fetch and parse team roster.

        Args:
            team_id: The team identifier.
            force: If True, bypass cache and fetch from source.

        Returns:
            TeamRoster: Parsed roster data.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On parsing errors.
            WinnerTimeoutError: On request timeout.

        Example:
            >>> roster = scraper.fetch_team_roster("100")
            >>> for player in roster.players:
            ...     print(f"#{player.jersey_number}: {player.name}")
        """
        resource_type = "team_page"
        resource_id = team_id

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")
                return self._parse_team_roster(html, team_id)

        url = self.config.get_team_url(team_id)
        html = self._fetch_html(url, resource_type, resource_id)

        self._save_cache(resource_type, resource_id, html, http_status=200)

        return self._parse_team_roster(html, team_id)

    def fetch_historical_results(
        self,
        year: int,
        force: bool = False,
    ) -> HistoricalResults:
        """
        Fetch and parse historical game results.

        Args:
            year: The season year.
            force: If True, bypass cache and fetch from source.

        Returns:
            HistoricalResults: Parsed results data.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On parsing errors.
            WinnerTimeoutError: On request timeout.

        Example:
            >>> results = scraper.fetch_historical_results(2024)
            >>> print(f"Found {len(results.games)} games in {results.year}")
        """
        resource_type = "results_page"
        resource_id = str(year)

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")
                return self._parse_historical_results(html, year)

        url = self.config.get_results_url(year)
        html = self._fetch_html(url, resource_type, resource_id)

        self._save_cache(resource_type, resource_id, html, http_status=200)

        return self._parse_historical_results(html, year)

    def fetch_segevstats_game_id(
        self,
        basket_game_id: str,
        force: bool = False,
    ) -> str | None:
        """
        Fetch the segevstats game ID for a basket.co.il game ID.

        The game-zone.asp page contains a link to segevstats with the
        correct game_id that can be used for boxscore and PBP fetching.

        Args:
            basket_game_id: The basket.co.il game ID (e.g., "24904").
            force: If True, bypass cache and fetch from source.

        Returns:
            The segevstats game ID (e.g., "56135"), or None if not found.

        Example:
            >>> segev_id = scraper.fetch_segevstats_game_id("24904")
            >>> print(f"Segevstats ID: {segev_id}")  # "56135"
        """
        resource_type = "game_zone_page"
        resource_id = basket_game_id

        # Check cache
        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")
                return self._extract_segevstats_id(html)

        # Fetch game-zone page
        url = f"https://basket.co.il/game-zone.asp?GameId={basket_game_id}"
        try:
            html = self._fetch_html(url, resource_type, resource_id)
            self._save_cache(resource_type, resource_id, html, http_status=200)
            return self._extract_segevstats_id(html)
        except Exception:
            return None

    def _extract_segevstats_id(self, html: str) -> str | None:
        """Extract segevstats game_id from HTML content."""
        import re

        # Look for game_id parameter in segevstats URLs
        match = re.search(r"game_id=(\d+)", html)
        if match:
            return match.group(1)
        return None
