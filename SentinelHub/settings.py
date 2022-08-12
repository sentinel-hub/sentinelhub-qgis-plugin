"""
Module containing parameters and settings for Sentinel Hub services
"""
import copy

from PyQt5.QtCore import QSettings

from .constants import BaseUrl, CrsType, ExtentType, ImageFormat, ImagePriority, ServiceType, TimeType


class Settings:
    """A class in charge of all settings. It also handles loading and saving of settings to QGIS settings store"""

    # pylint: disable=too-many-instance-attributes

    base_url = BaseUrl.MAIN
    client_id = ""
    client_secret = ""

    instance_id = ""
    service_type = ServiceType.WMS
    layer_id = ""
    data_source = ""
    crs = CrsType.POP_WEB
    maxcc = "100"
    priority = ImagePriority.MOST_RECENT.url_param

    active_time = TimeType.START_TIME
    start_time = ""
    end_time = ""
    is_exact_date = False

    image_format = ImageFormat.PNG.url_param
    show_logo = "false"

    download_extent_type = ExtentType.CURRENT
    resx = "10"
    resy = "10"
    lat_min = ""
    lat_max = ""
    lng_min = ""
    lng_max = ""

    download_folder = ""

    _STORE_NAMESPACE = "SentinelHub"
    _AUTO_SAVE_STORE_PARAMETERS = {
        "instance_id",
        "service_type",
        "layer_id",
        "crs",
        "start_time",
        "end_time",
        "priority",
        "image_format",
        "resx",
        "resy",
        "lat_min",
        "lat_max",
        "lng_min",
        "lng_max",
        "download_folder",
    }
    _auto_save = False
    _CREDENTIAL_STORE_PARAMETERS = {"base_url", "client_id", "client_secret"}
    _STORE_PARAMETERS = _AUTO_SAVE_STORE_PARAMETERS | _CREDENTIAL_STORE_PARAMETERS

    def __init__(self):
        self.load_local_settings()
        self._auto_save = True

    def __setattr__(self, key, value):
        """Whenever one of the attributes from _AUTO_SAVE_STORE_PARAMETERS is set it is automatically saved to
        QGIS store
        """
        if self._auto_save and key in self._AUTO_SAVE_STORE_PARAMETERS:
            store_path = self._get_store_path(key)
            QSettings().setValue(store_path, value)

        super().__setattr__(key, value)

    def load_local_settings(self):
        """Loads settings from QGIS local store"""
        qsettings = QSettings()

        for parameter in self._STORE_PARAMETERS:
            store_path = self._get_store_path(parameter)
            store_value = qsettings.value(store_path)

            if store_value is not None:
                setattr(self, parameter, str(store_value))

    def save_credentials(self):
        """Saves settings to QGIS local store"""
        qsettings = QSettings()

        for parameter in self._CREDENTIAL_STORE_PARAMETERS:
            store_path = self._get_store_path(parameter)
            qsettings.setValue(store_path, getattr(self, parameter))

    def _get_store_path(self, parameter_name):
        """Provides a location of the parameter in the local store"""
        return "{}/{}".format(self._STORE_NAMESPACE, parameter_name)

    def copy(self):
        """Provides a copy of a Settings object instance"""
        return copy.copy(self)
