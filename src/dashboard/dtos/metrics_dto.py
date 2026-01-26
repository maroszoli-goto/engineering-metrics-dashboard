"""Data Transfer Objects for metrics data."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseDTO, DORAMetricsDTO


@dataclass
class JiraMetricsDTO(BaseDTO):
    """Data Transfer Object for Jira metrics."""

    completed_issues: int = 0
    bugs_created: int = 0
    bugs_resolved: int = 0
    scope_created: int = 0
    scope_resolved: int = 0
    wip_count: int = 0
    avg_cycle_time_days: float = 0.0
    incidents_count: int = 0

    def validate(self) -> None:
        """Validate Jira metrics."""
        if self.completed_issues < 0:
            raise ValueError("Completed issues cannot be negative")
        if self.bugs_created < 0:
            raise ValueError("Bugs created cannot be negative")
        if self.bugs_resolved < 0:
            raise ValueError("Bugs resolved cannot be negative")
        if self.wip_count < 0:
            raise ValueError("WIP count cannot be negative")
        if self.avg_cycle_time_days < 0:
            raise ValueError("Average cycle time cannot be negative")


@dataclass
class TeamMetricsDTO(BaseDTO):
    """Data Transfer Object for team metrics."""

    # Basic info
    name: str
    member_count: int

    # GitHub metrics
    total_prs: int = 0
    merged_prs: int = 0
    total_reviews: int = 0
    total_commits: int = 0
    avg_cycle_time_hours: float = 0.0
    merge_rate: float = 0.0

    # Jira metrics
    jira_metrics: Optional[JiraMetricsDTO] = None

    # DORA metrics
    dora_metrics: Optional[DORAMetricsDTO] = None

    # Performance
    performance_score: float = 0.0

    # Additional data
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    last_updated: Optional[str] = None

    def validate(self) -> None:
        """Validate team metrics."""
        if self.member_count <= 0:
            raise ValueError("Member count must be positive")
        if self.total_prs < 0:
            raise ValueError("Total PRs cannot be negative")
        if self.merged_prs < 0:
            raise ValueError("Merged PRs cannot be negative")
        if self.merged_prs > self.total_prs:
            raise ValueError("Merged PRs cannot exceed total PRs")
        if not 0 <= self.merge_rate <= 100:
            raise ValueError("Merge rate must be between 0 and 100")
        if not 0 <= self.performance_score <= 100:
            raise ValueError("Performance score must be between 0 and 100")

        # Validate nested DTOs
        if self.jira_metrics:
            self.jira_metrics.validate()
        if self.dora_metrics:
            self.dora_metrics.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamMetricsDTO":
        """Create TeamMetricsDTO from dictionary."""
        # Convert nested Jira metrics
        if "jira_metrics" in data and data["jira_metrics"]:
            if isinstance(data["jira_metrics"], dict):
                data["jira_metrics"] = JiraMetricsDTO.from_dict(data["jira_metrics"])

        # Convert nested DORA metrics
        if "dora_metrics" in data and data["dora_metrics"]:
            if isinstance(data["dora_metrics"], dict):
                data["dora_metrics"] = DORAMetricsDTO.from_dict(data["dora_metrics"])

        return super().from_dict(data)


@dataclass
class PersonMetricsDTO(BaseDTO):
    """Data Transfer Object for individual contributor metrics."""

    # Basic info
    name: str
    github_username: str
    jira_username: Optional[str] = None

    # GitHub metrics
    prs_opened: int = 0
    prs_merged: int = 0
    reviews_given: int = 0
    commits: int = 0
    avg_pr_cycle_time_hours: float = 0.0
    merge_rate: float = 0.0

    # Jira metrics
    jira_metrics: Optional[JiraMetricsDTO] = None

    # Performance
    performance_score: float = 0.0

    # Additional data
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    last_updated: Optional[str] = None

    def validate(self) -> None:
        """Validate person metrics."""
        if self.prs_opened < 0:
            raise ValueError("PRs opened cannot be negative")
        if self.prs_merged < 0:
            raise ValueError("PRs merged cannot be negative")
        if self.prs_merged > self.prs_opened:
            raise ValueError("PRs merged cannot exceed PRs opened")
        if self.reviews_given < 0:
            raise ValueError("Reviews given cannot be negative")
        if self.commits < 0:
            raise ValueError("Commits cannot be negative")
        if not 0 <= self.merge_rate <= 100:
            raise ValueError("Merge rate must be between 0 and 100")
        if not 0 <= self.performance_score <= 100:
            raise ValueError("Performance score must be between 0 and 100")

        # Validate nested DTOs
        if self.jira_metrics:
            self.jira_metrics.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonMetricsDTO":
        """Create PersonMetricsDTO from dictionary."""
        # Convert nested Jira metrics
        if "jira_metrics" in data and data["jira_metrics"]:
            if isinstance(data["jira_metrics"], dict):
                data["jira_metrics"] = JiraMetricsDTO.from_dict(data["jira_metrics"])

        return super().from_dict(data)


@dataclass
class ComparisonDTO(BaseDTO):
    """Data Transfer Object for team comparison data."""

    teams: Dict[str, TeamMetricsDTO] = field(default_factory=dict)
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    last_updated: Optional[str] = None

    def validate(self) -> None:
        """Validate comparison data."""
        if not self.teams:
            raise ValueError("Comparison must include at least one team")

        # Validate each team's metrics
        for team_name, team_metrics in self.teams.items():
            if not isinstance(team_metrics, TeamMetricsDTO):
                raise ValueError(f"Team {team_name} metrics must be TeamMetricsDTO")
            team_metrics.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonDTO":
        """Create ComparisonDTO from dictionary."""
        # Convert nested team metrics
        if "teams" in data and data["teams"]:
            teams_dict = {}
            for team_name, team_data in data["teams"].items():
                if isinstance(team_data, dict):
                    teams_dict[team_name] = TeamMetricsDTO.from_dict(team_data)
                else:
                    teams_dict[team_name] = team_data
            data["teams"] = teams_dict

        return super().from_dict(data)


@dataclass
class CacheMetadataDTO(BaseDTO):
    """Data Transfer Object for cache metadata."""

    timestamp: str
    date_range: str
    environment: str
    teams_count: int
    persons_count: int
    collection_duration_seconds: Optional[float] = None

    def validate(self) -> None:
        """Validate cache metadata."""
        if self.teams_count < 0:
            raise ValueError("Teams count cannot be negative")
        if self.persons_count < 0:
            raise ValueError("Persons count cannot be negative")
        if self.collection_duration_seconds is not None and self.collection_duration_seconds < 0:
            raise ValueError("Collection duration cannot be negative")
