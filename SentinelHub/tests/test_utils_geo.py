# coding=utf-8
from typing import Tuple

import pytest

pytest.importorskip("qgis.core")

from qgis.core import QgsRectangle  # noqa: E402

from ..settings import Settings  # noqa: E402
from ..utils.geo import bbox_to_string, get_custom_bbox, is_bbox_too_large, is_supported_crs  # noqa: E402


@pytest.mark.parametrize(
    "input_coords, expected_coords",
    [
        (("1", "0", "1", "0"), (0, 0, 1, 1)),
        (("0", "0", "0", "0"), (0, 0, 0, 0)),
        (("2.0", "1.0", "8.0", "9.0"), (8, 1, 9, 2)),
    ],
)
def test_get_custom_bbox(
    input_coords: Tuple[str, str, str, str], expected_coords: Tuple[float, float, float, float]
) -> None:
    lat_max, lat_min, lng_max, lng_min = input_coords
    sett = Settings()
    sett.lat_max = lat_max
    sett.lat_min = lat_min
    sett.lng_max = lng_max
    sett.lng_min = lng_min

    assert get_custom_bbox(sett) == QgsRectangle(*expected_coords)


@pytest.mark.parametrize(
    "coords, crs, output",
    [
        ((10.00300000005, 20.123456789, 23.123456789, 3.123456789), "EPSG:4326", "3.123457,10.003,20.123457,23.123457"),
        ((10.00300000005, 20.123456789, 23.123456789, 3.123456789), "EPSG:3857", "10.0,3.12,23.12,20.12"),
        ((1.123456, 2.123456, 3.123456, 4.123456), "EPSG:3535", "1.12,2.12,3.12,4.12"),
    ],
)
def test_bbox_to_string(coords: Tuple[float, float, float, float], crs: str, output: str) -> None:
    coordinates = bbox_to_string(QgsRectangle(*coords), crs)
    assert coordinates == output


def test_is_bbox_too_large() -> None:
    assert is_bbox_too_large(QgsRectangle(0, 0, 0, 1), "EPSG:4326", 1e5)
    assert not is_bbox_too_large(QgsRectangle(0, 0, 0, 1), "EPSG:4326", 1e6)


@pytest.mark.parametrize(
    "crs",
    ["EPSG:3857", "EPSG:3535", "EPSG:3030", "EPSG:4326"],
)
def test_is_supported_crs(crs: str) -> None:
    assert is_supported_crs(crs)
