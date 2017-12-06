# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SentinelHub
                                 A QGIS plugin
 SentinelHub
                              -------------------
        begin                : 2017-07-07
        git sha              : $Format:%H$
        copyright            : (C) 2017 by TODO
        email                : TODO
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
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.gui import *
from qgis.core import *
from SentinelHub_dockwidget import SentinelHubDockWidget
from xml.etree import ElementTree
import os.path
import requests
import json
import time
import calendar
import datetime
import math
import qgis
import resources
import warnings
import urllib

import Settings


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
        self.menu = self.tr(u'&SentinelHub')
        self.toolbar = self.iface.addToolBar(u'SentinelHub')
        self.toolbar.setObjectName(u'SentinelHub')
        self.pluginIsActive = False
        self.dockwidget = None

        # Set value
        self.parameters = Settings.parameters
        self.instanceId = Settings.instanceId
        self.capabilities = []
        self.activeTime = 'time0'
        self.cloudCover = {}
        self.currentExtent = {}
        self.customExtent = ''
        self.downloadCurrentExtent = True

    def tr(self, message):
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
            text=self.tr(u'SentinelHub'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def initGuiSettings(self):
        """Fill combo boxes:
        Layers - Renderers
        Priority
        """

        self.updateLayers()

        self.dockwidget.instanceId.setText(Settings.instanceId)
        self.dockwidget.inputResX.setText(Settings.parametersWCS['resx'])
        self.dockwidget.inputResY.setText(Settings.parametersWCS['resy'])

        self.dockwidget.priority.clear()
        self.dockwidget.priority.addItems(Settings.priority_list)

        self.dockwidget.format.clear()
        self.dockwidget.format.addItems(Settings.img_formats)

        self.dockwidget.epsg.clear()
        self.dockwidget.epsg.addItems(Settings.epsg)

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

        layers = self.iface.legendInterface().layers()
        if len(layers) != 0:
            layer_list = []
            for layer in layers:
                # if layer.type() == 1:
                layer_list.append(layer.name())
            self.dockwidget.sentinelWMSlayers.clear()
            self.dockwidget.sentinelWMSlayers.addItems(layer_list)

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
                self.tr(u'&SentinelHub'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

        # --------------------------------------------------------------------------

    def getURIrequestWMS(self):
        """ Generate URI for WMS request from parameters """

        uri = ''
        requestParameters = dict(Settings.parametersWMS.items() + Settings.parameters.items())
        for parameter, value in requestParameters.iteritems():
            uri = uri + parameter + '=' + value + '&'

        # Every parameter that QGIS layer doesn't use by default must be in url
        # And url has to be encoded
        url = Settings.urlBase + 'wms/' + self.instanceId + '?TIME=' + self.getTime() + '&priority=' \
              + Settings.parameters['priority'] + '&maxcc=' + Settings.parameters['maxcc']
        return uri + 'url=' + urllib.quote_plus(url)

    def getURLrequestWCS(self, bbox):
        """ Generate URL for WCS request from parameters

            :param bbox: Bounding box [xmin, ymin, xmax, ymax]
            :type bbox: str
        """

        url = Settings.urlBase + 'wcs/' + self.instanceId + '?'
        requestParameters = dict(Settings.parametersWCS.items() + Settings.parameters.items())

        for parameter, value in requestParameters.iteritems():
            if parameter in ('resx', 'resy'):
                value = value.strip('m') + 'm'
            url += parameter + '=' + value + '&'
        return url + 'bbox=' + bbox

    def getURLrequestWFS(self, timeRange):
        """ Generate URL for WFS request from parameters """

        url = Settings.urlBase + 'wfs/' + self.instanceId + '?'
        for parameter, value in Settings.parametersWFS.iteritems():
            url = url + parameter + '=' + value + '&'

        return url + 'bbox=' + self.getExtent()[0] + '&time=' + timeRange

        # ---------------------------------------------------------------------------

    def getCapabilities(self, service):
        """ Get capabilities of desired service

        :param service: Service (wms, wfs, wdc)
        :type service: object
        """

        props = []

        try:
            response = requests.get(Settings.urlBase + service + '/' +
                                    self.instanceId +
                                    '?service=' + service + '&request=GetCapabilities&version=1.1.1')
        except requests.ConnectionError as error:
            self.iface.messageBar().pushMessage("Connection error: ",
                                                'Can not access serivce! Check your intrenet connection.',
                                                level=QgsMessageBar.CRITICAL)
            response = False

        if response:
            root = ElementTree.fromstring(response.content)
            for layer in root.findall('./Capability/Layer/Layer'):
                props.append({'Title': layer.find('Title').text,
                              'Name': layer.find('Name').text})
        return props

    def getCloudCover(self, timeRange):
        """ Get cloud cover for current extent.

        :return:
        """

        self.currentExtent, width = self.getExtent()
        self.cloudCover = {}
        url = self.getURLrequestWFS(timeRange)
        try:
            response = requests.get(url)
        except requests.ConnectionError as error:
            self.iface.messageBar().pushMessage("Connection error: ",
                                                'Can not access serivce! Check your intrenet connection. - ' + error,
                                                level=QgsMessageBar.CRITICAL)
            response = False
        if response:
            content = json.loads(response.content)
            for features in content['features']:
                self.cloudCover.update(
                    {str(features['properties']['date']): features['properties']['cloudCoverPercentage']})
            self.updatecalendarFromCloudCover()

    def downloadWCS(self, url, filename, destination):
        """
        Download image from provided URL WCS request

        :param url: WCS url request with specified bounding box
        :param filename: filename of image
        :param destination: path to destination
        :return:
        """
        # self.iface.messageBar().pushMessage("Downloading ", filename, level=QgsMessageBar.INFO)

        with open(destination + '/' + filename, "wb") as dlfile:
            try:
                response = requests.get(url, stream=True)
            except requests.ConnectionError as error:
                self.iface.messageBar().pushMessage("Connection error: ",
                                                    'Can not access serivce! Check your intrenet connection. - ' + error,
                                                    level=QgsMessageBar.CRITICAL)
                response = False

            if response:
                total_length = response.headers.get('content-length')

                if total_length is None:
                    dlfile.write(response.content)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        dlfile.write(data)
                        done = int(100 * dl / total_length)
                downloaded = True
            else:
                downloaded = False
        if downloaded:
            self.iface.messageBar().pushMessage("Done downloading: ", filename,
                                                level=QgsMessageBar.SUCCESS)
            time.sleep(1)
        else:
            self.iface.messageBar().pushMessage("Error ", 'Download failed: ' + filename,
                                                level=QgsMessageBar.CRITICAL)

            # ----------------------------------------------------------------------------

    def addWms(self):
        """
        Add WMS raster layer to canvas,
        :return:
        """

        self.updateParameters()
        name = self.parameters['prettyName'] + " - " + self.parameters['title']
        rlayer = QgsRasterLayer(self.getURIrequestWMS(),
                                name,
                                'wms')
        if not rlayer.isValid():
            print "Layer failed to load!"

        QgsMapLayerRegistry.instance().addMapLayer(rlayer)
        self.updateCurrentWMSLayers()

    def getExtent(self):
        """
        Get Current extent if not same as target transorfm it to target, transform it to WebMercator
        TODO: If user defined CRS it might fail?!
        :return:
        """

        bbox = self.iface.mapCanvas().extent()
        current_crs = QgsCoordinateReferenceSystem(self.iface.mapCanvas().mapRenderer().destinationCrs().authid())
        target_crs = QgsCoordinateReferenceSystem(self.parameters['crs'])

        if current_crs != target_crs:
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
                self.iface.messageBar().pushMessage("Info", "No feature selected",
                                                    level=QgsMessageBar.INFO)
            elif len(features) == 1:
                bbox = features[0].geometry().boundingBox()

                current_crs = QgsCoordinateReferenceSystem(self.iface.activeLayer().crs().authid())
                target_crs = QgsCoordinateReferenceSystem(self.parameters['crs'])

                if current_crs != target_crs:
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
            else:
                self.iface.messageBar().pushMessage("Info", "More than one features selected. Please select only one!",
                                                    level=QgsMessageBar.INFO)
        else:
            self.iface.messageBar().pushMessage("Info", "Select vector layer from Layers panel, then select feature on map!",
                                                level=QgsMessageBar.INFO)
        return False

    def updateCustomExtent(self):
        """
        From Custom extent get values, save them and show them in UI
        :return:
        """

        if self.getSelectedExtent():
            self.customExtent, self.customExtentWidthHeight = self.getSelectedExtent()
            bbox = self.customExtent.split(',')
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
        width = int(math.fabs((bbox.xMaximum() - bbox.xMinimum()) / int(Settings.parametersWCS['resx'].strip('m'))))
        height = int(math.fabs((bbox.yMinimum() - bbox.yMaximum()) / int(Settings.parametersWCS['resy'].strip('m'))))
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
        layers = self.iface.legendInterface().layers()
        rlayer = layers[self.dockwidget.sentinelWMSlayers.currentIndex()]
        self.addWms()
        QgsMapLayerRegistry.instance().removeMapLayer(rlayer)
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

        Settings.parametersWCS['resx'] = self.dockwidget.inputResX.text()
        Settings.parametersWCS['resy'] = self.dockwidget.inputResY.text()

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

        if self.activeTime == 'time0':
            timeInput = self.dockwidget.time0
        elif self.activeTime == 'time1':
            timeInput = self.dockwidget.time1

        timeInput.setText(str(self.dockwidget.calendar.selectedDate().toPyDate()))

        # ------------------------------------------------------------------------

    def clearAllCells(self):
        """
        Clear all cells
        :return:
        """

        style = QTextCharFormat()
        style.setBackground(Qt.white)
        self.dockwidget.calendar.setDateTextFormat(QDate(), style)

    def updatecalendarFromCloudCover(self):
        """
        Update painted cells regrading Max Cloud Coverage
        :return:
        """

        self.clearAllCells()
        for date, value in self.cloudCover.iteritems():
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
        self.activeTime = active

    def selectDestination(self):
        """
        Opens dialog to select destination folder
        :return:
        """

        folder = QFileDialog.getExistingDirectory(self.dockwidget, "Select folder")
        self.dockwidget.destination.setText(folder)

    def download(self):
        """
        Prepare download request and then download images
        :return:
        """

        self.updateParameters()
        if self.dockwidget.destination.text():
            destination = self.dockwidget.destination.text()
        else:
            self.selectDestination()
            destination = self.dockwidget.destination.text()

        if self.dockwidget.destination.text():
            if self.downloadCurrentExtent:
                bbox, widthHeight = self.getExtent()
            else:
                bbox = self.customExtent
                widthHeight = self.customExtentWidthHeight

            url = self.getURLrequestWCS(bbox)
            filename = self.getFileName(bbox)

            self.downloadWCS(url, filename, destination)
        else:
            self.iface.messageBar().pushMessage("Info", "Download canceled. No destination set",
                                                level=QgsMessageBar.INFO)

    def getFileName(self, bbox):
        """
        Prepare unique filename with some metadata encoded (YYYYMMDD_sentil2_LAYER_xmin_y_min.FORMAT)
        :param bbox:
        :return:
        """

        bboxArray = []
        for value in bbox.split(','):
            bboxArray.append(value.split('.')[0])

        return '.'.join(map(str, ['_'.join(map(str, [Settings.parameters['time'].split('/')[0].replace('-', ''),
                                                     Settings.parameters['name'],
                                                     Settings.parameters['layers'],
                                                     bboxArray[0],
                                                     bboxArray[1]])),
                                  Settings.parametersWCS['format'].split(';')[0].split('/')[1]]))

    def updateMaxcc(self):
        """
        Update max cloud cover
        :return:
        """

        self.updateParameters()
        self.updatecalendarFromCloudCover()

    def updateDownloadFormat(self):
        """
        Update image format
        :return:
        """

        Settings.parametersWCS['format'] = self.dockwidget.format.currentText()

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

        try:
            response = requests.get(Settings.urlBase + 'wms/' +
                                    self.dockwidget.instanceId.text() +
                                    '?service=wms&request=GetCapabilities&version=1.1.1')
        except requests.ConnectionError as error:
            response = False
            self.iface.messageBar().pushMessage("Connection error: ",
                                                'Can not access serivce! Check your intrenet connection. - ' + error,
                                                level=QgsMessageBar.CRITICAL)

        if response.status_code == 400:
            self.iface.messageBar().pushMessage("Error", "Instance ID not valid",
                                                level=QgsMessageBar.CRITICAL)
        elif response.status_code == 200:
            self.instanceId = self.dockwidget.instanceId.text()
            self.capabilities = self.getCapabilities('wms')
            self.updateLayers()
            self.iface.messageBar().pushMessage("Success", "New Instance ID and available renderer set",
                                                level=QgsMessageBar.SUCCESS)
        else:
            self.iface.messageBar().pushMessage("Error", "Instance ID not valid",
                                                level=QgsMessageBar.CRITICAL)


    def updateMonth(self):
        """
        On Widget Month update, get first and last dates to get Cloud Cover
        :return:
        """

        year = self.dockwidget.calendar.yearShown()
        month = self.dockwidget.calendar.monthShown()
        _, numberOfDays = calendar.monthrange(year, month)
        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, numberOfDays)

        self.getCloudCover(first.strftime('%Y-%m-%d') + '/' + last.strftime('%Y-%m-%d') + '/P1D')

    def toggleExtent(self, setting):
        """
        Toggle Current / Custom extent
        :param setting:
        :return:
        """

        if setting == 'current':
            self.downloadCurrentExtent = True
            self.dockwidget.widgetCustomExtent.hide()
        elif setting == 'custom':
            self.downloadCurrentExtent = False
            self.dockwidget.widgetCustomExtent.show()

    def run(self):
        """Run method that loads and starts the plugin and binds all UI actions"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            if self.dockwidget == None:
                # Initial function calls
                self.dockwidget = SentinelHubDockWidget()
                self.capabilities = self.getCapabilities('wms')
                self.initGuiSettings()
                self.updateMonth()
                self.toggleExtent('current')
                self.dockwidget.calendarSpacer.hide()
                self.updateCurrentWMSLayers()

                # Bind actions to buttons
                self.dockwidget.buttonAddWms.clicked.connect(self.addWms)
                self.dockwidget.buttonUpdateWms.clicked.connect(self.updateQgisLayer)
                self.dockwidget.buttonDownload.clicked.connect(self.download)
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
