# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SentinelHubDockWidget
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
 Module wrapping the widget interface
"""

import os

from PyQt5.QtWidgets import QDockWidget
from PyQt5.uic import loadUiType
from PyQt5.QtCore import pyqtSignal


FORM_CLASS, _ = loadUiType(os.path.join(os.path.dirname(__file__), 'SentinelHub_dockwidget_base.ui'))


class SentinelHubDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """ Constructor
        """
        super().__init__(parent)
        self.setupUi(self)

    def closeEvent(self, event):
        """ When plugin is closed
        """
        self.closingPlugin.emit()
        event.accept()
