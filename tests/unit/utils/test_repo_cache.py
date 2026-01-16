"""Tests for repository cache module"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.utils.repo_cache import (
    CACHE_DIR,
    CACHE_EXPIRATION_HOURS,
    _get_cache_filename,
    _get_cache_key,
    clear_cache,
    get_cached_repositories,
    save_cached_repositories,
)


class TestCacheRetrieval:
    """Test get_cached_repositories function"""

    def test_get_cached_repositories_valid_cache(self, tmp_path, monkeypatch):
        """Test retrieving repositories from a valid cache"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        cache_data = {
            "cache_key": "test-org:team1",
            "organization": "test-org",
            "teams": ["team1"],
            "repositories": ["org/repo1", "org/repo2"],
            "timestamp": datetime.now().isoformat(),
            "count": 2,
        }

        cache_key = _get_cache_key("test-org", ["team1"])
        cache_file = cache_dir / _get_cache_filename(cache_key).name
        cache_file.write_text(json.dumps(cache_data))

        # Act
        result = get_cached_repositories("test-org", ["team1"])

        # Assert
        assert result == ["org/repo1", "org/repo2"]

    def test_get_cached_repositories_expired_cache(self, tmp_path, monkeypatch):
        """Test that expired cache returns None"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        expired_time = datetime.now() - timedelta(hours=CACHE_EXPIRATION_HOURS + 1)
        cache_data = {
            "cache_key": "test-org:team1",
            "repositories": ["org/repo1"],
            "timestamp": expired_time.isoformat(),
        }

        cache_key = _get_cache_key("test-org", ["team1"])
        cache_file = cache_dir / _get_cache_filename(cache_key).name
        cache_file.write_text(json.dumps(cache_data))

        # Act
        result = get_cached_repositories("test-org", ["team1"])

        # Assert
        assert result is None

    def test_get_cached_repositories_missing_cache(self, tmp_path, monkeypatch):
        """Test that missing cache file returns None"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        # Act
        result = get_cached_repositories("test-org", ["team1"])

        # Assert
        assert result is None

    def test_get_cached_repositories_corrupted_json(self, tmp_path, monkeypatch):
        """Test that corrupted JSON returns None"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        cache_key = _get_cache_key("test-org", ["team1"])
        cache_file = cache_dir / _get_cache_filename(cache_key).name
        cache_file.write_text("invalid json{")

        # Act
        result = get_cached_repositories("test-org", ["team1"])

        # Assert
        assert result is None

    def test_get_cached_repositories_empty_params_returns_none(self):
        """Test that empty organization or teams returns None"""
        # Act & Assert
        assert get_cached_repositories("", ["team1"]) is None
        assert get_cached_repositories("test-org", []) is None
        assert get_cached_repositories(None, ["team1"]) is None


class TestCacheSaving:
    """Test save_cached_repositories function"""

    def test_save_cached_repositories_success(self, tmp_path, monkeypatch):
        """Test successfully saving repositories to cache"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        # Act
        save_cached_repositories("test-org", ["team1"], ["org/repo1", "org/repo2"])

        # Assert
        assert cache_dir.exists()
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        cache_data = json.loads(cache_files[0].read_text())
        assert cache_data["organization"] == "test-org"
        assert cache_data["teams"] == ["team1"]
        assert cache_data["repositories"] == ["org/repo1", "org/repo2"]
        assert cache_data["count"] == 2
        assert "timestamp" in cache_data

    def test_save_cached_repositories_creates_directory(self, tmp_path, monkeypatch):
        """Test that cache directory is created if it doesn't exist"""
        # Arrange
        cache_dir = tmp_path / "new_cache_dir"
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)
        assert not cache_dir.exists()

        # Act
        save_cached_repositories("test-org", ["team1"], ["org/repo1"])

        # Assert
        assert cache_dir.exists()

    def test_save_cached_repositories_empty_params_does_nothing(self, tmp_path, monkeypatch):
        """Test that empty params don't create cache files"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        # Act
        save_cached_repositories("", ["team1"], ["org/repo1"])
        save_cached_repositories("test-org", [], ["org/repo1"])
        save_cached_repositories("test-org", ["team1"], [])

        # Assert
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 0

    def test_save_cached_repositories_handles_write_errors(self, tmp_path, monkeypatch, capsys):
        """Test that write errors are handled gracefully"""
        # Arrange
        cache_dir = tmp_path / "readonly_cache"
        cache_dir.mkdir()
        cache_dir.chmod(0o444)  # Read-only directory
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        # Act (should not raise exception)
        save_cached_repositories("test-org", ["team1"], ["org/repo1"])

        # Assert (check that error was printed)
        captured = capsys.readouterr()
        assert "Cache write error" in captured.out or len(list(cache_dir.glob("*.json"))) == 0

        # Cleanup
        cache_dir.chmod(0o755)


class TestCacheUtilities:
    """Test cache utility functions"""

    def test_get_cache_key_generation(self):
        """Test cache key generation format"""
        # Act
        key = _get_cache_key("test-org", ["team1", "team2"])

        # Assert
        assert key == "test-org:team1,team2"

    def test_get_cache_key_sorts_teams(self):
        """Test that teams are sorted in cache key"""
        # Act
        key1 = _get_cache_key("test-org", ["team2", "team1"])
        key2 = _get_cache_key("test-org", ["team1", "team2"])

        # Assert
        assert key1 == key2  # Both should be same after sorting

    def test_get_cache_filename_hashing(self):
        """Test that cache filename is properly hashed"""
        # Act
        cache_key = "test-org:team1"
        filename = _get_cache_filename(cache_key)

        # Assert
        assert filename.suffix == ".json"
        assert len(filename.stem) == 16  # MD5 hash truncated to 16 chars

    def test_clear_cache_removes_all_files(self, tmp_path, monkeypatch, capsys):
        """Test that clear_cache removes all cache files"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        # Create some cache files
        (cache_dir / "cache1.json").write_text("{}")
        (cache_dir / "cache2.json").write_text("{}")
        (cache_dir / "not_json.txt").write_text("text")  # Should not be deleted

        # Act
        clear_cache()

        # Assert
        json_files = list(cache_dir.glob("*.json"))
        txt_files = list(cache_dir.glob("*.txt"))
        assert len(json_files) == 0
        assert len(txt_files) == 1  # .txt file should still exist

        captured = capsys.readouterr()
        assert "Cleared repository cache" in captured.out


