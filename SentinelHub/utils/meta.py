"""
Utilities for handling meta information and procedures
"""
import os
import sys
from configparser import ConfigParser

from qgis.utils import plugins_metadata_parser


def add_external_path():
    plugin_dir = _get_main_dir()

    external = os.path.join(plugin_dir, "external")

    if os.path.exists(external) and external not in sys.path:
        sys.path.insert(0, external)


def ensure_import(package_name: str, version: str = None) -> None:
    """Ensures that a dependency package could be imported. It is either already available in the QGIS environment or
    it is available in a subfolder `external` of this plugin and should be added to PATH
    """
    package_name = package_name.replace("-", "_")

    if not _is_package_compatible(package_name, version):
        plugin_dir = _get_main_dir()
        external_path = os.path.join(plugin_dir, "external")

        for wheel_name in sorted(os.listdir(external_path)):
            if wheel_name.startswith(package_name) and wheel_name.endswith(".whl"):
                wheel_path = os.path.join(external_path, wheel_name)
                sys.path.insert(0, wheel_path)
                return
    try:
        __import__(package_name)
    except ImportError as exception:
        raise ImportError(f"A wheel of a package {package_name} not found in {external_path}") from exception


def _is_package_compatible(package_name: str, version: str = None) -> bool:
    """Checks if the package is installed and meets version requirements"""
    try:
        package_version = version(package_name)
        if version is None:
            return True
        else:
            return package_version >= version
    except Exception:
        return False


def _get_plugin_name(missing="SentinelHub"):
    """Reads the plugin name from metadata"""
    plugin_dir = _get_main_dir()
    metadata_path = os.path.join(plugin_dir, "metadata.txt")

    if not os.path.exists(metadata_path):
        return missing

    config = ConfigParser()
    config.read(metadata_path)

    return config["general"]["name"]


def get_plugin_version():
    """Provides the current plugin version by looking into a metadata file

    :return: A plugin version
    :rtype: str
    """
    return plugins_metadata_parser[PLUGIN_NAME]["general"]["version"]


def _get_main_dir():
    """Provides a path to the main plugin folder"""
    utils_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(utils_dir, ".."))


PLUGIN_NAME = _get_plugin_name()
