# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SentinelHub
                                 A QGIS plugin
 SentinelHub
                              -------------------
        begin                : 2017-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Sentinel Hub, Sinergise ltd.
        email                : info@sentinel-hub.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# This looks like the best way to make plugin compatible for QGIS versions 2.* and 3.0
from sys import version_info
def is_qgis_version_3():
    return version_info[0] >= 3

import os.path
import requests
import time
import calendar
import datetime
import math
from xml.etree import ElementTree
try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from . import resources  # this import is used because it imports resources.qrc
from .SentinelHub_dockwidget import SentinelHubDockWidget
from . import Settings

from qgis.core import QgsRasterLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle, QgsMessageLog

if is_qgis_version_3():
    from qgis.utils import Qgis
    from qgis.core import QgsProject

    from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QDate
    from PyQt5.QtGui import QIcon, QTextCharFormat
    from PyQt5.QtWidgets import QAction, QFileDialog
else:
    from qgis.utils import QGis as Qgis
    from qgis.core import QgsMapLayerRegistry as QgsProject
    from qgis.gui import QgsMessageBar

    from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QDate
    from PyQt4.QtGui import QIcon, QAction, QTextCharFormat, QFileDialog


POP_WEB = 'EPSG:3857'
WGS84 = 'EPSG:4326'


class InvalidInstanceId(ValueError):
    pass


class Message:  # Don't use Enum classes as some older Python versions don't have them
    INFO = ('Info', Qgis.Info if is_qgis_version_3() else QgsMessageBar.INFO)
    WARNING = ('Warning', Qgis.Warning if is_qgis_version_3() else QgsMessageBar.WARNING)
    CRITICAL = ('Error', Qgis.Critical if is_qgis_version_3() else QgsMessageBar.CRITICAL)
    SUCCESS = ('Success', Qgis.Success if is_qgis_version_3() else QgsMessageBar.SUCCESS)


class Capabilities:
    """ Stores info about capabilities of Sentinel Hub services
    """

    class Layer:
        """ Stores info about Sentinel Hub WMS layer
        """
        def __init__(self, layer_id, name, info='', data_source=None):
            self.id = layer_id
            self.name = name
            self.info = info
            self.data_source = data_source

    class CRS:
        """ Stores info about available CRS at Sentinel Hub WMS
        """
        def __init__(self, crs_id, name):
            self.id = crs_id
            self.name = name

    def __init__(self, instance_id, base_url=Settings.services_base_url):
        self.instance_id = instance_id
        self.base_url = base_url

        self.layers = []
        self.crs_list = []

    def load_xml(self, xml_root):
        """ Loads info from getCapabilities.xml
        """
        if xml_root.tag.startswith('{'):
            namespace = '{}}}'.format(xml_root.tag.split('}')[0])
        else:
            namespace = ''

        self.layers = []
        for layer in xml_root.findall('./{0}Capability/{0}Layer/{0}Layer'.format(namespace)):
            info_node = layer.find('{}Abstract'.format(namespace))
            self.layers.append(self.Layer(layer.find('{}Name'.format(namespace)).text,
                                          layer.find('{}Title'.format(namespace)).text,
                                          info_node.text if info_node else ''))
        self.layers.sort(key=lambda l: l.name)

        self.crs_list = []
        for crs in xml_root.findall('./{0}Capability/{0}Layer/{0}CRS'.format(namespace)):
            self.crs_list.append(self.CRS(crs.text, crs.text.replace(':', ': ')))
        self._sort_crs_list()

    def load_json(self, json_dict):
        """ Loads info from getCapabilities.json
        """
        try:
            json_layers = {json_layer['id']: json_layer for json_layer in json_dict['layers']}
            for layer in self.layers:
                json_layer = json_layers.get(layer.id)
                if json_layer:
                    layer.data_source = json_layer['dataset']
        except KeyError:
            pass

    def _sort_crs_list(self):
        """ Sorts list of CRS so that 3857 and 4326 are on the top
        """
        new_crs_list = []
        for main_crs in [POP_WEB, WGS84]:
            for index, crs in enumerate(self.crs_list):
                if crs and crs.id == main_crs:
                    new_crs_list.append(crs)
                    self.crs_list[index] = None
        for crs in self.crs_list:
            if crs:
                new_crs_list.append(crs)
        self.crs_list = new_crs_list


