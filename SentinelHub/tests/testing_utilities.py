"""
Utility tools for writing unit tests
"""
import os

from qgis.PyQt.QtCore import QPoint, Qt
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QAbstractButton


def get_input_folder(current_file: str) -> str:
    return os.path.join(os.path.dirname(os.path.realpath(current_file)), "TestInputs")


def click_button(button: QAbstractButton) -> None:
    QTest.mouseClick(
        button,
        Qt.LeftButton,
        pos=QPoint(0, int(button.height() / 2)),
    )
