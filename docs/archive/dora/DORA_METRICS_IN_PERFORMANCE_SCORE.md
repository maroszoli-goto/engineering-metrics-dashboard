# DORA Metrics in Performance Score

> ⚠️ **Historical Document** - This document reflects the codebase state at the time of completion. The metrics module structure has since been refactored (Jan 2026) from a single `metrics.py` file into 4 focused modules. See [ARCHITECTURE.md](ARCHITECTURE.md) for current structure.

**Last Updated:** January 14, 2026
**Version:** 1.0

## Overview

As of January 14, 2026, the Team Metrics Dashboard now includes **DORA (DevOps Research and Assessment) metrics** in the performance score calculation. This provides a more comprehensive view of team and individual performance by incorporating deployment practices and reliability metrics alongside traditional GitHub and Jira metrics.

## What Changed

### Performance Score Composition

**Before:** 6 metrics
**After:** 10 metrics

The performance score is now calculated from 10 weighted metrics across three categories:

### Metric Breakdown

| Category | Metric | Default Weight | Direction | Description |
|----------|--------|---------------|-----------|-------------|
| **GitHub Metrics** | Pull Requests | 15% | ↑ Higher is better | PRs created in period |
| | Code Reviews | 15% | ↑ Higher is better | Reviews submitted |
| | Commits | 10% | ↑ Higher is better | Commits in PRs |
| | Cycle Time | 10% | ↓ Lower is better | PR creation to merge time |
| | Merge Rate | 5% | ↑ Higher is better | % of PRs merged |
| **DORA Metrics** | Deployment Frequency | 10% | ↑ Higher is better | Deployments per week |
| | Lead Time | 10% | ↓ Lower is better | Days from commit to production |
| | Change Failure Rate | 5% | ↓ Lower is better | % of deployments causing incidents |
| | MTTR | 5% | ↓ Lower is better | Mean time to recover from incidents |
| **Jira Metrics** | Jira Completed | 15% | ↑ Higher is better | Issues completed in period |
| | | **Total: 100%** | | |

### Weight Changes

To accommodate DORA metrics, existing metric weights were reduced:

| Metric | Old Weight | New Weight | Change |
|--------|-----------|-----------|--------|
| Pull Requests | 20% | 15% | -5% |
| Code Reviews | 20% | 15% | -5% |
| Commits | 15% | 10% | -5% |
| Cycle Time | 15% | 10% | -5% |
| Jira Completed | 20% | 15% | -5% |
| Merge Rate | 10% | 5% | -5% |
| **Deployment Frequency** | - | **10%** | **+10%** |
| **Lead Time** | - | **10%** | **+10%** |
| **Change Failure Rate** | - | **5%** | **+5%** |
| **MTTR** | - | **5%** | **+5%** |

**Total DORA contribution:** 30% of performance score

## How It Works

### Scoring Algorithm

1. **Normalization**: Each metric is normalized to 0-100 scale using min-max normalization across all teams/individuals
2. **Inversion**: For "lower is better" metrics (Cycle Time, Lead Time, CFR, MTTR), the score is inverted: `score = 100 - normalized_value`
3. **Weighting**: Each normalized score is multiplied by its weight
4. **Summation**: All weighted scores are summed to produce the final performance score (0-100)

### None Value Handling

DORA metrics may be `None` if:
- **Deployment Frequency / Lead Time**: No releases found in the period
- **Change Failure Rate / MTTR**: No incident data available (requires Jira incidents filter)

When metrics are `None`:
- They are **excluded** from the performance score calculation
- The remaining metrics are still weighted correctly
- Performance score is still calculated from available metrics

### Example Calculation

**Team A Metrics:**
- PRs: 50 (normalized: 75/100)
- Reviews: 100 (normalized: 90/100)
- Commits: 200 (normalized: 80/100)
- Cycle Time: 2 days (normalized: 85/100 → inverted: 15/100)
- Merge Rate: 95% (normalized: 95/100)
- Deployment Frequency: 2.5/week (normalized: 80/100)
- Lead Time: 1.5 days (normalized: 70/100 → inverted: 30/100)
- CFR: None (excluded)
- MTTR: None (excluded)
- Jira Completed: 40 (normalized: 85/100)

**Performance Score Calculation:**
```
Score = (75 × 0.15) + (90 × 0.15) + (80 × 0.10) + (15 × 0.10) + (95 × 0.05) +
        (80 × 0.10) + (30 × 0.10) + (85 × 0.15)
      = 11.25 + 13.5 + 8.0 + 1.5 + 4.75 + 8.0 + 3.0 + 12.75
      = 62.75

Note: CFR and MTTR weights (5% + 5% = 10%) are distributed proportionally
across remaining metrics when None.
```

## Settings Page Updates

