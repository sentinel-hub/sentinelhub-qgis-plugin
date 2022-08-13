"""
/***************************************************************************
 SentinelHub
                             -------------------
        begin                : 2017-07-07
        copyright            : (C) 2020 by Sinergise
        email                : info@sentinel-hub.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

WHEELS = [  # TODO: separate wheels requirements and import them from requirements file
    "oauthlib",
    "requests-oauthlib",
    "click",
    "aenum",
    "tqdm",
    "dataclasses-json",
    "marshmallow",
    "marshmallow-enum",
    "packaging",
    "typing-inspect",
    "mypy-extensions",
    "typing-extensions",
]


def classFactory(iface):
    """Load SentinelHub class from file SentinelHub.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # pylint: disable=invalid-name
    # pylint: disable=import-outside-toplevel
    # pylint: disable=unused-import

    from .utils.meta import configure_external_import_path, ensure_wheel_import

    configure_external_import_path()
    for package_name in WHEELS:
        ensure_wheel_import(package_name)

    # TODO: this import is just for testing purpose:
    import sentinelhub

    from .exceptions import MessageType, show_message

    show_message(f"Imported sentinelhub-py {sentinelhub.__version__} !!", MessageType.INFO)

    # The following initializes UI
    from . import resources
    from .main import SentinelHubPlugin

    return SentinelHubPlugin(iface)
