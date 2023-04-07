# coding=utf-8
import pytest

pytest.importorskip("qgis.core")


from ..constants import ServiceType  # noqa: E402
from ..sentinelhub.common import DataSource, Layer  # noqa: E402
from ..settings import Settings  # noqa: E402
from ..utils.naming import get_filename, get_qgis_layer_name  # noqa: E402

CRS = "EPSG:3035"
MAXCC = "20"
PRIORITY = "mostRecent"
START_TIME = "2023-03-01"
END_TIME = "2023-03-10"
BOX = "12.44693, 41.870072, 12.541001, 41.917096"
FILENAME_CRS = "EPSG_3035"
FILENAME_TIME = "2023-03-01_2023-03-10"
FILENAME_BOX = "12.44693_41.870072_12.541001_41.917096"
LAYER_ID, DATA_SOURCE_ID = "1", "2"
IMAGE_FORMAT = "png"

qsettings = Settings()
qsettings.crs = CRS
qsettings.maxcc = MAXCC
qsettings.start_time = START_TIME
qsettings.end_time = END_TIME


@pytest.mark.parametrize(
    "data_source_type, layer_name, data_source_name, service_type, expected_str",
    [
        ("DEM", "TOPOGRAPHIC-VIS", "COP_30", ServiceType.WMS, f"COP_30 - TOPOGRAPHIC-VIS (WMS, {CRS})"),
        (
            "S1GRD",
            "VH-DB",
            "S1GRD_ASC",
            ServiceType.WMTS,
            f"S1GRD_ASC - VH-DB (WMTS, {START_TIME}/{END_TIME}, {PRIORITY}, {CRS})",
        ),
        (
            "S2L2A",
            "TRUE-COLOR",
            "S2L2A",
            ServiceType.WCS,
            f"S2L2A - TRUE-COLOR (WCS, {START_TIME}/{END_TIME}, {MAXCC}%, {PRIORITY}, {CRS})",
        ),
        (
            "S2L1C",
            "TRUE-COLOR",
            "S2L1C",
            ServiceType.WFS,
            f"S2L1C (WFS, {START_TIME}/{END_TIME}, {MAXCC}%, {PRIORITY}, {CRS})",
        ),
    ],
)
def test_get_qgis_layer_name(data_source_type, layer_name, data_source_name, service_type, expected_str) -> None:
    qsettings.service_type = service_type
    ds = DataSource(data_source_type, DATA_SOURCE_ID, name=data_source_name)
    layer = Layer(LAYER_ID, layer_name, ds)
    assert get_qgis_layer_name(qsettings, layer) == expected_str


@pytest.mark.parametrize(
    "data_source_type, data_source_name, layer_name, show_logo, expected_str",
    [
        (
            "DEM",
            "COP_30",
            "TOPOGRAPHIC-VIS",
            True,
            f"COP_30_{LAYER_ID}_{FILENAME_BOX}_{FILENAME_CRS}_logo.{IMAGE_FORMAT}",
        ),
        (
            "S1GRD",
            "S1GRD_ASC",
            "VH-DB",
            True,
            f"S1GRD_ASC_{LAYER_ID}_{FILENAME_TIME}_{FILENAME_BOX}_{FILENAME_CRS}_{PRIORITY}_logo.{IMAGE_FORMAT}",
        ),
        (
            "S2L2A",
            "S2L2A",
            "TRUE-COLOR",
            True,
            f"S2L2A_{LAYER_ID}_{FILENAME_TIME}_{FILENAME_BOX}_{FILENAME_CRS}_{MAXCC}_{PRIORITY}_logo.{IMAGE_FORMAT}",
        ),
        (
            "S2L1C",
            "S2L1C",
            "TRUE-COLOR",
            False,
            f"S2L1C_{LAYER_ID}_{FILENAME_TIME}_{FILENAME_BOX}_{FILENAME_CRS}_{MAXCC}_{PRIORITY}.{IMAGE_FORMAT}",
        ),
    ],
)
def test_get_filename(data_source_type, data_source_name, layer_name, show_logo, expected_str) -> None:
    qsettings.show_logo = show_logo
    ds = DataSource(data_source_type, DATA_SOURCE_ID, name=data_source_name)
    layer = Layer(LAYER_ID, layer_name, ds)
    assert get_filename(qsettings, layer, BOX) == expected_str
