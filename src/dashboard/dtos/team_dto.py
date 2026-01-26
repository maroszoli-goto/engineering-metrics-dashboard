"""Data Transfer Objects for team and member data."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseDTO


@dataclass
class TeamMemberDTO(BaseDTO):
    """Data Transfer Object for team member information."""

    name: str
    github_username: str
    jira_username: Optional[str] = None
    email: Optional[str] = None

    def validate(self) -> None:
        """Validate team member data."""
        if not self.name or not self.name.strip():
            raise ValueError("Member name cannot be empty")
        if not self.github_username or not self.github_username.strip():
            raise ValueError("GitHub username cannot be empty")


@dataclass
class TeamDTO(BaseDTO):
    """Data Transfer Object for team configuration."""

    name: str
    members: List[TeamMemberDTO] = field(default_factory=list)
    jira_filters: Optional[Dict[str, int]] = None
    description: Optional[str] = None

    def validate(self) -> None:
        """Validate team data."""
        if not self.name or not self.name.strip():
            raise ValueError("Team name cannot be empty")
        if not self.members:
            raise ValueError("Team must have at least one member")

        # Validate each member
        for member in self.members:
            member.validate()

        # Check for duplicate GitHub usernames
        github_usernames = [m.github_username for m in self.members]
        if len(github_usernames) != len(set(github_usernames)):
            raise ValueError("Duplicate GitHub usernames found in team")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamDTO":
        """Create TeamDTO from dictionary."""
        # Convert nested members
        if "members" in data and data["members"]:
            members_list = []
            for member_data in data["members"]:
                if isinstance(member_data, dict):
                    members_list.append(TeamMemberDTO.from_dict(member_data))
                else:
                    members_list.append(member_data)
            data["members"] = members_list

        return super().from_dict(data)


@dataclass
class TeamSummaryDTO(BaseDTO):
    """Data Transfer Object for team summary (lightweight team info)."""

    name: str
    member_count: int
    has_jira_filters: bool = False
    description: Optional[str] = None

    def validate(self) -> None:
        """Validate team summary."""
        if not self.name or not self.name.strip():
            raise ValueError("Team name cannot be empty")
        if self.member_count <= 0:
            raise ValueError("Member count must be positive")
