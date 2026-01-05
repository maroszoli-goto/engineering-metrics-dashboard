from typing import Dict, List, Tuple


def calculate_team_averages(team_metrics: Dict) -> Dict:
    """Calculate average metrics across team members

    Args:
        team_metrics: Dictionary with 'member_trends' containing per-person metrics

    Returns:
        Dictionary with average values for each metric
        Example: {'prs': 15.5, 'reviews': 20.3, 'commits': 80.2}
    """
    member_trends = team_metrics.get('member_trends', {})

    if not member_trends:
        return {}

    totals = {
        'prs': 0,
        'reviews': 0,
        'commits': 0,
        'lines_added': 0,
        'lines_deleted': 0
    }

    count = len(member_trends)

    for username, metrics in member_trends.items():
        totals['prs'] += metrics.get('prs', 0)
        totals['reviews'] += metrics.get('reviews', 0)
        totals['commits'] += metrics.get('commits', 0)
        totals['lines_added'] += metrics.get('lines_added', 0)
        totals['lines_deleted'] += metrics.get('lines_deleted', 0)

    averages = {
        key: total / count if count > 0 else 0
        for key, total in totals.items()
    }

    return averages


def identify_below_average(person_metrics: Dict, team_averages: Dict) -> List[str]:
    """Identify metrics where person is below team average

    Args:
        person_metrics: Person's metrics dictionary
        team_averages: Team average metrics dictionary

    Returns:
        List of metric names where person is below average
        Example: ['reviews', 'commits']
    """
    below_avg_metrics = []

    metric_keys = ['prs', 'reviews', 'commits']

    for key in metric_keys:
        person_value = person_metrics.get(key, 0)
        avg_value = team_averages.get(key, 0)

        if avg_value > 0 and person_value < avg_value:
            below_avg_metrics.append(key)

    return below_avg_metrics


def calculate_trend(current_period: Dict, previous_period: Dict) -> Dict:
    """Calculate trend indicators (up/down/stable) for each metric

    Args:
        current_period: Metrics for current period
        previous_period: Metrics for previous period

    Returns:
        Dictionary with trend direction and percentage change
        Example: {'prs': ('down', -15.5), 'reviews': ('up', 10.2)}
    """
    trends = {}

    metric_keys = ['prs', 'reviews', 'commits', 'lines_added', 'lines_deleted']

    for key in metric_keys:
        current = current_period.get(key, 0)
        previous = previous_period.get(key, 0)

        if previous == 0:
            if current > 0:
                trends[key] = ('up', 100.0)
            else:
                trends[key] = ('stable', 0.0)
        else:
            change_percent = ((current - previous) / previous) * 100

            if abs(change_percent) < 5:  # Less than 5% change is stable
                direction = 'stable'
            elif change_percent > 0:
                direction = 'up'
            else:
                direction = 'down'

            trends[key] = (direction, change_percent)

    return trends


def check_custom_thresholds(person_metrics: Dict, thresholds: Dict) -> List[str]:
    """Check against custom minimum thresholds from config

    Args:
        person_metrics: Person's metrics dictionary
        thresholds: Threshold configuration (e.g., {'prs_min': 5, 'reviews_min': 10})

    Returns:
        List of metrics below threshold
        Example: ['reviews']
    """
    below_threshold = []

    metric_mapping = {
        'prs_per_month': 'prs',
        'reviews_per_month': 'reviews',
        'commits_per_month': 'commits'
    }

    for threshold_key, metric_key in metric_mapping.items():
        threshold_value = thresholds.get(threshold_key, 0)
        person_value = person_metrics.get(metric_key, 0)

        if person_value < threshold_value:
            below_threshold.append(metric_key)

    return below_threshold


def get_attention_flags(person_metrics: Dict, team_metrics: Dict, config: Dict) -> Dict:
    """Combine all threshold checks into attention flags

    Args:
        person_metrics: Person's metrics dictionary
        team_metrics: Team metrics dictionary (with averages)
        config: Activity threshold configuration

    Returns:
        Dictionary with attention flags and reasons
        Example: {
            'needs_attention': True,
            'reasons': ['Below avg reviews', 'Declining PR trend', 'Below min commits'],
            'severity': 'medium'
        }
    """
    reasons = []

    # Calculate team averages
    team_averages = calculate_team_averages(team_metrics)

    # Check below average
    below_avg_threshold = config.get('below_average_threshold_percent', 70) / 100
    below_avg = []

    for key in ['prs', 'reviews', 'commits']:
        person_value = person_metrics.get(key, 0)
        avg_value = team_averages.get(key, 0)

        if avg_value > 0 and person_value < (avg_value * below_avg_threshold):
            below_avg.append(key)
            reasons.append(f"Below average {key}")

    # Check custom thresholds
    min_values = config.get('minimum_values', {})
    below_min = check_custom_thresholds(person_metrics, min_values)

    for metric in below_min:
        if f"Below average {metric}" not in reasons:
            reasons.append(f"Below minimum {metric}")

    # Check declining trends if previous period data available
    if 'previous_period' in person_metrics:
        trends = calculate_trend(
            person_metrics.get('current_period', person_metrics),
            person_metrics.get('previous_period', {})
        )

        decline_threshold = config.get('trend_decline_threshold_percent', 20)

        for key, (direction, change_percent) in trends.items():
            if direction == 'down' and abs(change_percent) > decline_threshold:
                reasons.append(f"Declining {key} trend ({change_percent:.1f}%)")

    # Determine severity
    severity = 'low'
    if len(reasons) >= 4:
        severity = 'high'
    elif len(reasons) >= 2:
        severity = 'medium'

    return {
        'needs_attention': len(reasons) > 0,
        'reasons': reasons,
        'severity': severity,
        'metrics_flagged': list(set(below_avg + below_min))
    }


def get_trend_indicator(direction: str) -> str:
    """Get visual indicator for trend direction

    Args:
        direction: 'up', 'down', or 'stable'

    Returns:
        Unicode arrow character
    """
    indicators = {
        'up': '▲',
        'down': '▼',
        'stable': '→'
    }
    return indicators.get(direction, '→')
