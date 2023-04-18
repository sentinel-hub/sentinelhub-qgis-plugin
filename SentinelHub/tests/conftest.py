"""
Module with global fixtures
"""


import os
import subprocess

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


@pytest.fixture(scope="function")
def sh_widget() -> None:
    """Initialize the Sentinel Hub plugin widget"""
    from ..dockwidget import SentinelHubDockWidget  # noqa: E402

    sh_widget = SentinelHubDockWidget()
    yield sh_widget
    sh_widget.close()


@pytest.fixture(scope="function")
def qsettings() -> None:
    """Create a temporary file and return a Settings instance"""

    from ..settings import Settings  # noqa: E402

    settings = Settings("test")
    yield settings
    settings.clear()


@pytest.fixture(scope="function")
def myenv():
    env_name = "env"

    # Create the virtual environment
    subprocess.run(["bash", "-c", "deactivate"])

    # Activate the virtual environment
    activate_path = os.path.join(env_name, "bin", "activate")
    subprocess.run(["bash", "-c", f"source {activate_path}"])

    # Upgrade pip and install the necessary packages

    yield

    activate_path = os.path.join(env_name, "bin", "activate")
    subprocess.run(["bash", "-c", f"source {activate_path}"])

    # Deactivate the virtual environment
