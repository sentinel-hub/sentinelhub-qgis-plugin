"""
Download client for Sentinel Hub service
"""
from xml.etree import ElementTree

import requests
from PyQt5.QtCore import QSettings

from .session import Session
from ..exceptions import DownloadError


class Client:

    _CACHED_SESSIONS = {}

    def __init__(self, iface, plugin_version):
        self.iface = iface
        self.plugin_version = plugin_version

    def download(self, url, timeout=None, session_settings=None):
        """ Downloads data from url and handles possible errors

        :param url: download url
        :type url: str
        :param timeout: A number of seconds before a request will timeout
        :type timeout: int or None
        :param session_settings: If specified, these settings will be used to create a session
        :type session_settings: Settings or None
        :return: download response or None if download failed
        :rtype: requests.response or None
        """
        proxy_dict, auth = get_proxy_config()
        headers = self._prepare_headers(session_settings)
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                proxies=proxy_dict,
                auth=auth
            )
            response.raise_for_status()
        except requests.RequestException as exception:
            raise DownloadError(get_error_message(exception))

        return response

    def _prepare_headers(self, session_settings):
        """ Prepares final headers by potentially joining them with session headers
        """
        headers = {
            'User-Agent': 'sh_qgis_plugin_{}'.format(self.plugin_version)
        }

        if session_settings:
            session = self._get_session(session_settings)
            headers = {
                **headers,
                **session.session_headers
            }

        return headers

    @staticmethod
    def _get_session(settings):
        """ Provides a session object either from cache or it creates a new one
        """
        cache_key = settings.client_id, settings.client_secret, settings.base_url
        if cache_key in Client._CACHED_SESSIONS:
            return Client._CACHED_SESSIONS[cache_key]

        session = Session(
            base_url=settings.base_url,
            client_id=settings.client_id,
            client_secret=settings.client_secret
        )

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
