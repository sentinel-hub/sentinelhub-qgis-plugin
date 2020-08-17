"""
Utilities for handling exceptions and error messaging
"""


def action_handler(validators=None, timeout=None):
    pass


class CustomPluginException(Exception):
    """ Base class of all custom exceptions defined in the plugin
    """
    def __init__(self, message, message_type):
        """
        :param message: Exception message
        :type message: str
        :param message_type: A type of the message
        :type message_type: MessageType
        """
        self.message = message
        self.message_type = message_type
        super().__init__(message)
