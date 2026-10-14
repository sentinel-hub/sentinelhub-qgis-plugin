"""
Module for applying QGIS proxy settings to the plugin's HTTP requests
"""
from urllib.parse import quote

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtNetwork import QNetworkProxy

#: QGIS proxy types mapped to a URL scheme that `requests` uses for the same kind of proxy. A type that is missing
#: from the mapping cannot be used for the HTTP traffic that the plugin makes.
PROXY_TYPE_SCHEMES = {
    QNetworkProxy.ProxyType.HttpProxy: "http",
    QNetworkProxy.ProxyType.HttpCachingProxy: "http",
    # The trailing "h" makes the proxy resolve hostnames instead of the plugin, which is what QGIS does as well
    QNetworkProxy.ProxyType.Socks5Proxy: "socks5h",
}


def get_proxies(url):
    """Provides parameters for downloading the given URL over the proxy that is configured in QGIS

    Parameters are collected from QgsNetworkAccessManager, which is the same source that QGIS itself uses for map
    layers. Because QGIS already resolves its settings into a proxy object, this also covers a system proxy and
    credentials from a QGIS authentication configuration.

    If QGIS has no usable proxy configured, an empty dictionary is returned and `requests` falls back to the
    standard proxy environment variables.

    :param url: A URL that is about to be downloaded
    :type url: str
    :return: Proxy parameters for a `requests` call
    :rtype: dict
    """
    network_manager = QgsNetworkAccessManager.instance()
    proxy = network_manager.fallbackProxy()

    # URLs on the QGIS no-proxy list must not be downloaded over any proxy at all
    if _is_url_matched(url, network_manager.noProxyList()) or proxy.type() == QNetworkProxy.ProxyType.NoProxy:
        return _get_direct_connection_proxies()

    # URLs on the QGIS exclude list only bypass the proxy that is configured in QGIS
    scheme = PROXY_TYPE_SCHEMES.get(proxy.type())
    if scheme is None or not proxy.hostName() or _is_url_matched(url, network_manager.excludeList()):
        return {}

    proxy_url = _build_proxy_url(scheme, proxy)
    return {"http": proxy_url, "https": proxy_url}


def get_proxy_description():
    """Provides a description of the proxy that QGIS is configured to use, meant to be shown in error messages

    Credentials are deliberately left out of the description.

    :return: A description of the proxy or None if QGIS has no usable proxy configured
    :rtype: str or None
    """
    proxy = QgsNetworkAccessManager.instance().fallbackProxy()
    scheme = PROXY_TYPE_SCHEMES.get(proxy.type())

    if scheme is None or not proxy.hostName():
        return None

    return _build_proxy_url(scheme, proxy, with_credentials=False)


def _get_direct_connection_proxies():
    """Provides parameters for connecting without a proxy

    A `None` value makes `requests` connect directly and also stops it from falling back to a proxy environment
    variable for that protocol. A new dictionary is built on every call because `requests` modifies the dictionary
    that it is given.
    """
    return {"http": None, "https": None, "all": None}


def _is_url_matched(url, url_prefixes):
    """Checks if the given URL matches any of the given prefixes, which is how QGIS stores proxy exceptions"""
    prefixes = (prefix.strip() for prefix in url_prefixes)
    return any(url.startswith(prefix) for prefix in prefixes if prefix)


def _build_proxy_url(scheme, proxy, with_credentials=True):
    """Builds a proxy URL in a form that `requests` understands

    Note that credentials have to be a part of the URL. Only in that case `requests` also uses them to authenticate
    a CONNECT tunnel, which it opens for every HTTPS request, and the plugin only makes HTTPS requests.
    """
    credentials = _build_credentials(proxy) if with_credentials else ""
    port = f":{proxy.port()}" if proxy.port() else ""
    return f"{scheme}://{credentials}{proxy.hostName()}{port}"


def _build_credentials(proxy):
    """Builds a percent-encoded user information part of a proxy URL"""
    if not proxy.user():
        return ""

    credentials = quote(proxy.user(), safe="")
    if proxy.password():
        credentials = f"{credentials}:{quote(proxy.password(), safe='')}"

    return f"{credentials}@"