class TestCacheExpiration:
    """Test cache expiration logic"""

    def test_cache_within_24_hours_is_valid(self, tmp_path, monkeypatch):
        """Test that cache within expiration window is valid"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        recent_time = datetime.now() - timedelta(hours=12)  # 12 hours ago
        cache_data = {"repositories": ["org/repo1"], "timestamp": recent_time.isoformat()}

        cache_key = _get_cache_key("test-org", ["team1"])
        cache_file = cache_dir / _get_cache_filename(cache_key).name
        cache_file.write_text(json.dumps(cache_data))

        # Act
        result = get_cached_repositories("test-org", ["team1"])

        # Assert
        assert result is not None
        assert result == ["org/repo1"]

    def test_cache_beyond_24_hours_is_expired(self, tmp_path, monkeypatch):
        """Test that cache beyond expiration window returns None"""
        # Arrange
        cache_dir = tmp_path / "repo_cache"
        cache_dir.mkdir()
        monkeypatch.setattr("src.utils.repo_cache.CACHE_DIR", cache_dir)

        old_time = datetime.now() - timedelta(hours=25)  # 25 hours ago
        cache_data = {"repositories": ["org/repo1"], "timestamp": old_time.isoformat()}

        cache_key = _get_cache_key("test-org", ["team1"])
        cache_file = cache_dir / _get_cache_filename(cache_key).name
        cache_file.write_text(json.dumps(cache_data))

        # Act
        result = get_cached_repositories("test-org", ["team1"])

        # Assert
        assert result is None
