"""Tests for Data Transfer Objects."""

import json
from datetime import datetime

import pytest

from src.dashboard.dtos import (
    BaseDTO,
    CacheMetadataDTO,
    ComparisonDTO,
    DORAMetricsDTO,
    JiraMetricsDTO,
    PersonMetricsDTO,
    TeamDTO,
    TeamMemberDTO,
    TeamMetricsDTO,
    TeamSummaryDTO,
)


class TestBaseDTO:
    """Tests for BaseDTO class."""

    def test_to_dict(self):
        """Test converting DTO to dictionary."""
        dto = DORAMetricsDTO(
            deployment_frequency=1.5,
            lead_time_hours=48.0,
            change_failure_rate=10.0,
            mttr_hours=2.5,
            deployment_frequency_level="High",
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        result = dto.to_dict()
        assert isinstance(result, dict)
        assert result["deployment_frequency"] == 1.5
        assert result["lead_time_hours"] == 48.0

    def test_from_dict(self):
        """Test creating DTO from dictionary."""
        data = {
            "deployment_frequency": 1.5,
            "lead_time_hours": 48.0,
            "change_failure_rate": 10.0,
            "mttr_hours": 2.5,
            "deployment_frequency_level": "High",
            "lead_time_level": "Medium",
            "cfr_level": "Elite",
            "mttr_level": "Elite",
        }

        dto = DORAMetricsDTO.from_dict(data)
        assert dto.deployment_frequency == 1.5
        assert dto.lead_time_hours == 48.0
        assert dto.cfr_level == "Elite"

    def test_from_dict_with_extra_fields(self):
        """Test from_dict ignores extra fields."""
        data = {
            "deployment_frequency": 1.5,
            "lead_time_hours": 48.0,
            "change_failure_rate": 10.0,
            "mttr_hours": 2.5,
            "deployment_frequency_level": "High",
            "lead_time_level": "Medium",
            "cfr_level": "Elite",
            "mttr_level": "Elite",
            "extra_field": "should_be_ignored",
        }

        dto = DORAMetricsDTO.from_dict(data)
        assert dto.deployment_frequency == 1.5
        assert not hasattr(dto, "extra_field")

    def test_from_dict_missing_required_field(self):
        """Test from_dict raises error for missing required fields."""
        data = {
            "deployment_frequency": 1.5,
            # Missing other required fields
        }

        with pytest.raises(ValueError, match="Failed to create"):
            DORAMetricsDTO.from_dict(data)

    def test_to_json(self):
        """Test converting DTO to JSON."""
        dto = DORAMetricsDTO(
            deployment_frequency=1.5,
            lead_time_hours=48.0,
            change_failure_rate=10.0,
            mttr_hours=2.5,
            deployment_frequency_level="High",
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        json_str = dto.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["deployment_frequency"] == 1.5

    def test_from_json(self):
        """Test creating DTO from JSON."""
        json_str = json.dumps(
            {
                "deployment_frequency": 1.5,
                "lead_time_hours": 48.0,
                "change_failure_rate": 10.0,
                "mttr_hours": 2.5,
                "deployment_frequency_level": "High",
                "lead_time_level": "Medium",
                "cfr_level": "Elite",
                "mttr_level": "Elite",
            }
        )

        dto = DORAMetricsDTO.from_json(json_str)
        assert dto.deployment_frequency == 1.5
        assert dto.cfr_level == "Elite"

    def test_from_json_invalid(self):
        """Test from_json raises error for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            DORAMetricsDTO.from_json("not valid json")


class TestDORAMetricsDTO:
    """Tests for DORAMetricsDTO."""

    def test_validate_success(self):
        """Test validation passes for valid metrics."""
        dto = DORAMetricsDTO(
            deployment_frequency=1.5,
            lead_time_hours=48.0,
            change_failure_rate=10.0,
            mttr_hours=2.5,
            deployment_frequency_level="High",
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        dto.validate()  # Should not raise

    def test_validate_negative_deployment_frequency(self):
        """Test validation fails for negative deployment frequency."""
        dto = DORAMetricsDTO(
            deployment_frequency=-1.0,
            lead_time_hours=48.0,
            change_failure_rate=10.0,
            mttr_hours=2.5,
            deployment_frequency_level="High",
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        with pytest.raises(ValueError, match="cannot be negative"):
            dto.validate()

    def test_validate_invalid_cfr(self):
        """Test validation fails for invalid CFR."""
        dto = DORAMetricsDTO(
            deployment_frequency=1.5,
            lead_time_hours=48.0,
            change_failure_rate=150.0,  # > 100
            mttr_hours=2.5,
            deployment_frequency_level="High",
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            dto.validate()

    def test_validate_invalid_level(self):
        """Test validation fails for invalid performance level."""
        dto = DORAMetricsDTO(
            deployment_frequency=1.5,
            lead_time_hours=48.0,
            change_failure_rate=10.0,
            mttr_hours=2.5,
            deployment_frequency_level="Invalid",  # Not a valid level
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        with pytest.raises(ValueError, match="must be one of"):
            dto.validate()


class TestJiraMetricsDTO:
    """Tests for JiraMetricsDTO."""

    def test_create_with_defaults(self):
        """Test creating JiraMetricsDTO with default values."""
        dto = JiraMetricsDTO()

        assert dto.completed_issues == 0
        assert dto.bugs_created == 0
        assert dto.wip_count == 0

    def test_validate_success(self):
        """Test validation passes for valid metrics."""
        dto = JiraMetricsDTO(completed_issues=10, bugs_created=2, bugs_resolved=1, wip_count=5)

        dto.validate()  # Should not raise

    def test_validate_negative_values(self):
        """Test validation fails for negative values."""
        dto = JiraMetricsDTO(bugs_created=-1)

        with pytest.raises(ValueError, match="cannot be negative"):
            dto.validate()


class TestTeamMetricsDTO:
    """Tests for TeamMetricsDTO."""

    def test_create_basic(self):
        """Test creating basic team metrics."""
        dto = TeamMetricsDTO(
            name="Backend Team", member_count=5, total_prs=100, merged_prs=90, merge_rate=90.0, performance_score=85.5
        )

        assert dto.name == "Backend Team"
        assert dto.member_count == 5
        assert dto.performance_score == 85.5

    def test_validate_success(self):
        """Test validation passes for valid metrics."""
        dto = TeamMetricsDTO(
            name="Backend Team", member_count=5, total_prs=100, merged_prs=90, merge_rate=90.0, performance_score=85.5
        )

        dto.validate()  # Should not raise

    def test_validate_invalid_member_count(self):
        """Test validation fails for zero member count."""
        dto = TeamMetricsDTO(name="Backend Team", member_count=0)

        with pytest.raises(ValueError, match="must be positive"):
            dto.validate()

    def test_validate_merged_exceeds_total(self):
        """Test validation fails when merged PRs exceed total."""
        dto = TeamMetricsDTO(name="Backend Team", member_count=5, total_prs=100, merged_prs=110)  # More than total

        with pytest.raises(ValueError, match="cannot exceed total"):
            dto.validate()

    def test_validate_invalid_performance_score(self):
        """Test validation fails for invalid performance score."""
        dto = TeamMetricsDTO(name="Backend Team", member_count=5, performance_score=150.0)  # > 100

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            dto.validate()

    def test_with_nested_dtos(self):
        """Test team metrics with nested DORA and Jira metrics."""
        dora = DORAMetricsDTO(
            deployment_frequency=1.5,
            lead_time_hours=48.0,
            change_failure_rate=10.0,
            mttr_hours=2.5,
            deployment_frequency_level="High",
            lead_time_level="Medium",
            cfr_level="Elite",
            mttr_level="Elite",
        )

        jira = JiraMetricsDTO(completed_issues=50, bugs_created=5, wip_count=10)

        dto = TeamMetricsDTO(name="Backend Team", member_count=5, dora_metrics=dora, jira_metrics=jira)

        assert dto.dora_metrics.deployment_frequency == 1.5
        assert dto.jira_metrics.completed_issues == 50

    def test_from_dict_with_nested_dicts(self):
        """Test creating TeamMetricsDTO from dict with nested dicts."""
        data = {
            "name": "Backend Team",
            "member_count": 5,
            "total_prs": 100,
            "dora_metrics": {
                "deployment_frequency": 1.5,
                "lead_time_hours": 48.0,
                "change_failure_rate": 10.0,
                "mttr_hours": 2.5,
                "deployment_frequency_level": "High",
                "lead_time_level": "Medium",
                "cfr_level": "Elite",
                "mttr_level": "Elite",
            },
            "jira_metrics": {"completed_issues": 50, "bugs_created": 5},
        }

        dto = TeamMetricsDTO.from_dict(data)
        assert dto.name == "Backend Team"
        assert isinstance(dto.dora_metrics, DORAMetricsDTO)
        assert dto.dora_metrics.deployment_frequency == 1.5
        assert isinstance(dto.jira_metrics, JiraMetricsDTO)
        assert dto.jira_metrics.completed_issues == 50


class TestPersonMetricsDTO:
    """Tests for PersonMetricsDTO."""

    def test_create_basic(self):
        """Test creating basic person metrics."""
        dto = PersonMetricsDTO(
            name="John Doe",
            github_username="johndoe",
            jira_username="jdoe",
            prs_opened=20,
            prs_merged=18,
            reviews_given=30,
            commits=100,
        )

        assert dto.name == "John Doe"
        assert dto.github_username == "johndoe"
        assert dto.prs_opened == 20

    def test_validate_success(self):
        """Test validation passes for valid metrics."""
        dto = PersonMetricsDTO(
            name="John Doe",
            github_username="johndoe",
            prs_opened=20,
            prs_merged=18,
            merge_rate=90.0,
            performance_score=80.0,
        )

        dto.validate()  # Should not raise

    def test_validate_merged_exceeds_opened(self):
        """Test validation fails when merged exceeds opened."""
        dto = PersonMetricsDTO(
            name="John Doe", github_username="johndoe", prs_opened=20, prs_merged=25  # More than opened
        )

        with pytest.raises(ValueError, match="cannot exceed"):
            dto.validate()


class TestComparisonDTO:
    """Tests for ComparisonDTO."""

    def test_create_with_teams(self):
        """Test creating comparison DTO with teams."""
        team1 = TeamMetricsDTO(name="Team A", member_count=5)
        team2 = TeamMetricsDTO(name="Team B", member_count=3)

        dto = ComparisonDTO(
            teams={"Team A": team1, "Team B": team2}, date_range_start="2026-01-01", date_range_end="2026-01-31"
        )

        assert len(dto.teams) == 2
        assert "Team A" in dto.teams
        assert dto.date_range_start == "2026-01-01"

    def test_validate_success(self):
        """Test validation passes for valid comparison."""
        team1 = TeamMetricsDTO(name="Team A", member_count=5)
        dto = ComparisonDTO(teams={"Team A": team1})

        dto.validate()  # Should not raise

    def test_validate_empty_teams(self):
        """Test validation fails for empty teams."""
        dto = ComparisonDTO(teams={})

        with pytest.raises(ValueError, match="at least one team"):
            dto.validate()

    def test_from_dict_with_nested_teams(self):
        """Test creating ComparisonDTO from dict with nested team dicts."""
        data = {
            "teams": {
                "Team A": {"name": "Team A", "member_count": 5, "total_prs": 100},
                "Team B": {"name": "Team B", "member_count": 3, "total_prs": 50},
            },
            "date_range_start": "2026-01-01",
        }

        dto = ComparisonDTO.from_dict(data)
        assert len(dto.teams) == 2
        assert isinstance(dto.teams["Team A"], TeamMetricsDTO)
        assert dto.teams["Team A"].member_count == 5


class TestTeamMemberDTO:
    """Tests for TeamMemberDTO."""

    def test_create_basic(self):
        """Test creating team member."""
        dto = TeamMemberDTO(name="John Doe", github_username="johndoe", jira_username="jdoe")

        assert dto.name == "John Doe"
        assert dto.github_username == "johndoe"

    def test_validate_success(self):
        """Test validation passes for valid member."""
        dto = TeamMemberDTO(name="John Doe", github_username="johndoe")

        dto.validate()  # Should not raise

    def test_validate_empty_name(self):
        """Test validation fails for empty name."""
        dto = TeamMemberDTO(name="", github_username="johndoe")

        with pytest.raises(ValueError, match="cannot be empty"):
            dto.validate()

    def test_validate_empty_github_username(self):
        """Test validation fails for empty GitHub username."""
        dto = TeamMemberDTO(name="John Doe", github_username="")

        with pytest.raises(ValueError, match="cannot be empty"):
            dto.validate()


class TestTeamDTO:
    """Tests for TeamDTO."""

    def test_create_with_members(self):
        """Test creating team with members."""
        member1 = TeamMemberDTO(name="John Doe", github_username="johndoe")
        member2 = TeamMemberDTO(name="Jane Smith", github_username="janesmith")

        dto = TeamDTO(name="Backend Team", members=[member1, member2], jira_filters={"wip": 12345, "bugs": 12346})

        assert dto.name == "Backend Team"
        assert len(dto.members) == 2
        assert dto.jira_filters["wip"] == 12345

    def test_validate_success(self):
        """Test validation passes for valid team."""
        member = TeamMemberDTO(name="John Doe", github_username="johndoe")
        dto = TeamDTO(name="Backend Team", members=[member])

        dto.validate()  # Should not raise

    def test_validate_empty_name(self):
        """Test validation fails for empty team name."""
        member = TeamMemberDTO(name="John Doe", github_username="johndoe")
        dto = TeamDTO(name="", members=[member])

        with pytest.raises(ValueError, match="cannot be empty"):
            dto.validate()

    def test_validate_no_members(self):
        """Test validation fails for team with no members."""
        dto = TeamDTO(name="Backend Team", members=[])

        with pytest.raises(ValueError, match="at least one member"):
            dto.validate()

    def test_validate_duplicate_github_usernames(self):
        """Test validation fails for duplicate GitHub usernames."""
        member1 = TeamMemberDTO(name="John Doe", github_username="johndoe")
        member2 = TeamMemberDTO(name="John D.", github_username="johndoe")  # Same username

        dto = TeamDTO(name="Backend Team", members=[member1, member2])

        with pytest.raises(ValueError, match="Duplicate GitHub usernames"):
            dto.validate()

    def test_from_dict_with_nested_members(self):
        """Test creating TeamDTO from dict with nested member dicts."""
        data = {
            "name": "Backend Team",
            "members": [
                {"name": "John Doe", "github_username": "johndoe"},
                {"name": "Jane Smith", "github_username": "janesmith"},
            ],
            "jira_filters": {"wip": 12345},
        }

        dto = TeamDTO.from_dict(data)
        assert dto.name == "Backend Team"
        assert len(dto.members) == 2
        assert isinstance(dto.members[0], TeamMemberDTO)
        assert dto.members[0].name == "John Doe"


class TestCacheMetadataDTO:
    """Tests for CacheMetadataDTO."""

    def test_create_basic(self):
        """Test creating cache metadata."""
        dto = CacheMetadataDTO(
            timestamp="2026-01-26T10:00:00",
            date_range="90d",
            environment="prod",
            teams_count=5,
            persons_count=25,
            collection_duration_seconds=120.5,
        )

        assert dto.timestamp == "2026-01-26T10:00:00"
        assert dto.date_range == "90d"
        assert dto.teams_count == 5

    def test_validate_success(self):
        """Test validation passes for valid metadata."""
        dto = CacheMetadataDTO(
            timestamp="2026-01-26T10:00:00", date_range="90d", environment="prod", teams_count=5, persons_count=25
        )

        dto.validate()  # Should not raise

    def test_validate_negative_counts(self):
        """Test validation fails for negative counts."""
        dto = CacheMetadataDTO(
            timestamp="2026-01-26T10:00:00", date_range="90d", environment="prod", teams_count=-1, persons_count=25
        )

        with pytest.raises(ValueError, match="cannot be negative"):
            dto.validate()
