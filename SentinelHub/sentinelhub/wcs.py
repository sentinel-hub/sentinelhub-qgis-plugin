"""
Utilities for interacting with Sentinel Hub WCS service
"""
import os

from .ogc import get_wcs_url
from ..constants import CrsType, ExtentType
from ..utils.geo import bbox_to_string
from ..utils.naming import get_filename


def download_wcs_image(settings, layer, bbox, client):
    crs = None if settings.download_extent_type is ExtentType.CURRENT else CrsType.WGS84
    bbox_str = bbox_to_string(bbox, crs)
    url = get_wcs_url(settings, layer, bbox_str, crs)

    filename = get_filename(settings, layer, bbox_str)
    path = os.path.join(settings.download_folder, filename)

    response = client.download(url, stream=True)

    with open(path, 'wb') as fp:
        fp.write(response.content)
