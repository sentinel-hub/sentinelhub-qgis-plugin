# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SentinelHubDockWidget
                                 A QGIS plugin
 SentinelHub
                             -------------------
        begin                : 2017-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2017 by s
        email                : s
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os.path
from sys import version_info

if version_info[0] >= 3:
    from PyQt5.QtWidgets import QDockWidget
    from PyQt5.uic import loadUiType
    from PyQt5.QtCore import pyqtSignal
else:
    from PyQt4.QtGui import QDockWidget
    from PyQt4.uic import loadUiType
    from PyQt4.QtCore import pyqtSignal

FORM_CLASS, _ = loadUiType(os.path.join(os.path.dirname(__file__),
                                        'SentinelHub_dockwidget_base.ui'))


class SentinelHubDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(SentinelHubDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

