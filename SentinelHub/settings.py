"""
Module containing parameters and settings for Sentinel Hub services
"""
import copy
from typing import Any

from PyQt5.QtCore import QSettings

from .constants import BaseUrl, CrsType, ExtentType, ImageFormat, ImagePriority, ServiceType, TimeType


class Settings(QSettings):
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

    def __init__(self, path=None):
        super().__init__(path)
        self.load_local_settings()
        self._auto_save = True

    def __setattr__(self, key: str, value: Any) -> None:
        """Whenever one of the attributes from _AUTO_SAVE_STORE_PARAMETERS is set it is automatically saved to
        QGIS store
        """
        if key in self._AUTO_SAVE_STORE_PARAMETERS:
            store_path = self._get_store_path(key)
            self.setValue(store_path, value)
        super().__setattr__(key, value)

    def load_local_settings(self) -> None:
        for parameter in self._STORE_PARAMETERS:
            store_path = self._get_store_path(parameter)
            store_value = self.value(store_path)

            if store_value is not None:
                setattr(self, parameter, str(store_value))

    @staticmethod
    def _get_store_path(parameter: str) -> str:
        return f"{Settings._STORE_NAMESPACE}/{parameter}"

    def save_credentials(self) -> None:
        """Saves settings to QGIS local store"""
        for parameter in self._CREDENTIAL_STORE_PARAMETERS:
            store_path = self._get_store_path(parameter)
            self.setValue(store_path, getattr(self, parameter))

    def copy(self) -> None:
        """Provides a copy of a Settings object instance"""
        return copy.copy(self)
