"""
Module with global fixtures
"""
import pytest
from testing_utilities import get_input_folder

INPUT_FOLDER = get_input_folder(__file__)


@pytest.fixture(name="input_folder")
def input_folder_fixture() -> str:
    return INPUT_FOLDER
