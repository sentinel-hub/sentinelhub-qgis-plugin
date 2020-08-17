"""
Time utilities
"""
import calendar
import datetime as dt

import dateutil.parser


def parse_date(date):
    """ If a date string is set it parses it into a format YYYY-MM-DD. In case parsing fails None is returned.

    :param date: A string describing a date
    :type date: str
    :return: A string in a format YYYY-MM-DD, an empty string, or None
    :rtype: str or None
    """
    if date == '':
        return date
    try:
        return dateutil.parser.parse(date).date().isoformat()
    except ValueError:
        return None


def get_month_time_interval(year, month):
    """ Provides a time interval for the given month in a year
    """
    _, number_of_days = calendar.monthrange(year, month)

    first_day = dt.date(year, month, 1)
    last_day = dt.date(year, month, number_of_days)

    return '{}/{}/P1D'.format(first_day.isoformat(), last_day.isoformat())
