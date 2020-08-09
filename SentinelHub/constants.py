"""
Module containing constants
"""
from enum import Enum

from qgis.core import Qgis


class MessageType(Enum):
    """ Types of messages to display in a message bar
    """
    INFO = 'Info', Qgis.Info
    WARNING = 'Warning', Qgis.Warning
    CRITICAL = 'Error', Qgis.Critical
    SUCCESS = 'Success', Qgis.Success

    @property
    def nice_name(self):
        """ Provides a nice name
        """
        return self.value[0]

    @property
    def level(self):
        """ Provides a QGIS message flag
        """
        return self.value[1]


class CRS:
    """ Class containing CRS EPSG strings
    """
    POP_WEB = 'EPSG:3857'
    WGS84 = 'EPSG:4326'


class _BaseParameter(Enum):
    """ A base class for parameters
    """
    @property
    def url_param(self):
        """ Parameter to be used for service requests
        """
        return self.value[0]

    @property
    def nice_name(self):
        """ Nice name to display in UI
        """
        return self.value[1]


class ImagePriority(_BaseParameter):
    """ Image priority parameter for Sentinel Hub service
    """
    MOST_RECENT = 'mostRecent', 'Most recent'
    LEAST_RECENT = 'leastRecent', 'Least recent'
    LEAST_CC = 'leastCC', 'Least cloud coverage'


class ImageFormat(_BaseParameter):
    """ Image formats
    """
    PNG = 'image/png', 'PNG'
    JPEG = 'image/jpeg', 'JPEG'
    TIFF = 'image/tiff', 'TIFF'


class BaseUrl:
    MAIN = 'https://services.sentinel-hub.com/ogc/'
    USWEST = 'https://services-uswest2.sentinel-hub.com/ogc/'
    EOCLOUD = 'http://services.eocloud.sentinel-hub.com/v1/'


SERVICE_TYPES = [
    'WMS',
    'WMTS'
]

MAX_CLOUD_COVER_IMAGE_SIZE = 1000000
