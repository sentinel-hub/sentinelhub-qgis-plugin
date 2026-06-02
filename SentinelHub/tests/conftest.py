"""
Module with global fixtures
"""

import pytest

from .testing_utilities import get_input_folder

INPUT_FOLDER = get_input_folder(__file__)


@pytest.fixture(name="input_folder")
def input_folder_fixture() -> str:
    """Fixture for the path to the folder with test inputs"""
    return INPUT_FOLDER


@pytest.fixture(scope="session")
def qgis_app() -> None:
    """Initialize a QgsApplication"""
    from qgis.core import QgsApplication  # noqa: E402

    app = QgsApplication([], True)
    app.initQgis()

    yield app
    app.exitQgis()


@pytest.fixture(scope="function")
def sh_widget() -> None:
    """Initialize the Sentinel Hub plugin widget"""
    from ..dockwidget import SentinelHubDockWidget  # noqa: E402

    widget = SentinelHubDockWidget()
    yield widget
    widget.close()


@pytest.fixture(scope="function")
def qsettings() -> None:
    """Create a temporary file and return a Settings instance"""

    from ..settings import Settings  # noqa: E402

    settings = Settings()
    yield settings

    settings.clear()
