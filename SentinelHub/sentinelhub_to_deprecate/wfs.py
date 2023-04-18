"""
Utilities for interacting with Sentinel Hub WFS service
"""
import functools

from ..constants import COVERAGE_REQUEST_TIMEOUT, CrsType
from ..exceptions import DownloadError
from ..utils.geo import bbox_to_string
from .ogc import get_wfs_url


def get_cloud_cover(settings, layer, bbox, time_interval, client):
    """Finds all available dates and their cloud coverage"""
    bbox_str = bbox_to_string(bbox, CrsType.POP_WEB)

    wfs_url = get_wfs_url(settings, layer, bbox_str, time_interval, maxcc=100)

    try:
        return _cached_cloud_cover(wfs_url, client)
    except DownloadError:
        return {}


@functools.lru_cache(maxsize=10**4)
def _cached_cloud_cover(wfs_url, client):
    """Caches WFS calls to prevent too many repeating calls"""
    results = client.download(wfs_url, timeout=COVERAGE_REQUEST_TIMEOUT).json()

    cloud_cover_map = {}
    for feature in results["features"]:
        date_str = str(feature["properties"]["date"])
        cloud_cover_map[date_str] = float(feature["properties"].get("cloudCoverPercentage", 0))

    return cloud_cover_map
