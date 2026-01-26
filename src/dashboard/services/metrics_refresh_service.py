"""Metrics refresh service for dashboard

Orchestrates collection of GitHub and Jira metrics for teams.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.collectors.github_graphql_collector import GitHubGraphQLCollector
from src.collectors.jira_collector import JiraCollector
from src.config import Config
from src.models.metrics import MetricsCalculator


class MetricsRefreshService:
    """Service for refreshing metrics data

    Orchestrates GitHub and Jira data collection, metrics calculation,
    and team comparison generation.
    """

    def __init__(self, config: Config, logger=None):
        """Initialize metrics refresh service

        Args:
            config: Application configuration
            logger: Optional logger instance for logging collection progress
        """
        self.config = config
        self.logger = logger

    def refresh_metrics(self) -> Optional[Dict[str, Any]]:
        """Collect and calculate metrics using GraphQL API

        Collects GitHub and Jira data for all configured teams,
        calculates metrics, and generates team comparison data.

        Returns:
            Dictionary containing teams metrics, comparison data, and timestamp.
            Returns None if no teams are configured.

        Example structure:
            {
                "teams": {
                    "Native Team": {...},
                    "WebTC Team": {...}
                },
                "comparison": {...},
                "timestamp": datetime(...)
            }
        """
        teams = self.config.teams

        if not teams:
            if self.logger:
                self.logger.warning("No teams configured. Please configure teams in config.yaml")
            return None

        if self.logger:
            self.logger.info(f"Refreshing metrics for {len(teams)} team(s) using GraphQL API...", emoji="🔄")

        # Connect to Jira
        jira_config = self.config.jira_config
        jira_collector = None

        if jira_config.get("server"):
            try:
                jira_collector = JiraCollector(
                    server=jira_config["server"],
                    username=jira_config["username"],
                    api_token=jira_config["api_token"],
                    project_keys=jira_config.get("project_keys", []),
                    days_back=self.config.days_back,
                    verify_ssl=False,
                    timeout=self.config.dashboard_config.get("jira_timeout_seconds", 120),
                )
                if self.logger:
                    self.logger.success("Connected to Jira")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Could not connect to Jira: {e}")

        # Collect data for each team
        team_metrics = {}
        all_github_data: Dict[str, List] = {"pull_requests": [], "reviews": [], "commits": [], "deployments": []}

        for team in teams:
            team_name = team.get("name")
            if self.logger:
                self.logger.info("")
                self.logger.info(f"Collecting {team_name} Team...", emoji="📊")

            github_members = team.get("github", {}).get("members", [])
            filter_ids = team.get("jira", {}).get("filters", {})

            # Collect GitHub metrics using GraphQL
            github_collector = GitHubGraphQLCollector(
                token=self.config.github_token,
                organization=self.config.github_organization,
                teams=[team.get("github", {}).get("team_slug")] if team.get("github", {}).get("team_slug") else [],
                team_members=github_members,
                days_back=self.config.days_back,
            )

            team_github_data = github_collector.collect_all_metrics()

            all_github_data["pull_requests"].extend(team_github_data["pull_requests"])
            all_github_data["reviews"].extend(team_github_data["reviews"])
            all_github_data["commits"].extend(team_github_data["commits"])

            if self.logger:
                self.logger.info(f"- PRs: {len(team_github_data['pull_requests'])}", indent=1)
                self.logger.info(f"- Reviews: {len(team_github_data['reviews'])}", indent=1)
                self.logger.info(f"- Commits: {len(team_github_data['commits'])}", indent=1)

            # Collect Jira filter metrics
            jira_filter_results = {}
            if jira_collector and filter_ids:
                if self.logger:
                    self.logger.info(f"Collecting Jira filters for {team_name}...", emoji="📊")
                jira_filter_results = jira_collector.collect_team_filters(filter_ids)

            # Calculate team metrics
            team_dfs = {
                "pull_requests": pd.DataFrame(team_github_data["pull_requests"]),
                "reviews": pd.DataFrame(team_github_data["reviews"]),
                "commits": pd.DataFrame(team_github_data["commits"]),
                "deployments": pd.DataFrame(team_github_data["deployments"]),
            }

            # Inject logger into domain model (Application layer responsibility)
            calculator = MetricsCalculator(team_dfs, logger=self.logger)
            team_metrics[team_name] = calculator.calculate_team_metrics(
                team_name=team_name, team_config=team, jira_filter_results=jira_filter_results
            )

        # Calculate team comparison
        all_dfs = {
            "pull_requests": pd.DataFrame(all_github_data["pull_requests"]),
            "reviews": pd.DataFrame(all_github_data["reviews"]),
            "commits": pd.DataFrame(all_github_data["commits"]),
            "deployments": pd.DataFrame(all_github_data["deployments"]),
        }

        # Inject logger for comparison calculation too
        calculator_all = MetricsCalculator(all_dfs, logger=self.logger)
        team_comparison = calculator_all.calculate_team_comparison(team_metrics)

        # Package data
        cache_data = {"teams": team_metrics, "comparison": team_comparison, "timestamp": datetime.now()}

        if self.logger:
            self.logger.info("")
            self.logger.success(f"Metrics refreshed at {cache_data['timestamp']}")

        return cache_data
