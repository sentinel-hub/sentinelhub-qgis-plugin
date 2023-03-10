# coding=utf-8
import pytest

pytest.importorskip("qgis.core")

from ..settings import Settings  # noqa: E402


def test_auto_save(qsettings: Settings) -> None:
    assert qsettings.crs == "EPSG:3857"
    qsettings.crs = "new crs"

    assert qsettings.value(qsettings._get_store_path("crs")) == "new crs"


def test_no_autosave_credentials(qsettings: Settings) -> None:
    qsettings.client_secret = "abcdef123"
    qsettings.client_id = "test_client_id"
    qsettings.base_url = "www.base-url.com"
    assert all(
        qsettings.value(qsettings._get_store_path(key)) is None for key in ["client_secret", "client_id", "base_url"]
    )


def test_save_credentials(qsettings: Settings) -> None:
    qsettings.client_secret = "abcdef123"
    qsettings.client_id = "test_client_id"
    qsettings.base_url = "www.base-url.com"
    qsettings.save_credentials()
    assert all(
        qsettings.value(qsettings._get_store_path(key)) == value
        for key, value in [
            ("client_secret", "abcdef123"),
            ("client_id", "test_client_id"),
            ("base_url", "www.base-url.com"),
        ]
    )
