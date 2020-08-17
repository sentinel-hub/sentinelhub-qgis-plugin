"""
Download client for Sentinel Hub service
"""
from xml.etree import ElementTree

import requests
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from PyQt5.QtCore import QSettings

from .session import Session
from ..constants import MessageType
from ..utils.exceptions import show_message


class Client:

    _CACHED_SESSIONS = {}

    def __init__(self, iface, plugin_version):
        self.iface = iface
        self.plugin_version = plugin_version

    def download(self, url, stream=False, use_session=False, ignore_exception=False, settings=None):
        """ Downloads data from url and handles possible errors

        :param url: download url
        :type url: str
        :param stream: True if download should be streamed and False otherwise
        :type stream: bool
        :param raise_invalid_id: If True an InvalidInstanceId exception will be raised in case service returns HTTP 400
        :type raise_invalid_id: bool
        :param ignore_exception: If True no error messages will be shown in case of exceptions
        :type ignore_exception: bool
        :return: download response or None if download failed
        :rtype: requests.response or None
        """
        try:
            proxy_dict, auth = get_proxy_config()
            response = requests.get(
                url,
                stream=stream,
                headers=self._prepare_headers(use_session, settings),
                proxies=proxy_dict,
                auth=auth
            )
            response.raise_for_status()
        except requests.RequestException as exception:
            if ignore_exception:
                return

            show_message(self.iface, get_error_message(exception), MessageType.CRITICAL)
            response = None

        return response

    def _prepare_headers(self, use_session, settings):
        """ Prepares final headers by potentially joining them with session headers
        """
        headers = {
            'User-Agent': 'sh_qgis_plugin_{}'.format(self.plugin_version)
        }

        if use_session:
            session = self._get_session(settings)
            headers = {
                **headers,
                **session.session_headers
            }

        return headers

    def _get_session(self, settings):
        """ Provides a session object either from cache or it creates a new one
        """
        cache_key = settings.client_id, settings.client_secret, settings.base_url
        if cache_key in Client._CACHED_SESSIONS:
            return Client._CACHED_SESSIONS[cache_key]

        try:
            session = Session(
                base_url=settings.base_url,
                client_id=settings.client_id,
                client_secret=settings.client_secret
            )
        except OAuth2Error as exception:
            show_message(self.iface, exception.error, MessageType.CRITICAL)  # TODO: fix this by moving logging to the main

        Client._CACHED_SESSIONS[cache_key] = session
        return session


def get_error_message(exception):
    """ Creates an error message from the given exception

    :param exception: Exception obtained during download
    :type exception: requests.RequestException
    :return: error message
    :rtype: str
    """
    message = '{}: '.format(exception.__class__.__name__)

    if isinstance(exception, requests.ConnectionError):
        message += 'Cannot access service, check your internet connection.'

        enabled, host, port, _, _ = get_proxy_from_qsettings()
        if enabled:
            message += ' QGIS is configured to use proxy: {}'.format(host)
            if port:
                message += ':{}'.format(port)

        return message

    if isinstance(exception, requests.HTTPError):
        try:
            server_message = ''
            for elem in ElementTree.fromstring(exception.response.content):
                if 'ServiceException' in elem.tag:
                    server_message += elem.text.strip('\n\t ')
        except ElementTree.ParseError:
            server_message = exception.response.text.strip('\n\t ')
        server_message = server_message.encode('ascii', errors='ignore').decode('utf-8')
        if 'Config instance "instance.' in server_message:
            instance_id = server_message.split('"')[1][9:]
            server_message = 'Invalid instance id: {}'.format(instance_id)
        return message + 'server response: "{}"'.format(server_message)

    return message + str(exception)


def get_proxy_config():
    """ Get proxy config from QSettings and builds proxy parameters

    :return: dictionary of transfer protocols mapped to addresses, also authentication if set in QSettings
    :rtype: (dict, requests.auth.HTTPProxyAuth) or (dict, None)
    """
    enabled, host, port, user, password = get_proxy_from_qsettings()

    proxy_dict = {}
    if enabled and host:
        port_str = ':{}'.format(port) if port else ''
        for protocol in ['http', 'https', 'ftp']:
            proxy_dict[protocol] = '{}://{}{}'.format(protocol, host, port_str)

    auth = requests.auth.HTTPProxyAuth(user, password) if enabled and user and password else None

    return proxy_dict, auth


def get_proxy_from_qsettings():
    """ Gets the proxy configuration from QSettings

    :return: Proxy settings: flag specifying if proxy is enabled, host, port, user and password
    :rtype: tuple(str)
    """
    qsettings = QSettings()
    qsettings.beginGroup('proxy')
    enabled = str(qsettings.value('proxyEnabled')).lower() == 'true'
    host = qsettings.value('proxyHost')
    port = qsettings.value('proxyPort')
    user = qsettings.value('proxyUser')
    password = qsettings.value('proxyPassword')
    qsettings.endGroup()
    return enabled, host, port, user, password
