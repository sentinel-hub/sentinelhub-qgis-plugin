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
    MAIN = 'https://services.sentinel-hub.com'
    USWEST = 'https://services-uswest2.sentinel-hub.com'
    EOCLOUD = 'http://services.eocloud.sentinel-hub.com/v1/'


class ServiceType:
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


MAX_CLOUD_COVER_BBOX_SIZE = 1000000

DATA_SOURCES = {
    'S2L1C': {
        'url': BaseUrl.MAIN,
        'wfs_name': 'S2.TILE',
        'pretty_name': 'Sentinel-2 L1C'
    },
    'S2L2A': {
        'url': BaseUrl.MAIN,
        'wfs_name': 'DSS2',
        'pretty_name': 'Sentinel-2 L2A'
    },
    'S1GRD': {
        'url': BaseUrl.MAIN,
        'wfs_name': 'DSS3',
        'pretty_name': 'Sentinel-1'
    },
    'L8L1C': {
        'url': BaseUrl.USWEST,
        'wfs_name': 'DSS6',
        'pretty_name': 'Landsat 8'
    },
    'MODIS': {
        'url': BaseUrl.USWEST,
        'wfs_name': 'DSS5',
        'pretty_name': 'MODIS'
    },
    'DEM': {
        'url': BaseUrl.USWEST,
        'wfs_name': 'DSS4',
        'pretty_name': 'DEM'
    }
}
