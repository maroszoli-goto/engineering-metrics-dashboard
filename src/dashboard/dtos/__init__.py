"""Data Transfer Objects for the dashboard layer.

This package provides type-safe DTOs for communication between
the Application layer (services) and Presentation layer (blueprints).

DTOs ensure:
- Type safety through dataclasses and type hints
- Validation of data before use
- Clear contracts between layers
- Easy serialization/deserialization
"""

from .base import BaseDTO, DORAMetricsDTO
from .metrics_dto import (
    CacheMetadataDTO,
    ComparisonDTO,
    JiraMetricsDTO,
    PersonMetricsDTO,
    TeamMetricsDTO,
)
from .team_dto import TeamDTO, TeamMemberDTO, TeamSummaryDTO

__all__ = [
    # Base
    "BaseDTO",
    "DORAMetricsDTO",
    # Metrics
    "JiraMetricsDTO",
    "TeamMetricsDTO",
    "PersonMetricsDTO",
    "ComparisonDTO",
    "CacheMetadataDTO",
    # Team
    "TeamDTO",
    "TeamMemberDTO",
    "TeamSummaryDTO",
]
