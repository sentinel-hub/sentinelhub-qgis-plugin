"""
Time utilities
"""
import calendar
import datetime as dt
from typing import Optional

import dateutil.parser


def parse_date(date: str) -> Optional[str]:
    """If a date string is set it parses it into a format YYYY-MM-DD. In case parsing fails None is returned.

    :param date: A string describing a date
    :return: A string in a format YYYY-MM-DD, an empty string, or None
    """
    if date == "":
        return date
    try:
        return dateutil.parser.parse(date).date().isoformat()
    except ValueError:
        return None


def get_month_time_interval(year: int, month: int) -> str:
    """Provides a time interval for the given month in a year

    :param year: An integer representing a year.
    :param month: An integer representing a month.
    :return: A string representing the time interval
    """
    _, number_of_days = calendar.monthrange(year, month)

    first_day = dt.date(year, month, 1)
    last_day = dt.date(year, month, number_of_days)

    return f"{first_day.isoformat()}/{last_day.isoformat()}/P1D"
