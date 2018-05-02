#!/usr/bin/env python
# encoding: utf-8
"""
This script contains all
"""

# Base url
services_base_url = 'https://services.sentinel-hub.com/ogc/'
uswest_base_url = 'https://services-uswest2.sentinel-hub.com/ogc/'
ipt_base_url = 'http://services.eocloud.sentinel-hub.com/v1/'

# Locations where QGIS will save values
instance_id_location = "SentinelHub/instance_id"
download_folder_location = "SentinelHub/download_folder"

service_types = ['WMS', 'WMTS']

# Main request parameters
parameters = {
    'title': '',
    'showLogo': 'false',
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
    'format': 'image/jpeg',
    'transparent': 'true',
    'version': '1.3.0',
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
    'format': 'image/jpeg',
    'transparent': 'true',
    'tileMatrixSet': 'PopularWebMercator512'
}

data_source_props = {'S2L1C': {'url': services_base_url,
                               'wfs_name': 'S2.TILE',
                               'pretty_name': 'Sentinel-2 L1C'},
                     'S2L2A': {'url': services_base_url,
                               'wfs_name': 'DSS2',
                               'pretty_name': 'Sentinel-2 L2A'},
                     'S1GRD': {'url': services_base_url,
                               'wfs_name': 'DSS3',
                               'pretty_name': 'Sentinel-1'},
                     'L8L1C': {'url': uswest_base_url,
                               'wfs_name': 'DSS6',
                               'pretty_name': 'Landsat 8'},
                     'MODIS': {'url': uswest_base_url,
                               'wfs_name': 'DSS5',
                               'pretty_name': 'MODIS'},
                     'DEM': {'url': uswest_base_url,
                             'wfs_name': 'DSS4',
                             'pretty_name': 'DEM'}}

# values for UI selections
priority_map = {'Most recent': 'mostRecent',
                'Least recent': 'leastRecent',
                'Least cloud coverage': 'leastCC'}
atmfilter_list = ['NONE', 'DOS1', 'ATMCOR']
cloud_correction = ['NONE', 'REPLACE']
img_formats = ['image/png', 'image/jpeg',
               'image/tiff', 'image/tiff;depth=8', 'image/tiff;depth=16', 'image/tiff;depth=32f']
maxcc_range = [0, 100]

max_cloud_cover_image_size = 1000000
