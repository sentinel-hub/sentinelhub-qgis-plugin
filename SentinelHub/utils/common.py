"""
Any other utilities
"""
import math


def is_float_or_undefined(value):
    """ Checks if a value represents a float or an empty string
    """
    if value == '':
        return True

    try:
        return math.isfinite(float(value))
    except ValueError:
        return False
