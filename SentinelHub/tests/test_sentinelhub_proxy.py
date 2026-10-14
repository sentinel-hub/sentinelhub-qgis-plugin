from typing import Callable, Dict, Optional

import pytest

pytest.importorskip("qgis.core")

from qgis.PyQt.QtNetwork import QNetworkProxy  # noqa: E402

from ..sentinelhub.proxy import get_proxies, get_proxy_description  # noqa: E402

SERVICE_URL = "https://sh.dataspace.copernicus.eu/api/v1/wms/instance"
DIRECT_CONNECTION = {"http": None, "https": None, "all": None}
NO_QGIS_PROXY: Dict[str, str] = {}

SetProxyType = Callable[..., None]


@pytest.mark.parametrize(
    "proxy_type, expected_proxy_url",
    [
        (QNetworkProxy.ProxyType.HttpProxy, "http://proxy.example.org:3128"),
        (QNetworkProxy.ProxyType.HttpCachingProxy, "http://proxy.example.org:3128"),
        (QNetworkProxy.ProxyType.Socks5Proxy, "socks5h://proxy.example.org:3128"),
    ],
)
def test_supported_proxy_types(
    set_qgis_proxy: SetProxyType, proxy_type: QNetworkProxy.ProxyType, expected_proxy_url: str
) -> None:
    """Proxy types that can serve the plugin's HTTP traffic are mapped to a scheme that `requests` understands"""
    set_qgis_proxy(QNetworkProxy(proxy_type, "proxy.example.org", 3128))

    assert get_proxies(SERVICE_URL) == {"http": expected_proxy_url, "https": expected_proxy_url}
    assert get_proxy_description() == expected_proxy_url


@pytest.mark.parametrize(
    "proxy_type",
    [QNetworkProxy.ProxyType.DefaultProxy, QNetworkProxy.ProxyType.FtpCachingProxy],
)
def test_unusable_proxy_types_fall_back_to_environment(
    set_qgis_proxy: SetProxyType, proxy_type: QNetworkProxy.ProxyType
) -> None:
    """When QGIS has no proxy that could be used, proxy resolution is left to `requests`"""
    set_qgis_proxy(QNetworkProxy(proxy_type, "proxy.example.org", 3128))

    assert get_proxies(SERVICE_URL) == NO_QGIS_PROXY
    assert get_proxy_description() is None


def test_missing_host_falls_back_to_environment(set_qgis_proxy: SetProxyType) -> None:
    """This is how QGIS reports its configuration when the proxy is disabled"""
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.DefaultProxy))

    assert get_proxies(SERVICE_URL) == NO_QGIS_PROXY
    assert get_proxy_description() is None


def test_no_proxy_type_makes_a_direct_connection(set_qgis_proxy: SetProxyType) -> None:
    """When QGIS explicitly requires no proxy, proxy environment variables must not be used either"""
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))

    assert get_proxies(SERVICE_URL) == DIRECT_CONNECTION
    assert get_proxy_description() is None


def test_proxy_without_a_port(set_qgis_proxy: SetProxyType) -> None:
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org"))

    assert get_proxies(SERVICE_URL) == {"http": "http://proxy.example.org", "https": "http://proxy.example.org"}


def test_credentials_are_a_part_of_the_proxy_url(set_qgis_proxy: SetProxyType) -> None:
    """Credentials have to be in the URL so that `requests` also uses them for an HTTPS CONNECT tunnel, while they
    must never appear in a description that is shown to a user"""
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org", 3128, "user", "pass"))

    expected_proxy_url = "http://user:pass@proxy.example.org:3128"
    assert get_proxies(SERVICE_URL) == {"http": expected_proxy_url, "https": expected_proxy_url}
    assert get_proxy_description() == "http://proxy.example.org:3128"


def test_special_characters_in_credentials_are_encoded(set_qgis_proxy: SetProxyType) -> None:
    """Unencoded characters would break the parsing of a proxy URL"""
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org", 3128, "my@user", "p@ss:/?#"))

    expected_proxy_url = "http://my%40user:p%40ss%3A%2F%3F%23@proxy.example.org:3128"
    assert get_proxies(SERVICE_URL) == {"http": expected_proxy_url, "https": expected_proxy_url}


def test_user_without_a_password(set_qgis_proxy: SetProxyType) -> None:
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org", 3128, "user"))

    expected_proxy_url = "http://user@proxy.example.org:3128"
    assert get_proxies(SERVICE_URL) == {"http": expected_proxy_url, "https": expected_proxy_url}


@pytest.mark.parametrize(
    "url_prefix, expected_proxies",
    [
        ("https://sh.dataspace.copernicus.eu", NO_QGIS_PROXY),
        ("https://sh.dataspace.copernicus.eu/api/v1", NO_QGIS_PROXY),
        (SERVICE_URL, NO_QGIS_PROXY),
        ("https://services.sentinel-hub.com", None),
        ("  ", None),
        ("", None),
    ],
)
def test_excluded_urls_bypass_the_qgis_proxy(
    set_qgis_proxy: SetProxyType, url_prefix: str, expected_proxies: Optional[Dict[str, str]]
) -> None:
    """QGIS stores proxy exceptions as beginnings of URL strings. A blank entry must not match every URL."""
    proxy_url = "http://proxy.example.org:3128"
    set_qgis_proxy(
        QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org", 3128), excluded_urls=[url_prefix]
    )

    if expected_proxies is None:
        expected_proxies = {"http": proxy_url, "https": proxy_url}
    assert get_proxies(SERVICE_URL) == expected_proxies


@pytest.mark.parametrize(
    "url_prefix, expected_proxies",
    [
        ("https://sh.dataspace.copernicus.eu", DIRECT_CONNECTION),
        ("https://services.sentinel-hub.com", None),
        ("", None),
    ],
)
def test_no_proxy_urls_make_a_direct_connection(
    set_qgis_proxy: SetProxyType, url_prefix: str, expected_proxies: Optional[Dict[str, str]]
) -> None:
    """URLs on this list must not use any proxy, not even one from a proxy environment variable"""
    proxy_url = "http://proxy.example.org:3128"
    set_qgis_proxy(
        QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org", 3128), no_proxy_urls=[url_prefix]
    )

    if expected_proxies is None:
        expected_proxies = {"http": proxy_url, "https": proxy_url}
    assert get_proxies(SERVICE_URL) == expected_proxies


def test_proxies_are_not_shared_between_calls(set_qgis_proxy: SetProxyType) -> None:
    """`requests` modifies the dictionary that it is given, therefore every call must provide a new one"""
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))

    proxies = get_proxies(SERVICE_URL)
    proxies["https"] = "http://leaked.example.org:3128"

    assert get_proxies(SERVICE_URL) == DIRECT_CONNECTION
