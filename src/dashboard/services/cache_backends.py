"""Cache backend implementations

Provides different storage backends for the enhanced cache service.
"""

import pickle
from pathlib import Path
from typing import Any, Optional

from werkzeug.security import safe_join

from src.utils.date_ranges import get_cache_filename

from .cache_protocols import CacheBackend


class FileBackend:
    """File-based cache backend using pickle

    Stores cache entries as pickle files in a directory.
    Compatible with existing cache file format.
    """

    def __init__(self, data_dir: Path, logger=None):
        """Initialize file backend

        Args:
            data_dir: Directory to store cache files
            logger: Optional logger instance
        """
        self.data_dir = data_dir
        self.logger = logger

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """Load cache entry from file

        Args:
            key: Cache key (e.g., "90d_prod")

        Returns:
            Cached data or None if not found
        """
        try:
            # Parse key format: "{range}_{env}" (e.g., "90d_prod")
            parts = key.split("_", 1)
            if len(parts) == 2:
                range_key, environment = parts
            else:
                range_key = parts[0]
                environment = "prod"

            # Get cache filename
            cache_filename = get_cache_filename(range_key, environment)

            # Use safe_join to prevent path traversal
            safe_path = safe_join(str(self.data_dir), cache_filename)
            if safe_path is None:
                if self.logger:
                    self.logger.warning(f"Path traversal detected in key: {key}")
                return None

            cache_file_path = Path(safe_path)

            # Try legacy filename for backward compatibility (prod only)
            if not cache_file_path.exists() and environment == "prod":
                legacy_filename = cache_filename.replace("_prod.pkl", ".pkl")
                legacy_path = safe_join(str(self.data_dir), legacy_filename)
                if legacy_path:
                    cache_file_path = Path(legacy_path)

            if not cache_file_path.exists():
                return None

            with open(cache_file_path, "rb") as f:
                return pickle.load(f)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load cache from file: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Save cache entry to file

        Args:
            key: Cache key (e.g., "90d_prod")
            value: Data to cache
            ttl_seconds: Ignored for file backend (no expiration)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse key format
            parts = key.split("_", 1)
            if len(parts) == 2:
                range_key, environment = parts
            else:
                range_key = parts[0]
                environment = "prod"

            # Get cache filename
            cache_filename = get_cache_filename(range_key, environment)

            # Use safe_join to prevent path traversal
            safe_path = safe_join(str(self.data_dir), cache_filename)
            if safe_path is None:
                if self.logger:
                    self.logger.warning(f"Path traversal detected in key: {key}")
                return False

            cache_file_path = Path(safe_path)

            # Ensure parent directory exists
            cache_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(cache_file_path, "wb") as f:
                pickle.dump(value, f)

            if self.logger:
                self.logger.debug(f"Saved cache to file: {cache_file_path}")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save cache to file: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete cache file

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found or error
        """
        try:
            # Parse key format
            parts = key.split("_", 1)
            if len(parts) == 2:
                range_key, environment = parts
            else:
                range_key = parts[0]
                environment = "prod"

            # Get cache filename
            cache_filename = get_cache_filename(range_key, environment)

            # Use safe_join
            safe_path = safe_join(str(self.data_dir), cache_filename)
            if safe_path is None:
                return False

            cache_file_path = Path(safe_path)

            if cache_file_path.exists():
                cache_file_path.unlink()
                if self.logger:
                    self.logger.info(f"Deleted cache file: {cache_file_path}")
                return True

            return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to delete cache file: {e}")
            return False

    def clear(self) -> bool:
        """Delete all cache files

        Returns:
            True if successful
        """
        try:
            count = 0
            for cache_file in self.data_dir.glob("metrics_cache_*.pkl"):
                cache_file.unlink()
                count += 1

            if self.logger:
                self.logger.info(f"Cleared {count} cache files")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to clear cache files: {e}")
            return False

    def keys(self) -> list[str]:
        """Get all cache keys

        Returns:
            List of cache keys (e.g., ["90d_prod", "30d_uat"])
        """
        keys = []

        try:
            for cache_file in self.data_dir.glob("metrics_cache_*.pkl"):
                # Parse filename: metrics_cache_{range}_{env}.pkl
                stem = cache_file.stem  # Remove .pkl
                parts = stem.replace("metrics_cache_", "").split("_")

                if len(parts) >= 2:
                    # Has environment: metrics_cache_90d_prod.pkl
                    range_key = parts[0]
                    environment = "_".join(parts[1:])  # Handle multi-part envs
                    keys.append(f"{range_key}_{environment}")
                else:
                    # Legacy format: metrics_cache_90d.pkl
                    range_key = parts[0]
                    keys.append(f"{range_key}_prod")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to list cache keys: {e}")

        return keys


class MemoryBackend:
    """In-memory cache backend using dictionary

    Fast but volatile - data lost on restart.
    Useful for testing or temporary caching.
    """

    def __init__(self, logger=None):
        """Initialize memory backend

        Args:
            logger: Optional logger instance
        """
        self._cache: dict[str, Any] = {}
        self.logger = logger

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store value in memory

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Ignored for memory backend

        Returns:
            Always True
        """
        self._cache[key] = value
        return True

    def delete(self, key: str) -> bool:
        """Delete value from memory

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> bool:
        """Clear all values

        Returns:
            Always True
        """
        self._cache.clear()
        return True

    def keys(self) -> list[str]:
        """Get all keys

        Returns:
            List of cache keys
        """
        return list(self._cache.keys())
