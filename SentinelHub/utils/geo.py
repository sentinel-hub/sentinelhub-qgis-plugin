"""
Geographical utilities
"""
import math

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle, QgsCsException
from qgis.utils import iface

from ..constants import CrsType
from ..exceptions import BBoxTransformError


def get_bbox(crs):
    """ Get a bounding box of the current window
    """
    bbox = iface.mapCanvas().extent()
    target_crs = QgsCoordinateReferenceSystem(crs)

    current_crs_authority = iface.mapCanvas().mapSettings().destinationCrs().authid()
    current_crs = QgsCoordinateReferenceSystem(current_crs_authority)

    if current_crs != target_crs:
        xform = QgsCoordinateTransform(current_crs, target_crs, QgsProject.instance())
        try:
            bbox = xform.transform(bbox)
        except QgsCsException:
            raise BBoxTransformError(crs)

    return bbox


def get_custom_bbox(settings):
    """ Creates a bbox from settings parameters
    """
    lat_min = min(float(settings.lat_min), float(settings.lat_max))
    lat_max = max(float(settings.lat_min), float(settings.lat_max))
    lng_min = min(float(settings.lng_min), float(settings.lng_max))
    lng_max = max(float(settings.lng_min), float(settings.lng_max))
    return QgsRectangle(lng_min, lat_min, lng_max, lat_max)


def bbox_to_string(bbox, crs):
    """ Transforms a bounding box into string a string of comma-separated values
    """
    target_crs = QgsCoordinateReferenceSystem(crs)
    if target_crs.authid() == CrsType.WGS84:
        precision = 6
        bbox_list = [bbox.yMinimum(), bbox.xMinimum(), bbox.yMaximum(), bbox.xMaximum()]
    else:
        precision = 2
        bbox_list = [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]

    return ','.join(map(lambda coord: str(round(coord, precision)), bbox_list))


def is_bbox_too_large(bbox, crs, size_limit):
    """ Checks if any of the bbox dimensions is larger than a given size limit
    """
    try:
        width, height = _get_bbox_size(bbox, crs)
    except BBoxTransformError:
        return True

    return max(width, height) > size_limit


def is_current_map_crs(crs_id):
    """ Checks if the current underlying CRS on the map is given CRS
    """
    return iface.mapCanvas().mapSettings().destinationCrs().authid() == crs_id


def is_supported_crs(crs_id):
    """ Determines if QGIS recognizes the CRS from a given id string
    """
    return bool(QgsCoordinateReferenceSystem(crs_id).authid())


def _get_bbox_size(bbox, crs):
    """ Returns an approximate width and height of bounding box in meters
    """
    bbox_crs = QgsCoordinateReferenceSystem(crs)

    utm_epsg = _lng_to_utm_zone(
        (bbox.xMinimum() + bbox.xMaximum()) / 2,
        (bbox.yMinimum() + bbox.yMaximum()) / 2
    )
    utm_crs = QgsCoordinateReferenceSystem(utm_epsg)

    xform = QgsCoordinateTransform(bbox_crs, utm_crs, QgsProject.instance())

    try:
        bbox = xform.transform(bbox)
    except QgsCsException:
        raise BBoxTransformError(utm_epsg)

    width = abs(bbox.xMaximum() - bbox.xMinimum())
    height = abs(bbox.yMinimum() - bbox.yMaximum())
    return width, height


def _lng_to_utm_zone(longitude, latitude):
    """ Calculates UTM zone from latitude and longitude
    """
    zone = int(math.floor((longitude + 180) / 6) + 1)
    hemisphere = 6 if latitude > 0 else 7
    return 'EPSG:32{0}{1:02d}'.format(hemisphere, zone)
