"""
Analytics Schemas Module

Pydantic models for analytics filtering and configuration.

This module provides filter schemas for advanced analytics queries:
- ClutchFilter: Configure clutch time criteria (time remaining, score margin)

Usage:
    from src.schemas.analytics import ClutchFilter

    # NBA standard clutch: last 5 min of Q4/OT, within 5 points
    filter = ClutchFilter()

    # Super clutch: last 2 min, within 3 points
    filter = ClutchFilter(time_remaining_seconds=120, score_margin=3)

Clutch Time Definitions (research sources):
- NBA official: Last 5 minutes of 4th quarter or OT, score within 5 points
- "Crunch time" / "Super clutch": Last 2 minutes, within 3 points
- Source: NBA.com/stats, Basketball Reference clutch stats
"""

from pydantic import BaseModel, Field


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
