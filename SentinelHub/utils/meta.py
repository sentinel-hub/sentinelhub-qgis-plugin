"""
Utilities for handling meta information and procedures
"""
import os
import sys
from configparser import ConfigParser

from qgis.utils import plugins_metadata_parser


def configure_external_import_path() -> None:
    """Adds path to the folder with external packages to the list of Python package import paths. This way if a package
    doesn't exist in the Python environment used by QGIS it will be imported from the external folder.

    Note that on Windows QGIS typically uses its own Python environment with an installation of most common Python
    packages. But on Linux and macOS it typically uses the default system Python environment.
    """
    plugin_dir = _get_main_dir()
    external_path = os.path.join(plugin_dir, "external")

    sys.path.append(external_path)


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
