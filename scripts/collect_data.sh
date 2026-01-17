#!/bin/bash

# Navigate to project directory
cd /Users/zmaros/Work/Projects/team_metrics

# Activate virtual environment
source venv/bin/activate

echo "=================================="
echo "Data Collection (6 Ranges)"
echo "=================================="
echo ""

# Collect 6 essential date ranges for comprehensive analysis
# Ranges: 30d, 60d, 90d, 180d, 365d, previous year
# Each range creates a separate cache file

# Short-term trend (30 days)
echo "📊 Collecting 30-day data..."
python collect_data.py --date-range 30d
if [ $? -ne 0 ]; then
    echo "⚠️  30-day collection failed"
fi
echo ""

# Medium-term trend (60 days)
echo "📊 Collecting 60-day data..."
python collect_data.py --date-range 60d
if [ $? -ne 0 ]; then
    echo "⚠️  60-day collection failed"
fi
echo ""

# Standard range (90 days) - default for dashboard
echo "📊 Collecting 90-day data..."
python collect_data.py --date-range 90d
if [ $? -ne 0 ]; then
    echo "⚠️  90-day collection failed"
    exit 1  # Exit with error if default range fails
fi
echo ""

# 6-month trend (180 days)
echo "📊 Collecting 180-day data..."
python collect_data.py --date-range 180d
if [ $? -ne 0 ]; then
    echo "⚠️  180-day collection failed"
fi
echo ""

# Long-term trend (365 days)
echo "📊 Collecting 365-day data..."
python collect_data.py --date-range 365d
if [ $? -ne 0 ]; then
    echo "⚠️  365-day collection failed"
fi
echo ""

# Previous year (historical comparison)
PREVIOUS_YEAR=$(($(date +"%Y") - 1))
echo "📊 Collecting ${PREVIOUS_YEAR} (previous year)..."
python collect_data.py --date-range "${PREVIOUS_YEAR}"
if [ $? -ne 0 ]; then
    echo "⚠️  ${PREVIOUS_YEAR} collection failed"
fi
echo ""

echo "=================================="
echo "✅ Collection complete (6 ranges)"
echo "=================================="

# Exit successfully if at least the default 90d range succeeded
exit 0
