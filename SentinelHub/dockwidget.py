"""
Module wrapping the widget interface
"""

import os

from PyQt5.QtWidgets import QDockWidget
from PyQt5.uic import loadUiType
from PyQt5.QtCore import pyqtSignal


FORM_CLASS, _ = loadUiType(os.path.join(os.path.dirname(__file__), 'dockwidget.ui'))


class SentinelHubDockWidget(QDockWidget, FORM_CLASS):
    """ The main widget class for interaction with UI
    """
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
