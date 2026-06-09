"""
Utility tools for writing unit tests
"""
import os


def get_input_folder(current_file: str) -> str:
    return os.path.join(os.path.dirname(os.path.realpath(current_file)), "TestInputs")
