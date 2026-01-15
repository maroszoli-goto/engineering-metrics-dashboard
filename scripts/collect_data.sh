#!/bin/bash

# Navigate to project directory
cd /Users/zmaros/Work/Projects/team_metrics

# Activate virtual environment
source venv/bin/activate

echo "=================================="
echo "Multi-Range Data Collection"
echo "=================================="
echo ""

# Collect multiple date ranges for comprehensive analysis
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

# Dynamic quarter collection
# Collect current quarter, completed quarters of current year, and all quarters of previous year

CURRENT_YEAR=$(date +"%Y")
PREVIOUS_YEAR=$((CURRENT_YEAR - 1))
CURRENT_MONTH=$(date +"%m")
CURRENT_QUARTER=$(( (10#$CURRENT_MONTH - 1) / 3 + 1 ))

echo "=================================="
echo "Quarterly Data Collection"
echo "Current: Q${CURRENT_QUARTER}-${CURRENT_YEAR}"
echo "=================================="
echo ""

# Collect current quarter of current year
echo "📊 Collecting Q${CURRENT_QUARTER}-${CURRENT_YEAR} (current quarter)..."
python collect_data.py --date-range "Q${CURRENT_QUARTER}-${CURRENT_YEAR}"
if [ $? -ne 0 ]; then
    echo "⚠️  Q${CURRENT_QUARTER}-${CURRENT_YEAR} collection failed"
fi
echo ""

# Collect completed quarters of current year (quarters before current)
for q in $(seq 1 $((CURRENT_QUARTER - 1))); do
    echo "📊 Collecting Q${q}-${CURRENT_YEAR} (completed quarter)..."
    python collect_data.py --date-range "Q${q}-${CURRENT_YEAR}"
    if [ $? -ne 0 ]; then
        echo "⚠️  Q${q}-${CURRENT_YEAR} collection failed"
    fi
    echo ""
done

# Collect all 4 quarters of previous year
for q in 1 2 3 4; do
    echo "📊 Collecting Q${q}-${PREVIOUS_YEAR} (previous year)..."
    python collect_data.py --date-range "Q${q}-${PREVIOUS_YEAR}"
    if [ $? -ne 0 ]; then
        echo "⚠️  Q${q}-${PREVIOUS_YEAR} collection failed"
    fi
    echo ""
done

# Current year (full year data)
echo "📊 Collecting ${CURRENT_YEAR} (current year)..."
python collect_data.py --date-range "${CURRENT_YEAR}"
if [ $? -ne 0 ]; then
    echo "⚠️  ${CURRENT_YEAR} collection failed"
fi
echo ""

# Previous year (historical comparison)
echo "📊 Collecting ${PREVIOUS_YEAR} (previous year)..."
python collect_data.py --date-range "${PREVIOUS_YEAR}"
if [ $? -ne 0 ]; then
    echo "⚠️  ${PREVIOUS_YEAR} collection failed"
fi
echo ""

echo "=================================="
echo "✅ Multi-range collection complete"
echo "=================================="

# Exit successfully if at least the default 90d range succeeded
exit 0
