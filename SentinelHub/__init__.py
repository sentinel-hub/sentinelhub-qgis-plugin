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


def classFactory(iface):
    """Load SentinelHub class from file SentinelHub.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # pylint: disable=invalid-name
    # pylint: disable=import-outside-toplevel
    # pylint: disable=unused-import

    # The following initializes UI
    from . import resources
    from .exceptions import MessageType, show_message
    from .utils.meta import add_external_path, ensure_import

    add_external_path()

    ensure_import("oauthlib")
    ensure_import("requests_oauthlib")
    ensure_import("requests")

    import sentinelhub

    show_message(f"Imported sentinelhub-py {sentinelhub.__version__} !!", MessageType.INFO)

    from .main import SentinelHubPlugin

    return SentinelHubPlugin(iface)
