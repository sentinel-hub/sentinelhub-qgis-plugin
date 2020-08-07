"""
Module containing various utilities
"""
import os


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
