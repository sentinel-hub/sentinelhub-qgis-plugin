"""Tests for the common utilities"""

from typing import Union

import pytest

from ..utils.common import is_float_or_undefined


@pytest.mark.parametrize(
    "input_value, output",
    [
        ("", True),
        (0.1, True),
        (-2, True),
        ("0.1", True),
        ("222", True),
        (0.0, True),
        (2, True),
        (1e1000, False),
        (float("nan"), False),
        (float("inf"), False),
        (float("-inf"), False),
        ("abcd", False),
    ],
)
def test_is_float_or_undefined(input_value: Union[str, float], output: bool) -> None:
    """Tests the is_float_or_undefined function"""
    assert is_float_or_undefined(input_value) == output
