"""
Utilities for handling meta information and procedures
"""
import os
import sys
from configparser import ConfigParser

from qgis.utils import plugins_metadata_parser


def ensure_import(package_name):
    """ Ensures that a dependency package could be imported. It is either already available in the QGIS environment or
    it is available in a subfolder `external` of this plugin and should be added to PATH
    """
    try:
        __import__(package_name)
    except ImportError:
        plugin_dir = _get_main_dir()
        external_path = os.path.join(plugin_dir, 'external')

        for wheel_name in os.listdir(external_path):
            if wheel_name.startswith(package_name):
                wheel_path = os.path.join(external_path, wheel_name)
                sys.path.append(wheel_path)
                return
        raise ImportError('Package {} not found'.format(package_name))


def _get_plugin_name(missing='SentinelHub'):
    """ Reads the plugin name from metadata
    """
    plugin_dir = _get_main_dir()
    metadata_path = os.path.join(plugin_dir, 'metadata.txt')

    if not os.path.exists(metadata_path):
        return missing

    config = ConfigParser()
    config.read(metadata_path)

    return config['general']['name']


def get_plugin_version():
    """ Provides the current plugin version by looking into a metadata file

    :return: A plugin version
    :rtype: str
    """
    return plugins_metadata_parser[PLUGIN_NAME]['general']['version']


def _get_main_dir():
    """ Provides a path to the main plugin folder
    """
    utils_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(utils_dir, '..'))


PLUGIN_NAME = _get_plugin_name()
