"""
Module containing various utilities
"""
import os
import sys


def ensure_import(package_name):
    """ Ensures that a dependency package could be imported. It is either already available in the QGIS environment or
    it is available in a subfolder `external` of this plugin and should be added to PATH
    """
    try:
        __import__(package_name)
    except ImportError:
        plugin_dir = os.path.dirname(__file__)
        external_path = os.path.join(plugin_dir, 'external')

        for wheel_name in os.listdir(external_path):
            if wheel_name.startswith(package_name):
                wheel_path = os.path.join(external_path, wheel_name)
                sys.path.append(wheel_path)
                return
        raise ImportError('Package {} not found'.format(package_name))


def get_plugin_version():
    """ Provides the current plugin version by looking into a metadata file

    :return: A plugin version
    :rtype: str
    """
    plugin_dir = os.path.dirname(__file__)
    metadata_path = os.path.join(plugin_dir, 'metadata.txt')

    if not os.path.exists(metadata_path):
        return '?'

    with open(metadata_path) as metadata_file:
        for line in metadata_file:
            if line.startswith('version'):
                return line.split('=')[1].strip()

    raise ValueError('Failed to parse version from metadata.txt file')


def show_message(iface, message, message_type):
    """ Show message for user

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    :param message: Message for user
    :param message: str
    :param message_type: Type of message
    :param message_type: MessageType
    """
    iface.messageBar().pushMessage(message_type.nice_name, message, level=message_type.level)
