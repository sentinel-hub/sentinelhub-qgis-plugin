"""
Geographical utilities
"""
import math

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle

from ..constants import CrsType


def get_bbox(iface, crs):
    """ Get a bounding box of the current window
    """
    bbox = iface.mapCanvas().extent()
    target_crs = QgsCoordinateReferenceSystem(crs)

    current_crs_authority = iface.mapCanvas().mapSettings().destinationCrs().authid()
    current_crs = QgsCoordinateReferenceSystem(current_crs_authority)

    if current_crs != target_crs:
        xform = QgsCoordinateTransform(current_crs, target_crs, QgsProject.instance())
        # if target CRS is UTM and bbox is out of UTM bounds this fails, not sure how to fix
        bbox = xform.transform(bbox)

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
    except BaseException:
        return

    return max(width, height) > size_limit


def _get_bbox_size(bbox, crs):
    """ Returns an approximate width and height of bounding box in meters
    """
    bbox_crs = QgsCoordinateReferenceSystem(crs)

    utm_crs = QgsCoordinateReferenceSystem(
        _lng_to_utm_zone(
            (bbox.xMinimum() + bbox.xMaximum()) / 2,
            (bbox.yMinimum() + bbox.yMaximum()) / 2
        )
    )

    xform = QgsCoordinateTransform(bbox_crs, utm_crs, QgsProject.instance())
    bbox = xform.transform(bbox)
    width = abs(bbox.xMaximum() - bbox.xMinimum())
    height = abs(bbox.yMinimum() - bbox.yMaximum())
    return width, height


def _lng_to_utm_zone(longitude, latitude):
    """ Calculates UTM zone from latitude and longitude
    """
    zone = int(math.floor((longitude + 180) / 6) + 1)
    hemisphere = 6 if latitude > 0 else 7
    return 'EPSG:32{0}{1:02d}'.format(hemisphere, zone)
