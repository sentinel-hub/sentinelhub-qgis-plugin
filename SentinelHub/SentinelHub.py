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

import os.path
import requests
import time
import calendar
import datetime
import math
from enum import Enum
from xml.etree import ElementTree
try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

from . import resources  # this imports resources.qrc
from .SentinelHub_dockwidget import SentinelHubDockWidget
from . import Settings

try:
    from qgis.utils import Qgis
except ImportError:
    from qgis.utils import QGis as Qgis

def is_qgis_version_3():
    return Qgis.QGIS_VERSION >= '3.0'

from qgis.core import QgsRasterLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform

if is_qgis_version_3():
    from qgis.core import QgsProject
else:
    from qgis.core import QgsMapLayerRegistry as QgsProject
    from qgis.gui import QgsMessageBar

if is_qgis_version_3():
    from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QDate
    from PyQt5.QtGui import QIcon, QTextCharFormat
    from PyQt5.QtWidgets import QAction, QFileDialog
else:
    from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt, QDate
    from PyQt4.QtGui import QIcon, QAction, QTextCharFormat, QFileDialog


class MessageType(Enum):
    INFO = ('Info', Qgis.Info if is_qgis_version_3() else QgsMessageBar.INFO)
    WARNING = ('Warning', Qgis.Warning if is_qgis_version_3() else QgsMessageBar.WARNING)
    CRITICAL = ('Error', Qgis.Critical if is_qgis_version_3() else QgsMessageBar.CRITICAL)
    SUCCESS = ('Success', Qgis.Success if is_qgis_version_3() else QgsMessageBar.SUCCESS)


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
        self.parameters = Settings.parameters
        self.instance_id = Settings.instance_id
        self.capabilities = []
        self.active_time = 'time0'
        self.cloud_cover = {}
        self.current_extent = {}
        self.custom_extent = ''
        self.download_current_extent = True
        self.qgis_layers = []

    @staticmethod
    def translate(message):
        """Get the translation for a string using Qt translation API.
        """
        return QCoreApplication.translate('SentinelHub', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
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

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SentinelHub/favicon.ico'
        self.add_action(
            icon_path,
            text=self.translate(u'SentinelHub'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def initGuiSettings(self):
        """Fill combo boxes:
        Layers - Renderers
        Priority
        """
        self.updateLayers()

        self.dockwidget.instanceId.setText(Settings.instance_id)
        self.dockwidget.inputResX.setText(Settings.parameters_wcs['resx'])
        self.dockwidget.inputResY.setText(Settings.parameters_wcs['resy'])

        self.dockwidget.priority.clear()
        self.dockwidget.priority.addItems(Settings.priority_list)

        self.dockwidget.format.clear()
        self.dockwidget.format.addItems(Settings.img_formats)

        self.dockwidget.epsg.clear()
        self.dockwidget.epsg.addItems(Settings.epsg)

    def show_message(self, message, message_type):
        """ Show message for user

        :param message: Message for user
        :param message: str
        :param message_type: Type of message
        :param message_type: MessageType
        """
        self.iface.messageBar().pushMessage(message_type.value[0], message, level=message_type.value[1])

    def updateLayers(self):
        """
        Update list of Layers avalivale at Sentinel Hub Instance
        :return:
        """
        self.dockwidget.layers.clear()

        layer_list = []
        for layer in self.capabilities:
            layer_list.append(layer['Title'])
        self.dockwidget.layers.addItems(layer_list)

    def updateCurrentWMSLayers(self):
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

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
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

    def getURIrequestWMS(self):
        """ Generate URI for WMS request from parameters """

        uri = ''
        request_parameters = list(Settings.parameters_wms.items()) + list(Settings.parameters.items())
        for parameter, value in request_parameters:
            uri = uri + parameter + '=' + value + '&'

        # Every parameter that QGIS layer doesn't use by default must be in url
        # And url has to be encoded
        url = Settings.url_base + 'wms/' + self.instance_id + '?TIME=' + self.getTime() + '&priority=' \
            + Settings.parameters['priority'] + '&maxcc=' + Settings.parameters['maxcc']
        return uri + 'url=' + quote_plus(url)

    def getURLrequestWCS(self, bbox):
        """ Generate URL for WCS request from parameters

            :param bbox: Bounding box [xmin, ymin, xmax, ymax]
            :type bbox: str
        """

        url = Settings.url_base + 'wcs/' + self.instance_id + '?'
        request_parameters = list(Settings.parameters_wcs.items()) + list(Settings.parameters.items())

        for parameter, value in request_parameters:
            if parameter in ('resx', 'resy'):
                value = value.strip('m') + 'm'
            url += parameter + '=' + value + '&'
        return url + 'bbox=' + bbox

    def getURLrequestWFS(self, time_range):
        """ Generate URL for WFS request from parameters """

        url = Settings.url_base + 'wfs/' + self.instance_id + '?'
        for parameter, value in Settings.parameters_wfs.items():
            url = url + parameter + '=' + value + '&'

        return url + 'bbox=' + self.getExtent()[0] + '&time=' + time_range

    # ---------------------------------------------------------------------------

    def getCapabilities(self, service, instance_id):
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

    def getCloudCover(self, time_range):
        """ Get cloud cover for current extent.

        :return:
        """

        self.current_extent, width = self.getExtent()
        self.cloud_cover = {}

        if not self.instance_id:
            return

        response = self.download_from_url(self.getURLrequestWFS(time_range))

        if response:
            area_info = response.json()
            for feature in area_info['features']:
                self.cloud_cover.update(
                    {str(feature['properties']['date']):feature['properties']['cloudCoverPercentage']})
            self.updateCalendarFromCloudCover()

    def downloadWCS(self, url, filename, destination):
        """
        Download image from provided URL WCS request

        :param url: WCS url request with specified bounding box
        :param filename: filename of image
        :param destination: path to destination
        :return:
        """
        with open('{}/{}'.format(destination, filename), "wb") as download_file:
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
            self.show_message("Done downloading to {}".format(filename), MessageType.SUCCESS)
            time.sleep(1)
        else:
            self.show_message("Failed to download from {} to {}".format(url, filename), MessageType.CRITICAL)

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

            self.show_message(message, MessageType.CRITICAL)
            response = None

        return response
    # ----------------------------------------------------------------------------

    def addWms(self):
        """
        Add WMS raster layer to canvas,
        :return:
        """
        self.updateParameters()
        name = '{} - {}'.format(self.parameters['prettyName'], self.parameters['title'])
        new_layer = QgsRasterLayer(self.getURIrequestWMS(), name, 'wms')
        if new_layer.isValid():
            QgsProject.instance().addMapLayer(new_layer)
            self.updateCurrentWMSLayers()
        else:
            self.show_message('Failed to create layer {}.'.format(name), MessageType.CRITICAL)

    def getExtent(self):
        """
        Get Current extent if not same as target transorfm it to target, transform it to WebMercator
        TODO: If user defined CRS it might fail?!
        :return:
        """

        bbox = self.iface.mapCanvas().extent()
        if is_qgis_version_3():
            current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapSettings().destinationCrs().authid())
        else:
            current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapRenderer().destinationCrs().authid())
        target_crs = QgsCoordinateReferenceSystem(self.parameters['crs'])

        if current_crs != target_crs:
            if is_qgis_version_3():
                xform = QgsCoordinateTransform(current_crs, target_crs, QgsProject.instance())
            else:
                xform = QgsCoordinateTransform(current_crs, target_crs)
            bbox = xform.transform(bbox)

        if target_crs.authid() == 'EPSG:4326':
            return [",".join(map(str, [round(bbox.yMinimum(), 6), round(bbox.xMinimum(), 6),
                                       round(bbox.yMaximum(), 6), round(bbox.xMaximum(), 6)])), self.getWidthHeight(
                bbox,
                target_crs)]
        else:
            return [",".join(map(str, [round(bbox.xMinimum(), 6), round(bbox.yMinimum(), 6),
                                       round(bbox.xMaximum(), 6), round(bbox.yMaximum(), 6)])), '']

    def getSelectedExtent(self):
        """
        Get extent of selected feature
        :return:
        """
        self.updateParameters()

        if self.iface.activeLayer().type() == 0:
            features = self.iface.activeLayer().selectedFeatures()
            if len(features) == 0:
                self.show_message("No feature selected", MessageType.INFO)
            elif len(features) == 1:
                bbox = features[0].geometry().boundingBox()

                current_crs = QgsCoordinateReferenceSystem(self.iface.activeLayer().crs().authid())
                target_crs = QgsCoordinateReferenceSystem(self.parameters['crs'])

                if current_crs != target_crs:
                    xform = QgsCoordinateTransform(current_crs, target_crs)
                    bbox = xform.transform(bbox)

                if target_crs.authid() == 'EPSG:4326':
                    return [",".join(map(str, [round(bbox.yMinimum(), 6), round(bbox.xMinimum(), 6),
                                               round(bbox.yMaximum(), 6), round(bbox.xMaximum(), 6)])),
                            self.getWidthHeight(bbox, target_crs)]
                else:
                    return [",".join(map(str, [round(bbox.xMinimum(), 6), round(bbox.yMinimum(), 6),
                                               round(bbox.xMaximum(), 6), round(bbox.yMaximum(), 6)])), '']
            else:
                self.show_message("More than one feature selected, please select only one.", MessageType.INFO)
        else:
            self.show_message("Select a layer from 'Select Layer', then select 'Create new WMS layer'",
                              MessageType.INFO)
        return False

    def updateCustomExtent(self):
        """
        From Custom extent get values, save them and show them in UI
        :return:
        """

        if self.getSelectedExtent():
            self.custom_extent, self.custom_extent_width_height = self.getSelectedExtent()
            bbox = self.custom_extent.split(',')
            self.dockwidget.xMin.setText(bbox[0])
            self.dockwidget.yMin.setText(bbox[1])
            self.dockwidget.xMax.setText(bbox[2])
            self.dockwidget.yMax.setText(bbox[3])

    def getWidthHeight(self, bbox, bbox_crs):

        utm_crs = QgsCoordinateReferenceSystem(self.longitudeToUTMzone(
            (bbox.xMinimum() + bbox.xMaximum()) / 2,
            (bbox.yMinimum() + bbox.yMaximum()) / 2))
        xform = QgsCoordinateTransform(bbox_crs, utm_crs)
        bbox = xform.transform(bbox)
        width = int(math.fabs((bbox.xMaximum() - bbox.xMinimum()) / int(Settings.parameters_wcs['resx'].strip('m'))))
        height = int(math.fabs((bbox.yMinimum() - bbox.yMaximum()) / int(Settings.parameters_wcs['resy'].strip('m'))))
        return '&width={0}&height={1}'.format(width, height)

    def longitudeToUTMzone(self, longitude, latitude):
        zone = int(math.floor((longitude + 180) / 6) + 1)
        hemisphere = 6 if latitude > 0 else 7
        return 'EPSG:32{0}{1:02d}'.format(hemisphere, zone)

    def updateQgisLayer(self):
        """
        Updating layer in pyqgis somehow doesn't work therefore this method creates a new layer and deletes the old one
        :param rlayer: rlayer that should be updated
        :return:
        """
        selected_index = self.dockwidget.sentinelWMSlayers.currentIndex()
        if selected_index < 0:
            return

        for layer in self.get_qgis_layers():
            if layer == self.qgis_layers[selected_index]:
                self.addWms()
                QgsProject.instance().removeMapLayer(layer)
                self.updateCurrentWMSLayers()
                return
        self.show_message('Chosen layer {} does not exist anymore.'
                          ''.format(self.dockwidget.sentinelWMSlayers.currentText()), MessageType.INFO)
        self.updateCurrentWMSLayers()

    def updateParameters(self):
        """
        Update parameters from GUI
        :return:
        """

        self.parameters['layers'] = self.capabilities[self.dockwidget.layers.currentIndex()]['Name']
        self.parameters['coverage'] = self.capabilities[self.dockwidget.layers.currentIndex()]['Name']
        self.parameters['title'] = self.capabilities[self.dockwidget.layers.currentIndex()]['Title']
        self.parameters['priority'] = self.dockwidget.priority.currentText()
        self.parameters['maxcc'] = str(self.dockwidget.maxcc.value())
        self.parameters['time'] = str(self.getTime())
        self.parameters['crs'] = self.dockwidget.epsg.currentText().replace(' ', '')

        Settings.parameters_wcs['resx'] = self.dockwidget.inputResX.text()
        Settings.parameters_wcs['resy'] = self.dockwidget.inputResY.text()

    def updateMaxccLabel(self):
        """
        Update Max Cloud Coverage Label when slider value change
        :return:
        """

        self.dockwidget.maxccLabel.setText('Cloud coverage ' + str(self.dockwidget.maxcc.value()) + ' %')

    def getTime(self):
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

    def addTime(self):
        """
        Add / update time parameter from calendar regrading which time was chosen and paint calander
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

    def clearAllCells(self):
        """
        Clear all cells
        :return:
        """

        style = QTextCharFormat()
        style.setBackground(Qt.white)
        self.dockwidget.calendar.setDateTextFormat(QDate(), style)

    def updateCalendarFromCloudCover(self):
        """
        Update painted cells regrading Max Cloud Coverage
        :return:
        """

        self.clearAllCells()
        for date, value in self.cloud_cover.items():
            if float(value) < int(self.parameters['maxcc']):
                d = date.split('-')
                style = QTextCharFormat()
                style.setBackground(Qt.gray)
                self.dockwidget.calendar.setDateTextFormat(QDate(int(d[0]), int(d[1]), int(d[2])), style)

    def moveCalendar(self, active):
        """
        :param active:
        :return:
        """
        if active == 'time0':
            self.dockwidget.calendarSpacer.hide()
        else:
            self.dockwidget.calendarSpacer.show()
        self.active_time = active

    def selectDestination(self):
        """
        Opens dialog to select destination folder
        :return:
        """

        folder = QFileDialog.getExistingDirectory(self.dockwidget, "Select folder")
        self.dockwidget.destination.setText(folder)

    def download_caption(self):
        """
        Prepare download request and then download images
        :return:
        """
        if not self.instance_id:
            self.show_message("Please set Sentinel Hub Instance ID first.", MessageType.INFO)
            return

        self.updateParameters()
        if self.dockwidget.destination.text():
            destination = self.dockwidget.destination.text()
        else:
            self.selectDestination()
            destination = self.dockwidget.destination.text()

        if self.dockwidget.destination.text():
            if self.download_current_extent:
                bbox, width_height = self.getExtent()
            else:
                bbox = self.custom_extent
                width_height = self.custom_extent_width_height

            url = self.getURLrequestWCS(bbox)
            filename = self.getFileName(bbox)

            self.downloadWCS(url, filename, destination)
        else:
            self.show_message("Download canceled. No destination set", MessageType.CRITICAL)

    def getFileName(self, bbox):
        """
        Prepare unique filename with some metadata encoded (YYYYMMDD_sentil2_LAYER_xmin_y_min.FORMAT)
        :param bbox:
        :return:
        """

        bbox_array = []
        for value in bbox.split(','):
            bbox_array.append(value.split('.')[0])

        return '.'.join(map(str, ['_'.join(map(str, [Settings.parameters['time'].split('/')[0].replace('-', ''),
                                                     Settings.parameters['name'],
                                                     Settings.parameters['layers'],
                                                     bbox_array[0],
                                                     bbox_array[1]])),
                                  Settings.parameters_wcs['format'].split(';')[0].split('/')[1]]))

    def updateMaxcc(self):
        """
        Update max cloud cover
        :return:
        """

        self.updateParameters()
        self.updateCalendarFromCloudCover()

    def updateDownloadFormat(self):
        """
        Update image format
        :return:
        """

        Settings.parameters_wcs['format'] = self.dockwidget.format.currentText()

    def changeExactDate(self):
        """
        Change if using exact date or not
        :return:
        """

        if self.dockwidget.exactDate.isChecked():
            self.dockwidget.time1.hide()
            self.moveCalendar('time0')
        else:
            self.dockwidget.time1.show()

    def changeInstanceId(self):
        """
        Change Instance ID, and validate that is valid
        :return:
        """
        new_instance_id = self.dockwidget.instanceId.text()
        if new_instance_id == self.instance_id:
            return

        capabilities, is_valid = self.getCapabilities('wms', new_instance_id)

        if is_valid:
            self.instance_id = new_instance_id
            self.capabilities = capabilities
            self.updateLayers()
            self.show_message("New Instance ID and layers set.", MessageType.SUCCESS)
        else:
            self.dockwidget.instanceId.setText(self.instance_id)

    def updateMonth(self):
        """
        On Widget Month update, get first and last dates to get Cloud Cover
        :return:
        """

        year = self.dockwidget.calendar.yearShown()
        month = self.dockwidget.calendar.monthShown()
        _, number_of_days = calendar.monthrange(year, month)
        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, number_of_days)

        self.getCloudCover(first.strftime('%Y-%m-%d') + '/' + last.strftime('%Y-%m-%d') + '/P1D')

    def toggleExtent(self, setting):
        """
        Toggle Current / Custom extent
        :param setting:
        :return:
        """

        if setting == 'current':
            self.download_current_extent = True
            self.dockwidget.widgetCustomExtent.hide()
        elif setting == 'custom':
            self.download_current_extent = False
            self.dockwidget.widgetCustomExtent.show()

    def run(self):
        """Run method that loads and starts the plugin and binds all UI actions"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            if self.dockwidget is None:
                # Initial function calls
                self.dockwidget = SentinelHubDockWidget()
                self.capabilities, _ = self.getCapabilities('wms', self.instance_id)
                self.initGuiSettings()
                self.updateMonth()
                self.toggleExtent('current')
                self.dockwidget.calendarSpacer.hide()
                self.updateCurrentWMSLayers()

                # Bind actions to buttons
                self.dockwidget.buttonAddWms.clicked.connect(self.addWms)
                self.dockwidget.buttonUpdateWms.clicked.connect(self.updateQgisLayer)
                self.dockwidget.buttonDownload.clicked.connect(self.download_caption)
                self.dockwidget.refreshExtent.clicked.connect(self.updateCustomExtent)
                self.dockwidget.selectDestination.clicked.connect(self.selectDestination)

                # Render input fields changes and events
                self.dockwidget.time0.selectionChanged.connect(lambda: self.moveCalendar('time0'))
                self.dockwidget.time1.selectionChanged.connect(lambda: self.moveCalendar('time1'))
                self.dockwidget.calendar.clicked.connect(self.addTime)
                self.dockwidget.exactDate.stateChanged.connect(self.changeExactDate)
                self.dockwidget.calendar.currentPageChanged.connect(self.updateMonth)
                self.dockwidget.maxcc.valueChanged.connect(self.updateMaxccLabel)
                self.dockwidget.maxcc.sliderReleased.connect(self.updateMaxcc)
                self.dockwidget.instanceId.editingFinished.connect(self.changeInstanceId)

                # Download input fields changes and events
                self.dockwidget.format.currentIndexChanged.connect(self.updateDownloadFormat)
                self.dockwidget.radioCurrentExtent.clicked.connect(lambda: self.toggleExtent('current'))
                self.dockwidget.radioCustomExtent.clicked.connect(lambda: self.toggleExtent('custom'))

            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
