import pytest

pytest.importorskip("qgis.core")

from qgis.core import QgsApplication  # noqa: E402
from qgis.PyQt.QtCore import QPoint, Qt  # noqa: E402
from qgis.PyQt.QtTest import QTest  # noqa: E402
from qgis.PyQt.QtWidgets import QAbstractButton  # noqa: E402

from ..dockwidget import SentinelHubDockWidget  # noqa: E402


def click_button(button: QAbstractButton) -> None:
    QTest.mouseClick(
        button,
        Qt.LeftButton,
        pos=QPoint(0, int(button.height() / 2)),
    )


def test_widget_creation(qgis_app: QgsApplication, sh_widget: SentinelHubDockWidget) -> None:
    sh_widget.show()
    assert sh_widget.isVisible()

    sh_widget.close()
    qgis_app.processEvents()
    assert not sh_widget.isVisible()


def test_widget_button(sh_widget: SentinelHubDockWidget) -> None:
    click_button(sh_widget.currentExtentRadioButton)

    assert sh_widget.currentExtentRadioButton.isChecked()
    assert not sh_widget.customExtentRadioButton.isChecked()

    click_button(sh_widget.customExtentRadioButton)

    assert not sh_widget.currentExtentRadioButton.isChecked()
    assert sh_widget.customExtentRadioButton.isChecked()
