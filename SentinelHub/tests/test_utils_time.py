from typing import Optional

import pytest

from ..utils.time import get_month_time_interval, parse_date


@pytest.mark.parametrize(
    "input_date, parsed_date",
    [
        ("01-02-2020", "2020-01-02"),
        ("2022/12/25", "2022-12-25"),
        ("2022, 12, 25", "2022-12-25"),
        ("14.7.2019", "2019-07-14"),
        ("2020-02-29", "2020-02-29"),
        ("2020-01-01", "2020-01-01"),
        ("", ""),
        ("abcd", None),
        ("12202022", None),
        ("2022/25/12", None),
        ("2017-01-32", None),
        ("2017-13-1", None),
        ("2017-02-29", None),
        ("2023-02-30", None),
    ],
)
def test_parse_date(input_date: str, parsed_date: Optional[str]) -> None:
    assert parse_date(input_date) == parsed_date


@pytest.mark.parametrize(
    "year, month, output",
    [
        (2019, 2, "2019-02-01/2019-02-28/P1D"),
        (2020, 2, "2020-02-01/2020-02-29/P1D"),
        (2022, 3, "2022-03-01/2022-03-31/P1D"),
    ],
)
def test_get_month_time_interval(year: int, month: int, output: str) -> None:
    assert get_month_time_interval(year, month) == output
