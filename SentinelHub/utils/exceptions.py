"""
Utilities for handling exceptions and error messaging
"""


def show_message(iface, message, message_type):
    """ Show message for user

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    :param message: Message for user
    :param message: str
    :param message_type: Type of message
    :param message_type: MessageType
    """
    iface.messageBar().pushMessage(message_type.nice_name, message, level=message_type.level)