The Settings page (`/settings`) now includes **4 new weight sliders** for DORA metrics:

### New UI Elements

- **Section Divider**: Visual separator between traditional and DORA metrics
- **DORA Metrics Section**: Clearly labeled with heading
- **4 New Sliders**:
  1. Deployment Frequency
  2. Lead Time
  3. Change Failure Rate
  4. MTTR

### Updated Presets

All 4 preset configurations now include DORA metrics:

**⚖️ Balanced** (Equal emphasis):
```
PRs: 15%, Reviews: 15%, Commits: 10%, Cycle Time: 10%, Jira: 15%, Merge Rate: 5%
Deploy Freq: 10%, Lead Time: 10%, CFR: 5%, MTTR: 5%
```

**🎯 Code Quality** (Focus on reviews, merge rate, deployment stability):
```
PRs: 10%, Reviews: 25%, Commits: 5%, Cycle Time: 10%, Jira: 10%, Merge Rate: 15%
Deploy Freq: 5%, Lead Time: 10%, CFR: 5%, MTTR: 5%
```

**🚀 Velocity** (Emphasize output, delivery speed, deployment frequency):
```
PRs: 20%, Reviews: 10%, Commits: 15%, Cycle Time: 5%, Jira: 20%, Merge Rate: 5%
Deploy Freq: 15%, Lead Time: 5%, CFR: 3%, MTTR: 2%
```

**📋 Jira Focus** (Prioritize Jira completion and reliability):
```
PRs: 10%, Reviews: 10%, Commits: 5%, Cycle Time: 5%, Jira: 30%, Merge Rate: 10%
Deploy Freq: 10%, Lead Time: 10%, CFR: 5%, MTTR: 5%
```

## Files Modified

### Core Logic

1. **`src/models/metrics.py`** (lines 1360-1499)
   - Updated `calculate_performance_score()` method
   - Added default weights with DORA metrics
   - Added DORA scoring logic with None handling
   - Implemented score inversion for "lower is better" metrics

2. **`src/config.py`** (lines 99-111)
   - Updated `performance_weights` property default weights
   - Updated docstring to include DORA metrics

### UI

3. **`src/dashboard/templates/settings.html`**
   - Added DORA Metrics section with visual divider (line 94-96)
   - Added 4 new weight sliders (lines 98-120)
   - Updated JavaScript sliders array to include DORA metrics (line 342)
   - Updated all 4 preset configurations (lines 336-340)

4. **`src/dashboard/templates/documentation.html`** (lines 747-808)
   - Updated Performance Score section
   - Added metric breakdown table
   - Updated preset descriptions with DORA weights
   - Added guidance on metric grouping

## Testing

### Test Script

A test script is available at `/test_dora_performance.py` to verify DORA metrics in cache files:

```bash
python test_dora_performance.py
```

**What it checks:**
- Cache file exists and loads correctly
- DORA metrics present in teams data
- DORA metrics present in comparison data
- Performance scores calculated with DORA metrics

### Manual Testing Steps

1. **Collect fresh data** with new code:
   ```bash
   python collect_data.py --date-range 90d
   ```

2. **Verify Settings Page**:
   - Navigate to http://localhost:5001/settings
   - Confirm 10 weight sliders visible (6 traditional + 4 DORA)
   - Test preset buttons include DORA weights
   - Verify total validation (must equal 100%)

3. **Verify Performance Scores**:
   - Navigate to Team Comparison page
   - Check "Overall Performance" card shows scores
   - Navigate to Team Member Comparison page
   - Check "Top Performers" leaderboard displays

4. **Verify Documentation**:
   - Navigate to http://localhost:5001/documentation
   - Search for "Performance Score" section
   - Verify 10 metrics listed with DORA included

## Impact

### Benefits

1. **More Comprehensive Scoring**: Incorporates deployment practices and reliability
2. **Aligns with Industry Standards**: DORA metrics are DevOps best practices
3. **Balanced View**: 30% DORA, 55% GitHub, 15% Jira provides holistic assessment
4. **Customizable**: All weights remain fully adjustable via Settings page

### Backward Compatibility

- **Old cache files**: Will work but show DORA metrics as N/A until re-collected
- **Old configurations**: Will use new default weights automatically
- **Existing dashboards**: Continue to function, just with updated scores

### Migration Path

1. No immediate action required
2. Next scheduled data collection will include DORA metrics in performance scores
3. Existing cache files can be refreshed by running collection manually
4. Performance scores will automatically recalculate with new weights

## Troubleshooting

### DORA Metrics Show as None

**Change Failure Rate / MTTR:**
- Requires Jira incidents filter configured in `config.yaml`
- If no incidents filter exists, these metrics will always be None
- This is expected behavior - CFR/MTTR only apply if incident tracking is enabled

