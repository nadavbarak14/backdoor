"""
Stats Schema Module

Pydantic schemas for player and team game statistics:
- PlayerGameStatsResponse: Per-game player statistics
- PlayerGameStatsWithGameResponse: Player stats with game context
- PlayerGameLogResponse: Paginated player game log
- TeamGameStatsResponse: Per-game team statistics
- TeamGameSummaryResponse: Team game summary
- TeamGameHistoryResponse: Paginated team game history

Usage:
    from src.schemas.stats import PlayerGameStatsResponse, TeamGameStatsResponse

    @router.get("/games/{game_id}/players/{player_id}/stats")
    def get_player_game_stats() -> PlayerGameStatsResponse:
        ...
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field

from src.schemas.base import OrmBase


def _compute_percentage(made: int, attempted: int) -> float:
    """
    Compute shooting percentage.

    Args:
        made: Number of shots made.
        attempted: Number of shots attempted.

    Returns:
        Percentage as float (0.0 if no attempts).

    Example:
        >>> _compute_percentage(7, 14)
        50.0
        >>> _compute_percentage(0, 0)
        0.0
    """
    if attempted == 0:
        return 0.0
    return round((made / attempted) * 100, 1)


def _format_minutes(seconds: int) -> str:
    """
    Format seconds into MM:SS display string.

    Args:
        seconds: Playing time in seconds.

    Returns:
        Formatted string like "25:30".

    Example:
        >>> _format_minutes(1800)
        '30:00'
        >>> _format_minutes(754)
        '12:34'
    """
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


class PlayerGameStatsResponse(OrmBase):
    """
    Schema for per-game player statistics response.

    Contains all box score data for a player in a single game.
    Percentage fields are computed from made/attempted values.

    Attributes:
        id: Unique stat line identifier.
        game_id: UUID of the game.
        player_id: UUID of the player.
        player_name: Full name of the player.
        team_id: UUID of the team.
        minutes_played: Playing time in seconds.
        is_starter: Whether the player was in the starting lineup.
        points: Total points scored.
        field_goals_made: Number of field goals made.
        field_goals_attempted: Number of field goals attempted.
        two_pointers_made: Number of 2-point field goals made.
        two_pointers_attempted: Number of 2-point field goals attempted.
        three_pointers_made: Number of 3-point field goals made.
        three_pointers_attempted: Number of 3-point field goals attempted.
        free_throws_made: Number of free throws made.
        free_throws_attempted: Number of free throws attempted.
        offensive_rebounds: Number of offensive rebounds.
        defensive_rebounds: Number of defensive rebounds.
        total_rebounds: Total number of rebounds.
        assists: Number of assists.
        turnovers: Number of turnovers.
        steals: Number of steals.
        blocks: Number of blocks.
        personal_fouls: Number of personal fouls.
        plus_minus: Plus/minus statistic.
        efficiency: Performance index rating.
        extra_stats: League-specific stats.

    Computed Fields:
        minutes_display: Formatted playing time (e.g., "25:30").
        field_goal_pct: Field goal percentage.
        two_point_pct: 2-point percentage.
        three_point_pct: 3-point percentage.
        free_throw_pct: Free throw percentage.

    Example:
        >>> stats = PlayerGameStatsResponse(
        ...     id=uuid4(),
        ...     game_id=game_uuid,
        ...     player_id=player_uuid,
        ...     player_name="LeBron James",
        ...     team_id=team_uuid,
        ...     minutes_played=2040,
        ...     points=25,
        ...     field_goals_made=9,
        ...     field_goals_attempted=18,
        ...     ...
        ... )
        >>> print(stats.minutes_display)
        '34:00'
        >>> print(stats.field_goal_pct)
        50.0
    """

    id: uuid.UUID
    game_id: uuid.UUID
    player_id: uuid.UUID
    player_name: str
    team_id: uuid.UUID

    # Time
    minutes_played: int = Field(description="Playing time in seconds")
    is_starter: bool

    # Scoring
    points: int
    field_goals_made: int
    field_goals_attempted: int
    two_pointers_made: int
    two_pointers_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int

    # Rebounds
    offensive_rebounds: int
    defensive_rebounds: int
    total_rebounds: int

    # Other stats
    assists: int
    turnovers: int
    steals: int
    blocks: int
    personal_fouls: int
    plus_minus: int
    efficiency: int
    extra_stats: dict[str, Any]

    @computed_field
    @property
    def minutes_display(self) -> str:
        """Format minutes_played seconds as MM:SS string."""
        return _format_minutes(self.minutes_played)

    @computed_field
    @property
    def field_goal_pct(self) -> float:
        """Compute field goal percentage."""
        return _compute_percentage(self.field_goals_made, self.field_goals_attempted)

    @computed_field
    @property
    def two_point_pct(self) -> float:
        """Compute 2-point field goal percentage."""
        return _compute_percentage(self.two_pointers_made, self.two_pointers_attempted)

    @computed_field
    @property
    def three_point_pct(self) -> float:
        """Compute 3-point field goal percentage."""
        return _compute_percentage(
            self.three_pointers_made, self.three_pointers_attempted
        )

    @computed_field
    @property
    def free_throw_pct(self) -> float:
        """Compute free throw percentage."""
        return _compute_percentage(self.free_throws_made, self.free_throws_attempted)


class PlayerGameStatsWithGameResponse(PlayerGameStatsResponse):
    """
    Schema for player game stats with game context.

    Extends PlayerGameStatsResponse with game information.
    Used for /players/{id}/games endpoint.

    Attributes:
        game_date: Date and time of the game.
        opponent_team_id: UUID of the opposing team.
        opponent_team_name: Name of the opposing team.
        is_home: Whether the player's team was the home team.
        team_score: Player's team final score.
        opponent_score: Opposing team's final score.

    Computed Fields:
        result: "W" if team won, "L" if team lost.

    Example:
        >>> stats = PlayerGameStatsWithGameResponse(
        ...     # ... all PlayerGameStatsResponse fields ...
        ...     game_date=datetime(2024, 1, 15, 19, 30),
        ...     opponent_team_id=opponent_uuid,
        ...     opponent_team_name="Boston Celtics",
        ...     is_home=True,
        ...     team_score=112,
        ...     opponent_score=108,
        ... )
        >>> print(stats.result)
        'W'
    """

    game_date: datetime
    opponent_team_id: uuid.UUID
    opponent_team_name: str
    is_home: bool
    team_score: int
    opponent_score: int

    @computed_field
    @property
    def result(self) -> str:
        """Compute game result (W/L)."""
        return "W" if self.team_score > self.opponent_score else "L"


class PlayerGameLogResponse(BaseModel):
    """
    Schema for paginated player game log response.

    Contains a list of player game stats with game context.

    Attributes:
        items: List of game stats for the current page.
        total: Total number of games across all pages.

    Example:
        >>> response = PlayerGameLogResponse(
        ...     items=[game1_stats, game2_stats, ...],
        ...     total=82
        ... )
    """

    items: list[PlayerGameStatsWithGameResponse]
    total: int


class TeamGameStatsResponse(OrmBase):
    """
    Schema for per-game team statistics response.

    Contains all aggregated team stats for a single game.
    Percentage fields are computed from made/attempted values.

    Attributes:
        game_id: UUID of the game.
        team_id: UUID of the team.
        team_name: Name of the team.
        is_home: Whether this team is the home team.
        points: Total points scored.
        field_goals_made: Number of field goals made.
        field_goals_attempted: Number of field goals attempted.
        two_pointers_made: Number of 2-point field goals made.
        two_pointers_attempted: Number of 2-point field goals attempted.
        three_pointers_made: Number of 3-point field goals made.
        three_pointers_attempted: Number of 3-point field goals attempted.
        free_throws_made: Number of free throws made.
        free_throws_attempted: Number of free throws attempted.
        offensive_rebounds: Number of offensive rebounds.
        defensive_rebounds: Number of defensive rebounds.
        total_rebounds: Total number of rebounds.
        assists: Number of assists.
        turnovers: Number of turnovers.
        steals: Number of steals.
        blocks: Number of blocks.
        personal_fouls: Number of personal fouls.
        fast_break_points: Points scored on fast breaks.
        points_in_paint: Points scored in the paint.
        second_chance_points: Points from second chance opportunities.
        bench_points: Points scored by bench players.
        biggest_lead: Largest lead during the game.
        time_leading: Time spent leading in seconds.
        extra_stats: League-specific stats.

    Computed Fields:
        field_goal_pct: Field goal percentage.
        two_point_pct: 2-point percentage.
        three_point_pct: 3-point percentage.
        free_throw_pct: Free throw percentage.

    Example:
        >>> stats = TeamGameStatsResponse(
        ...     game_id=game_uuid,
        ...     team_id=team_uuid,
        ...     team_name="Los Angeles Lakers",
        ...     is_home=True,
        ...     points=112,
        ...     field_goals_made=42,
        ...     field_goals_attempted=88,
        ...     ...
        ... )
        >>> print(stats.field_goal_pct)
        47.7
    """

    game_id: uuid.UUID
    team_id: uuid.UUID
    team_name: str
    is_home: bool

    # Scoring
    points: int
    field_goals_made: int
    field_goals_attempted: int
    two_pointers_made: int
    two_pointers_attempted: int
    three_pointers_made: int
    three_pointers_attempted: int
    free_throws_made: int
    free_throws_attempted: int

    # Rebounds
    offensive_rebounds: int
    defensive_rebounds: int
    total_rebounds: int

    # Other stats
    assists: int
    turnovers: int
    steals: int
    blocks: int
    personal_fouls: int

    # Team-only stats
    fast_break_points: int
    points_in_paint: int
    second_chance_points: int
    bench_points: int
    biggest_lead: int
    time_leading: int
    extra_stats: dict[str, Any]

    @computed_field
    @property
    def field_goal_pct(self) -> float:
        """Compute field goal percentage."""
        return _compute_percentage(self.field_goals_made, self.field_goals_attempted)

    @computed_field
    @property
    def two_point_pct(self) -> float:
        """Compute 2-point field goal percentage."""
        return _compute_percentage(self.two_pointers_made, self.two_pointers_attempted)

    @computed_field
    @property
    def three_point_pct(self) -> float:
        """Compute 3-point field goal percentage."""
        return _compute_percentage(
            self.three_pointers_made, self.three_pointers_attempted
        )

    @computed_field
    @property
    def free_throw_pct(self) -> float:
        """Compute free throw percentage."""
        return _compute_percentage(self.free_throws_made, self.free_throws_attempted)


class TeamGameSummaryResponse(OrmBase):
    """
    Schema for team game summary response.

    Provides a summary view of a game from a team's perspective.
    Used for /teams/{id}/games endpoint.

    Attributes:
        game_id: UUID of the game.
        game_date: Date and time of the game.
        opponent_team_id: UUID of the opposing team.
        opponent_team_name: Name of the opposing team.
        is_home: Whether the team was the home team.
        team_score: Team's final score.
        opponent_score: Opposing team's final score.
        venue: Name of the arena/venue.

    Computed Fields:
        result: "W" if team won, "L" if team lost.

    Example:
        >>> summary = TeamGameSummaryResponse(
        ...     game_id=game_uuid,
        ...     game_date=datetime(2024, 1, 15, 19, 30),
        ...     opponent_team_id=opponent_uuid,
        ...     opponent_team_name="Boston Celtics",
        ...     is_home=True,
        ...     team_score=112,
        ...     opponent_score=108,
        ...     venue="Crypto.com Arena"
        ... )
        >>> print(summary.result)
        'W'
    """

    game_id: uuid.UUID
    game_date: datetime
    opponent_team_id: uuid.UUID
    opponent_team_name: str
    is_home: bool
    team_score: int
    opponent_score: int
    venue: str | None

    @computed_field
    @property
    def result(self) -> str:
        """Compute game result (W/L)."""
        return "W" if self.team_score > self.opponent_score else "L"


class TeamGameHistoryResponse(BaseModel):
    """
    Schema for paginated team game history response.

    Contains a list of team game summaries.

    Attributes:
        items: List of game summaries for the current page.
        total: Total number of games across all pages.

    Example:
        >>> response = TeamGameHistoryResponse(
        ...     items=[game1_summary, game2_summary, ...],
        ...     total=82
        ... )
    """

    items: list[TeamGameSummaryResponse]
    total: int
