"""
Module for obtaining user information from Sentinel Hub service
"""
from ..constants import USER_INFO_REQUEST_TIMEOUT


def get_username(settings, client):
    """ Obtains username if it is specified else returns None
    """
    url = '{}/oauth/tokeninfo'.format(settings.base_url)

    user_info = client.download(url, timeout=USER_INFO_REQUEST_TIMEOUT, session_settings=settings).json()

    return user_info.get('given_name') or user_info.get('name') or user_info.get('email')
