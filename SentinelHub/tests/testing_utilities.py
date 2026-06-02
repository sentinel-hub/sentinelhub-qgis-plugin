"""
Utility tools for writing unit tests
"""

import os


def get_input_folder(current_file: str) -> str:
    """Returns the path to the folder with test inputs"""
    return os.path.join(os.path.dirname(os.path.realpath(current_file)), "TestInputs")
