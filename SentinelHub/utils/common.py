"""
Any other utilities
"""
import math
from typing import Union


def is_float_or_undefined(value: Union[str, float]) -> bool:
    """Checks if a value represents a float or an empty string"""
    if value == "":
        return True

    try:
        return math.isfinite(float(value))
    except ValueError:
        return False
