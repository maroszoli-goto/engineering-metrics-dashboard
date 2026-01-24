#!/usr/bin/env python3
"""
Config Validation Tool - Validates config.yaml before running collection

Usage:
    python validate_config.py
    python validate_config.py --config path/to/config.yaml
"""

import argparse
import sys
from pathlib import Path

import yaml


def validate_config(config_path="config/config.yaml", environment=None):
    """Validate configuration file

    Args:
        config_path: Path to config.yaml file
        environment: Optional environment to validate specifically (e.g., "prod", "uat")
    """
    errors = []
    warnings = []

    # Check file exists
    config_file = Path(config_path)
    if not config_file.exists():
        errors.append(f"Config file not found: {config_path}")
        return errors, warnings

    # Parse YAML
    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML: {e}")
        return errors, warnings

    # Validate structure
    if not isinstance(config, dict):
        errors.append("Config must be a dictionary")
        return errors, warnings

    # Check required sections
    required_sections = ["github", "jira", "teams"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")

    # Validate GitHub config
    if "github" in config:
        gh = config["github"]

        if "token" not in gh:
            errors.append("GitHub token missing")
        elif not gh["token"]:
            errors.append("GitHub token is empty")
        elif not gh["token"].startswith(("ghp_", "gho_", "ghs_", "github_pat_")):
            warnings.append("GitHub token format unusual (expected ghp_*, gho_*, ghs_*, or github_pat_*)")

        if "organization" not in gh:
            warnings.append("GitHub organization not specified (optional but recommended)")

    # Validate Jira config
    if "jira" in config:
        jira = config["jira"]

        # Check if using multi-environment structure
        if "environments" in jira:
            # Multi-environment config
            environments = jira["environments"]

            if not isinstance(environments, dict):
                errors.append("jira.environments must be a dictionary")
            elif len(environments) == 0:
                errors.append("jira.environments is empty (must have at least one environment)")
            else:
                # Validate each environment
                env_names = list(environments.keys())
                for env_name, env_config in environments.items():
                    # If specific environment requested, only validate that one
                    if environment and env_name != environment:
                        continue

                    if not isinstance(env_config, dict):
                        errors.append(f"jira.environments.{env_name} must be a dictionary")
                        continue

                    # Check required fields
                    if "server" not in env_config:
                        errors.append(f"jira.environments.{env_name}: server URL missing")
                    elif not env_config["server"].startswith(("http://", "https://")):
                        errors.append(f"jira.environments.{env_name}: server must be a valid URL (http:// or https://)")

                    if "username" not in env_config:
                        warnings.append(f"jira.environments.{env_name}: username missing (may be optional)")

                    if "api_token" not in env_config:
                        errors.append(f"jira.environments.{env_name}: API token missing")

                    # Validate time_offset_days if present
                    if "time_offset_days" in env_config:
                        offset = env_config["time_offset_days"]
                        if not isinstance(offset, int):
                            errors.append(
                                f"jira.environments.{env_name}: time_offset_days must be an integer, got {type(offset).__name__}"
                            )
                        elif offset < 0:
                            errors.append(
                                f"jira.environments.{env_name}: time_offset_days must be non-negative, got {offset}"
                            )

            # Check default_environment if present
            if "default_environment" in jira:
                default = jira["default_environment"]
                if default not in environments:
                    errors.append(
                        f"jira.default_environment '{default}' not found in environments. "
                        f"Available: {list(environments.keys())}"
                    )
        else:
            # Legacy single-environment config
            if "server" not in jira:
                errors.append("Jira server URL missing")
            elif not jira["server"].startswith(("http://", "https://")):
                errors.append("Jira server must be a valid URL (http:// or https://)")

            if "username" not in jira:
                warnings.append("Jira username missing (may be optional depending on auth method)")

            if "api_token" not in jira:
                errors.append("Jira API token missing")

    # Validate teams
    if "teams" in config:
        teams = config["teams"]

        if not isinstance(teams, list):
            errors.append("'teams' must be a list")
        elif len(teams) == 0:
            errors.append("No teams configured")
        else:
            team_names = set()

            for i, team in enumerate(teams):
                if not isinstance(team, dict):
                    errors.append(f"Team {i+1} must be a dictionary")
                    continue

                # Check required fields
                if "name" not in team:
                    errors.append(f"Team {i+1} missing 'name'")
                else:
                    name = team["name"]
                    if name in team_names:
                        errors.append(f"Duplicate team name: {name}")
                    team_names.add(name)

                if "members" not in team:
                    errors.append(f"Team '{team.get('name', i+1)}' missing 'members'")
                elif not isinstance(team["members"], list):
                    errors.append(f"Team '{team.get('name', i+1)}' members must be a list")
                elif len(team["members"]) == 0:
                    warnings.append(f"Team '{team.get('name', i+1)}' has no members")
                else:
                    # Validate members
                    for j, member in enumerate(team["members"]):
                        if not isinstance(member, dict):
                            errors.append(f"Team '{team.get('name', i+1)}' member {j+1} must be a dictionary")
                            continue

                        if "name" not in member:
                            errors.append(f"Team '{team.get('name', i+1)}' member {j+1} missing 'name'")

                        if "github" not in member:
                            errors.append(
                                f"Team '{team.get('name', i+1)}' member '{member.get('name', j+1)}' missing 'github'"
                            )

                        if "jira" not in member:
                            warnings.append(
                                f"Team '{team.get('name', i+1)}' member '{member.get('name', j+1)}' missing 'jira' (optional but recommended)"
                            )

                # Validate Jira filters if present
                if "jira" in team and "filters" in team["jira"]:
                    filters = team["jira"]["filters"]
                    if not isinstance(filters, dict):
                        errors.append(f"Team '{team.get('name', i+1)}' jira.filters must be a dictionary")
                    else:
                        # Check if using multi-environment structure
                        is_multi_env = any(isinstance(v, dict) for v in filters.values())

                        if is_multi_env:
                            # New format: team.jira.filters.{env}.{filter_name}
                            # Check if Jira config has environments
                            if "jira" in config and "environments" in config["jira"]:
                                jira_envs = set(config["jira"]["environments"].keys())
                                team_envs = set(filters.keys())

                                # Warn if team has filters for environments that don't exist
                                extra_envs = team_envs - jira_envs
                                if extra_envs:
                                    warnings.append(
                                        f"Team '{team.get('name', i+1)}' has filters for unknown environments: {extra_envs}"
                                    )

                                # Warn if team missing filters for configured environments
                                missing_envs = jira_envs - team_envs
                                if missing_envs:
                                    warnings.append(
                                        f"Team '{team.get('name', i+1)}' missing filters for environments: {missing_envs}"
                                    )

                                # Validate filter IDs in each environment
                                for env_name, env_filters in filters.items():
                                    # If specific environment requested, only validate that one
                                    if environment and env_name != environment:
                                        continue

                                    if not isinstance(env_filters, dict):
                                        errors.append(
                                            f"Team '{team.get('name', i+1)}' jira.filters.{env_name} must be a dictionary"
                                        )
                                        continue

                                    for filter_name, filter_id in env_filters.items():
                                        if not isinstance(filter_id, int):
                                            errors.append(
                                                f"Team '{team.get('name', i+1)}' filter '{env_name}.{filter_name}' must be an integer, got {type(filter_id).__name__}"
                                            )
                            else:
                                warnings.append(
                                    f"Team '{team.get('name', i+1)}' uses multi-environment filters but jira.environments not configured"
                                )
                        else:
                            # Legacy format: flat filter IDs
                            for filter_name, filter_id in filters.items():
                                if not isinstance(filter_id, int):
                                    errors.append(
                                        f"Team '{team.get('name', i+1)}' filter '{filter_name}' must be an integer, got {type(filter_id).__name__}"
                                    )

    # Validate dashboard config
    if "dashboard" in config:
        dashboard = config["dashboard"]

        if "port" in dashboard:
            port = dashboard["port"]
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Dashboard port must be between 1 and 65535, got {port}")

        if "cache_duration_minutes" in dashboard:
            duration = dashboard["cache_duration_minutes"]
            if not isinstance(duration, (int, float)) or duration <= 0:
                errors.append(f"Cache duration must be positive, got {duration}")

        if "jira_timeout_seconds" in dashboard:
            timeout = dashboard["jira_timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append(f"Jira timeout must be positive, got {timeout}")

    # Validate performance weights
    if "performance_weights" in config:
        weights = config["performance_weights"]

        if not isinstance(weights, dict):
            errors.append("performance_weights must be a dictionary")
        else:
            required_weight_keys = ["prs", "reviews", "commits", "cycle_time", "jira_completed", "merge_rate"]

            # Check all required keys present
            for key in required_weight_keys:
                if key not in weights:
                    errors.append(f"Missing weight for '{key}' in performance_weights")

            # Validate weight values
            total = 0
            for metric, weight in weights.items():
                if not isinstance(weight, (int, float)):
                    errors.append(f"Weight for '{metric}' must be a number, got {type(weight).__name__}")
                elif not (0.0 <= weight <= 1.0):
                    errors.append(f"Weight for '{metric}' must be between 0.0 and 1.0, got {weight}")
                else:
                    total += weight

            # Check sum (only if all weights are valid numbers)
            if not any("must be a number" in err for err in errors):
                if not (0.999 <= total <= 1.001):
                    errors.append(f"Performance weights must sum to 1.0, got {total:.4f}")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate Team Metrics config file")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Validate specific environment (e.g., prod, uat). If not specified, validates all environments.",
    )
    args = parser.parse_args()

    print(f"Validating config: {args.config}")
    if args.env:
        print(f"Environment: {args.env}")
    print("-" * 50)

    errors, warnings = validate_config(args.config, environment=args.env)

    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")

    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  • {error}")
        print(f"\n❌ Validation failed with {len(errors)} error(s)")
        sys.exit(1)
    else:
        print("\n✅ Config validation passed!")
        if warnings:
            print(f"   ({len(warnings)} warning(s))")
        sys.exit(0)


if __name__ == "__main__":
    main()
