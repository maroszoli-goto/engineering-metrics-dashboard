"""Base Data Transfer Object classes."""

import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T", bound="BaseDTO")


@dataclass
class BaseDTO:
    """Base class for all Data Transfer Objects.

    Provides common utilities for converting between DTOs and dictionaries,
    serialization, and validation.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert DTO to dictionary.

        Returns:
            Dictionary representation of the DTO
        """
        return asdict(self)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create DTO from dictionary.

        Args:
            data: Dictionary containing DTO fields

        Returns:
            Instance of the DTO class

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Get the field names for this dataclass
        field_names = {f.name for f in fields(cls)}

        # Filter data to only include fields that exist in the dataclass
        filtered_data = {k: v for k, v in data.items() if k in field_names}

        try:
            return cls(**filtered_data)
        except TypeError as e:
            raise ValueError(f"Failed to create {cls.__name__} from dict: {e}")

    def to_json(self) -> str:
        """Convert DTO to JSON string.

        Returns:
            JSON representation of the DTO
        """
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """Create DTO from JSON string.

        Args:
            json_str: JSON string containing DTO data

        Returns:
            Instance of the DTO class

        Raises:
            ValueError: If JSON is invalid or fields are missing
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def validate(self) -> None:
        """Validate DTO fields.

        Override this method in subclasses to add custom validation logic.

        Raises:
            ValueError: If validation fails
        """
        pass


@dataclass
class DORAMetricsDTO(BaseDTO):
    """Data Transfer Object for DORA metrics."""

    deployment_frequency: float  # Deployments per week
    lead_time_hours: float  # Hours from commit to production
    change_failure_rate: float  # Percentage (0-100)
    mttr_hours: float  # Mean time to recover in hours
    deployment_frequency_level: str  # Elite/High/Medium/Low
    lead_time_level: str  # Elite/High/Medium/Low
    cfr_level: str  # Elite/High/Medium/Low
    mttr_level: str  # Elite/High/Medium/Low

    def validate(self) -> None:
        """Validate DORA metrics."""
        if self.deployment_frequency < 0:
            raise ValueError("Deployment frequency cannot be negative")
        if self.lead_time_hours < 0:
            raise ValueError("Lead time cannot be negative")
        if not 0 <= self.change_failure_rate <= 100:
            raise ValueError("Change failure rate must be between 0 and 100")
        if self.mttr_hours < 0:
            raise ValueError("MTTR cannot be negative")

        valid_levels = {"Elite", "High", "Medium", "Low", "N/A"}
        for level_field in ["deployment_frequency_level", "lead_time_level", "cfr_level", "mttr_level"]:
            level = getattr(self, level_field)
            if level not in valid_levels:
                raise ValueError(f"{level_field} must be one of {valid_levels}")
