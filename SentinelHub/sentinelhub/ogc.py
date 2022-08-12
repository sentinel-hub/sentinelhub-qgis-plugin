"""
Module with Sentinel Hub OGC utilities
"""
import datetime as dt
from urllib.parse import quote_plus, urlencode

from qgis.core import QgsDataSourceUri

from ..constants import ServiceType

DEFAULT_START_TIME = "1985-01-01"


def get_service_uri(settings, layer):
    """Generates URI for any type of supported Sentinel Hub service"""
    service_type = settings.service_type.upper()

    if service_type in [ServiceType.WMS, ServiceType.WMTS]:
        return get_wms_or_wmts_uri(settings, layer)

    if service_type == ServiceType.WFS:
        return get_wfs_uri(settings, layer)

    raise ValueError("Unsupported service type {}".format(service_type))


def get_wms_or_wmts_uri(settings, layer):
    """Generates URI for a QGIS WMS or WMTS map layer"""
    base_url = _get_service_endpoint(settings, layer)
    url_params = {
        "showLogo": "false",
        "time": _build_time(settings),
        "priority": settings.priority,
        "maxcc": settings.maxcc,
        "preview": "1",
    }

    service_type = settings.service_type.upper()
    uri_params = {
        "IgnoreGetFeatureInfoUrl": "1",
        "IgnoreGetMapUrl": "1",
        "contextualWMSLegend": "0",
        "service": service_type,
        "version": "1.3.0" if service_type == ServiceType.WMS else "1.0.0",
        "styles": "",
        "format": "image/png",
        "transparent": "true",
        "layers": layer.id,
        "crs": settings.crs,
    }
    if service_type == ServiceType.WMTS:
        uri_params["tileMatrixSet"] = "PopularWebMercator512"

    return _build_uri(base_url, url_params, uri_params, use_builder=False)


def get_wfs_uri(settings, layer):
    """Generates URI for a QGIS WFS vector map layer"""
    base_url = _get_service_endpoint(settings, layer)
    url_params = {
        "srsname": settings.crs,
        "time": _build_time(settings),
        "maxcc": settings.maxcc,
        "priority": settings.priority,
    }
    uri_params = {
        "pagingEnabled": "true",
        "restrictToRequestBBOX": "1",
        "service": "WFS",
        "version": "2.0.0",
        "typename": layer.data_source.get_wfs_id(),
        "maxfeatures": 100,
    }
    return _build_uri(base_url, url_params, uri_params, use_builder=True)


def get_wfs_url(settings, layer, bbox_str, time_range, maxcc=None):
    """Generate URL for WFS request from parameters"""
    base_url = _get_service_endpoint(settings, layer, ServiceType.WFS)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "maxfeatures": "100",
        "outputformat": "application/json",
        "typenames": layer.data_source.get_wfs_id(),
        "bbox": bbox_str,
        "time": time_range,
        "srsname": settings.crs,
        "maxcc": settings.maxcc if maxcc is None else maxcc,
    }
    return _build_url(base_url, params)


def get_wcs_url(settings, layer, bbox, crs=None):
    """Generate an URL for WCS request from parameters"""
    base_url = _get_service_endpoint(settings, layer, ServiceType.WCS)
    params = {
        "service": "wcs",
        "request": "GetCoverage",
        "version": "1.1.2",
        "coverage": settings.layer_id,
        "time": _build_time(settings),
        "bbox": bbox,
        "crs": crs if crs else settings.crs,
        "maxcc": settings.maxcc,
        "priority": settings.priority,
        "format": settings.image_format,
        "resx": settings.resx + "m",
        "resy": settings.resy + "m",
        "showLogo": settings.show_logo,
        "transparent": "false",
    }
    return _build_url(base_url, params)


def _get_service_endpoint(settings, layer, service_type=None):
    """A helper function to provide a service endpoint URL"""
    base_url = layer.data_source.service_url
    if service_type is None:
        service_type = settings.service_type
    return "{}/ogc/{}/{}".format(base_url, service_type.lower(), settings.instance_id)


def _build_url(base_url, params):
    """Builds an URL with encoded parameters"""
    return "{}?{}".format(base_url, urlencode(params))


def _build_uri(base_url, url_params, uri_params, use_builder=False):
    """Builds an URI for a QGIS layer. In some cases a builder class should be used and in some cases it shouldn't."""
    url = _build_url(base_url, url_params)

    if use_builder:
        uri_builder = QgsDataSourceUri()

        for key, value in uri_params.items():
            uri_builder.setParam(key, str(value))
        uri_builder.setParam("url", url)

        return uri_builder.uri()

    param_list = list(uri_params.items()) + [("url", quote_plus(url))]
    param_strings = ("{}={}".format(key, value) for key, value in param_list)
    return "&".join(param_strings)


def _build_time(settings):
    """Builds a time string to be sent to Sentinel Hub service"""
    if (settings.is_exact_date and not settings.start_time) or (not settings.start_time and not settings.end_time):
        return ""

    start_time = settings.start_time
    end_time = settings.end_time

    if settings.is_exact_date:
        end_time = start_time
    if not start_time:
        start_time = DEFAULT_START_TIME
    if not end_time:
        end_time = dt.datetime.now().isoformat()

    return "{}/{}/P1D".format(start_time, end_time)
