"""
Time utilities
"""
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
