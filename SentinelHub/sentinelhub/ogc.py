"""
Module with Sentinel Hub OGC utilities
"""
from urllib.parse import urlencode, quote_plus

from qgis.core import QgsDataSourceUri

from ..constants import ServiceType


def get_service_uri(settings, layer, time_str):
    service_type = settings.service_type.upper()

    if service_type == ServiceType.WMS:
        return get_wms_uri(settings, layer, time_str)

    if service_type == ServiceType.WMTS:
        return get_wmts_uri(settings, layer, time_str)

    if service_type == ServiceType.WFS:
        return get_wfs_uri(settings, layer, time_str)

    raise ValueError('Unsupported service type {}'.format(service_type))


WMS_PARAMETERS = {
    'IgnoreGetFeatureInfoUrl': '1',
    'IgnoreGetMapUrl': '1',
    'contextualWMSLegend': '0',
    'service': 'WMS',
    'styles': '',
    'request': 'GetMap',
    'format': 'image/png',
    'transparent': 'true',
    'showLogo': 'false',
    'version': '1.3.0',
    'preview': '1'
}


def get_wms_uri(settings, layer, time_str):
    """ Generates URI for a QGIS WMS map layer
    """
    url_params = {
        'showLogo': WMS_PARAMETERS['showLogo'],
        'time': time_str,
        'priority': settings.priority,
        'maxcc': settings.maxcc,
        'preview': WMS_PARAMETERS['preview']
    }
    url = quote_plus('{}?{}'.format(_get_service_endpoint(settings, layer), urlencode(url_params)))

    common_parameters = _get_common_parameters(settings, layer)
    uri_params = list(WMS_PARAMETERS.items()) + list(common_parameters.items()) + [('url', url)]
    return _join_uri_params(uri_params)


WMTS_PARAMETERS = {
    'IgnoreGetFeatureInfoUrl': '1',
    'IgnoreGetMapUrl': '1',
    'contextualWMSLegend': '0',
    'service': 'WMTS',
    'styles': '',
    'request': 'GetTile',
    'format': 'image/png',
    'showLogo': 'false',
    'transparent': 'true',
    'tileMatrixSet': 'PopularWebMercator512',
    'preview': '1'
}


def get_wmts_uri(settings, layer, time_str):
    """ Generates URI for a QGIS WMTS map layer
    """
    url_params = {
        'showLogo': WMTS_PARAMETERS['showLogo'],
        'time': time_str,
        'priority': settings.priority,
        'maxcc': settings.maxcc,
        'preview': WMTS_PARAMETERS['preview']
    }
    url = quote_plus('{}?{}'.format(_get_service_endpoint(settings, layer), urlencode(url_params)))

    common_parameters = _get_common_parameters(settings, layer)
    uri_params = list(WMTS_PARAMETERS.items()) + list(common_parameters.items()) + [('url', url)]
    return _join_uri_params(uri_params)


def get_wfs_uri(settings, layer, time_str):
    """ Generates URI for a QGIS WFS vector map layer
    """
    base_url = _get_service_endpoint(settings, layer)
    url_params = {
        'srsname': settings.crs,
        'time': time_str,
        'maxcc': settings.maxcc,
        'priority': settings.priority
    }
    uri_params = {
        'pagingEnabled': 'true',
        'restrictToRequestBBOX': '1',
        'service': 'WFS',
        'version': '2.0.0',
        'typename': layer.data_source.get_wfs_id(),
        'maxfeatures': 100
    }
    return _build_uri(base_url, url_params, uri_params)


def get_wfs_url(settings, layer, bbox_str, time_range):
    """ Generate URL for WFS request from parameters
    """
    base_url = _get_service_endpoint(settings, layer, ServiceType.WFS)
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'maxfeatures': '100',
        'outputformat': 'application/json',
        'typenames': layer.data_source.get_wfs_id(),
        'bbox': bbox_str,
        'time': time_range,
        'srsname': settings.crs,
        'maxcc': settings.maxcc
    }
    return _build_url(base_url, params)


def get_wcs_url(settings, layer, bbox, crs=None):  # TODO: update
    """ Generate URL for WCS request from parameters

    :param bbox: Bounding box in form of "xmin,ymin,xmax,ymax"
    :type bbox: str
    :param crs: CRS of bounding box
    :type crs: str or None
    """
    base_url = _get_service_endpoint(settings, layer, ServiceType.WCS)

    common_parameters = _get_common_parameters(settings, layer)
    wcs_parameters = _get_wcs_parameters(settings)
    request_parameters = list(wcs_parameters.items()) + list(common_parameters.items())

    for parameter, value in request_parameters:
        if parameter in ('resx', 'resy'):
            value = value.strip('m') + 'm'
        if parameter == 'crs':  # TODO: fix
            value = crs if crs else settings.crs
        url += '{}={}&'.format(parameter, value)
    return '{}bbox={}'.format(url, bbox)


def _get_service_endpoint(settings, layer, service_type=None):
    """ A helper function to provide a service endpoint URL
    """
    base_url = layer.data_source.service_url
    if service_type is None:
        service_type = settings.service_type
    return '{}/ogc/{}/{}'.format(base_url, service_type.lower(), settings.instance_id)


def _build_url(base_url, params):
    """ Builds an URL with encoded parameters
    """
    return '{}?{}'.format(base_url, urlencode(params))


def _build_uri(base_url, url_params, uri_params):
    """ Builds an URI for a QGIS layer
    """
    uri_builder = QgsDataSourceUri()

    for key, value in uri_params.items():
        uri_builder.setParam(key, str(value))

    url = _build_url(base_url, url_params)
    uri_builder.setParam('url', url)

    return uri_builder.uri()


def _join_uri_params(param_list):
    """ For some reason it doesn't work if they are urlencoded -> TODO
    """
    param_strings = ('{}={}'.format(key, value) for key, value in param_list)
    return '&'.join(param_strings)


def _get_common_parameters(settings, layer):
    return {
        'layers': layer.id,
        'crs': settings.crs,
        'title': layer.name,
        **settings.parameters
    }


def _get_wcs_parameters(settings):
    return {
        'coverage': settings.layer_id,
        **settings.parameters_wcs
    }
