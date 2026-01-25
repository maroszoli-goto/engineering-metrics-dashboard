"""Cache service for dashboard metrics

Manages loading, validation, and discovery of cached metrics data.
"""

import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from werkzeug.security import safe_join

from src.utils.date_ranges import get_cache_filename, get_preset_ranges


class CacheService:
    """Service for managing metrics cache files

    Handles loading cached metrics from pickle files, validating cache freshness,
    and discovering available date ranges.
    """

    def __init__(self, data_dir: Path, logger=None):
        """Initialize cache service

        Args:
            data_dir: Directory containing cache files (e.g., project_root/data)
            logger: Optional logger instance for logging cache operations
        """
        self.data_dir = data_dir
        self.logger = logger

    def load_cache(self, range_key: str = "90d", environment: str = "prod") -> Optional[Dict[str, Any]]:
        """Load cached metrics from file for a specific date range and environment

        Args:
            range_key: Date range key (e.g., '90d', 'Q1-2025')
            environment: Environment name (e.g., 'prod', 'uat')

        Returns:
            Dictionary containing cached metrics data, or None if load failed

        Examples:
            >>> service = CacheService(Path("/path/to/data"))
            >>> cache = service.load_cache("90d", "prod")
            >>> cache is not None
            True
        """
        # Security: Validate range_key and environment to prevent path traversal
        try:
            cache_filename = get_cache_filename(range_key, environment)
        except ValueError as e:
            if self.logger:
                self.logger.warning(f"Invalid range or environment parameter: {e}")
            return None

        # Use werkzeug.safe_join() - CodeQL recognizes this as a sanitizer
        # safe_join returns None if path traversal is detected
        safe_path = safe_join(str(self.data_dir), cache_filename)

        if safe_path is None:
            if self.logger:
                self.logger.warning(f"Path traversal detected in: {cache_filename}")
            return None

        # Convert to Path object for convenience
        cache_file_path = Path(safe_path)

        # Fallback to legacy filename for backward compatibility (only for prod)
        if not cache_file_path.exists() and environment == "prod":
            try:
                legacy_filename = get_cache_filename(range_key, "prod").replace("_prod.pkl", ".pkl")
                legacy_path = safe_join(str(self.data_dir), legacy_filename)
                if legacy_path:
                    cache_file_path = Path(legacy_path)
                    if self.logger:
                        self.logger.info(f"Falling back to legacy cache file: {legacy_filename}")
            except Exception:
                pass  # Fallback failed, continue with original path

        if not cache_file_path.exists():
            return None

        try:
            # Open using werkzeug-sanitized path (CodeQL trusts this)
            with open(cache_file_path, "rb") as f:
                cache_data = pickle.load(f)

                # Validate environment matches
                cached_env = cache_data.get("environment", "prod")
                if cached_env != environment:
                    if self.logger:
                        self.logger.warning(
                            f"Cache environment mismatch: requested '{environment}', " f"cache contains '{cached_env}'"
                        )

                # Build result dictionary with metadata
                result = {
                    "data": cache_data.get("data") or cache_data,  # Handle both old and new formats
                    "timestamp": cache_data.get("timestamp"),
                    "range_key": range_key,
                    "date_range": cache_data.get("date_range", {}),
                    "environment": cache_data.get("environment", "prod"),
                    "time_offset_days": cache_data.get("time_offset_days", 0),
                    "jira_server": cache_data.get("jira_server", ""),
                }

                if self.logger:
                    self.logger.info(f"Loaded cached metrics from {cache_file_path}")
                    self.logger.info(f"Cache timestamp: {result['timestamp']}")
                    self.logger.info(f"Environment: {result['environment']}")
                    if result["date_range"]:
                        self.logger.info(f"Date range: {result['date_range'].get('description')}")

                return result

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load cache: {e}")
            return None

    def should_refresh(self, cache_data: Optional[Dict], ttl_minutes: int = 60) -> bool:
        """Check if cache should be refreshed based on age

        Args:
            cache_data: Current cache data dictionary (must contain 'timestamp' key)
            ttl_minutes: Time-to-live in minutes (default: 60)

        Returns:
            True if cache should be refreshed (missing or expired)

        Examples:
            >>> from datetime import datetime, timedelta
            >>> service = CacheService(Path("/path/to/data"))
            >>> old_cache = {"timestamp": datetime.now() - timedelta(hours=2)}
            >>> service.should_refresh(old_cache, ttl_minutes=60)
            True
            >>> recent_cache = {"timestamp": datetime.now()}
            >>> service.should_refresh(recent_cache, ttl_minutes=60)
            False
        """
        if cache_data is None or cache_data.get("timestamp") is None:
            return True

        elapsed = (datetime.now() - cache_data["timestamp"]).total_seconds() / 60
        return elapsed > ttl_minutes

    def get_available_ranges(self) -> List[Tuple[str, str, bool]]:
        """Get list of available cached date ranges

        Scans the data directory for cached metrics files and returns
        information about available date ranges.

        Returns:
            List of (range_key, description, file_exists) tuples
            Example: [('90d', 'Last 90 days', True), ('Q1-2025', 'Q1 2025', True)]

        Examples:
            >>> service = CacheService(Path("/path/to/data"))
            >>> ranges = service.get_available_ranges()
            >>> all(len(r) == 3 for r in ranges)  # Each tuple has 3 elements
            True
        """
        available = []

        # Check preset ranges
        for range_spec, description in get_preset_ranges():
            try:
                cache_filename = get_cache_filename(range_spec)
                cache_file = self.data_dir / cache_filename
                if cache_file.exists():
                    # Try to load date range info from cache
                    try:
                        with open(cache_file, "rb") as f:
                            cache_data = pickle.load(f)
                            if "date_range" in cache_data:
                                description = cache_data["date_range"].get("description", description)
                    except:
                        pass
                    available.append((range_spec, description, True))
            except ValueError:
                # Invalid range_spec, skip it
                if self.logger:
                    self.logger.warning(f"Skipping invalid preset range: {range_spec}")
                continue

        # Check for other cached files (quarters, years, custom)
        if self.data_dir.exists():
            for cache_file in self.data_dir.glob("metrics_cache_*.pkl"):
                range_key = cache_file.stem.replace("metrics_cache_", "")
                if range_key not in [r[0] for r in available]:
                    # Validate range_key before using it
                    try:
                        # This will raise ValueError if invalid
                        _ = get_cache_filename(range_key)
                        # Try to get description from cache
                        try:
                            with open(cache_file, "rb") as f:
                                cache_data = pickle.load(f)
                                if "date_range" in cache_data:
                                    description = cache_data["date_range"].get("description", range_key)
                                else:
                                    description = range_key
                                available.append((range_key, description, True))
                        except:
                            available.append((range_key, range_key, True))
                    except ValueError:
                        # Invalid range_key in filename, skip it
                        if self.logger:
                            self.logger.warning(f"Skipping invalid cached range file: {cache_file.name}")
                        continue

        return available
