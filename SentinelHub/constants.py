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


class CrsType:
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
    """ Base URLs of some of the Sentinel Hub service deployments
    """
    MAIN = 'https://services.sentinel-hub.com'
    USWEST = 'https://services-uswest2.sentinel-hub.com'
    EOCLOUD = 'http://services.eocloud.sentinel-hub.com/v1/'


class ServiceType:
    """ Types of service used in the plugin
    """
    WMS = 'WMS'
    WCS = 'WCS'
    WMTS = 'WMTS'
    WFS = 'WFS'


AVAILABLE_SERVICE_TYPES = [ServiceType.WMS, ServiceType.WMTS, ServiceType.WFS]


class TimeType(Enum):
    """ A type of time
    """
    START_TIME = 'start_time'
    END_TIME = 'end_time'


class ExtentType(Enum):
    """ A type of map extend, either a current map bbox or a custom defined bbox
    """
    CURRENT = 'current'
    CUSTOM = 'custom'


DEFAULT_REQUEST_TIMEOUT = 30
USER_INFO_REQUEST_TIMEOUT = 1

VECTOR_LAYER_COLOR_OPACITY = 0.1

COVERAGE_REQUEST_TIMEOUT = 1
COVERAGE_MAX_BBOX_SIZE = 1000000

ACTION_COOLDOWN = 1
