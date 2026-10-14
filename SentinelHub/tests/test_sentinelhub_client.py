import pytest

pytest.importorskip("qgis.core")

import requests  # noqa: E402
from qgis.PyQt.QtNetwork import QNetworkProxy  # noqa: E402

from ..sentinelhub.client import get_error_message  # noqa: E402
from .test_sentinelhub_proxy import SetProxyType  # noqa: E402


def test_connection_error_reports_the_qgis_proxy(set_qgis_proxy: SetProxyType) -> None:
    """A user who is behind a proxy should see which proxy failed, but never their password"""
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, "proxy.example.org", 3128, "user", "s3cr3t"))

    message = get_error_message(requests.ConnectionError("failed"))

    assert "QGIS is configured to use proxy: http://proxy.example.org:3128" in message
    assert "s3cr3t" not in message


def test_connection_error_without_a_configured_proxy(set_qgis_proxy: SetProxyType) -> None:
    set_qgis_proxy(QNetworkProxy(QNetworkProxy.ProxyType.DefaultProxy))

    assert "proxy" not in get_error_message(requests.ConnectionError("failed"))


def test_missing_socks_dependency_is_explained() -> None:
    """Without PySocks a SOCKS proxy fails with a message that means nothing to a user"""
    exception = requests.exceptions.InvalidSchema("Missing dependencies for SOCKS support.")

    assert "PySocks" in get_error_message(exception)
