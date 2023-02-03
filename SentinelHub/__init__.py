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
    from .utils.meta import ensure_import

    ensure_import("aenum")
    ensure_import("alabaster")
    ensure_import("astroid")
    ensure_import("Babel")
    ensure_import("bcrypt")
    ensure_import("blinker")
    ensure_import("certifi")
    ensure_import("charset_normalizer")
    ensure_import("click")
    ensure_import("colorama")
    ensure_import("dataclasses_json")
    ensure_import("dill")
    ensure_import("docutils")
    ensure_import("marshmallow_enum")
    ensure_import("marshmallow")
    ensure_import("mypy_extensions")
    ensure_import("oauthlib")
    ensure_import("packaging")
    ensure_import("python_dateutil")
    ensure_import("requests_oauthlib")
    ensure_import("requests")
    ensure_import("sentinelhub")
    ensure_import("tqdm")
    ensure_import("typing_extensions")
    ensure_import("typing_inspect")
    ensure_import("utm")
    ensure_import("oauthlib")
    ensure_import("requests_oauthlib")

    from .main import SentinelHubPlugin

    return SentinelHubPlugin(iface)
