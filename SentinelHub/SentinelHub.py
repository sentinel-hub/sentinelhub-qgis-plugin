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

from qgis.core import QgsRasterLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle

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


WGS84 = 'EPSG:4326'

INFO_MSG = ('Info', Qgis.Info if is_qgis_version_3() else QgsMessageBar.INFO)
WARNING_MSG = ('Warning', Qgis.Warning if is_qgis_version_3() else QgsMessageBar.WARNING)
CRITICAL_MSG = ('Error', Qgis.Critical if is_qgis_version_3() else QgsMessageBar.CRITICAL)
SUCCESS_MSG = ('Success', Qgis.Success if is_qgis_version_3() else QgsMessageBar.SUCCESS)


class SentinelHub:

    def __init__(self, iface):
        """Constructor.
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

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

        # Set value
        self.instance_id = QSettings().value(Settings.instance_id_location)
        if self.instance_id is None:
            self.instance_id = ''
        self.download_folder = QSettings().value(Settings.download_folder_location)
        if self.download_folder is None:
            self.download_folder = ''

        self.qgis_layers = []
        self.capabilities = []
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
        self.update_available_layers()

        self.dockwidget.instanceId.setText(self.instance_id)
        self.dockwidget.destination.setText(self.download_folder)
        self.set_values()

        self.dockwidget.priority.clear()
        self.dockwidget.priority.addItems(Settings.priority_list)

        self.dockwidget.format.clear()
        self.dockwidget.format.addItems(Settings.img_formats)

        self.dockwidget.epsg.clear()
        self.dockwidget.epsg.addItems(Settings.epsg)

    def set_values(self):
        self.dockwidget.inputResX.setText(Settings.parameters_wcs['resx'])
        self.dockwidget.inputResY.setText(Settings.parameters_wcs['resy'])
        self.dockwidget.latMin.setText(self.custom_bbox_params['latMin'])
        self.dockwidget.latMax.setText(self.custom_bbox_params['latMax'])
        self.dockwidget.lngMin.setText(self.custom_bbox_params['lngMin'])
        self.dockwidget.lngMax.setText(self.custom_bbox_params['lngMax'])

    # --------------------------------------------------------------------------

    def show_message(self, message, message_type):
        """ Show message for user

        :param message: Message for user
        :param message: str
        :param message_type: Type of message
        :param message_type: One of the constants INFO_MSG, WARNING_MSG, CRITICAL_MSG, SUCCESS_MSG
        """
        self.iface.messageBar().pushMessage(message_type[0], message, level=message_type[1])

    def missing_instance_id(self):
        """Show message about missing instance ID"""
        self.show_message("Please set Sentinel Hub Instance ID first.", INFO_MSG)

    # --------------------------------------------------------------------------

    def update_available_layers(self):
        """
        Update list of Layers avalivale at Sentinel Hub Instance
        :return:
        """
        self.dockwidget.layers.clear()

        layer_list = []
        for layer in self.capabilities:
            layer_list.append(layer['Title'])
        self.dockwidget.layers.addItems(layer_list)

    def update_current_wms_layers(self):
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

    def get_qgis_layers(self):
        if is_qgis_version_3():
            return list(QgsProject.instance().mapLayers().values())
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
        url = '{}wms/{}?TIME={}&priority={}&maxcc={}'.format(Settings.url_base, self.instance_id, self.get_time(),
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
        url = '{}wcs/{}?'.format(Settings.url_base, self.instance_id)
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

        url = '{}wfs/{}?'.format(Settings.url_base, self.instance_id)
        for parameter, value in Settings.parameters_wfs.items():
            url += '{}={}&'.format(parameter, value)

        return '{}bbox={}&time={}&srsname={}&maxcc=100'.format(url, self.bbox_to_string(self.get_bbox()), time_range,
                                                               Settings.parameters['crs'])

    # ---------------------------------------------------------------------------

    def get_capabilities(self, service, instance_id):
        """ Get capabilities of desired service

        :param service: Service (wms, wfs, wcs)
        :type service: str
        :param instance_id: Sentinel Hub instance id
        :type instance_id: str
        :return: list of properties and flag if capabilities were obtained
        :rtype: list(str), bool
        """
        if not instance_id:
            return [], False

        response = self.download_from_url('{}{}/{}?service={}&request=GetCapabilities'
                                          '&version=1.1.1'.format(Settings.url_base, service, instance_id, service))
        props = []
        if response:
            root = ElementTree.fromstring(response.content)
            for layer in root.findall('./Capability/Layer/Layer'):
                props.append({'Title': layer.find('Title').text,
                              'Name': layer.find('Name').text})
        return props, response is not None

    def get_cloud_cover(self, time_range):
        """ Get cloud cover for current extent.

        :return:
        """
        self.cloud_cover = {}

        if not self.instance_id or len(self.qgis_layers) == 0:
            return

        # Check if area is too large
        width, height = self.get_bbox_size(self.get_bbox())
        if max(width, height) > Settings.max_cloud_cover_image_size:
            return

        response = self.download_from_url(self.get_wfs_url(time_range))

        if response:
            area_info = response.json()
            for feature in area_info['features']:
                self.cloud_cover.update(
                    {str(feature['properties']['date']): feature['properties']['cloudCoverPercentage']})
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
            self.show_message("Done downloading to {}".format(filename), SUCCESS_MSG)
            time.sleep(1)
        else:
            self.show_message("Failed to download from {} to {}".format(url, filename), CRITICAL_MSG)

    def download_from_url(self, url, stream=False):
        """ Downloads data from url and handles possible errors

        :param url: download url
        :type url: str
        :param stream: True if download should be streamed and False otherwise
        :type stream: bool
        :return: download response or None if download failed
        :rtype: requests.response or None
        """
        try:
            response = requests.get(url, stream=stream)
            response.raise_for_status()
        except requests.RequestException as exception:
            message = '{}: '.format(exception.__class__.__name__)

            if isinstance(exception, requests.ConnectionError):
                message += 'Cannot access service, check your internet connection.'
            elif isinstance(exception, requests.HTTPError):
                try:
                    server_message = ''
                    for elem in ElementTree.fromstring(exception.response.content):
                        if 'ServiceException' in elem.tag:
                            server_message += elem.text.strip('\n\t ')
                except ElementTree.ParseError:
                    server_message = exception.response.text.strip('\n\t ')
                server_message = server_message.encode('ascii', errors='ignore').decode('utf-8')
                message += 'server response: "{}"'.format(server_message)
            else:
                message += str(exception)

            self.show_message(message, CRITICAL_MSG)
            response = None

        return response
    # ----------------------------------------------------------------------------

    def add_wms_layer(self):
        """
        Add WMS raster layer to canvas,
        :return:
        """
        if not self.instance_id:
            return self.missing_instance_id()

        self.update_parameters()
        name = '{} - {}'.format(Settings.parameters['prettyName'], Settings.parameters['title'])
        new_layer = QgsRasterLayer(self.get_wms_uri(), name, 'wms')
        if new_layer.isValid():
            QgsProject.instance().addMapLayer(new_layer)
            self.update_current_wms_layers()
        else:
            self.show_message('Failed to create layer {}.'.format(name), CRITICAL_MSG)

    def get_bbox(self, crs=None):
        """
        Get window bbox
        """
        target_crs = QgsCoordinateReferenceSystem(crs if crs else Settings.parameters['crs'])

        bbox = self.iface.mapCanvas().extent()
        if is_qgis_version_3():
            current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapSettings().destinationCrs().authid())
        else:
            current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapRenderer().destinationCrs().authid())

        if current_crs != target_crs:
            if is_qgis_version_3():
                xform = QgsCoordinateTransform(current_crs, target_crs, QgsProject.instance())
            else:
                xform = QgsCoordinateTransform(current_crs, target_crs)
            bbox = xform.transform(bbox)

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
        if not self.instance_id:
            self.missing_instance_id()

        selected_index = self.dockwidget.sentinelWMSlayers.currentIndex()
        if selected_index < 0:
            return

        for layer in self.get_qgis_layers():
            if layer == self.qgis_layers[selected_index]:
                self.add_wms_layer()
                QgsProject.instance().removeMapLayer(layer)
                self.update_current_wms_layers()
                return
        self.show_message('Chosen layer {} does not exist anymore.'
                          ''.format(self.dockwidget.sentinelWMSlayers.currentText()), INFO_MSG)
        self.update_current_wms_layers()

    def update_parameters(self):
        """
        Update parameters from GUI
        :return:
        """
        Settings.parameters['layers'] = self.capabilities[self.dockwidget.layers.currentIndex()]['Name']
        Settings.parameters['coverage'] = self.capabilities[self.dockwidget.layers.currentIndex()]['Name']
        Settings.parameters['title'] = self.capabilities[self.dockwidget.layers.currentIndex()]['Title']
        Settings.parameters['priority'] = self.dockwidget.priority.currentText()
        Settings.parameters['maxcc'] = str(self.dockwidget.maxcc.value())
        Settings.parameters['time'] = str(self.get_time())
        Settings.parameters['crs'] = self.dockwidget.epsg.currentText().replace(' ', '')

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
            return self.dockwidget.time0.text() + '/' + self.dockwidget.time0.text() + '/P1D'
        else:
            return self.dockwidget.time0.text() + '/' + self.dockwidget.time1.text() + '/P1D'

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
            return self.show_message('Spatial resolution parameters are not set.', CRITICAL_MSG)
        if not self.download_current_window:
            for value in self.custom_bbox_params.values():
                if value == '':
                    return self.show_message('Custom bounding box parameters are missing.', CRITICAL_MSG)

        self.update_parameters()

        if not self.download_folder:
            self.select_destination()
            if not self.download_folder:
                return self.show_message("Download canceled. No destination set.", CRITICAL_MSG)

        bbox = self.get_bbox() if self.download_current_window else self.get_custom_bbox()

        bbox_str = self.bbox_to_string(bbox, None if self.download_current_window else WGS84)
        url = self.get_wcs_url(bbox_str, None if self.download_current_window else WGS84)
        filename = self.get_filename(bbox_str)

        self.download_wcs_data(url, filename)

    @staticmethod
    def get_filename(bbox):
        """ Prepare filename which contains some metadata
        sentinel2_LAYER_time0_time1_xmin_y_min_xmax_ymax_maxcc_priority.FORMAT

        :param bbox:
        :return:
        """
        info_list = [Settings.parameters['name'], Settings.parameters['layers']] \
            + Settings.parameters['time'].split('/')[:2] + bbox.split(',') \
            + [Settings.parameters['maxcc'], Settings.parameters['priority']]
        return '.'.join(map(str, ['_'.join(map(str, info_list)),
                                  Settings.parameters_wcs['format'].split(';')[0].split('/')[1]]))

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
        Change Instance ID, and validate that is valid
        :return:
        """
        new_instance_id = self.dockwidget.instanceId.text()
        if new_instance_id == self.instance_id:
            return

        if new_instance_id == '':
            capabilities, is_valid = [], True
        else:
            capabilities, is_valid = self.get_capabilities('wms', new_instance_id)

        if is_valid:
            self.instance_id = new_instance_id
            self.capabilities = capabilities
            self.update_available_layers()
            if self.instance_id:
                self.show_message("New Instance ID and layers set.", SUCCESS_MSG)
            QSettings().setValue(Settings.instance_id_location, new_instance_id)
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
                              CRITICAL_MSG)

    def update_month(self):
        """
        On Widget Month update, get first and last dates to get Cloud Cover
        :return:
        """
        self.update_parameters()

        year = self.dockwidget.calendar.yearShown()
        month = self.dockwidget.calendar.monthShown()
        _, number_of_days = calendar.monthrange(year, month)
        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, number_of_days)

        self.get_cloud_cover(first.strftime('%Y-%m-%d') + '/' + last.strftime('%Y-%m-%d') + '/P1D')

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
            self.show_message('Please input a numerical value.', INFO_MSG)
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
                    return None
        return new_values

    def run(self):
        """Run method that loads and starts the plugin and binds all UI actions"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            if self.dockwidget is None:
                # Initial function calls
                self.dockwidget = SentinelHubDockWidget()
                self.capabilities, _ = self.get_capabilities('wms', self.instance_id)
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

            self.dockwidget.closingPlugin.connect(self.on_close_plugin)

            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
