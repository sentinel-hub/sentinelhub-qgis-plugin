"""
Module with Sentinel Hub OGC utilities
"""
from urllib.parse import urlencode, quote_plus


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


def get_wms_uri(settings, time_str):
    """ Generates URI for a QGIS WMS map layer
    """
    url_params = {
        'showLogo': WMS_PARAMETERS['showLogo'],
        'time': time_str,
        'priority': settings.parameters['priority'],
        'maxcc': settings.parameters['maxcc'],
        'preview': WMS_PARAMETERS['preview']
    }
    url = quote_plus('{}?{}'.format(_get_service_endpoint(settings, 'wms'), urlencode(url_params)))

    uri_params = list(WMS_PARAMETERS.items()) + list(settings.parameters.items()) + [('url', url)]
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


def get_wmts_uri(settings, time_str):
    """ Generates URI for a QGIS WMTS map layer
    """
    url_params = {
        'showLogo': WMTS_PARAMETERS['showLogo'],
        'time': time_str,
        'priority': settings.parameters['priority'],
        'maxcc': settings.parameters['maxcc'],
        'preview': WMTS_PARAMETERS['preview']
    }
    url = quote_plus('{}?{}'.format(_get_service_endpoint(settings, 'wmts'), urlencode(url_params)))

    uri_params = list(WMTS_PARAMETERS.items()) + list(settings.parameters.items()) + [('url', url)]
    return _join_uri_params(uri_params)


def _get_service_endpoint(settings, service_type):
    """ A helper function to provide a service endpoint URL
    """
    return '{}{}/{}'.format(settings.base_url, service_type, settings.instance_id)


def _join_uri_params(param_list):
    """ For some reason it doesn't work if they are urlencoded -> TODO
    """
    param_strings = ('{}={}'.format(key, value) for key, value in param_list)
    return '&'.join(param_strings)
