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
