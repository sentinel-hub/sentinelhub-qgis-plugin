"""
Module containing parameters and settings for Sentinel Hub services
"""
import copy

from PyQt5.QtCore import QSettings

from .constants import BaseUrl, ServiceType, CrsType, ExtentType


class Settings:
    """ A class in charge of all settings
    """
    base_url = BaseUrl.MAIN
    client_id = ''
    client_secret = ''

    instance_id = ''
    service_type = ServiceType.WMS
    layer = ''
    data_source = ''
    crs = CrsType.POP_WEB

    download_extent_type = ExtentType.CURRENT
    download_folder = ''

    active_time = 'time0'
    time0 = ''
    time1 = ''

    parameters = {
        'title': '',
        'layers': '',
        'maxcc': '100',
        'priority': 'mostRecent',
        'time': ''
    }

    # WFS parameters
    parameters_wfs = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typenames': 'S2.TILE',
        'maxfeatures': '100',
        'outputformat': 'application/json',
    }

    # WCS parameters
    parameters_wcs = {
        'service': 'wcs',
        'request': 'GetCoverage',
        'format': 'image/png',
        'showLogo': 'false',
        'transparent': 'false',
        'version': '1.1.1',
        'resx': '10',
        'resy': '10'
    }

    _STORE_NAMESPACE = 'SentinelHub'
    _AUTO_SAVE_STORE_PARAMETERS = {
        'instance_id',
        'service_type',
        'layer',
        'crs',
        'download_folder'
    }
    _auto_save = False
    _CREDENTIAL_STORE_PARAMETERS = {
        'base_url',
        'client_id',
        'client_secret'
    }
    _STORE_PARAMETERS = _AUTO_SAVE_STORE_PARAMETERS | _CREDENTIAL_STORE_PARAMETERS

    def __init__(self):
        self.load_local_settings()
        self._auto_save = True

    def __setattr__(self, key, value):
        if self._auto_save and key in self._AUTO_SAVE_STORE_PARAMETERS:
            store_path = self._get_store_path(key)
            QSettings().setValue(store_path, value)

        super().__setattr__(key, value)

    def load_local_settings(self):
        """ Loads settings from QGIS local store
        """
        qsettings = QSettings()

        for parameter in self._STORE_PARAMETERS:
            store_path = self._get_store_path(parameter)
            store_value = qsettings.value(store_path)

            if store_value is not None:
                setattr(self, parameter, str(store_value))

    def save_credentials(self):
        """ Saves settings to QGIS local store
        """
        qsettings = QSettings()

        for parameter in self._CREDENTIAL_STORE_PARAMETERS:
            store_path = self._get_store_path(parameter)
            qsettings.setValue(store_path, getattr(self, parameter))

    def _get_store_path(self, parameter_name):
        """ Provides a location of the parameter in the local store
        """
        return '{}/{}'.format(self._STORE_NAMESPACE, parameter_name)

    def copy(self):
        """ Provides a copy of a Settings object instance
        """
        return copy.copy(self)