**Deployment Frequency / Lead Time:**
- Requires releases to be collected from Jira Fix Versions
- If no releases found in the period, these will be None
- Check that Fix Versions are properly named (e.g., "Live - DD/MMM/YYYY")

### Performance Scores Changed After Update

This is expected! The new weights redistribute importance:
- Traditional GitHub metrics reduced by 5% each
- DORA metrics now contribute 30%
- Teams with strong deployment practices will see higher scores
- Teams with weak deployment practices may see lower scores

### Settings Page Shows Old Presets

- Hard refresh browser cache (Ctrl+Shift+R or Cmd+Shift+R)
- Check that template changes were applied
- Restart dashboard server

### Config File Shows Warning About Old Weights

**Warning Message:**
```
UserWarning: Config has old performance_weights without DORA metrics.
Using new defaults. Please update config.yaml or remove performance_weights section.
```

**Solution (Choose one):**

**Option 1 - Remove performance_weights (Recommended):**
```bash
# Edit config/config.yaml and delete the performance_weights section
# System will automatically use built-in defaults with all 10 metrics
```

**Option 2 - Update to new format:**
```yaml
# Edit config/config.yaml and add DORA metrics
performance_weights:
  # GitHub metrics
  prs: 0.15
  reviews: 0.15
  commits: 0.10
  cycle_time: 0.10
  merge_rate: 0.05
  jira_completed: 0.15
  # DORA metrics (NEW - add these)
  deployment_frequency: 0.10
  lead_time: 0.10
  change_failure_rate: 0.05
  mttr: 0.05
```

**Why this happens:**
- Your `config.yaml` has old 6-metric weights from before DORA metrics were added
- System has backward compatibility - automatically uses new defaults with warning
- Config file should be updated to reflect current system capabilities

**Impact:**
- ✅ System works correctly (uses new defaults)
- ⚠️ Warning appears on every config load
- ⚠️ Config file is misleading (shows outdated weights)

## Configuration Guide

### Where to Configure Weights

You can configure performance weights in two ways:

**1. Settings Page (Recommended for most users)**
- Navigate to http://localhost:5001/settings
- Use interactive sliders for all 10 metrics
- Choose from 4 quick presets
- Real-time validation (must sum to 100%)
- Changes saved automatically

**2. Config File (For programmatic configuration)**
- Edit `config/config.yaml`
- Add `performance_weights` section with all 10 metrics
- All weights must sum to 1.0
- Useful for version control or team standards

### Config File Format

**Complete example:**
```yaml
# Optional - if omitted, uses built-in defaults
performance_weights:
  # GitHub metrics
  prs: 0.15                    # Pull requests created (higher is better)
  reviews: 0.15                # Code reviews given (higher is better)
  commits: 0.10                # Commits made (higher is better)
  cycle_time: 0.10             # PR cycle time (lower is better)
  merge_rate: 0.05             # PR merge success rate (higher is better)
  jira_completed: 0.15         # Jira issues completed (higher is better)
  # DORA metrics (requires releases and incident tracking)
  deployment_frequency: 0.10   # Deployments per week (higher is better)
  lead_time: 0.10              # Lead time for changes (lower is better)
  change_failure_rate: 0.05    # % deployments causing incidents (lower is better)
  mttr: 0.05                   # Mean time to recover (lower is better)
```

**Important notes:**
- All 10 metrics must be specified
- Total must equal 1.0 (100%)
- Comments are optional but helpful
- Settings page overrides config file

### Backward Compatibility

**Old config files** (with only 6 metrics) are automatically handled:
- System detects missing DORA metrics
- Falls back to new default weights
- Shows warning message on load
- No functionality is broken

**Migration options:**
1. **Do nothing** - System works with warning
2. **Remove section** - Clean config, no warning
3. **Update section** - Add DORA metrics, no warning

## Future Enhancements

Potential improvements for future versions:

1. **Team-Specific DORA Weights**: Allow different teams to have different weight configurations
2. **Time-Based Weighting**: Adjust weights based on organizational maturity
3. **Conditional Weights**: Automatically adjust weights when metrics are None
4. **Historical Trending**: Track performance score changes over time with DORA inclusion
5. **Benchmarking**: Compare DORA metric scores against industry benchmarks

## References

- **DORA Research**: https://dora.dev/
- **DORA Metrics Guide**: https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance
- **Project Documentation**: `docs/DORA_METRICS.md`
- **Settings Page**: http://localhost:5001/settings
- **In-Dashboard Help**: http://localhost:5001/documentation

## Support

For questions or issues:
1. Check the in-dashboard Documentation page (`/documentation`)
2. Review `docs/DORA_METRICS.md` for DORA metrics collection details
3. Check `CLAUDE.md` for general project guidance
4. Review this document for performance score specifics
