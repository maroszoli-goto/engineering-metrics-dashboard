#!/bin/bash
# CI Diagnostic Script
# Helps identify differences between local and CI environment

set -e

echo "=== CI Environment Diagnostic ==="
echo ""

# Python version
echo "1. Python Version:"
python --version
echo ""

# OS Info
echo "2. Operating System:"
uname -a
echo ""

# Installed packages
echo "3. Installed Packages:"
pip list | head -20
echo "   ... (showing first 20)"
echo ""

# Working directory
echo "4. Working Directory:"
pwd
echo ""

# Directory structure
echo "5. Directory Structure:"
ls -la
echo ""

# Data directory
echo "6. Data Directory:"
if [ -d "data" ]; then
    ls -la data/
    echo "   Files: $(ls data/ | wc -l)"
else
    echo "   ❌ data/ directory doesn't exist"
fi
echo ""

# Config files
echo "7. Config Files:"
if [ -f "config/config.yaml" ]; then
    echo "   ✓ config/config.yaml exists"
    head -5 config/config.yaml
else
    echo "   ❌ config/config.yaml doesn't exist"
fi
echo ""

# Cache files
echo "8. Cache Files:"
if [ -f "data/metrics_cache_90d.pkl" ]; then
    echo "   ✓ 90d cache exists ($(du -h data/metrics_cache_90d.pkl | cut -f1))"
else
    echo "   ❌ 90d cache doesn't exist"
fi
echo ""

# Environment variables
echo "9. Environment Variables:"
echo "   PYTHONPATH: ${PYTHONPATH:-not set}"
echo "   CI: ${CI:-not set}"
echo "   HOME: ${HOME}"
echo ""

# Git status
echo "10. Git Status:"
if command -v git &> /dev/null; then
    git branch
    git log -1 --oneline
else
    echo "   Git not available"
fi
echo ""

# Run minimal test
echo "11. Running Minimal Test:"
if python -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor} OK')"; then
    echo "   ✓ Python import works"
else
    echo "   ❌ Python import failed"
fi
echo ""

# Check pytest
echo "12. Pytest Version:"
if pytest --version; then
    echo "   ✓ Pytest available"
else
    echo "   ❌ Pytest not installed"
fi
echo ""

# Check critical imports
echo "13. Critical Imports:"
python -c "
try:
    import flask
    print('   ✓ Flask:', flask.__version__)
except ImportError as e:
    print('   ❌ Flask:', e)

try:
    import pandas
    print('   ✓ Pandas:', pandas.__version__)
except ImportError as e:
    print('   ❌ Pandas:', e)

try:
    import pytest
    print('   ✓ Pytest:', pytest.__version__)
except ImportError as e:
    print('   ❌ Pytest:', e)
"
echo ""

# Test database connection
echo "14. SQLite Version:"
python -c "import sqlite3; print('   SQLite:', sqlite3.sqlite_version)"
echo ""

# Memory info (if available)
echo "15. System Resources:"
if command -v free &> /dev/null; then
    free -h
elif command -v vm_stat &> /dev/null; then
    # macOS
    vm_stat | head -5
else
    echo "   Memory info not available"
fi
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "💡 Tips:"
echo "  - Compare output with CI logs"
echo "  - Look for missing files/directories"
echo "  - Check Python version matches CI matrix"
echo "  - Verify all dependencies are installed"
