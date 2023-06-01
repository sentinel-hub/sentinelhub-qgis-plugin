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
