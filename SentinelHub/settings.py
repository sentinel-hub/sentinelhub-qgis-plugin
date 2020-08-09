# -*- coding: utf-8 -*-
"""
Module containing parameters and settings for Sentinel Hub services
"""

from .constants import BaseUrl


class Settings:
    """ A class in charge of all settings
    """

# Locations where QGIS will save values
instance_id_location = 'SentinelHub/instance_id'
download_folder_location = 'SentinelHub/download_folder'

# Main request parameters
parameters = {
    'title': '',
    'layers': '',
    'maxcc': '100',
    'priority': 'mostRecent',
    'time': '',
    'crs': 'EPSG:3857'
}

# WMS parameters - the first 3 parameters are required for qgis layer
parameters_wms = {
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

# WFS parameters
parameters_wfs = {
    'service': 'WFS',
    'version': '2.0.0',
    'request': 'GetFeature',
    'typenames': 'S2.TILE',
    'maxfeatures': '100',
    'outputformat': 'application/json',
}

# WCS parameters
parameters_wcs = {
    'service': 'wcs',
    'request': 'GetCoverage',
    'format': 'image/png',
    'showLogo': 'false',
    'transparent': 'false',
    'version': '1.1.1',
    'resx': '10',
    'resy': '10'
}

# WMTS parameters
parameters_wmts = {
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

data_source_props = {
    'S2L1C': {
        'url': BaseUrl.MAIN,
        'wfs_name': 'S2.TILE',
        'pretty_name': 'Sentinel-2 L1C'
    },
    'S2L2A': {
        'url': BaseUrl.MAIN,
        'wfs_name': 'DSS2',
        'pretty_name': 'Sentinel-2 L2A'
    },
    'S1GRD': {
        'url': BaseUrl.MAIN,
        'wfs_name': 'DSS3',
        'pretty_name': 'Sentinel-1'
    },
    'L8L1C': {
        'url': BaseUrl.USWEST,
        'wfs_name': 'DSS6',
        'pretty_name': 'Landsat 8'
    },
    'MODIS': {
        'url': BaseUrl.USWEST,
        'wfs_name': 'DSS5',
        'pretty_name': 'MODIS'
    },
    'DEM': {
        'url': BaseUrl.USWEST,
        'wfs_name': 'DSS4',
        'pretty_name': 'DEM'
    }
}
