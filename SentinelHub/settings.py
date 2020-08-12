# -*- coding: utf-8 -*-
"""
Module containing parameters and settings for Sentinel Hub services
"""
from PyQt5.QtCore import QSettings

from .constants import BaseUrl


class Settings:
    """ A class in charge of all settings
    """
    base_url = BaseUrl.MAIN
    client_id = None
    client_secret = None

    instance_id = None
    download_folder = None

    active_time = 'time0'
    time0 = ''
    time1 = ''

    parameters = {
        'title': '',
        'layers': '',
        'maxcc': '100',
        'priority': 'mostRecent',
        'time': '',
        'crs': 'EPSG:3857'
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

    _INSTANCE_ID_LOCATION = 'SentinelHub/instance_id'
    _DOWNLOAD_FOLDER_LOCATION = 'SentinelHub/download_folder'

    def __init__(self):
        self.load_local_settings()

    def load_local_settings(self):
        """ Loads settings from QGIS local store
        """
        qsettings = QSettings()

        self.instance_id = qsettings.value(self._INSTANCE_ID_LOCATION, '')
        self.download_folder = qsettings.value(self._DOWNLOAD_FOLDER_LOCATION, '')

        # Just in case something else would be saved
        if not isinstance(self.instance_id, str):
            self.instance_id = ''
        if not isinstance(self.download_folder, str):
            self.download_folder = ''

    def save_local_settings(self):
        """ Saves settings to QGIS local store
        """
        qsettings = QSettings()

        qsettings.setValue(self._INSTANCE_ID_LOCATION, self.instance_id)
        qsettings.setValue(self._DOWNLOAD_FOLDER_LOCATION, self.download_folder)
