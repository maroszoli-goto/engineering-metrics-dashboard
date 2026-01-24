# Performance Monitoring

This document describes the performance monitoring system for the Team Metrics dashboard.

## Overview

The performance monitoring system provides route-level and API call timing to identify bottlenecks and optimize the dashboard. All timing data is logged in structured JSON format for easy analysis.

## Features

- **Route Timing**: Track execution time of all Flask routes
- **API Call Timing**: Monitor GitHub and Jira API calls
- **Operation Timing**: Time arbitrary code blocks
- **Structured Logging**: JSON format for machine parsing
- **Analysis Tools**: CLI tool to parse logs and generate reports

## Usage

### Decorators

#### @timed_route

Decorator to time Flask route execution:

```python
from src.dashboard.utils.performance import timed_route

@app.route('/team/<team_name>')
@timed_route
def team_dashboard(team_name):
    return render_template('team.html')
```

Logs:
- Route name
- Duration in milliseconds
- Status code
- Cache hit/miss status
- Route arguments

#### @timed_api_call

Decorator to time API calls in collectors:

```python
from src.dashboard.utils.performance import timed_api_call

@timed_api_call('github_fetch_prs')
def fetch_pull_requests(self, repo):
    # ... fetch PRs
    return prs
```

Logs:
- Operation name
- Duration in milliseconds
- Success/failure status
- Error details (if failed)

#### timed_operation Context Manager

Context manager for timing arbitrary operations:

```python
from src.dashboard.utils.performance import timed_operation

def process_data():
    with timed_operation('database_query', {'table': 'metrics'}):
        results = db.query(...)
    return results
```

Logs:
- Operation name
- Duration in milliseconds
- Success/failure status
- Custom metadata

## Log Format

Performance logs are written in structured JSON format:

```json
{
  "type": "route",
  "route": "team_dashboard",
  "duration_ms": 123.45,
  "status_code": 200,
  "cache_hit": true,
  "route_args": "('Backend',)",
  "kwargs": {"env": "prod"}
}
```

```json
{
  "type": "api_call",
  "operation": "github_fetch_prs",
  "duration_ms": 456.78,
  "success": true
}
```

```json
{
  "type": "operation",
  "operation": "cache_load",
  "duration_ms": 12.34,
  "success": true,
  "table": "metrics"
}
```

## Analysis Tool

The `analyze_performance.py` tool parses logs and generates reports with percentiles and histograms.

### Basic Usage

```bash
# Analyze all performance data
python tools/analyze_performance.py logs/team_metrics.log

# Show only routes
python tools/analyze_performance.py logs/team_metrics.log --type route

# Show only API calls
python tools/analyze_performance.py logs/team_metrics.log --type api_call
```

### Advanced Options

```bash
# Show custom percentiles
python tools/analyze_performance.py logs/team_metrics.log --percentiles 50 90 95 99

# Show histograms
python tools/analyze_performance.py logs/team_metrics.log --histogram

# Show top 5 slowest operations
python tools/analyze_performance.py logs/team_metrics.log --top 5

# Combine options
python tools/analyze_performance.py logs/team_metrics.log --type route --top 3 --histogram
```

### Sample Output

```
================================================================================
OVERALL SUMMARY
================================================================================
Total performance entries: 1,247
  Routes:       523
  API calls:    612
  Operations:   112

================================================================================
PERFORMANCE ANALYSIS REPORT
================================================================================

Operation: team_dashboard
  Count:   45
  Mean:    234.56 ms
  Median:  198.23 ms
  Min:     87.12 ms
  Max:     1,023.45 ms
  Percentiles:
    p50:    198.23 ms
    p95:    678.90 ms
    p99:    945.12 ms
  Histogram:
     87.1 -  180.7 ms: ████████████████████ (12)
    180.7 -  274.3 ms: ████████████████████████████ (18)
    274.3 -  367.9 ms: ████████ (6)
    367.9 -  461.5 ms: ████ (3)
    461.5 -  555.1 ms: ██ (2)
    555.1 -  648.7 ms: ██ (2)
    648.7 -  742.3 ms: █ (1)
    742.3 -  835.9 ms: (0)
    835.9 -  929.5 ms: (0)
    929.5 - 1023.1 ms: █ (1)
```

## Identifying Bottlenecks

Use the analysis tool to identify performance bottlenecks:

1. **Routes**: Look for routes with high mean or p95 times
2. **API Calls**: Check for slow GitHub/Jira API calls
3. **Cache Misses**: Routes with `cache_hit: false` may need optimization
4. **Outliers**: Check p99 and max values for intermittent issues

### Top 3 Bottlenecks to Check

1. **Slow routes** (mean > 500ms)
   - Review database queries
   - Check cache effectiveness
   - Consider pagination for large datasets

2. **Slow API calls** (mean > 1000ms)
   - Check network latency
   - Review API query complexity
   - Consider rate limiting issues

3. **Cache misses** (cache_hit: false for frequently accessed routes)
   - Review cache expiration settings
   - Check cache key generation
   - Consider pre-warming cache

## Integration with Collectors

### GitHub Collector

Add timing to key operations:

```python
from src.dashboard.utils.performance import timed_api_call

class GitHubGraphQLCollector:
    @timed_api_call('github_collect_all_metrics')
    def collect_all_metrics(self, team, date_range):
        # ... existing code
        pass

    @timed_api_call('github_fetch_prs')
    def _fetch_pull_requests(self, repo, since_date):
        # ... existing code
        pass
```

### Jira Collector

Add timing to pagination and filtering:

```python
from src.dashboard.utils.performance import timed_api_call

class JiraCollector:
    @timed_api_call('jira_paginate_search')
    def _paginate_search(self, jql, expand=None):
        # ... existing code
        pass

    @timed_api_call('jira_filter_collection')
    def collect_filter_results(self, filter_ids, date_range):
        # ... existing code
        pass
```

## Best Practices

1. **Use appropriate decorators**: Routes → @timed_route, API calls → @timed_api_call
2. **Add metadata**: Include relevant context (table names, filter IDs, etc.)
3. **Review logs regularly**: Run analysis tool weekly to identify trends
4. **Set baselines**: Establish baseline performance for key operations
5. **Monitor production**: Track performance metrics in production environment

## Configuration

Performance logging uses the existing dashboard logger configuration. No additional configuration is required.

To adjust log rotation or format, see `config/logging.yaml`.

## Testing

Run performance monitoring tests:

```bash
pytest tests/dashboard/utils/test_performance.py -v
pytest tests/tools/test_analyze_performance.py -v
```

## Future Enhancements

Potential improvements for future releases:

- Real-time performance dashboard
- Alerting for performance regressions
- Automatic bottleneck detection
- Integration with monitoring tools (Prometheus, Grafana)
- Performance benchmarking in CI/CD
- Historical performance trending

## Troubleshooting

### No Performance Data in Logs

Check that:
1. Decorators are applied to routes/functions
2. Logger is configured properly
3. Log file path is correct
4. Log level is set to INFO or lower

### Analysis Tool Shows No Data

Verify:
1. Log file exists and has content
2. Log entries contain `[PERF]` markers or structured JSON
3. Entries have `duration_ms` field
4. File permissions allow reading

### High Overhead

Performance monitoring has minimal overhead (<1ms per operation), but if concerned:
1. Remove decorators from hot paths
2. Use sampling (time 1 in N requests)
3. Disable in development if not needed

## Support

For issues or questions about performance monitoring:
1. Check logs for error messages
2. Run tests to verify functionality
3. Review this documentation
4. Open issue in project repository
