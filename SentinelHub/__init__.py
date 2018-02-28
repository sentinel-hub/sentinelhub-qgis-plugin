# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SentinelHub
                                 A QGIS plugin
 SentinelHub
                             -------------------
        begin                : 2017-07-07
        copyright            : (C) 2017 by s
        email                : s
        git sha              : $Format:%H$
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

# noinspection PyPep8Naming
# pylint: disable=invalid-name


def classFactory(iface):
    """Load SentinelHub class from file SentinelHub.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .SentinelHub import SentinelHub
    return SentinelHub(iface)