class SentinelHub:

    def __init__(self, iface):
        """Constructor.
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        self.plugin_version = self.get_plugin_version()

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SentinelHub_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.translate(u'&SentinelHub')
        self.toolbar = self.iface.addToolBar(u'SentinelHub')
        self.toolbar.setObjectName(u'SentinelHub')
        self.pluginIsActive = False
        self.dockwidget = None
        self.base_url = None
        self.data_source = None

        # Set value
        self.instance_id = QSettings().value(Settings.instance_id_location)
        if self.instance_id is None:
            self.instance_id = ''
        self.download_folder = QSettings().value(Settings.download_folder_location)
        if self.download_folder is None:
            self.download_folder = ''

        self.qgis_layers = []
        self.capabilities = Capabilities('')
        self.active_time = 'time0'
        self.cloud_cover = {}

        self.download_current_window = True
        self.custom_bbox_params = {}
        for name in ['latMin', 'latMax', 'lngMin', 'lngMax']:
            self.custom_bbox_params[name] = ''

    @staticmethod
    def translate(message):
        """Get the translation for a string using Qt translation API.
        """
        return QCoreApplication.translate('SentinelHub', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar.
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):  # This method is called by QGIS
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SentinelHub/favicon.ico'
        self.add_action(
            icon_path,
            text=self.translate(u'SentinelHub'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def init_gui_settings(self):
        """Fill combo boxes:
        Layers - Renderers
        Priority
        """
        self.update_instance_props()

        self.dockwidget.instanceId.setText(self.instance_id)
        self.dockwidget.destination.setText(self.download_folder)
        self.set_values()

        self.dockwidget.priority.clear()
        self.dockwidget.priority.addItems(sorted(Settings.priority_map.keys(), reverse=True))

        self.dockwidget.format.clear()
        self.dockwidget.format.addItems(Settings.img_formats)

    def set_values(self):
        """ Updates some values for the wcs download request
        """
        self.dockwidget.inputResX.setText(Settings.parameters_wcs['resx'])
        self.dockwidget.inputResY.setText(Settings.parameters_wcs['resy'])
        self.dockwidget.latMin.setText(self.custom_bbox_params['latMin'])
        self.dockwidget.latMax.setText(self.custom_bbox_params['latMax'])
        self.dockwidget.lngMin.setText(self.custom_bbox_params['lngMin'])
        self.dockwidget.lngMax.setText(self.custom_bbox_params['lngMax'])

    def get_plugin_version(self):
        """
        :return: Plugin version
        :rtype: str
        """
        try:
            with open(os.path.join(self.plugin_dir, 'metadata.txt')) as metadata_file:
                for line in metadata_file:
                    if line.startswith('version'):
                        return line.split("=")[1].strip()
        except IOError:
            return '?'

    # --------------------------------------------------------------------------

    def show_message(self, message, message_type):
        """ Show message for user

        :param message: Message for user
        :param message: str
        :param message_type: Type of message
        :param message_type: Attributes of Message class
        """
        self.iface.messageBar().pushMessage(message_type[0], message, level=message_type[1])

    def missing_instance_id(self):
        """Show message about missing instance ID"""
        self.show_message("Please set Sentinel Hub Instance ID first.", Message.INFO)

    # --------------------------------------------------------------------------

    def update_instance_props(self):
        """
        Update lists of Layers and CRS available with current Sentinel Hub Instance
        """
        if self.capabilities:
            self.dockwidget.layers.clear()
            self.dockwidget.layers.addItems([layer.name for layer in self.capabilities.layers])

            self.dockwidget.epsg.clear()
            self.dockwidget.epsg.addItems([crs.name for crs in self.capabilities.crs_list])

    def update_current_wms_layers(self, selected_layer=None):
        """
        Updates List of Qgis layers
        :return:
        """
        self.qgis_layers = self.get_qgis_layers()
        layer_names = []
        for layer in self.qgis_layers:
            layer_names.append(layer.name())
        self.dockwidget.sentinelWMSlayers.clear()
        self.dockwidget.sentinelWMSlayers.addItems(layer_names)

        if selected_layer:
            for index, layer in enumerate(self.qgis_layers):
                if layer == selected_layer:
                    self.dockwidget.sentinelWMSlayers.setCurrentIndex(index)

    def get_qgis_layers(self):
        """
        :return: List of existing QGIS layers in the same order as they are in the QGIS menu
        :rtype: list(QgsMapLayer)
        """
        if is_qgis_version_3():
            return [tree_layer.layer() for tree_layer in QgsProject.instance().layerTreeRoot().findLayers()]
        return self.iface.legendInterface().layers()

    # --------------------------------------------------------------------------

    def on_close_plugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.on_close_plugin)
        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.translate(u'&SentinelHub'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    # --------------------------------------------------------------------------

    def get_wms_uri(self):
        """ Generate URI for WMS request from parameters """
        uri = ''
        request_parameters = list(Settings.parameters_wms.items()) + list(Settings.parameters.items())
        for parameter, value in request_parameters:
            uri += '{}={}&'.format(parameter, value)

        # Every parameter that QGIS layer doesn't use by default must be in url
        # And url has to be encoded
        url = '{}wms/{}?TIME={}&priority={}&maxcc={}'.format(self.base_url, self.instance_id, self.get_time(),
                                                             Settings.parameters['priority'],
                                                             Settings.parameters['maxcc'])
        return '{}url={}'.format(uri, quote_plus(url))

    def get_wmts_uri(self):
        """ Generate URI for WMTS request from parameters """
        uri = ''
        request_parameters = list(Settings.parameters_wmts.items()) + list(Settings.parameters.items())
        for parameter, value in request_parameters:
            uri += '{}={}&'.format(parameter, value)
        url = '{}wmts/{}?TIME={}&priority={}&maxcc={}'.format(self.base_url, self.instance_id, self.get_time(),
                                                              Settings.parameters['priority'],
                                                              Settings.parameters['maxcc'])
        return '{}url={}'.format(uri, quote_plus(url))

    def get_wcs_url(self, bbox, crs=None):
        """ Generate URL for WCS request from parameters

        :param bbox: Bounding box in form of "xmin,ymin,xmax,ymax"
        :type bbox: str
        :param crs: CRS of bounding box
        :type crs: str or None
        """
        url = '{}wcs/{}?'.format(self.base_url, self.instance_id)
        request_parameters = list(Settings.parameters_wcs.items()) + list(Settings.parameters.items())

        for parameter, value in request_parameters:
            if parameter in ('resx', 'resy'):
                value = value.strip('m') + 'm'
            if parameter == 'crs':
                value = crs if crs else Settings.parameters['crs']
            url += '{}={}&'.format(parameter, value)
        return '{}bbox={}'.format(url, bbox)

    def get_wfs_url(self, time_range):
        """ Generate URL for WFS request from parameters """

        url = '{}wfs/{}?'.format(self.base_url, self.instance_id)
        for parameter, value in Settings.parameters_wfs.items():
            url += '{}={}&'.format(parameter, value)

        return '{}bbox={}&time={}&srsname={}&maxcc=100'.format(url, self.bbox_to_string(self.get_bbox()), time_range,
                                                               Settings.parameters['crs'])

    @staticmethod
    def get_capabilities_url(base_url, service, instance_id, get_json=False):
        """ Generates url for obtaining service capabilities
        """
        url = '{}{}/{}?service={}&request=GetCapabilities&version=1.3.0'.format(base_url, service, instance_id, service)
        if get_json:
            return url + '&format=application/json'
        return url

    # ---------------------------------------------------------------------------

    def get_capabilities(self, instance_id, service='wms'):
        """ Get capabilities of desired service

        :param instance_id: Sentinel Hub instance id
        :type instance_id: str
        :param service: Service (wms, wfs, wcs)
        :type service: str
        :return: Capabilities class or none
        :rtype: Capabilities or None
        """
        if not instance_id:
            return None

        try:
            response = self.download_from_url(self.get_capabilities_url(Settings.services_base_url, service,
                                                                        instance_id), raise_invalid_id=True)
            self.base_url = Settings.services_base_url
        except InvalidInstanceId:
            response = self.download_from_url(self.get_capabilities_url(Settings.ipt_base_url, service, instance_id))
            self.base_url = Settings.ipt_base_url

        if not response:
            return None

        capabilities = Capabilities(instance_id, self.base_url)

        xml_root = ElementTree.fromstring(response.content)
        capabilities.load_xml(xml_root)

        if self.base_url == Settings.services_base_url:
            json_response = self.download_from_url(self.get_capabilities_url(self.base_url, service, instance_id,
                                                                             get_json=True), raise_invalid_id=True)
            try:
                capabilities.load_json(json_response.json())
            except ValueError:
                pass

        return capabilities

    def get_cloud_cover(self):
        """ Get cloud cover for current extent.
        """
        self.cloud_cover = {}
        self.clear_calendar_cells()

        if not self.capabilities or len(self.qgis_layers) == 0:
            return
        if self.base_url != Settings.services_base_url:  # Uswest is too slow for this
            return

        # Check if area is too large
        try:
            width, height = self.get_bbox_size(self.get_bbox())
        except Exception:
            return
        if max(width, height) > Settings.max_cloud_cover_image_size:
            return

        time_range = self.get_calendar_month_interval()
        response = self.download_from_url(self.get_wfs_url(time_range), ignore_exception=True)

        if response:
            area_info = response.json()
            for feature in area_info['features']:
                self.cloud_cover[str(feature['properties']['date'])] = feature['properties'].get('cloudCoverPercentage',
                                                                                                 0)
            self.update_calendar_from_cloud_cover()

    # ----------------------------------------------------------------------------

    def download_wcs_data(self, url, filename):
        """
        Download image from provided URL WCS request

        :param url: WCS url request with specified bounding box
        :param filename: filename of image
        :return:
        """
        with open(os.path.join(self.download_folder, filename), "wb") as download_file:
            response = self.download_from_url(url, stream=True)

            if response:
                total_length = response.headers.get('content-length')

                if total_length is None:
                    download_file.write(response.content)
                else:
                    for data in response.iter_content(chunk_size=4096):
                        download_file.write(data)
                downloaded = True
            else:
                downloaded = False
        if downloaded:
            self.show_message("Done downloading to {}".format(filename), Message.SUCCESS)
            time.sleep(1)
        else:
            self.show_message("Failed to download from {} to {}".format(url, filename), Message.CRITICAL)

    def download_from_url(self, url, stream=False, raise_invalid_id=False, ignore_exception=False):
        """ Downloads data from url and handles possible errors

        :param url: download url
        :type url: str
        :param stream: True if download should be streamed and False otherwise
        :type stream: bool
        :param raise_invalid_id: If True an InvalidInstanceId exception will be raised in case service returns HTTP 400
        :type raise_invalid_id: bool
        :param ignore_exception: If True no error messages will be shown in case of exceptions
        :type ignore_exception: bool
        :return: download response or None if download failed
        :rtype: requests.response or None
        """
        try:
            proxyDict, auth = self.getProxyDict()
            if proxyDict and auth:
                response = requests.get(url, stream=stream,
                                        headers={'User-Agent': 'sh_qgis_plugin_{}'.format(self.plugin_version)},
                        proxies=proxyDict,
                        auth=auth)
            else:
                response = requests.get(url, stream=stream,
                                        headers={'User-Agent': 'sh_qgis_plugin_{}'.format(self.plugin_version)})
            response = requests.get(url, stream=stream,
                                    headers={'User-Agent': 'sh_qgis_plugin_{}'.format(self.plugin_version)})
            response.raise_for_status()
        except requests.RequestException as exception:
            if ignore_exception:
                return
            if raise_invalid_id and isinstance(exception, requests.HTTPError) and exception.response.status_code == 400:
                raise InvalidInstanceId()

            self.show_message(self.get_error_message(exception), Message.CRITICAL)
            response = None

        return response

    def getProxyDict(self):
        """
        Gets the proxy dict used in requests
        """
        http_proxy, https_proxy, auth = self.getProxyConfiguration()
        if http_proxy and https_proxy and auth:
            proxyDict = { 
                "http" : http_proxy,
                "https" : https_proxy
                }
            return proxyDict, auth
        else:
            return {}, None
    
    def getProxyConfiguration()
        """
        Get proxy config from QSettings and builds proxy parameters
        """
        enabled, host, port, user, password = self.getProxyFromQSettings()
        if enabled and host and port and user and password:
            http_proxy = 'http://{0}:{1}'.format(host, port)
            https_proxy = 'https://{0}:{1}'.format(host, port)
            auth = requests.auth.HTTPProxyAuth(user, password)
            return http_proxy, https_proxy, auth
        else:
            return None, None, None

    def getProxyFromQSettings(self):
        """
        Gets the proxy configuration from QSettings
        """
        settings = QSettings()
        settings.beginGroup('proxy')
        enabled = settings.value('proxyEnabled')
        host = settings.value('proxyHost')
        port = settings.value('proxyPort')
        user = settings.value('proxyUser')
        password = settings.value('proxyPassword')
        settings.endGroup()
        return enabled, host, port, user, password

    @staticmethod
    def get_error_message(exception):
        """ Creates an error message from the given exception

        :param exception: Exception obtained during download
        :type exception: requests.RequestException
        :return: error message
        :rtype: str
        """
        message = '{}: '.format(exception.__class__.__name__)

        if isinstance(exception, requests.ConnectionError):
            return message + 'Cannot access service, check your internet connection.'

        if isinstance(exception, requests.HTTPError):
            try:
                server_message = ''
                for elem in ElementTree.fromstring(exception.response.content):
                    if 'ServiceException' in elem.tag:
                        server_message += elem.text.strip('\n\t ')
            except ElementTree.ParseError:
                server_message = exception.response.text.strip('\n\t ')
            server_message = server_message.encode('ascii', errors='ignore').decode('utf-8')
            if 'Config instance "instance.' in server_message:
                instance_id = server_message.split('"')[1][9:]
                server_message = 'Invalid instance id: {}'.format(instance_id)
            return message + 'server response: "{}"'.format(server_message)

        return message + str(exception)
    # ----------------------------------------------------------------------------

    def add_wms_layer(self, current_position=False):
        """
        Add WMS raster layer to canvas,
        :param current_position: If True the layer will be added on top of currently selected layers, if False it will
                                 be added on top of all layers
        :return: new layer
        """
        if not self.capabilities:
            return self.missing_instance_id()

        self.update_parameters()
        name = '{} - {}'.format(self.get_source_name(), Settings.parameters['title'])
        new_layer = QgsRasterLayer(self.get_wms_uri(), name, 'wms')
        #new_layer = QgsRasterLayer(self.get_wmts_uri(), name, 'wms')
        if new_layer.isValid():
            if not current_position and self.get_qgis_layers():
                self.iface.setActiveLayer(self.get_qgis_layers()[0])
            QgsProject.instance().addMapLayer(new_layer)
            self.update_current_wms_layers()
        else:
            self.show_message('Failed to create layer {}.'.format(name), Message.CRITICAL)
        return new_layer

    def get_bbox(self, crs=None):
        """
        Get window bbox
        """
        bbox = self.iface.mapCanvas().extent()
        target_crs = QgsCoordinateReferenceSystem(crs if crs else Settings.parameters['crs'])
        if is_qgis_version_3():
            current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapSettings().destinationCrs().authid())
        else:
            current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapRenderer().destinationCrs().authid())
        if current_crs != target_crs:
            if is_qgis_version_3():
                xform = QgsCoordinateTransform(current_crs, target_crs, QgsProject.instance())
            else:
                xform = QgsCoordinateTransform(current_crs, target_crs)
            bbox = xform.transform(bbox)  # if target CRS is UTM and bbox is out of UTM bounds this fails, not sure how to fix

        return bbox

    @staticmethod
    def bbox_to_string(bbox, crs=None):
        """ Transforms BBox object into string
        """
        target_crs = QgsCoordinateReferenceSystem(crs if crs else Settings.parameters['crs'])

        if target_crs.authid() == WGS84:
            precision = 6
            bbox_list = [bbox.yMinimum(), bbox.xMinimum(), bbox.yMaximum(), bbox.xMaximum()]
        else:
            precision = 2
            bbox_list = [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]

        return ','.join(map(lambda coord: str(round(coord, precision)), bbox_list))

    def get_custom_bbox(self):
        """ Creates BBox from values set by user
        """
        lat_min = min(float(self.custom_bbox_params['latMin']), float(self.custom_bbox_params['latMax']))
        lat_max = max(float(self.custom_bbox_params['latMin']), float(self.custom_bbox_params['latMax']))
        lng_min = min(float(self.custom_bbox_params['lngMin']), float(self.custom_bbox_params['lngMax']))
        lng_max = max(float(self.custom_bbox_params['lngMin']), float(self.custom_bbox_params['lngMax']))
        return QgsRectangle(lng_min, lat_min, lng_max, lat_max)

    def take_window_bbox(self):
        """
        From Custom extent get values, save them and show them in UI
        :return:
        """
        bbox = self.get_bbox(crs=WGS84)
        bbox_list = self.bbox_to_string(bbox, crs=WGS84).split(',')
        self.custom_bbox_params['latMin'] = bbox_list[0]
        self.custom_bbox_params['lngMin'] = bbox_list[1]
        self.custom_bbox_params['latMax'] = bbox_list[2]
        self.custom_bbox_params['lngMax'] = bbox_list[3]

        self.set_values()

    def get_bbox_size(self, bbox, crs=None):
        """ Returns approximate width and height of bounding box in meters
        """
        bbox_crs = QgsCoordinateReferenceSystem(crs if crs else Settings.parameters['crs'])
        utm_crs = QgsCoordinateReferenceSystem(self.lng_to_utm_zone(
            (bbox.xMinimum() + bbox.xMaximum()) / 2,
            (bbox.yMinimum() + bbox.yMaximum()) / 2))
        if is_qgis_version_3():
            xform = QgsCoordinateTransform(bbox_crs, utm_crs, QgsProject.instance())
        else:
            xform = QgsCoordinateTransform(bbox_crs, utm_crs)
        bbox = xform.transform(bbox)
        width = abs(bbox.xMaximum() - bbox.xMinimum())
        height = abs(bbox.yMinimum() - bbox.yMaximum())
        return width, height

    @staticmethod
    def lng_to_utm_zone(longitude, latitude):
        """ Calculates UTM zone from latitude and longitude"""
        zone = int(math.floor((longitude + 180) / 6) + 1)
        hemisphere = 6 if latitude > 0 else 7
        return 'EPSG:32{0}{1:02d}'.format(hemisphere, zone)

    def update_qgis_layer(self):
        """
        Updating layer in pyqgis somehow doesn't work therefore this method creates a new layer and deletes the old one
        :return:
        """
        if not self.capabilities:
            self.missing_instance_id()

        selected_index = self.dockwidget.sentinelWMSlayers.currentIndex()
        if selected_index < 0:
            return

        for layer in self.get_qgis_layers():
            # QgsMessageLog.logMessage(str(layer.name()) + ' ' + str(self.qgis_layers[selected_index].name()))
            if layer == self.qgis_layers[selected_index]:
                self.iface.setActiveLayer(layer)
                new_layer = self.add_wms_layer(current_position=True)
                if new_layer.isValid():
                    QgsProject.instance().removeMapLayer(layer)
                    self.update_current_wms_layers(selected_layer=new_layer)
                return
        self.show_message('Chosen layer {} does not exist anymore.'
                          ''.format(self.dockwidget.sentinelWMSlayers.currentText()), Message.INFO)
        self.update_current_wms_layers()

    def update_parameters(self):
        """
        Update parameters from GUI
        :return:
        """
        Settings.parameters['priority'] = Settings.priority_map[self.dockwidget.priority.currentText()]
        Settings.parameters['maxcc'] = str(self.dockwidget.maxcc.value())
        Settings.parameters['time'] = str(self.get_time())

        if self.capabilities:
            self.update_selected_crs()
            self.update_selected_layer()

    def update_selected_crs(self):
        """ Updates crs with selected Sentinel Hub CRS
        """
        crs_index = self.dockwidget.epsg.currentIndex()
        wms_crs = self.capabilities.crs_list
        if 0 <= crs_index < len(wms_crs):
            Settings.parameters['crs'] = wms_crs[crs_index].id

    def update_selected_layer(self):
        """ Updates properties of selected Sentinel Hub layer
        """
        layers_index = self.dockwidget.layers.currentIndex()
        old_data_source = self.data_source
        wms_layers = self.capabilities.layers
        if 0 <= layers_index < len(wms_layers):
            Settings.parameters['layers'] = wms_layers[layers_index].id
            Settings.parameters_wcs['coverage'] = wms_layers[layers_index].id
            Settings.parameters['title'] = wms_layers[layers_index].name

            if self.base_url in [Settings.services_base_url, Settings.uswest_base_url]:
                self.data_source = wms_layers[layers_index].data_source
                if self.data_source:
                    self.base_url = Settings.data_source_props[self.data_source]['url']
                    Settings.parameters_wfs['typenames'] = Settings.data_source_props[self.data_source]['wfs_name']

                # TODO: if DEM, disable times
        if old_data_source != self.data_source:
            self.get_cloud_cover()

    def update_maxcc_label(self):
        """
        Update Max Cloud Coverage Label when slider value change
        :return:
        """
        self.dockwidget.maxccLabel.setText('Cloud coverage ' + str(self.dockwidget.maxcc.value()) + ' %')

    def get_time(self):
        """
        Format time parameter according to settings
        :return:
        """
        if self.dockwidget.time0.text() == '' and not self.dockwidget.exactDate.isChecked():
            return self.dockwidget.time1.text()
        elif self.dockwidget.exactDate.isChecked():
            return '{}/{}/P1D'.format(self.dockwidget.time0.text(), self.dockwidget.time0.text())
        else:
            return '{}/{}/P1D'.format(self.dockwidget.time0.text(), self.dockwidget.time1.text())

    def add_time(self):
        """
        Add / update time parameter from calendar regrading which time was chosen and paint calendar
        time0 - starting time
        time1 - ending time
        :return:
        """
        if self.active_time == 'time0':
            time_input = self.dockwidget.time0
        elif self.active_time == 'time1':
            time_input = self.dockwidget.time1

        time_input.setText(str(self.dockwidget.calendar.selectedDate().toPyDate()))

    # ------------------------------------------------------------------------

    def clear_calendar_cells(self):
        """
        Clear all cells
        :return:
        """
        style = QTextCharFormat()
        style.setBackground(Qt.white)
        self.dockwidget.calendar.setDateTextFormat(QDate(), style)

    def update_calendar_from_cloud_cover(self):
        """
        Update painted cells regrading Max Cloud Coverage
        :return:
        """
        self.clear_calendar_cells()
        for date, value in self.cloud_cover.items():
            if float(value) <= int(Settings.parameters['maxcc']):
                d = date.split('-')
                style = QTextCharFormat()
                style.setBackground(Qt.gray)
                self.dockwidget.calendar.setDateTextFormat(QDate(int(d[0]), int(d[1]), int(d[2])), style)

    def move_calendar(self, active):
        """
        :param active:
        :return:
        """
        if active == 'time0':
            self.dockwidget.calendarSpacer.hide()
        else:
            self.dockwidget.calendarSpacer.show()
        self.active_time = active

    def select_destination(self):
        """
        Opens dialog to select destination folder
        :return:
        """
        folder = QFileDialog.getExistingDirectory(self.dockwidget, "Select folder")
        self.dockwidget.destination.setText(folder)
        self.change_download_folder()

    def download_caption(self):
        """
        Prepare download request and then download images
        :return:
        """
        if not self.instance_id:
            return self.missing_instance_id()

        if Settings.parameters_wcs['resx'] == '' or Settings.parameters_wcs['resy'] == '':
            return self.show_message('Spatial resolution parameters are not set.', Message.CRITICAL)
        if not self.download_current_window:
            for value in self.custom_bbox_params.values():
                if value == '':
                    return self.show_message('Custom bounding box parameters are missing.', Message.CRITICAL)

        self.update_parameters()

        if not self.download_folder:
            self.select_destination()
            if not self.download_folder:
                return self.show_message("Download canceled. No destination set.", Message.CRITICAL)

        try:
            bbox = self.get_bbox() if self.download_current_window else self.get_custom_bbox()
        except Exception:
            return self.show_message("Unable to transform to selected CRS, please zoom in or change CRS", Message.CRITICAL)

        bbox_str = self.bbox_to_string(bbox, None if self.download_current_window else WGS84)
        url = self.get_wcs_url(bbox_str, None if self.download_current_window else WGS84)
        filename = self.get_filename(bbox_str)

        self.download_wcs_data(url, filename)

    def get_filename(self, bbox):
        """ Prepare filename which contains some metadata
        DataSource_LayerName_time0_time1_xmin_y_min_xmax_ymax_maxcc_priority.FORMAT

        :param bbox:
        :return:
        """
        info_list = [self.get_source_name(), Settings.parameters['layers']] \
            + Settings.parameters['time'].split('/')[:2] + bbox.split(',') \
            + [Settings.parameters['maxcc'], Settings.parameters['priority']]
        name = '.'.join(map(str, ['_'.join(map(str, info_list)),
                                  Settings.parameters_wcs['format'].split(';')[0].split('/')[1]]))
        return name.replace(' ', '').replace(':', '_')

    def get_source_name(self):
        """ Returns name of the data source

        :return: name
        :rtype: string
        """
        if self.base_url == Settings.ipt_base_url:
            return 'EO Cloud'
        return Settings.data_source_props[self.data_source]['pretty_name']

    def update_maxcc(self):
        """
        Update max cloud cover
        :return:
        """
        self.update_parameters()
        self.update_calendar_from_cloud_cover()

    def update_download_format(self):
        """
        Update image format
        :return:
        """
        Settings.parameters_wcs['format'] = self.dockwidget.format.currentText()

    def change_exact_date(self):
        """
        Change if using exact date or not
        :return:
        """
        if self.dockwidget.exactDate.isChecked():
            self.dockwidget.time1.hide()
            self.move_calendar('time0')
        else:
            self.dockwidget.time1.show()

    def change_instance_id(self):
        """
        Change Instance ID, and check that it is valid
        :return:
        """
        new_instance_id = self.dockwidget.instanceId.text()
        if new_instance_id == self.instance_id:
            return

        if new_instance_id == '':
            capabilities = Capabilities(new_instance_id)
        else:
            capabilities = self.get_capabilities(new_instance_id)

        if capabilities:
            self.instance_id = new_instance_id
            self.capabilities = capabilities
            self.update_instance_props()
            if self.instance_id:
                self.show_message("New Instance ID and layers set.", Message.SUCCESS)
            QSettings().setValue(Settings.instance_id_location, new_instance_id)
            self.update_parameters()
            self.get_cloud_cover()
        else:
            self.dockwidget.instanceId.setText(self.instance_id)

    def change_download_folder(self):
        """ Sets new download folder"""
        new_download_folder = self.dockwidget.destination.text()
        if new_download_folder == self.download_folder:
            return

        if new_download_folder == '' or os.path.exists(new_download_folder):
            self.download_folder = new_download_folder
            QSettings().setValue(Settings.download_folder_location, new_download_folder)
        else:
            self.dockwidget.destination.setText(self.download_folder)
            self.show_message('Folder {} does not exist. Please set a valid folder'.format(new_download_folder),
                              Message.CRITICAL)

    def update_month(self):
        """
        On Widget Month update, get first and last dates to get Cloud Cover
        :return:
        """
        self.update_parameters()
        self.get_cloud_cover()

    def get_calendar_month_interval(self):
        year = self.dockwidget.calendar.yearShown()
        month = self.dockwidget.calendar.monthShown()
        _, number_of_days = calendar.monthrange(year, month)
        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, number_of_days)

        return '{}/{}/P1D'.format(first.strftime('%Y-%m-%d'), last.strftime('%Y-%m-%d'))

    def toggle_extent(self, setting):
        """
        Toggle Current / Custom extent
        :param setting:
        :return:
        """
        if setting == 'current':
            self.download_current_window = True
            self.dockwidget.widgetCustomExtent.hide()
        elif setting == 'custom':
            self.download_current_window = False
            self.dockwidget.widgetCustomExtent.show()

    def update_values(self):
        """ Updates numerical values from user input"""
        new_values = self.get_values()

        if not new_values:
            self.show_message('Please input a numerical value.', Message.INFO)
            self.set_values()
            return

        for name, value in new_values.items():
            if name in ['resx', 'resy']:
                Settings.parameters_wcs[name] = value
            else:
                self.custom_bbox_params[name] = value

    def get_values(self):
        """ Retrieves numerical values from user input"""
        new_values = {
            'resx': self.dockwidget.inputResX.text(),
            'resy': self.dockwidget.inputResY.text(),
            'latMin': self.dockwidget.latMin.text(),
            'latMax': self.dockwidget.latMax.text(),
            'lngMin': self.dockwidget.lngMin.text(),
            'lngMax': self.dockwidget.lngMax.text()
        }
        for name, value in new_values.items():
            if value != '':
                try:
                    float(value)
                except ValueError:
                    return
        return new_values

    def run(self):
        """Run method that loads and starts the plugin and binds all UI actions"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            if self.dockwidget is None:
                # Initial function calls
                self.dockwidget = SentinelHubDockWidget()
                self.capabilities = self.get_capabilities(self.instance_id)
                self.init_gui_settings()
                self.update_month()
                self.toggle_extent('current')
                self.dockwidget.calendarSpacer.hide()
                self.update_current_wms_layers()

                # Bind actions to buttons
                self.dockwidget.buttonAddWms.clicked.connect(self.add_wms_layer)
                self.dockwidget.buttonUpdateWms.clicked.connect(self.update_qgis_layer)
                self.dockwidget.buttonDownload.clicked.connect(self.download_caption)
                self.dockwidget.refreshExtent.clicked.connect(self.take_window_bbox)
                self.dockwidget.selectDestination.clicked.connect(self.select_destination)

                # Render input fields changes and events
                self.dockwidget.layers.currentIndexChanged.connect(self.update_selected_layer)
                self.dockwidget.time0.selectionChanged.connect(lambda: self.move_calendar('time0'))
                self.dockwidget.time1.selectionChanged.connect(lambda: self.move_calendar('time1'))
                self.dockwidget.calendar.clicked.connect(self.add_time)
                self.dockwidget.exactDate.stateChanged.connect(self.change_exact_date)
                self.dockwidget.calendar.currentPageChanged.connect(self.update_month)
                self.dockwidget.maxcc.valueChanged.connect(self.update_maxcc_label)
                self.dockwidget.maxcc.sliderReleased.connect(self.update_maxcc)
                self.dockwidget.instanceId.editingFinished.connect(self.change_instance_id)
                self.dockwidget.destination.editingFinished.connect(self.change_download_folder)

                self.dockwidget.inputResX.editingFinished.connect(self.update_values)
                self.dockwidget.inputResY.editingFinished.connect(self.update_values)
                self.dockwidget.latMin.editingFinished.connect(self.update_values)
                self.dockwidget.latMax.editingFinished.connect(self.update_values)
                self.dockwidget.lngMin.editingFinished.connect(self.update_values)
                self.dockwidget.lngMax.editingFinished.connect(self.update_values)

                # Download input fields changes and events
                self.dockwidget.format.currentIndexChanged.connect(self.update_download_format)
                self.dockwidget.radioCurrentExtent.clicked.connect(lambda: self.toggle_extent('current'))
                self.dockwidget.radioCustomExtent.clicked.connect(lambda: self.toggle_extent('custom'))

            # Tracks which layer is selected in left menu
            # self.iface.currentLayerChanged.connect(self.update_current_wms_layers)

            self.dockwidget.closingPlugin.connect(self.on_close_plugin)

            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
