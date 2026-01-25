"""
Analytics Schemas Module

Pydantic models for analytics filtering and configuration.

This module provides filter schemas for advanced analytics queries:
- ClutchFilter: Configure clutch time criteria (time remaining, score margin)
- SituationalFilter: Filter PBP events by situational attributes
- OpponentFilter: Filter by opponent team and home/away games

Usage:
    from src.schemas.analytics import ClutchFilter, SituationalFilter, OpponentFilter

    # NBA standard clutch: last 5 min of Q4/OT, within 5 points
    filter = ClutchFilter()

    # Super clutch: last 2 min, within 3 points
    filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)

    # Filter for fast break shots
    filter = SituationalFilter(fast_break=True)

    # Filter for contested catch-and-shoot attempts
    filter = SituationalFilter(contested=True, shot_type="CATCH_AND_SHOOT")

    # Filter for games against a specific opponent
    filter = OpponentFilter(opponent_team_id=celtics_id)

    # Filter for home games only
    filter = OpponentFilter(home_only=True)

Clutch Time Definitions (research sources):
- NBA official: Last 5 minutes of 4th quarter or OT, score within 5 points
- "Crunch time" / "Super clutch": Last 2 minutes, within 3 points
- Source: NBA.com/stats, Basketball Reference clutch stats
"""

from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ClutchFilter(BaseModel):
    """
    Filter configuration for clutch time analysis.

    Clutch time is defined as moments in the game where the outcome is
    uncertain and pressure is highest. The NBA standard definition is:
    last 5 minutes of 4th quarter or overtime, with score within 5 points.

    Attributes:
        time_remaining_seconds: Maximum seconds remaining in period to qualify.
            Default 300 (5 minutes) matches NBA standard.
        score_margin: Maximum point difference to qualify as clutch.
            Default 5 matches NBA standard.
        include_overtime: Whether to include overtime periods.
            Default True.
        min_period: Minimum period number for clutch (4 = 4th quarter).
            Default 4.

    Example:
        >>> # NBA standard clutch
        >>> filter = ClutchFilter()
        >>> assert filter.time_remaining_seconds == 300
        >>> assert filter.score_margin == 5

        >>> # Stricter "super clutch"
        >>> filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)
    """

    time_remaining_seconds: int = Field(
        default=300,
        ge=0,
        le=720,
        description="Max seconds remaining in period (default 300 = 5 min)",
    )
    score_margin: int = Field(
        default=5,
        ge=0,
        le=50,
        description="Max point difference to qualify (default 5)",
    )
    include_overtime: bool = Field(
        default=True,
        description="Include overtime periods as clutch time",
    )
    min_period: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Minimum period for clutch (4 = 4th quarter)",
    )

    model_config = {"frozen": True}


class SituationalFilter(BaseModel):
    """
    Filter configuration for situational shot analysis.

    Filters play-by-play events based on situational attributes stored
    in the event's attributes JSON field. All filter fields are optional;
    only non-None fields are applied as filter criteria.

    Attributes:
        fast_break: Filter for fast break opportunities.
            True = only fast break, False = exclude fast break, None = no filter.
        second_chance: Filter for second chance (offensive rebound) opportunities.
            True = only second chance, False = exclude, None = no filter.
        contested: Filter for contested shot attempts.
            True = only contested, False = only uncontested, None = no filter.
        shot_type: Filter by shot type classification.
            Options: "PULL_UP", "CATCH_AND_SHOOT", "POST_UP", None = no filter.

    Example:
        >>> # Get all fast break shots
        >>> filter = SituationalFilter(fast_break=True)

        >>> # Get contested catch-and-shoot attempts
        >>> filter = SituationalFilter(contested=True, shot_type="CATCH_AND_SHOOT")

        >>> # Get uncontested shots that are NOT fast breaks
        >>> filter = SituationalFilter(fast_break=False, contested=False)
    """

    fast_break: bool | None = Field(
        default=None,
        description="Filter for fast break opportunities (True/False/None)",
    )
    second_chance: bool | None = Field(
        default=None,
        description="Filter for second chance opportunities (True/False/None)",
    )
    contested: bool | None = Field(
        default=None,
        description="Filter for contested shot attempts (True/False/None)",
    )
    shot_type: str | None = Field(
        default=None,
        description="Shot type: PULL_UP, CATCH_AND_SHOOT, POST_UP",
    )

    model_config = {"frozen": True}


class OpponentFilter(BaseModel):
    """
    Filter configuration for opponent-based and home/away analysis.

    Filters stats by opponent team and/or home/away game location.
    Used with AnalyticsService methods to get games against specific
    opponents or player performance splits by game location.

    Attributes:
        opponent_team_id: UUID of the opponent team to filter against.
            If None, no opponent filtering is applied.
        home_only: If True, only include home games.
            Default False.
        away_only: If True, only include away games.
            Default False.

    Note:
        home_only and away_only are mutually exclusive.
        Setting both to True will raise a ValidationError.

    Example:
        >>> # Get stats vs Celtics only
        >>> filter = OpponentFilter(opponent_team_id=celtics_id)

        >>> # Get home game stats only
        >>> filter = OpponentFilter(home_only=True)

        >>> # Get away games vs Celtics
        >>> filter = OpponentFilter(opponent_team_id=celtics_id, away_only=True)
    """

    opponent_team_id: UUID | None = Field(
        default=None,
        description="UUID of opponent team to filter against",
    )
    home_only: bool = Field(
        default=False,
        description="If True, only include home games",
    )
    away_only: bool = Field(
        default=False,
        description="If True, only include away games",
    )

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_home_away_exclusive(self) -> "OpponentFilter":
        """Validate that home_only and away_only are mutually exclusive."""
        if self.home_only and self.away_only:
            raise ValueError("home_only and away_only cannot both be True")
        return self


class TimeFilter(BaseModel):
    """Filter for time-based period analysis (quarter, OT, garbage time)."""

    period: int | None = Field(default=None, ge=1, le=10)
    periods: list[int] | None = Field(default=None)
    exclude_garbage_time: bool = Field(default=False)
    min_time_remaining: int | None = Field(default=None, ge=0, le=720)
    max_time_remaining: int | None = Field(default=None, ge=0, le=720)

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_filters(self) -> "TimeFilter":
        """Validate period and time range constraints."""
        if self.period is not None and self.periods is not None:
            raise ValueError("period and periods cannot both be set")
        if self.periods is not None:
            for p in self.periods:
                if not 1 <= p <= 10:
                    raise ValueError(f"Period {p} must be between 1 and 10")
        if (
            self.min_time_remaining is not None
            and self.max_time_remaining is not None
            and self.min_time_remaining > self.max_time_remaining
        ):
            raise ValueError("min_time_remaining must be <= max_time_remaining")
        return self
