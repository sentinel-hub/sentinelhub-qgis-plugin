from typing import Union

import pytest
from ..utils.common import is_float_or_undefined


@pytest.mark.parametrize(
    "input, output",
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
def test_is_float_or_undefined(input: Union[str, float], output: bool) -> None:
    assert is_float_or_undefined(input) == output
