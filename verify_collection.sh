#!/bin/bash
# Quick verification script to check if collection was successful

echo "=================================="
echo "Collection Verification Summary"
echo "=================================="
echo ""

LOG_FILE="/tmp/collection_final.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Collection log not found: $LOG_FILE"
    exit 1
fi

echo "1. Checking for NoneType errors..."
NONE_ERRORS=$(grep -c "argument of type 'NoneType' is not iterable" "$LOG_FILE" 2>/dev/null || echo "0")
if [ "$NONE_ERRORS" -eq 0 ]; then
    echo "   ✅ No NoneType errors found!"
else
    echo "   ❌ Found $NONE_ERRORS NoneType errors"
fi

echo ""
echo "2. Checking release collection..."
NATIVE_RELEASES=$(grep "Native Team" -A 20 "$LOG_FILE" | grep "Total releases collected:" | head -1 | awk '{print $4}')
WEBTC_RELEASES=$(grep "WebTC Team" -A 20 "$LOG_FILE" | grep "Total releases collected:" | head -1 | awk '{print $4}')

if [ -n "$NATIVE_RELEASES" ]; then
    echo "   ✅ Native Team: $NATIVE_RELEASES releases collected"
else
    echo "   ⚠️  Native Team: Release count not found in log"
fi

if [ -n "$WEBTC_RELEASES" ]; then
    echo "   ✅ WebTC Team: $WEBTC_RELEASES releases collected"
else
    echo "   ⚠️  WebTC Team: Release count not found in log"
fi

echo ""
echo "3. Checking issue mapping..."
NATIVE_MAPPED=$(grep "Native Team" -A 25 "$LOG_FILE" | grep "Mapped.*issues to fix versions" | head -1 | awk '{print $3}')
WEBTC_MAPPED=$(grep "WebTC Team" -A 25 "$LOG_FILE" | grep "Mapped.*issues to fix versions" | head -1 | awk '{print $3}')

if [ -n "$NATIVE_MAPPED" ] && [ "$NATIVE_MAPPED" -gt 0 ]; then
    echo "   ✅ Native Team: $NATIVE_MAPPED issues mapped to releases"
elif [ "$NATIVE_MAPPED" = "0" ]; then
    echo "   ❌ Native Team: 0 issues mapped (bug not fixed?)"
else
    echo "   ⚠️  Native Team: Mapping count not found in log"
fi

if [ -n "$WEBTC_MAPPED" ] && [ "$WEBTC_MAPPED" -gt 0 ]; then
    echo "   ✅ WebTC Team: $WEBTC_MAPPED issues mapped to releases"
elif [ "$WEBTC_MAPPED" = "0" ]; then
    echo "   ❌ WebTC Team: 0 issues mapped (bug not fixed?)"
else
    echo "   ⚠️  WebTC Team: Mapping count not found in log"
fi

echo ""
echo "4. Checking collection completion..."
if grep -q "✅ All metrics collected and saved" "$LOG_FILE"; then
    echo "   ✅ Collection completed successfully!"
else
    echo "   ⚠️  Collection may not have completed"
fi

echo ""
echo "5. Checking cache file..."
CACHE_FILE="data/metrics_cache_90d.pkl"
if [ -f "$CACHE_FILE" ]; then
    SIZE=$(ls -lh "$CACHE_FILE" | awk '{print $5}')
    MODIFIED=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$CACHE_FILE" 2>/dev/null || stat -c "%y" "$CACHE_FILE" | cut -d'.' -f1)
    echo "   ✅ Cache file exists: $SIZE"
    echo "      Modified: $MODIFIED"
else
    echo "   ❌ Cache file not found: $CACHE_FILE"
fi

echo ""
echo "=================================="
echo "Run 'python analyze_releases.py' for detailed analysis"
echo "=================================="
