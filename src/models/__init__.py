"""Models package for Team Metrics Dashboard.

This package contains the core metrics calculation logic split into focused modules:
- metrics.py: Core MetricsCalculator class (team, person, PR, review metrics)
- dora_metrics.py: DORA (DevOps Research and Assessment) metrics
- jira_metrics.py: Jira integration and processing
- performance_scoring.py: Performance scoring and normalization

The MetricsCalculator class is the main entry point and provides access to all functionality.
"""

from .dora_metrics import DORAMetrics
from .jira_metrics import JiraMetrics

# Main exports for backward compatibility
from .metrics import MetricsCalculator
from .performance_scoring import PerformanceScorer

__all__ = [
    "MetricsCalculator",
    "PerformanceScorer",
    "DORAMetrics",
    "JiraMetrics",
]
