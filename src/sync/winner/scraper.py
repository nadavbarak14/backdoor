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
        height_cm: Height in centimeters.
        birth_date: Date of birth.

    Example:
        >>> for player in roster.players:
        ...     print(f"#{player.jersey_number}: {player.name}")
    """

    player_id: str
    name: str
    jersey_number: str | None = None
    position: str | None = None
    height_cm: int | None = None
    birth_date: datetime | None = None


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


@dataclass
class BoxscorePlayerStats:
    """
    Player stats from basket.co.il game-zone boxscore.

    Contains player stats with the correct basket.co.il player ID.

    Attributes:
        player_id: basket.co.il player ID (e.g., "21828").
        player_name: Player name.
        jersey_number: Jersey number.
        team_id: Team ID (home or away from game).
        is_home: True if player is on home team.
        minutes: Minutes played string (e.g., "20:30").
        points: Points scored.
        two_pt_made: Two-pointers made.
        two_pt_attempted: Two-pointers attempted.
        three_pt_made: Three-pointers made.
        three_pt_attempted: Three-pointers attempted.
        ft_made: Free throws made.
        ft_attempted: Free throws attempted.
        offensive_rebounds: Offensive rebounds.
        defensive_rebounds: Defensive rebounds.
        total_rebounds: Total rebounds.
        assists: Assists.
        steals: Steals.
        blocks: Blocks.
        turnovers: Turnovers.
        fouls: Personal fouls.
        plus_minus: Plus/minus (if available).

    Example:
        >>> for player in boxscore.home_players:
        ...     print(f"#{player.jersey_number} {player.player_name}: {player.points} pts")
    """

    player_id: str
    player_name: str
    jersey_number: int | None = None
    team_id: str | None = None
    is_home: bool = True
    minutes: str | None = None
    points: int = 0
    two_pt_made: int = 0
    two_pt_attempted: int = 0
    three_pt_made: int = 0
    three_pt_attempted: int = 0
    ft_made: int = 0
    ft_attempted: int = 0
    offensive_rebounds: int = 0
    defensive_rebounds: int = 0
    total_rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    fouls: int = 0
    plus_minus: int | None = None


@dataclass
class GameZoneBoxscore:
    """
    Boxscore data scraped from basket.co.il game-zone.asp.

    Contains player stats with correct basket.co.il player IDs.

    Attributes:
        game_id: basket.co.il game ID.
        home_team_id: Home team ID.
        away_team_id: Away team ID.
        home_team_name: Home team name.
        away_team_name: Away team name.
        home_score: Home team final score.
        away_score: Away team final score.
        home_players: List of home team player stats.
        away_players: List of away team player stats.
        raw_html: Original HTML for debugging.

    Example:
        >>> boxscore = scraper.fetch_game_boxscore("26493")
        >>> print(f"{boxscore.home_team_name} {boxscore.home_score} - {boxscore.away_score} {boxscore.away_team_name}")
    """

    game_id: str
    game_date: datetime | None = None
    home_team_id: str | None = None
    away_team_id: str | None = None
    home_team_name: str | None = None
    away_team_name: str | None = None
    home_score: int | None = None
    away_score: int | None = None
    home_players: list[BoxscorePlayerStats] = field(default_factory=list)
    away_players: list[BoxscorePlayerStats] = field(default_factory=list)
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

            # Extract player name - from title (last pipe-separated part)
            # Title format: "LEAGUE | ... | Team Name | Player Name"
            name = ""
            title_element = soup.find("title")
            if title_element:
                title = title_element.get_text(strip=True)
                if "|" in title:
                    # Player name is the last part
                    name = title.split("|")[-1].strip()
                elif " - " in title:
                    name = title.split(" - ")[0].strip()
                else:
                    name = title

            # Try to find player info table/div
            profile = PlayerProfile(
                player_id=player_id,
                name=name or f"Player {player_id}",
                raw_html=html,
            )

            # Look for player info in div.p_info structure (current site format)
            # Format: <span class="p_info_title">Label:</span>Value<br />
            p_info_div = soup.find("div", class_="p_info")
            if p_info_div:
                for span in p_info_div.find_all("span", class_="p_info_title"):
                    label = span.get_text(strip=True).lower().rstrip(":")
                    # Value is the next sibling text node
                    next_sibling = span.next_sibling
                    if next_sibling:
                        value = str(next_sibling).strip()
                        # Clean up &nbsp; and other entities
                        value = value.replace("\xa0", "").strip()

                        if "team" in label or "קבוצה" in label:
                            # Team might be a link
                            team_link = span.find_next("a")
                            if team_link:
                                profile.team_name = team_link.get_text(strip=True)
                            else:
                                profile.team_name = value
                        elif "number" in label or "מספר" in label:
                            profile.jersey_number = value
                        elif "position" in label or "עמדה" in label:
                            profile.position = value
                        elif "height" in label or "גובה" in label:
                            try:
                                # Height can be "1.93" (meters) or "193" (cm)
                                height_str = value.replace(",", ".")
                                if "." in height_str:
                                    # Meters format like "1.93"
                                    profile.height_cm = int(float(height_str) * 100)
                                else:
                                    # Already cm
                                    height_num = "".join(c for c in value if c.isdigit())
                                    if height_num:
                                        profile.height_cm = int(height_num)
                            except ValueError:
                                pass
                        elif "nationality" in label or "לאום" in label:
                            profile.nationality = value
                        elif "birth" in label or "תאריך" in label or "dob" in label:
                            try:
                                # Try various date formats
                                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]:
                                    try:
                                        profile.birth_date = datetime.strptime(
                                            value, fmt
                                        )
                                        break
                                    except ValueError:
                                        continue
                            except ValueError:
                                pass

            # Fallback: Look for info table with player details (legacy format)
            if not profile.height_cm and not profile.birth_date:
                info_tables = soup.find_all("table")
                for table in info_tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)

                            if "team" in label or "קבוצה" in label:
                                profile.team_name = value
                            elif "number" in label or "מספר" in label:
                                profile.jersey_number = value
                            elif "position" in label or "עמדה" in label:
                                profile.position = value
                            elif "height" in label or "גובה" in label:
                                try:
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

                # Extract position, height, and birthdate from role_desc div
                # Format: <strong>G | 1.93</strong><br />04/12/1994
                position = None
                height_cm = None
                birth_date = None
                desc_div = box.find("div", class_="role_desc")
                if desc_div:
                    strong = desc_div.find("strong")
                    if strong:
                        pos_height = strong.get_text(strip=True)
                        # Replace &nbsp; with regular space
                        pos_height = pos_height.replace("\xa0", " ")
                        if "|" in pos_height:
                            parts = pos_height.split("|")
                            position = parts[0].strip()
                            # Height is in meters like "1.93"
                            if len(parts) > 1:
                                height_str = parts[1].strip()
                                try:  # noqa: SIM105
                                    height_cm = int(float(height_str) * 100)
                                except ValueError:
                                    pass

                    # Birthdate is after the <strong> tag
                    # Get all text in desc_div except the strong tag
                    desc_text = desc_div.get_text(separator=" ", strip=True)
                    # Remove the position|height part
                    if strong:
                        strong_text = strong.get_text(strip=True)
                        desc_text = desc_text.replace(strong_text, "").strip()
                    # Remove captain marker (קפטן = "captain" in Hebrew)
                    # Format: "קפטן | 20/06/1991" -> "20/06/1991"
                    if desc_text.startswith("קפטן"):
                        desc_text = desc_text.replace("קפטן", "").strip()
                        if desc_text.startswith("|"):
                            desc_text = desc_text[1:].strip()
                    # Try to parse date (format: DD/MM/YYYY)
                    if desc_text:
                        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"]:
                            try:
                                birth_date = datetime.strptime(desc_text, fmt)
                                break
                            except ValueError:
                                continue

                roster.players.append(
                    RosterPlayer(
                        player_id=player_id,
                        name=player_name,
                        jersey_number=jersey_number,
                        position=position,
                        height_cm=height_cm,
                        birth_date=birth_date,
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

    def fetch_game_boxscore(
        self,
        basket_game_id: str,
        force: bool = False,
    ) -> GameZoneBoxscore:
        """
        Fetch boxscore from basket.co.il game-zone page.

        Scrapes the boxscore directly from basket.co.il which has the correct
        player IDs (not segevstats internal IDs). This allows direct player
        matching without jersey number fallback.

        Args:
            basket_game_id: The basket.co.il game ID (e.g., "26493").
            force: If True, bypass cache and fetch from source.

        Returns:
            GameZoneBoxscore with player stats and correct player IDs.

        Raises:
            WinnerParseError: If the boxscore cannot be parsed.

        Example:
            >>> boxscore = scraper.fetch_game_boxscore("26493")
            >>> for p in boxscore.home_players:
            ...     print(f"#{p.jersey_number} {p.player_name}: {p.points} pts")
        """
        resource_type = "game_zone_page"
        resource_id = basket_game_id

        # Check cache first
        html = None
        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                html = cache.raw_data.get("html", "")

        # Fetch if not cached
        if not html:
            url = f"https://basket.co.il/game-zone.asp?GameId={basket_game_id}&lang=en"
            html = self._fetch_html(url, resource_type, resource_id)
            self._save_cache(resource_type, resource_id, html, http_status=200)

        return self._parse_game_boxscore(html, basket_game_id)

    def _parse_game_boxscore(self, html: str, game_id: str) -> GameZoneBoxscore:
        """
        Parse boxscore from game-zone HTML.

        Args:
            html: HTML content from game-zone.asp.
            game_id: basket.co.il game ID.

        Returns:
            GameZoneBoxscore with parsed player stats.
        """
        import re

        soup = BeautifulSoup(html, "html.parser")

        boxscore = GameZoneBoxscore(game_id=game_id, raw_html=html)

        # Extract game date from h5 element with class "en"
        # Format: "Kiryat Ata,&nbsp;&nbsp;Sunday ,&nbsp; 06/10/2024,&nbsp;19:45"
        h5_elements = soup.find_all("h5", class_="en")
        for h5 in h5_elements:
            text = h5.get_text()
            # Look for date pattern DD/MM/YYYY
            date_match = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
            if date_match:
                day, month, year = date_match.groups()
                boxscore.game_date = datetime(int(year), int(month), int(day))
                break

        # Extract team names from game_zone_team_name divs
        home_name_div = soup.find("div", class_=lambda x: x and "game_zone_team_name" in x and "home_team" in x)
        away_name_div = soup.find("div", class_=lambda x: x and "game_zone_team_name" in x and "away_team" in x)
        if home_name_div:
            boxscore.home_team_name = home_name_div.get_text(strip=True)
        if away_name_div:
            boxscore.away_team_name = away_name_div.get_text(strip=True)

        # Find team IDs from the boxscore tables (they link to team pages)
        # Look for team links in the boxscore area (within player stat tables)
        team_links = soup.find_all("a", href=re.compile(r"team\.asp\?TeamId=\d+"))
        team_ids = []
        for link in team_links:
            href = link.get("href", "")
            match = re.search(r"TeamId=(\d+)", href)
            if match:
                team_id = match.group(1)
                if team_id not in team_ids:
                    team_ids.append(team_id)

        if len(team_ids) >= 2:
            boxscore.home_team_id = team_ids[0]
            boxscore.away_team_id = team_ids[1]

        # Find all boxscore tables (there should be 2: home and away)
        # Look for tables with player stats - they have player links
        tables = soup.find_all("table")

        player_tables = []
        for table in tables:
            # Check if table contains player links
            player_links = table.find_all("a", href=re.compile(r"player\.asp\?PlayerId=\d+"))
            if player_links:
                player_tables.append(table)

        # Parse each table
        for idx, table in enumerate(player_tables[:2]):  # Max 2 teams
            is_home = idx == 0
            team_id = boxscore.home_team_id if is_home else boxscore.away_team_id

            players = self._parse_boxscore_table(table, team_id, is_home)

            if is_home:
                boxscore.home_players = players
            else:
                boxscore.away_players = players

        # Extract scores from the gz_result div
        score_pattern = re.compile(r"(\d+)\s*[-:]\s*(\d+)")
        gz_result = soup.find(id="gz_result")
        if gz_result:
            match = score_pattern.search(gz_result.get_text())
            if match:
                boxscore.home_score = int(match.group(1))
                boxscore.away_score = int(match.group(2))

        return boxscore

    def _parse_boxscore_table(
        self,
        table,
        team_id: str | None,
        is_home: bool,
    ) -> list[BoxscorePlayerStats]:
        """
        Parse a single team's boxscore table.

        Handles the basket.co.il game-zone boxscore table format:
        - Row 0: Team name
        - Row 1: Category headers (2PT, 3PT, 1PT, Rebounds, etc.)
        - Row 2: Column headers (#, Player Name, SF, Min, Pts, M/A, %, etc.)
        - Row 3: Team totals
        - Row 4+: Player rows

        Column indices (0-based):
        0: # (jersey), 1: Player Name, 2: SF (starter flag), 3: Min, 4: Pts,
        5: 2PT M/A, 6: 2PT %, 7: 3PT M/A, 8: 3PT %, 9: FT M/A, 10: FT %,
        11: DR, 12: OR, 13: TR, 14: PF, 15: FA, 16: ST, 17: TO, 18: AS,
        19: BKF, 20: BKA, 21: VAL, 22: +/-

        Args:
            table: BeautifulSoup table element.
            team_id: Team ID for all players.
            is_home: True if home team.

        Returns:
            List of BoxscorePlayerStats.
        """
        import re

        players = []
        rows = table.find_all("tr")

        # Fixed column indices for basket.co.il game-zone format
        COL_JERSEY = 0
        COL_MIN = 3
        COL_PTS = 4
        COL_2PT_MA = 5
        COL_3PT_MA = 7
        COL_FT_MA = 9
        COL_DR = 11
        COL_OR = 12
        COL_TR = 13
        COL_PF = 14
        COL_ST = 16
        COL_TO = 17
        COL_AS = 18
        COL_BKF = 19
        COL_PLUSMINUS = 22

        for row in rows:
            cells = row.find_all(["th", "td"])
            if len(cells) < 5:
                continue

            # Look for player link in the NAME column (index 1), not jersey column
            # The table has player links in both column 0 (jersey) and column 1 (name)
            name_cell = cells[1] if len(cells) > 1 else None
            if not name_cell:
                continue

            player_link = name_cell.find(
                "a", href=re.compile(r"player\.asp\?PlayerId=\d+")
            )
            if not player_link:
                continue

            href = player_link.get("href", "")
            match = re.search(r"PlayerId=(\d+)", href)
            if not match:
                continue

            player_id = match.group(1)
            player_name = player_link.get_text(strip=True)

            # Skip the "Team" totals row
            if player_name.lower() == "team":
                continue
            cell_texts = [c.get_text(strip=True) for c in cells]

            stats = BoxscorePlayerStats(
                player_id=player_id,
                player_name=player_name,
                team_id=team_id,
                is_home=is_home,
            )

            # Helper to safely get cell value
            def get_cell(idx: int) -> str:
                return cell_texts[idx] if idx < len(cell_texts) else ""  # noqa: B023

            def parse_int(idx: int) -> int:
                """Parse integer from cell, return 0 on failure."""
                try:
                    return int(get_cell(idx))
                except ValueError:
                    return 0

            def parse_made_attempted(idx: int) -> tuple[int, int]:
                """Parse M/A format (e.g., '3/5') into (made, attempted)."""
                text = get_cell(idx)
                if "/" in text:
                    parts = text.split("/")
                    if len(parts) == 2:
                        try:
                            return int(parts[0]), int(parts[1])
                        except ValueError:
                            pass
                return 0, 0

            # Parse jersey number
            jersey_text = get_cell(COL_JERSEY)
            if jersey_text.isdigit():
                stats.jersey_number = int(jersey_text)

            # Parse minutes
            stats.minutes = get_cell(COL_MIN) or None

            # Parse points
            stats.points = parse_int(COL_PTS)

            # Parse shooting stats (M/A format)
            stats.two_pt_made, stats.two_pt_attempted = parse_made_attempted(COL_2PT_MA)
            stats.three_pt_made, stats.three_pt_attempted = parse_made_attempted(
                COL_3PT_MA
            )
            stats.ft_made, stats.ft_attempted = parse_made_attempted(COL_FT_MA)

            # Parse rebounds
            stats.defensive_rebounds = parse_int(COL_DR)
            stats.offensive_rebounds = parse_int(COL_OR)
            stats.total_rebounds = parse_int(COL_TR)

            # Parse other stats
            stats.fouls = parse_int(COL_PF)
            stats.steals = parse_int(COL_ST)
            stats.turnovers = parse_int(COL_TO)
            stats.assists = parse_int(COL_AS)
            stats.blocks = parse_int(COL_BKF)

            # Parse plus/minus (may be empty or have a value)
            pm_text = get_cell(COL_PLUSMINUS)
            if pm_text:
                try:  # noqa: SIM105
                    stats.plus_minus = int(pm_text)
                except ValueError:
                    pass

            players.append(stats)

        return players
