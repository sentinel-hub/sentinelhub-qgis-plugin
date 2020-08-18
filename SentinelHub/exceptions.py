"""
Utilities for handling exceptions and error messaging
"""
import time
from abc import ABC, abstractmethod

from qgis.utils import iface

from .utils.meta import PLUGIN_NAME
from .constants import MessageType, ExtentType


def show_message(message, message_type):
    """ Show message for user

    :param message: Message for user
    :param message: str
    :param message_type: Type of message
    :param message_type: MessageType
    """
    iface.messageBar().pushMessage(PLUGIN_NAME, message, level=message_type.level)


def action_handler(validators=(), cooldown=0, suppressed_exceptions=()):
    """ A decorator for handling plugin actions.

    It is designed to handle exceptions, do parameter validations and prevents a method to be called too ofter. It can
    only be applied to the methods of the main SentinelHubPlugin class

    :param validators: A tuple of validators
    :type validators: tuple(BaseValidator)
    :param cooldown: A number of seconds after which an action could be called again
    :type cooldown: float or int or None
    :param suppressed_exceptions: A tuple of exceptions to suppress
    :type suppressed_exceptions: tuple(Exception)
    """
    return ActionHandler(validators, cooldown, suppressed_exceptions)


class ActionHandler:
    """ A class for handling plugin actions
    """
    def __init__(self, validators, cooldown, suppressed_exceptions):
        self.validators = validators
        self.cooldown = cooldown
        self.suppressed_exceptions = suppressed_exceptions

        self.last_time_called = -1

    def __call__(self, action_method):
        """ Method that builds a replacement action method
        """

        def new_action_method(plugin, *args, **kwargs):
            try:
                if self.last_time_called + self.cooldown > time.time():
                    raise CooldownException(self.cooldown)
                self.last_time_called = time.time()

                for validator in self.validators:
                    validator().validate(plugin)

                action_method(plugin, *args, **kwargs)
            except self.suppressed_exceptions:
                pass
            except PluginException as exception:
                show_message(exception.message, exception.message_type)

        return new_action_method


class PluginException(Exception):
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


class CooldownException(PluginException):
    """ This is raised if the same action is called again too fast after the first call
    """
    def __init__(self, cooldown):
        """
        :param cooldown: A number of seconds after which an action could be called again
        :type cooldown: float or int
        """
        message = 'Please wait at least {} seconds before doing this again'.format(cooldown)
        super().__init__(message, MessageType.WARNING)


class ValidationException(PluginException):
    """ This is raised by validators
    """
    def __init__(self, message):
        super().__init__(message, MessageType.WARNING)


class DownloadError(PluginException):
    """ An error that is raised if a download procedure fails
    """
    def __init__(self, message):
        super().__init__(message, MessageType.CRITICAL)


class SessionError(DownloadError):
    """ An error that is raised if a session creation fails
    """
    def __init__(self):
        super().__init__('Authentication failed, check your credentials')


class BBoxTransformError(PluginException):
    """ An error that is raised if a bounding box transformation from one CRS to another fails
    """
    def __init__(self, crs):
        super().__init__('Failed to transform the current bounding box into {}, '
                         'try to zoom in or switch CRS'.format(crs), MessageType.CRITICAL)


class BaseValidator(ABC):
    """ A base validation class
    """
    MESSAGE = 'Validation failed'

    def validate(self, plugin):
        """ Runs a validation
        """
        if not self.check(plugin):
            raise ValidationException(self.MESSAGE)

    @abstractmethod
    def check(self, plugin):
        """ A method that should return True if validation is successful or False otherwise
        """
        raise NotImplementedError


class LoginValidator(BaseValidator):
    """ Checks if a user is logged in
    """
    MESSAGE = 'Please login'

    def check(self, plugin):
        return plugin.manager is not None


class ConfigurationValidator(BaseValidator):
    """ Checks if a user set up a configuration
    """
    MESSAGE = 'Please select a configuration'

    def check(self, plugin):
        LoginValidator().validate(plugin)
        return bool(plugin.settings.instance_id)


class LayerValidator(BaseValidator):
    """ Checks if a user chose a layer
    """
    MESSAGE = 'Please select a layer'

    def check(self, plugin):
        ConfigurationValidator().validate(plugin)
        return bool(plugin.settings.layer_id)


class ResolutionValidator(BaseValidator):
    """ Checks if resolution parameters are set
    """
    MESSAGE = 'Please set resolution of the image to download'

    def check(self, plugin):
        return plugin.settings.resx and plugin.settings.resy


class ExtentValidator(BaseValidator):
    """ Check if a custom extent for download is set
    """
    MESSAGE = 'Please specify a custom bounding box'

    def check(self, plugin):
        if plugin.settings.download_extent_type is not ExtentType.CUSTOM:
            return True

        return plugin.settings.lat_min and plugin.settings.lat_max and \
            plugin.settings.lng_min and plugin.settings.lng_max


class DownloadFolderValidator(BaseValidator):
    """ Check if a download folder is set
    """
    MESSAGE = 'Please set a download folder'

    def check(self, plugin):
        return bool(plugin.settings.download_folder)
