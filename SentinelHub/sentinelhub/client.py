"""
Download client for Sentinel Hub service
"""

from defusedxml import ElementTree

import requests

from ..constants import DEFAULT_REQUEST_TIMEOUT
from ..exceptions import DownloadError
from ..utils.meta import get_plugin_version
from .proxy import get_proxies, get_proxy_description
from .session import Session


class Client:
    """Handles all interactions with Sentinel Hub service

    Note that the class is caching sessions to a class attribute in order to minimize the number of times a new
    session has to be created.
    """

    _CACHED_SESSIONS = {}

    def download(self, url, timeout=DEFAULT_REQUEST_TIMEOUT, session_settings=None):
        """Downloads data from url and handles possible errors

        :param url: download url
        :type url: str
        :param timeout: A number of seconds before a request will time out
        :type timeout: int
        :param session_settings: If specified, these settings will be used to create a session
        :type session_settings: Settings or None
        :return: download response or None if download failed
        :rtype: requests.Response or None
        """
        headers = self._prepare_headers(session_settings)
        try:
            response = requests.get(url, headers=headers, timeout=timeout, proxies=get_proxies(url))
            response.raise_for_status()
        except requests.RequestException as exception:
            raise DownloadError(get_error_message(exception)) from exception

        return response

    def _prepare_headers(self, session_settings):
        """Prepares final headers by potentially joining them with session headers"""
        headers = {"User-Agent": f"sh_qgis_plugin_{get_plugin_version()}"}

        if session_settings:
            session = self._get_session(session_settings)
            headers = {**headers, **session.session_headers}

        return headers

    @staticmethod
    def _get_session(settings):
        """Provides a session object either from cache or it creates a new one"""
        cache_key = settings.client_id, settings.client_secret, settings.base_url
        if cache_key in Client._CACHED_SESSIONS:
            return Client._CACHED_SESSIONS[cache_key]

        session = Session(
            base_url=settings.base_url, client_id=settings.client_id, client_secret=settings.client_secret
        )

        Client._CACHED_SESSIONS[cache_key] = session
        return session


def get_error_message(exception):
    """Creates an error message from the given exception

    :param exception: Exception obtained during download
    :type exception: requests.RequestException
    :return: error message
    :rtype: str
    """
    message = f"{exception.__class__.__name__}: "

    if isinstance(exception, (requests.ConnectionError, requests.Timeout)):
        if isinstance(exception, requests.ConnectionError):
            message += "Cannot access service, check your internet connection."
        else:
            message += "Connection timed out, service is too slow"

        proxy_description = get_proxy_description()
        if proxy_description:
            message += f" QGIS is configured to use proxy: {proxy_description}"

        return message

    if isinstance(exception, requests.exceptions.InvalidSchema) and "SOCKS" in str(exception):
        message += (
            "The SOCKS proxy that is configured in QGIS cannot be used because the PySocks package is missing. "
            "Install it into the Python environment that QGIS uses."
        )
        return message

    if isinstance(exception, requests.HTTPError):
        try:
            server_message = ""
            for elem in ElementTree.fromstring(exception.response.content):
                if "ServiceException" in elem.tag:
                    server_message += elem.text.strip("\n\t ")
        except ElementTree.ParseError:
            server_message = exception.response.text.strip("\n\t ")

        server_message = server_message.encode("ascii", errors="ignore").decode("utf-8")

        # Include HTTP status code
        status_code = exception.response.status_code
        message += f"HTTP {status_code} - "

        # Provide meaningful message when server response is empty
        if not server_message:
            server_message = "No additional details provided by server"

        return message + f"{server_message}"

    return message + str(exception)
