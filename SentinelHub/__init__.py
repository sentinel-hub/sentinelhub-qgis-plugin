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
from __future__ import absolute_import


def classFactory(iface):
    """Load SentinelHub class from file SentinelHub.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # pylint: disable=invalid-name
    # pylint: disable=import-outside-toplevel
    # pylint: disable=unused-import

    # The following initializes UI
    import os
    import sys

    from . import resources
    from .exceptions import MessageType, show_message
    from .utils.meta import ensure_import

    wheels = {
        "numpy": None,
        "requests_oauthlib": "1.3.1",
        "urllib3": None,
        "charset_normalizer": None,
        "idna": None,
        "certifi": None,
        "requests": "2.27.0",
        "PIL": "9.5.0",
    }
    for library, version in wheels.items():
        ensure_import(library, version)

    external = os.path.abspath(os.path.dirname(__file__) + "/external")
    if os.path.exists(external) and external not in sys.path:
        sys.path.insert(0, external)

    import sentinelhub

    show_message(f"Imported sentinelhub-py {sentinelhub.__version__} !!", MessageType.INFO)

    from .main import SentinelHubPlugin

    return SentinelHubPlugin(iface)
