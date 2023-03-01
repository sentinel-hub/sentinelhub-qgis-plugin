from qgis.core import QgsApplication

from ..dockwidget import SentinelHubDockWidget
from .testing_utilities import click_button


def test_widget_creation(qgis_app: QgsApplication) -> None:
    sh_widget = SentinelHubDockWidget()
    assert sh_widget is not None

    sh_widget.show()
    assert sh_widget.isVisible()

    sh_widget.close()
    qgis_app.processEvents()
    assert not sh_widget.isVisible()


def test_widget_button() -> None:
    sh_widget = SentinelHubDockWidget()
    click_button(sh_widget.currentExtentRadioButton)

    assert sh_widget.currentExtentRadioButton.isChecked()
    assert not sh_widget.customExtentRadioButton.isChecked()

    click_button(sh_widget.customExtentRadioButton)

    assert not sh_widget.currentExtentRadioButton.isChecked()
    assert sh_widget.customExtentRadioButton.isChecked()

    sh_widget.close()
