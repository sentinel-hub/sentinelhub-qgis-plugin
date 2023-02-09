# coding=utf-8
import os

from qgis.core import QgsCoordinateReferenceSystem, QgsProviderRegistry, QgsRasterLayer

CRS = "EPSG:4326"
WKT = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",'
    "0.0174532925199433]]"
)


def test_providers_registry():
    r = QgsProviderRegistry.instance()
    assert "gdal" in r.providerList()
    assert "ogr" in r.providerList()


def test_projection_reading():
    crs = QgsCoordinateReferenceSystem()
    crs.createFromWkt(WKT)
    auth_id = crs.authid()
    assert auth_id == CRS


def test_loaded_raster(input_folder):
    input_raster = os.path.join(input_folder, "raster_sample.tiff")
    title = "TestRaster"
    layer = QgsRasterLayer(input_raster, title)
    auth_id = layer.crs().authid()
    assert auth_id == CRS
