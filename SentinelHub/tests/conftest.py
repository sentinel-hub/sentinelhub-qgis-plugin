"""
Module with global fixtures
"""
import pytest

from .testing_utilities import get_input_folder

INPUT_FOLDER = get_input_folder(__file__)


@pytest.fixture(name="input_folder")
def input_folder_fixture() -> str:
    return INPUT_FOLDER


@pytest.fixture(scope="session")
def qgis_app() -> None:
    """Initialize a QgsApplication"""
    from qgis.core import QgsApplication  # noqa: E402

    qgis_app = QgsApplication([], True)
    qgis_app.initQgis()

    yield qgis_app
    qgis_app.exitQgis()
