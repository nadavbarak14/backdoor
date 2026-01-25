"""
Player Stats Schema Module

Pydantic schemas for player season statistics and league leaders:
- PlayerSeasonStatsResponse: Full season stats with player/team names
- PlayerCareerStatsResponse: Career totals with list of seasons
- LeagueLeaderEntry: Individual leader entry with rank
- LeagueLeadersResponse: Category leaders list
- LeagueLeadersFilter: Filter for querying league leaders

Usage:
    from src.schemas.player_stats import (
        PlayerSeasonStatsResponse,
        PlayerCareerStatsResponse,
        LeagueLeadersResponse,
        LeagueLeadersFilter,
    )

    @router.get("/players/{player_id}/stats/season/{season_id}")
    def get_player_season_stats() -> PlayerSeasonStatsResponse:
        ...
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field

from src.schemas.base import OrmBase


def _format_minutes(seconds: float) -> str:
    """
    Format seconds into MM:SS display string.

    Args:
        seconds: Playing time in seconds (can be fractional for averages).

    Returns:
        Formatted string like "25:30".

    Example:
        >>> _format_minutes(1800.0)
        '30:00'
        >>> _format_minutes(754.5)
        '12:34'
    """
    total_seconds = int(seconds)
    mins = total_seconds // 60
    secs = total_seconds % 60
    return f"{mins}:{secs:02d}"


class StatsCategory(str, Enum):
    """
    Statistical categories for league leaders.

    Attributes:
        POINTS: Points per game.
        REBOUNDS: Rebounds per game.
        ASSISTS: Assists per game.
        STEALS: Steals per game.
        BLOCKS: Blocks per game.
        FIELD_GOAL_PCT: Field goal percentage.
        THREE_POINT_PCT: Three-point percentage.
        FREE_THROW_PCT: Free throw percentage.
        MINUTES: Minutes per game.
        EFFICIENCY: Efficiency rating.
    """

    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    STEALS = "steals"
    BLOCKS = "blocks"
    FIELD_GOAL_PCT = "field_goal_pct"
    THREE_POINT_PCT = "three_point_pct"
    FREE_THROW_PCT = "free_throw_pct"
    MINUTES = "minutes"
    EFFICIENCY = "efficiency"


class PlayerSeasonStatsResponse(OrmBase):
    """
    Schema for player season statistics response.

    Contains aggregated totals, averages, and percentages for a player's
    season with a specific team. Percentages are on 0-100 scale.

    Attributes:
        id: Unique stat record identifier.
        player_id: UUID of the player.
        player_name: Full name of the player.
        team_id: UUID of the team.
        team_name: Name of the team.
        season_id: UUID of the season.
        season_name: Name of the season (e.g., "2023-24").
        games_played: Number of games played.
        games_started: Number of games started.
        total_minutes: Total playing time in seconds.
        total_points: Total points scored.
        total_field_goals_made: Total field goals made.
        total_field_goals_attempted: Total field goals attempted.
        total_two_pointers_made: Total 2-point field goals made.
        total_two_pointers_attempted: Total 2-point field goals attempted.
        total_three_pointers_made: Total 3-point field goals made.
        total_three_pointers_attempted: Total 3-point field goals attempted.
        total_free_throws_made: Total free throws made.
        total_free_throws_attempted: Total free throws attempted.
        total_offensive_rebounds: Total offensive rebounds.
        total_defensive_rebounds: Total defensive rebounds.
        total_rebounds: Total rebounds.
        total_assists: Total assists.
        total_turnovers: Total turnovers.
        total_steals: Total steals.
        total_blocks: Total blocks.
        total_personal_fouls: Total personal fouls.
        total_plus_minus: Cumulative plus/minus.
        avg_minutes: Average minutes per game (in seconds).
        avg_points: Average points per game.
        avg_rebounds: Average rebounds per game.
        avg_assists: Average assists per game.
        avg_turnovers: Average turnovers per game.
        avg_steals: Average steals per game.
        avg_blocks: Average blocks per game.
        field_goal_pct: Field goal percentage (0-100).
        two_point_pct: Two-point percentage (0-100).
        three_point_pct: Three-point percentage (0-100).
        free_throw_pct: Free throw percentage (0-100).
        true_shooting_pct: True shooting percentage (0-100).
        effective_field_goal_pct: Effective field goal percentage (0-100).
        assist_turnover_ratio: Assist to turnover ratio.
        last_calculated: When stats were last computed.

    Computed Fields:
        avg_minutes_display: Formatted average minutes (e.g., "34:00").

    Example:
        >>> stats = PlayerSeasonStatsResponse(
        ...     id=uuid4(),
        ...     player_id=player_uuid,
        ...     player_name="LeBron James",
        ...     team_id=team_uuid,
        ...     team_name="Los Angeles Lakers",
        ...     season_id=season_uuid,
        ...     season_name="2023-24",
        ...     games_played=72,
        ...     avg_points=25.0,
        ...     field_goal_pct=48.5,
        ...     ...
        ... )
    """

    id: uuid.UUID
    player_id: uuid.UUID
    player_name: str
    team_id: uuid.UUID
    team_name: str
    season_id: uuid.UUID
    season_name: str

    # Games
    games_played: int
    games_started: int

    # Totals
    total_minutes: int = Field(description="Total playing time in seconds")
    total_points: int
    total_field_goals_made: int
    total_field_goals_attempted: int
    total_two_pointers_made: int
    total_two_pointers_attempted: int
    total_three_pointers_made: int
    total_three_pointers_attempted: int
    total_free_throws_made: int
    total_free_throws_attempted: int
    total_offensive_rebounds: int
    total_defensive_rebounds: int
    total_rebounds: int
    total_assists: int
    total_turnovers: int
    total_steals: int
    total_blocks: int
    total_personal_fouls: int
    total_plus_minus: int

    # Averages
    avg_minutes: float = Field(description="Average playing time per game in seconds")
    avg_points: float
    avg_rebounds: float
    avg_assists: float
    avg_turnovers: float
    avg_steals: float
    avg_blocks: float

    # Percentages (0-100 scale)
    field_goal_pct: float | None = Field(
        default=None, description="Field goal percentage (0-100)"
    )
    two_point_pct: float | None = Field(
        default=None, description="Two-point percentage (0-100)"
    )
    three_point_pct: float | None = Field(
        default=None, description="Three-point percentage (0-100)"
    )
    free_throw_pct: float | None = Field(
        default=None, description="Free throw percentage (0-100)"
    )

    # Advanced stats (0-100 scale)
    true_shooting_pct: float | None = Field(
        default=None, description="True shooting percentage (0-100)"
    )
    effective_field_goal_pct: float | None = Field(
        default=None, description="Effective field goal percentage (0-100)"
    )
    assist_turnover_ratio: float | None = Field(
        default=None, description="Assist to turnover ratio"
    )

    last_calculated: datetime

    @computed_field
    @property
    def avg_minutes_display(self) -> str:
        """Format avg_minutes seconds as MM:SS string."""
        return _format_minutes(self.avg_minutes)


class PlayerCareerStatsResponse(BaseModel):
    """
    Schema for player career statistics response.

    Contains career totals and a list of individual season stats.

    Attributes:
        player_id: UUID of the player.
        player_name: Full name of the player.
        career_games_played: Total games played across all seasons.
        career_games_started: Total games started across all seasons.
        career_points: Total career points.
        career_rebounds: Total career rebounds.
        career_assists: Total career assists.
        career_steals: Total career steals.
        career_blocks: Total career blocks.
        career_turnovers: Total career turnovers.
        career_avg_points: Career average points per game.
        career_avg_rebounds: Career average rebounds per game.
        career_avg_assists: Career average assists per game.
        seasons: List of individual season stats.

    Example:
        >>> career = PlayerCareerStatsResponse(
        ...     player_id=player_uuid,
        ...     player_name="LeBron James",
        ...     career_games_played=1421,
        ...     career_points=38652,
        ...     career_avg_points=27.2,
        ...     seasons=[season1_stats, season2_stats, ...]
        ... )
    """

    player_id: uuid.UUID
    player_name: str

    # Career totals
    career_games_played: int
    career_games_started: int
    career_points: int
    career_rebounds: int
    career_assists: int
    career_steals: int
    career_blocks: int
    career_turnovers: int

    # Career averages
    career_avg_points: float
    career_avg_rebounds: float
    career_avg_assists: float

    # Individual seasons
    seasons: list[PlayerSeasonStatsResponse]


class LeagueLeaderEntry(BaseModel):
    """
    Schema for a single league leader entry.

    Represents one player's ranking in a statistical category.

    Attributes:
        rank: Player's rank in this category (1-indexed).
        player_id: UUID of the player.
        player_name: Full name of the player.
        team_id: UUID of the player's team.
        team_name: Name of the player's team.
        value: The statistical value (e.g., 27.5 for PPG).
        games_played: Number of games played (for qualification context).

    Example:
        >>> leader = LeagueLeaderEntry(
        ...     rank=1,
        ...     player_id=player_uuid,
        ...     player_name="Joel Embiid",
        ...     team_id=team_uuid,
        ...     team_name="Philadelphia 76ers",
        ...     value=33.1,
        ...     games_played=66
        ... )
    """

    rank: int = Field(ge=1, description="Player's rank in this category")
    player_id: uuid.UUID
    player_name: str
    team_id: uuid.UUID
    team_name: str
    value: float = Field(description="The statistical value")
    games_played: int


class LeagueLeadersResponse(BaseModel):
    """
    Schema for league leaders response.

    Contains the category and list of top players.

    Attributes:
        category: The statistical category.
        season_id: UUID of the season.
        season_name: Name of the season.
        min_games: Minimum games required for qualification.
        leaders: List of leader entries.

    Example:
        >>> response = LeagueLeadersResponse(
        ...     category=StatsCategory.POINTS,
        ...     season_id=season_uuid,
        ...     season_name="2023-24",
        ...     min_games=58,
        ...     leaders=[leader1, leader2, ...]
        ... )
    """

    category: StatsCategory
    season_id: uuid.UUID
    season_name: str
    min_games: int = Field(description="Minimum games for qualification")
    leaders: list[LeagueLeaderEntry]


class LeagueLeadersFilter(BaseModel):
    """
    Schema for filtering league leaders queries.

    Attributes:
        season_id: UUID of the season to query.
        category: Statistical category to rank by.
        limit: Maximum number of leaders to return (default 10).
        min_games: Minimum games played for qualification (default 0).

    Example:
        >>> filter = LeagueLeadersFilter(
        ...     season_id=season_uuid,
        ...     category=StatsCategory.POINTS,
        ...     limit=20,
        ...     min_games=58
        ... )
    """

    season_id: uuid.UUID
    category: StatsCategory = Field(default=StatsCategory.POINTS)
    limit: int = Field(default=10, ge=1, le=100, description="Max leaders to return")
    min_games: int = Field(
        default=0, ge=0, description="Minimum games for qualification"
    )
