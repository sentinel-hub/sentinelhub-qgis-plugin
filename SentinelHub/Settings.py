#!/usr/bin/env python
# encoding: utf-8

# Base setup values
urlBase = 'http://services.sentinel-hub.com/v1/'
instanceId = ''

epsg = [
    'EPSG:3857',
    'EPSG:4326'
]

# Request parameters
parameters = {
    'name': 'sentinel2',
    'prettyName': 'Sentinel 2',
    'title': '',
    'showLogo': 'false',
    'layers': '',
    'coverage': '',
    'gain': '',
    'gamma': '',
    'atmfilter': 'none',
    'cloudcorrection': 'none',
    'maxcc': '80',
    'priority': 'mostRecent',
    'time': '',
    'crs': 'EPSG:3857',
    'srs': 'EPSG:3857',
}

parametersWMS = {
    'IgnoreGetFeatureInfoUrl': '1',
    'IgnoreGetMapUrl': '1',
    'contextualWMSLegend': '0',
    'service': 'WMS',
    'request': 'GetMap',
    'styles': '',
    'format': 'image/jpeg',
    'transparent': 'false',
    'version': '1.3.0',
}

parametersWFS = {
    'service': 'WFS',
    'version': '2.0.0',
    'request': 'GetFeature',
    'typenames': 'S2.TILE',
    'maxfeatures': '100',
    'outputformat': 'application/json',
}

parametersWCS = {
    'service': 'wcs',
    'request': 'GetCoverage',
    'coverage': '',
    'styles': '',
    'format': 'image/png',
    'transparent': 'false',
    'version': '1.1.1',
    'name': 'sentinel2',
    'prettyName': 'Sentinel%202',
    'priority': 'mostRecent',
    'showLogo': 'false',
    'maxcc': '20',
    'resx': '10',
    'resy': '10'
}

# enum values of parameters
priority_list = ['mostRecent', 'leastRecent', 'leastCC', 'leastTimeDifference', 'maximumViewingElevation']
atmfilter_list = ['NONE', 'DOS1', 'ATMCOR']
cloudcorrection = ['NONE', 'REPLACE']
img_formats = ['image/png', 'image/jpeg', 'image/jp2', 'image/jpx',
               'image/tiff', 'image/tiff;depth=8', 'image/tiff;depth=16' 'image/tiff;depth=32f',
               'image/raw', 'image/raw;depth=8', 'image/raw;depth=16', 'image/raw;depth=32f']

gain_range = [0.01, 100]
gamma_range = [0.1, 10]
MAXCC_range = [0, 100]

