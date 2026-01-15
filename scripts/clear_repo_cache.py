#!/usr/bin/env python3
"""Utility to clear repository cache

Run this script to clear the repository cache if you need to force
a fresh fetch of repository lists from GitHub.
"""

from src.utils.repo_cache import clear_cache

if __name__ == "__main__":
    clear_cache()
