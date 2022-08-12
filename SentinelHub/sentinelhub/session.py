"""
Module for handling Sentinel Hub session
"""
import time

from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from qgis.core import QgsMessageLog
from requests_oauthlib import OAuth2Session

from ..exceptions import SessionError


class Session:
    """Sentinel Hub authentication class

    The class will do OAuth2 authentication with Sentinel Hub service and store the token. It will make sure that the
    token is never expired by automatically refreshing it if expiry time is close.

    Note: This is a modified copy of a class from sentinelhub-py
    """

    SECONDS_BEFORE_EXPIRY = 60

    def __init__(self, base_url, client_id, client_secret):
        """
        :param base_url: Base service URL
        :type base_url: str
        :param client_id: A Sentinel Hub OAuth client ID
        :type client_id: str
        :param client_secret: A Sentinel Hub Oauth client secret
        :type client_secret: str
        """
        self.oauth_url = f"{base_url}/oauth/token"
        self.client_id = client_id
        self.client_secret = client_secret

        self._token = None
        _ = self.token

    @property
    def token(self):
        """Always up-to-date session's token

        :return: A token in a form of dictionary of parameters
        :rtype: dict
        """
        if self._token and self._token["expires_at"] > time.time() + self.SECONDS_BEFORE_EXPIRY:
            return self._token

        self._token = self._fetch_token()
        return self._token

    @property
    def session_headers(self):
        """Provides session authorization headers

        :return: A dictionary with authorization headers
        :rtype: dict
        """
        return {"Authorization": f"Bearer {self.token['access_token']}"}

    def _fetch_token(self):
        """Collects a new token from Sentinel Hub service"""
        oauth_client = BackendApplicationClient(client_id=self.client_id)

        QgsMessageLog.logMessage("Creating a new authentication session with Sentinel Hub service")

        try:
            with OAuth2Session(client=oauth_client) as oauth_session:
                return oauth_session.fetch_token(
                    token_url=self.oauth_url, client_id=self.client_id, client_secret=self.client_secret
                )
        except OAuth2Error:
            raise SessionError
