from datetime import datetime, timedelta
from typing import Tuple
import re


def get_quarter_dates(year: int, quarter: int) -> Tuple[datetime, datetime]:
    """Get start and end dates for a calendar quarter

    Args:
        year: Year (e.g., 2024)
        quarter: Quarter number (1-4)

    Returns:
        Tuple of (start_date, end_date)
    """
    if quarter < 1 or quarter > 4:
        raise ValueError("Quarter must be between 1 and 4")

    quarter_starts = {
        1: (1, 1),
        2: (4, 1),
        3: (7, 1),
        4: (10, 1)
    }

    quarter_ends = {
        1: (3, 31),
        2: (6, 30),
        3: (9, 30),
        4: (12, 31)
    }

    start_month, start_day = quarter_starts[quarter]
    end_month, end_day = quarter_ends[quarter]

    start_date = datetime(year, start_month, start_day, 0, 0, 0)
    end_date = datetime(year, end_month, end_day, 23, 59, 59)

    return start_date, end_date


def get_last_n_days(n: int) -> Tuple[datetime, datetime]:
    """Get date range for last N days

    Args:
        n: Number of days to look back

    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=n)
    return start_date, end_date


def get_current_year() -> Tuple[datetime, datetime]:
    """Get current calendar year dates

    Returns:
        Tuple of (start_date, end_date)
    """
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1, 0, 0, 0)
    end_date = datetime(current_year, 12, 31, 23, 59, 59)
    return start_date, end_date


def get_previous_year() -> Tuple[datetime, datetime]:
    """Get previous calendar year dates

    Returns:
        Tuple of (start_date, end_date)
    """
    previous_year = datetime.now().year - 1
    start_date = datetime(previous_year, 1, 1, 0, 0, 0)
    end_date = datetime(previous_year, 12, 31, 23, 59, 59)
    return start_date, end_date


def parse_period_param(period: str) -> Tuple[datetime, datetime]:
    """Parse period string like '30d', 'Q1-2024', 'current-year', 'previous-year'

    Args:
        period: Period string to parse

    Returns:
        Tuple of (start_date, end_date)

    Examples:
        '30d' -> last 30 days
        'Q1-2024' -> Q1 of 2024
        'current-year' -> current calendar year
        'previous-year' -> previous calendar year
    """
    period = period.lower().strip()

    # Check for 'Nd' format (e.g., '30d', '90d')
    days_match = re.match(r'^(\d+)d$', period)
    if days_match:
        n = int(days_match.group(1))
        return get_last_n_days(n)

    # Check for 'QX-YYYY' format (e.g., 'Q1-2024')
    quarter_match = re.match(r'^q(\d)-(\d{4})$', period)
    if quarter_match:
        quarter = int(quarter_match.group(1))
        year = int(quarter_match.group(2))
        return get_quarter_dates(year, quarter)

    # Check for special keywords
    if period == 'current-year':
        return get_current_year()

    if period == 'previous-year':
        return get_previous_year()

    raise ValueError(f"Invalid period format: {period}. "
                     "Expected formats: 'Nd', 'QX-YYYY', 'current-year', 'previous-year'")


def get_current_quarter() -> Tuple[int, int]:
    """Get current quarter and year

    Returns:
        Tuple of (quarter, year)
    """
    now = datetime.now()
    quarter = (now.month - 1) // 3 + 1
    return quarter, now.year


def get_previous_quarter() -> Tuple[int, int]:
    """Get previous quarter and year

    Returns:
        Tuple of (quarter, year)
    """
    now = datetime.now()
    current_quarter = (now.month - 1) // 3 + 1

    if current_quarter == 1:
        return 4, now.year - 1
    else:
        return current_quarter - 1, now.year
