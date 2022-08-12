"""
Module for obtaining user information from Sentinel Hub service
"""
from ..constants import USER_INFO_REQUEST_TIMEOUT


def get_username(settings, client):
    """Obtains a username or an email if any of them are specified else returns None"""
    url = f"{settings.base_url}/oauth/tokeninfo"

    user_info = client.download(url, timeout=USER_INFO_REQUEST_TIMEOUT, session_settings=settings).json()

    username = user_info.get("name") or user_info.get("email")
    if username:
        username = username.strip()
    return username
