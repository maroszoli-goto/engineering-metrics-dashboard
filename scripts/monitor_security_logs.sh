#!/bin/bash
# Security Log Monitoring Script
# Monitors authentication failures and suspicious activity
# Usage: ./scripts/monitor_security_logs.sh [--alert-email admin@company.com]

set -e

# Configuration
LOG_FILE="${LOG_FILE:-logs/team_metrics.log}"
ALERT_EMAIL="${1}"
THRESHOLD_FAILED_LOGINS=5  # Alert after this many failed logins
TIME_WINDOW=300  # 5 minutes in seconds

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "🔒 Security Log Monitor - Team Metrics Dashboard"
echo "================================================"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "${RED}❌ Log file not found: $LOG_FILE${NC}"
    exit 1
fi

echo "📁 Log file: $LOG_FILE"
echo ""

# 1. Failed Authentication Attempts
echo "🔴 Failed Authentication Attempts (Last 24 Hours)"
echo "=================================================="
failed_logins=$(grep "Failed authentication" "$LOG_FILE" | tail -100 || true)
count=$(echo "$failed_logins" | grep -c "Failed authentication" || echo "0")

if [ "$count" -gt 0 ]; then
    echo "${RED}Found $count failed login attempts:${NC}"
    echo "$failed_logins" | tail -10
    echo ""

    if [ "$count" -gt "$THRESHOLD_FAILED_LOGINS" ]; then
        echo "${RED}⚠️  WARNING: High number of failed logins detected!${NC}"

        # Send email alert if configured
        if [ -n "$ALERT_EMAIL" ]; then
            echo "Sending alert email to $ALERT_EMAIL..."
            echo "Subject: Security Alert - Multiple Failed Logins

$count failed login attempts detected in the last 24 hours.

Recent failures:
$failed_logins

Log file: $LOG_FILE
Time: $(date)

Please investigate for potential brute force attack.
" | mail -s "Team Metrics Security Alert" "$ALERT_EMAIL"
        fi
    fi
else
    echo "${GREEN}✅ No failed login attempts${NC}"
fi
echo ""

# 2. Successful Authentications
echo "✅ Successful Authentications (Last 24 Hours)"
echo "=============================================="
successful_logins=$(grep "Authenticated user" "$LOG_FILE" | tail -20 || true)
count=$(echo "$successful_logins" | grep -c "Authenticated user" || echo "0")

if [ "$count" -gt 0 ]; then
    echo "${GREEN}Found $count successful logins:${NC}"
    echo "$successful_logins" | tail -10
else
    echo "No successful logins"
fi
echo ""

# 3. Suspicious Patterns
echo "⚠️  Suspicious Activity Patterns"
echo "================================"

# SQL injection attempts
sql_attempts=$(grep -iE "(DROP TABLE|UNION SELECT|OR 1=1)" "$LOG_FILE" | tail -10 || true)
if [ -n "$sql_attempts" ]; then
    echo "${RED}SQL Injection Attempts:${NC}"
    echo "$sql_attempts"
    echo ""
fi

# XSS attempts
xss_attempts=$(grep -iE "(<script>|<img|onerror=|javascript:)" "$LOG_FILE" | tail -10 || true)
if [ -n "$xss_attempts" ]; then
    echo "${RED}XSS Attempts:${NC}"
    echo "$xss_attempts"
    echo ""
fi

# Path traversal attempts
path_traversal=$(grep -E "\\.\\." "$LOG_FILE" | grep -v "docs/" | tail -10 || true)
if [ -n "$path_traversal" ]; then
    echo "${RED}Path Traversal Attempts:${NC}"
    echo "$path_traversal"
    echo ""
fi

# Check for clean slate
if [ -z "$sql_attempts" ] && [ -z "$xss_attempts" ] && [ -z "$path_traversal" ]; then
    echo "${GREEN}✅ No suspicious patterns detected${NC}"
fi
echo ""

# 4. Rate Limiting Events
echo "🚦 Rate Limiting Events"
echo "======================"
rate_limit=$(grep -iE "(rate limit|429|too many requests)" "$LOG_FILE" | tail -10 || true)
if [ -n "$rate_limit" ]; then
    echo "${YELLOW}Rate limiting triggered:${NC}"
    echo "$rate_limit"
else
    echo "${GREEN}✅ No rate limiting events${NC}"
fi
echo ""

# 5. Error Summary
echo "📊 Error Summary (Last 24 Hours)"
echo "================================"

# Count errors by type
error_count=$(grep -c "ERROR" "$LOG_FILE" || echo "0")
warning_count=$(grep -c "WARNING" "$LOG_FILE" || echo "0")

echo "Errors: $error_count"
echo "Warnings: $warning_count"
echo ""

if [ "$error_count" -gt 0 ]; then
    echo "Recent errors:"
    grep "ERROR" "$LOG_FILE" | tail -5
    echo ""
fi

# 6. Top IP Addresses (if X-Real-IP is logged)
echo "🌐 Top IP Addresses (Failed Logins)"
echo "===================================="
grep "Failed authentication" "$LOG_FILE" | grep -oE "from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -rn | head -5 || echo "No IP addresses found in logs"
echo ""

# 7. Authentication Timeline
echo "📅 Authentication Timeline (Last 24 Hours)"
echo "=========================================="
echo "Time Distribution:"
grep -E "(Failed authentication|Authenticated user)" "$LOG_FILE" | \
    awk '{print $1, $2}' | \
    cut -d: -f1-2 | \
    sort | uniq -c | \
    tail -10 || echo "No authentication events"
echo ""

# 8. Recommendations
echo "💡 Recommendations"
echo "=================="

if [ "$count" -gt "$THRESHOLD_FAILED_LOGINS" ]; then
    echo "${RED}🔴 HIGH PRIORITY:${NC}"
    echo "  - Review failed login attempts for brute force attack"
    echo "  - Consider blocking suspicious IP addresses"
    echo "  - Verify rate limiting is enabled"
    echo ""
fi

if [ -n "$sql_attempts" ] || [ -n "$xss_attempts" ]; then
    echo "${YELLOW}🟡 MEDIUM PRIORITY:${NC}"
    echo "  - Injection attempts detected - verify input validation"
    echo "  - Review security test results: pytest tests/security/"
    echo "  - Check WAF/IPS rules if configured"
    echo ""
fi

if [ "$error_count" -gt 50 ]; then
    echo "${YELLOW}🟡 MEDIUM PRIORITY:${NC}"
    echo "  - High error count detected - investigate application stability"
    echo "  - Review error logs: tail -100 logs/team_metrics_error.log"
    echo ""
fi

echo "${GREEN}✅ ALWAYS:${NC}"
echo "  - Rotate logs regularly (configured in logging.yaml)"
echo "  - Update dependencies weekly"
echo "  - Run security tests before releases"
echo "  - Monitor this report daily"
echo ""

# 9. Quick Actions
echo "🛠️  Quick Actions"
echo "================="
echo "View full error log:"
echo "  tail -100 logs/team_metrics_error.log"
echo ""
echo "View authentication events:"
echo "  grep -E '(Failed|Authenticated)' logs/team_metrics.log | tail -50"
echo ""
echo "Test rate limiting:"
echo "  for i in {1..15}; do curl http://localhost:5001/api/metrics; sleep 1; done"
echo ""
echo "Run security tests:"
echo "  pytest tests/security/ -v"
echo ""

echo "================================================"
echo "Report generated: $(date)"
echo "================================================"
