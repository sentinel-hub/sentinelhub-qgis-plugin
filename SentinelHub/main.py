"""
/***************************************************************************
 SentinelHub
                             -------------------
        begin                : 2017-07-07
        copyright            : (C) 2020 by Sinergise
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
 The main module
"""

import os
import time
import calendar
import datetime

from qgis.core import Qgis, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsCoordinateReferenceSystem,\
    QgsCoordinateTransform, QgsRectangle, QgsMessageLog
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon, QTextCharFormat
from PyQt5.QtWidgets import QAction, QFileDialog

from .constants import MessageType, CrsType, ImagePriority, ImageFormat, BaseUrl, ExtentType, ServiceType, TimeType, \
    AVAILABLE_SERVICE_TYPES, MAX_CLOUD_COVER_BBOX_SIZE, DATA_SOURCES
from .dockwidget import SentinelHubDockWidget
from .sentinelhub.configuration import ConfigurationManager
from .sentinelhub.client import Client
from .sentinelhub.ogc import get_service_uri, get_wcs_url, get_wfs_url
from .settings import Settings
from .utils.geo import get_bbox, is_bbox_too_large, bbox_to_string
from .utils.meta import get_plugin_version
from .utils.time import parse_date


class SentinelHubPlugin:
    """ The main class defining plugin logic
    """
    PLUGIN_NAME = 'SentinelHub'
    ICON_PATH = ':/plugins/SentinelHub/favicon.ico'

    def __init__(self, iface):
        """ Called by QGIS at the beginning when you open QGIS or when the plugin is enabled in the
        Plugin Manager.

        :param iface: A QGIS interface instance.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.toolbar = self.iface.addToolBar(self.PLUGIN_NAME)
        self.plugin_actions = []
        self.dockwidget = None

        self.plugin_version = get_plugin_version()
        self.settings = Settings()
        self.client = Client(self.iface, self.plugin_version)
        self.manager = None

        # TODO: remove all below:
        self.qgis_layers = []
        self.cloud_cover = {}

        self.custom_bbox_params = {}
        for name in ['latMin', 'latMax', 'lngMin', 'lngMax']:
            self.custom_bbox_params[name] = ''

        self.layer_selection_event = None

    def initGui(self):
        """ This method is called by QGIS when the main GUI starts up or when the plugin is enabled in the
        Plugin Manager.
        """
        icon = QIcon(self.ICON_PATH)
        bold_plugin_name = '<b>{}</b>'.format(self.PLUGIN_NAME)
        action = QAction(icon, bold_plugin_name, self.iface.mainWindow())

        action.triggered.connect(self.run)
        action.setEnabled(True)

        self.toolbar.addAction(action)
        self.iface.addPluginToWebMenu(self.PLUGIN_NAME, action)

        self.plugin_actions.append(action)

    def unload(self):
        """ This is called by QGIS when a user disables or uninstalls the plugin. This method removes the plugin and
        it's icon from everywhere it appears in QGIS GUI.
        """
        if self.dockwidget:
            self.dockwidget.close()

        for action in self.plugin_actions:
            self.iface.removePluginWebMenu(
                self.PLUGIN_NAME,
                action
            )
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """ It loads and starts the plugin and binds all UI actions.
        """
        if self.dockwidget is not None:
            return

        self.dockwidget = SentinelHubDockWidget()
        self.initialize_ui()

        # Login widget
        self.dockwidget.serviceUrlLineEdit.editingFinished.connect(self.validate_base_url)
        self.dockwidget.loginPushButton.clicked.connect(self.login)

        # Create widget
        self.dockwidget.configurationComboBox.activated.connect(self.update_configuration)
        self.dockwidget.serviceTypeComboBox.activated.connect(self.update_service_type)
        self.dockwidget.layersComboBox.activated.connect(self.update_layer)
        self.dockwidget.crsComboBox.activated.connect(self.update_crs)

        self.dockwidget.startTimeLineEdit.mousePressEvent = lambda _: self.move_calendar(TimeType.START_TIME)
        self.dockwidget.endTimeLineEdit.mousePressEvent = lambda _: self.move_calendar(TimeType.END_TIME)
        self.dockwidget.startTimeLineEdit.editingFinished.connect(self.update_dates)
        self.dockwidget.endTimeLineEdit.editingFinished.connect(self.update_dates)
        self.dockwidget.exactDateCheckBox.stateChanged.connect(self.change_exact_date)
        self.dockwidget.calendarWidget.clicked.connect(self.add_calendar_date)
        self.dockwidget.calendarWidget.currentPageChanged.connect(self.update_available_calendar_dates)

        self.dockwidget.maxccSlider.valueChanged.connect(self.update_maxcc)
        self.dockwidget.maxccSlider.sliderReleased.connect(self.update_calendar_from_cloud_cover)

        # Create widget bottom buttons
        self.dockwidget.createLayerPushButton.clicked.connect(self.add_qgis_layer)
        self.dockwidget.updateLayerPushButton.clicked.connect(self.update_qgis_layer)

        # This overrides a press event, better solution would be to detect changes of QGIS layers
        self.layer_selection_event = self.dockwidget.mapLayerComboBox.mousePressEvent

        def new_layer_selection_event(event):
            self.update_current_map_layers()
            self.layer_selection_event(event)

        self.dockwidget.mapLayerComboBox.mousePressEvent = new_layer_selection_event

        self.dockwidget.downloadFolderLineEdit.editingFinished.connect(self.change_download_folder)

        # Download input fields changes and events
        self.dockwidget.imageFormatComboBox.currentIndexChanged.connect(self.update_download_format)
        self.dockwidget.resXLineEdit.editingFinished.connect(self.update_values)
        self.dockwidget.resYLineEdit.editingFinished.connect(self.update_values)

        self.dockwidget.currentExtentRadioButton.clicked.connect(lambda: self.toggle_extent(ExtentType.CURRENT))
        self.dockwidget.customExtentRadioButton.clicked.connect(lambda: self.toggle_extent(ExtentType.CUSTOM))
        self.dockwidget.latMinLineEdit.editingFinished.connect(self.update_values)
        self.dockwidget.latMaxLineEdit.editingFinished.connect(self.update_values)
        self.dockwidget.lngMinLineEdit.editingFinished.connect(self.update_values)
        self.dockwidget.lngMaxLineEdit.editingFinished.connect(self.update_values)

        self.dockwidget.showLogoCheckBox.stateChanged.connect(self.change_show_logo)

        self.dockwidget.downloadPushButton.clicked.connect(self.download_caption)
        self.dockwidget.refreshExtentPushButton.clicked.connect(self.take_window_bbox)
        self.dockwidget.selectDownloadFolderPushButton.clicked.connect(self.select_download_folder)

        # Tracks which layer is selected in left menu
        # self.iface.currentLayerChanged.connect(self.update_current_map_layers)

        self.dockwidget.closingPlugin.connect(self.on_close_plugin)

        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockwidget)
        self.dockwidget.show()

    def initialize_ui(self):
        """ Initializes and resets entire UI
        """
        self.dockwidget.serviceUrlLineEdit.setText(self.settings.base_url)
        self.dockwidget.clientIdLineEdit.setText(self.settings.client_id)
        self.dockwidget.clientSecretLineEdit.setText(self.settings.client_secret)

        self.dockwidget.serviceTypeComboBox.addItems(AVAILABLE_SERVICE_TYPES)
        self.update_service_type(self.settings.service_type.upper())

        self.dockwidget.calendarSpacer.hide()
        self.dockwidget.priorityComboBox.addItems([priority.nice_name for priority in ImagePriority])

        self.update_current_map_layers()

        self.dockwidget.imageFormatComboBox.addItems([image_format.nice_name for image_format in ImageFormat])
        self.toggle_extent(self.settings.download_extent_type)
        self.dockwidget.downloadFolderLineEdit.setText(self.settings.download_folder)

    def validate_base_url(self):
        """ Makes sure the base url is in the correct format
        """
        base_url = self.dockwidget.serviceUrlLineEdit.text()
        expected_base_url = base_url.rstrip('/')
        if not expected_base_url:
            expected_base_url = BaseUrl.MAIN
        if base_url != expected_base_url:
            self.dockwidget.serviceUrlLineEdit.setText(expected_base_url)

    def login(self):
        """ Uses credentials to connect to Sentinel Hub services and updates
        """
        new_settings = self.settings.copy()
        new_settings.base_url = self.dockwidget.serviceUrlLineEdit.text()
        new_settings.client_id = self.dockwidget.clientIdLineEdit.text()
        new_settings.client_secret = self.dockwidget.clientSecretLineEdit.text()

        new_manager = ConfigurationManager(new_settings, self.client)
        configurations = new_manager.get_configurations(reload=True)

        self.settings = new_settings
        self.manager = new_manager
        self.settings.save_credentials()

        self.dockwidget.configurationComboBox.clear()
        self.dockwidget.layersComboBox.clear()
        self.dockwidget.crsComboBox.clear()

        configuration_names = [configuration.name for configuration in configurations]
        self.dockwidget.configurationComboBox.addItems(configuration_names)
        configuration_index = self.manager.get_configuration_index(self.settings.instance_id)
        self.update_configuration(configuration_index)

    def update_configuration(self, configuration_index=None):
        """ A different configuration has been chosen
        """
        if configuration_index is not None:
            self.dockwidget.configurationComboBox.setCurrentIndex(configuration_index)

        configuration_index = self.dockwidget.configurationComboBox.currentIndex()
        if configuration_index < 0:
            self.settings.instance_id = ''
            return

        self.settings.instance_id = self.manager.get_configurations()[configuration_index].id

        self.dockwidget.layersComboBox.clear()
        layers = self.manager.get_layers(self.settings.instance_id)
        self.dockwidget.layersComboBox.addItems([layer.name for layer in layers])
        layer_index = self.manager.get_layer_index(self.settings.instance_id, self.settings.layer_id)
        self.update_layer(layer_index)

        self._update_available_crs()

    def update_service_type(self, service_type=None):
        """ Update service type and content that depends on it
        """
        if service_type is not None and service_type in AVAILABLE_SERVICE_TYPES:
            index = AVAILABLE_SERVICE_TYPES.index(service_type)
            self.dockwidget.serviceTypeComboBox.setCurrentIndex(index)

        self.settings.service_type = self.dockwidget.serviceTypeComboBox.currentText().lower()
        self.dockwidget.createLayerLabel.setText('Create new {} layer'.format(self.settings.service_type.upper()))

        if self.manager:
            self._update_available_crs()

    def update_layer(self, layer_index=None):
        """ Updates properties of selected Sentinel Hub layer
        """
        if layer_index is not None:
            self.dockwidget.layersComboBox.setCurrentIndex(layer_index)

        available_layers = self.manager.get_layers(self.settings.instance_id)
        layer_index = self.dockwidget.layersComboBox.currentIndex()
        if not 0 <= layer_index < len(available_layers):
            self.settings.layer_id = ''
            self.settings.data_source = ''
            self._clear_calendar_cells()
            return

        layer = available_layers[layer_index]
        self.settings.layer_id = layer.id
        self.settings.data_source = layer.data_source.type

        self.update_available_calendar_dates()

        # TODO:
        # if layer.data_source.is_cloudless() and not self.dockwidget.maxccSlider.isHidden():
        #     self.dockwidget.maxccSlider.hide()
        #     self.dockwidget.maxccLabel.hide()
        # if not layer.data_source.is_cloudless() and self.dockwidget.maxccSlider.isHidden():
        #     self.dockwidget.maxccSlider.show()
        #     self.dockwidget.maxccLabel.show()

        """
        # This doesn't hide vertical spacer and therefore doesn't look good
        if layer.data_source.is_timeless() and not self.dockwidget.calendarWidget.isHidden():
            self.dockwidget.calendarWidget.hide()
            self.dockwidget.exactDateCheckBox.hide()
            self.dockwidget.timeRangeLabel.hide()
            self.dockwidget.timeLabel.hide()
            self.dockwidget.startTimeLineEdit.hide()
            self.dockwidget.endTimeLineEdit.hide()
        if not layer.data_source.is_timeless() and self.dockwidget.calendarWidget.isHidden():
            self.dockwidget.calendarWidget.show()
            self.dockwidget.exactDateCheckBox.show()
            self.dockwidget.timeRangeLabel.show()
            self.dockwidget.timeLabel.show()
            self.dockwidget.startTimeLineEdit.show()
            self.dockwidget.endTimeLineEdit.show()
        """

        # TODO:
        # old_data_source = self.settings.data_source
        # if old_data_source != self.settings.data_source:
        #     self.update_available_calendar_dates()

    def update_crs(self, crs_index=None):
        """ Updates crs with selected Sentinel Hub CRS
        """
        if crs_index is not None:
            self.dockwidget.crsComboBox.setCurrentIndex(crs_index)

        crs_index = self.dockwidget.crsComboBox.currentIndex()
        crs_list = self.manager.get_available_crs()

        self.settings.crs = self.manager.get_available_crs()[crs_index].id if 0 <= crs_index < len(crs_list) else ''

    def _update_available_crs(self):
        """ Updates the list of available CRS
        """
        self.dockwidget.crsComboBox.clear()
        self.dockwidget.crsComboBox.addItems([crs.name for crs in self.manager.get_available_crs()])
        crs_index = self.manager.get_crs_index(self.settings.crs)
        self.update_crs(crs_index)

    def move_calendar(self, active):
        """ Moves calendar between the start and end time line edit fields
        """
        if active is TimeType.START_TIME:
            self.dockwidget.calendarSpacer.hide()
        else:
            self.dockwidget.calendarSpacer.show()
        self.settings.active_time = active.value

    def update_dates(self):
        """ Checks if newly inserted dates are valid and updates date attributes
        """
        new_start_time = parse_date(self.dockwidget.startTimeLineEdit.text())
        new_end_time = parse_date(self.dockwidget.endTimeLineEdit.text())

        if new_start_time is None or new_end_time is None:
            self.show_message('Please insert a valid date in a form YYYY-MM-DD', MessageType.INFO)
        elif new_start_time and new_end_time and new_start_time > new_end_time and not self.settings.is_exact_date:
            self.show_message('Start date must not be later than end date', MessageType.INFO)
        else:
            self.settings.start_time = new_start_time
            self.settings.end_time = new_end_time

        self.dockwidget.startTimeLineEdit.setText(self.settings.start_time)
        self.dockwidget.endTimeLineEdit.setText(self.settings.end_time)

    def change_exact_date(self):
        """ A switch between specifying a time interval and an exact date
        """
        self.settings.is_exact_date = self.dockwidget.exactDateCheckBox.isChecked()

        if self.settings.is_exact_date:
            self.dockwidget.endTimeLineEdit.hide()
            self.dockwidget.timeLabel.hide()
            self.move_calendar(TimeType.START_TIME)
        else:
            if self.settings.start_time and self.settings.end_time and \
                    self.settings.start_time > self.settings.end_time:
                self.settings.end_time = ''
                self.dockwidget.endTimeLineEdit.setText(self.settings.end_time)

            self.dockwidget.endTimeLineEdit.show()
            self.dockwidget.timeLabel.show()

    def add_calendar_date(self):
        """ Handles selected calendar date
        """
        calendar_time = str(self.dockwidget.calendarWidget.selectedDate().toPyDate())

        if self.settings.active_time == TimeType.START_TIME.value and \
                (self.settings.is_exact_date or not self.settings.end_time or calendar_time <= self.settings.end_time):
            self.settings.start_time = calendar_time
            self.dockwidget.startTimeLineEdit.setText(calendar_time)
        elif self.settings.active_time == TimeType.END_TIME.value and \
                (not self.settings.start_time or self.settings.start_time <= calendar_time):
            self.settings.end_time = calendar_time
            self.dockwidget.endTimeLineEdit.setText(calendar_time)
        else:
            self.show_message('Start date must not be later than end date', MessageType.INFO)

    def update_available_calendar_dates(self):
        """ For the current extent, current layer and current month it will find all days for which there is available
        data for that layer
        """
        if self.manager is None or not self.settings.instance_id or not self.settings.layer_id:
            return

        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)

        # TODO

        self.cloud_cover = {}
        self._clear_calendar_cells()

        bbox = get_bbox(self.iface, self.settings.crs)
        if is_bbox_too_large(bbox, self.settings.crs, MAX_CLOUD_COVER_BBOX_SIZE):
            return

        time_range = self.get_calendar_month_interval()
        bbox_str = bbox_to_string(bbox, self.settings.crs)
        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)
        wfs_url = get_wfs_url(self.settings, layer, bbox_str, time_range)  # TODO: make sure that is also triggered when maxcc is changed
        response = self.client.download(wfs_url, ignore_exception=True)

        if response:
            area_info = response.json()
            for feature in area_info['features']:
                date_str = str(feature['properties']['date'])
                self.cloud_cover[date_str] = feature['properties'].get('cloudCoverPercentage', 0)
            self.update_calendar_from_cloud_cover()

    def _clear_calendar_cells(self):
        """ Resets all highlighted calendar cells
        """
        style = QTextCharFormat()
        style.setBackground(Qt.white)
        self.dockwidget.calendarWidget.setDateTextFormat(QDate(), style)

    def update_maxcc(self):
        """ Updates maximum cloud coverage and it's label
        """
        self.settings.maxcc = str(self.dockwidget.maxccSlider.value())
        self.dockwidget.maxccLabel.setText('Cloud coverage {}%'.format(self.settings.maxcc))

    def update_calendar_from_cloud_cover(self):
        """
        Update painted cells regrading Max Cloud Coverage
        :return:
        """
        self._clear_calendar_cells()
        for date, value in self.cloud_cover.items():
            if float(value) <= int(self.settings.maxcc):
                d = date.split('-')
                style = QTextCharFormat()
                style.setBackground(Qt.gray)
                self.dockwidget.calendarWidget.setDateTextFormat(QDate(int(d[0]), int(d[1]), int(d[2])), style)

    def get_calendar_month_interval(self):
        year = self.dockwidget.calendarWidget.yearShown()
        month = self.dockwidget.calendarWidget.monthShown()
        _, number_of_days = calendar.monthrange(year, month)
        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, number_of_days)

        return '{}/{}/P1D'.format(first.strftime('%Y-%m-%d'), last.strftime('%Y-%m-%d'))

# ---------------------------------------------------------

    def set_values(self):
        """ Updates some values for the wcs download request
        """
        self.dockwidget.resXLineEdit.setText(self.settings.resx)
        self.dockwidget.resYLineEdit.setText(self.settings.resy)
        self.dockwidget.latMinLineEdit.setText(self.custom_bbox_params['latMin'])
        self.dockwidget.latMaxLineEdit.setText(self.custom_bbox_params['latMax'])
        self.dockwidget.lngMinLineEdit.setText(self.custom_bbox_params['lngMin'])
        self.dockwidget.lngMaxLineEdit.setText(self.custom_bbox_params['lngMax'])

    # --------------------------------------------------------------------------

    def show_message(self, message, message_type):
        """ Show message for user

        :param message: Message for user
        :param message: str
        :param message_type: Type of message
        :param message_type: MessageType
        """
        self.iface.messageBar().pushMessage(message_type.nice_name, message, level=message_type.level)

    def missing_instance_id(self):
        """Show message about missing instance ID"""
        self.show_message("Please set Sentinel Hub Instance ID first.", MessageType.INFO)

    def update_current_map_layers(self, selected_layer=None):
        """ Updates the list of QGIS layers
        """
        self.qgis_layers = self.get_qgis_layers()
        layer_names = []
        for layer in self.qgis_layers:
            layer_names.append(layer.name())
        self.dockwidget.mapLayerComboBox.clear()
        self.dockwidget.mapLayerComboBox.addItems(layer_names)

        if selected_layer and selected_layer in self.qgis_layers:
            layer_index = self.qgis_layers.index(selected_layer)
            self.dockwidget.mapLayerComboBox.setCurrentIndex(layer_index)

    @staticmethod
    def get_qgis_layers():
        """
        :return: List of existing QGIS layers in the same order as they are in the QGIS menu
        :rtype: list(QgsMapLayer)
        """
        return [tree_layer.layer() for tree_layer in QgsProject.instance().layerTreeRoot().findLayers()]

    # ----------------------------------------------------------------------------

    def download_wcs_data(self, url, filename):
        """
        Download image from provided URL WCS request

        :param url: WCS url request with specified bounding box
        :param filename: filename of image
        :return:
        """
        with open(os.path.join(self.settings.download_folder, filename), "wb") as download_file:
            response = self.client.download(url, stream=True)

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

    def add_qgis_layer(self, on_top=False):
        """ Creates and adds a new QGIS layer to the Layers menu

        :param on_top: If True the layer will be added on top of all layers, if False it will be added on top of
            currently selected layer.
        :type on_top: bool
        :return: new layer
        """
        if not self.settings.instance_id:
            return self.missing_instance_id()

        self.update_parameters()

        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)
        name = self.get_qgis_layer_name(layer)

        service_uri = get_service_uri(self.settings, layer)

        QgsMessageLog.logMessage(str(service_uri))
        if self.settings.service_type.upper() == ServiceType.WFS:
            new_layer = QgsVectorLayer(service_uri, name, ServiceType.WFS)
        else:
            new_layer = QgsRasterLayer(service_uri, name, ServiceType.WMS.lower())

        if new_layer.isValid():
            qgis_layers = self.get_qgis_layers()
            if on_top and qgis_layers:
                self.iface.setActiveLayer(qgis_layers[0])
            QgsProject.instance().addMapLayer(new_layer)
            self.update_current_map_layers()
        else:
            self.show_message('Failed to create layer {}.'.format(name), MessageType.CRITICAL)
        return new_layer

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
        bbox = get_bbox(self.iface, CrsType.WGS84)
        bbox_list = bbox_to_string(bbox, CrsType.WGS84).split(',')
        self.custom_bbox_params['latMin'] = bbox_list[0]
        self.custom_bbox_params['lngMin'] = bbox_list[1]
        self.custom_bbox_params['latMax'] = bbox_list[2]
        self.custom_bbox_params['lngMax'] = bbox_list[3]

        self.set_values()

    def update_qgis_layer(self):
        """ Updating layer in pyqgis somehow doesn't work therefore this method creates a new layer and deletes the
            old one
        """
        if not self.settings.instance_id:
            return self.missing_instance_id()

        selected_index = self.dockwidget.mapLayerComboBox.currentIndex()
        if selected_index < 0:
            return

        for layer in self.get_qgis_layers():
            # QgsMessageLog.logMessage(str(layer.name()) + ' ' + str(self.qgis_layers[selected_index].name()))
            if layer == self.qgis_layers[selected_index]:
                self.iface.setActiveLayer(layer)
                new_layer = self.add_qgis_layer()
                if new_layer.isValid():
                    QgsProject.instance().removeMapLayer(layer)
                    self.update_current_map_layers(selected_layer=new_layer)
                return
        self.show_message('Chosen layer {} does not exist anymore.'
                          ''.format(self.dockwidget.mapLayerComboBox.currentText()), MessageType.INFO)
        self.update_current_map_layers()

    def update_parameters(self):
        """
        Update parameters from GUI
        :return:
        """
        priority_index = self.dockwidget.priorityComboBox.currentIndex()
        self.settings.priority = list(ImagePriority)[priority_index].url_param

    def select_download_folder(self):
        """
        Opens dialog to select destination folder
        :return:
        """
        folder = QFileDialog.getExistingDirectory(self.dockwidget, "Select folder")
        self.dockwidget.downloadFolderLineEdit.setText(folder)
        self.change_download_folder()

    def download_caption(self):
        """
        Prepare download request and then download images
        :return:
        """
        if not self.settings.instance_id:
            return self.missing_instance_id()

        if self.settings.resx == '' or self.settings.resy == '':
            return self.show_message('Spatial resolution parameters are not set.', MessageType.CRITICAL)
        if self.settings.download_extent_type is ExtentType.CUSTOM:
            for value in self.custom_bbox_params.values():
                if value == '':
                    return self.show_message('Custom bounding box parameters are missing.', MessageType.CRITICAL)

        self.update_parameters()

        if not self.settings.download_folder:
            self.select_download_folder()
            if not self.settings.download_folder:
                return self.show_message("Download canceled. No destination set.", MessageType.CRITICAL)

        try:
            is_current_extent = self.settings.download_extent_type is ExtentType.CURRENT
            bbox = get_bbox(self.iface, self.settings.crs) if is_current_extent else \
                self.get_custom_bbox()
        except Exception:
            return self.show_message("Unable to transform to selected CRS, please zoom in or change CRS",
                                     MessageType.CRITICAL)

        crs = None if self.settings.download_extent_type is ExtentType.CURRENT else CrsType.WGS84
        bbox_str = bbox_to_string(bbox, crs)
        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)
        url = get_wcs_url(self.settings, layer, bbox_str, crs)
        filename = self.get_filename(bbox_str)

        self.download_wcs_data(url, filename)

    def get_filename(self, bbox):
        """ Prepare filename which contains some metadata
        DataSource_LayerName_start_time_end_time_xmin_y_min_xmax_ymax_maxcc_priority.FORMAT

        :param bbox:
        :return:
        """
        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id)

        info_list = [self.get_source_name(), self.settings.layer_id]
        if not layer.data_source.is_timeless():
            info_list.append(self.get_time_name())
        info_list.extend(bbox.split(','))
        if not layer.data_source.is_cloudless():
            info_list.append(self.settings.maxcc)
        info_list.append(self.settings.priority)

        name = '.'.join(map(str, ['_'.join(map(str, info_list)),
                                  self.settings.image_format.split(';')[0].split('/')[1]]))
        return name.replace(' ', '').replace(':', '_').replace('/', '_')

    def get_source_name(self):
        """ Returns name of the data source or a service name

        :return: A name
        :rtype: str
        """
        if self.settings.base_url == BaseUrl.EOCLOUD:
            return 'EO Cloud'
        if self.settings.data_source in DATA_SOURCES:
            return DATA_SOURCES[self.settings.data_source]['pretty_name']
        return 'SH'

    def get_time_name(self):
        """ Returns time interval in a form that will be displayed in qgis layer name

        :return: string describing time interval
        :rtype: str
        """
        time_interval = self.settings.start_time, self.settings.end_time
        if self.settings.is_exact_date:
            time_interval = time_interval[:1]
        if len(time_interval) == 1:
            if not time_interval[0]:
                time_interval[0] = '-/-'  # 'all times'
        else:
            if not time_interval[0]:
                time_interval[0] = '-'  # 'start'
            if not time_interval[1]:
                time_interval[1] = '-'  # 'end'
        return '/'.join(time_interval)

    def get_qgis_layer_name(self, layer):  # TODO: move
        """ Returns name of new qgis layer

        :return: qgis layer name
        :rtype: str
        """
        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id)

        plugin_params = [self.settings.service_type.upper()]
        if not layer.data_source.is_timelesse():
            plugin_params.append(self.get_time_name())
        if not layer.data_source.is_cloudless():
            plugin_params.append('{}%'.format(self.settings.maxcc))
        plugin_params.extend([self.settings.priority, self.settings.crs])

        return '{} - {} ({})'.format(self.get_source_name(), layer.name, ', '.join(plugin_params))

    def update_download_format(self):
        """
        Update image format
        :return:
        """
        image_format_index = self.dockwidget.imageFormatComboBox.currentIndex()
        self.settings.image_format = list(ImageFormat)[image_format_index].url_param

    def change_download_folder(self):
        """ Sets new download folder"""
        new_download_folder = self.dockwidget.downloadFolderLineEdit.text()
        if new_download_folder == self.settings.download_folder:
            return

        if new_download_folder == '' or os.path.exists(new_download_folder):
            self.settings.download_folder = new_download_folder
        else:
            self.dockwidget.downloadFolderLineEdit.setText(self.settings.download_folder)
            self.show_message('Folder {} does not exist. Please set a valid folder'.format(new_download_folder),
                              MessageType.CRITICAL)

    def update_values(self):
        """ Updates numerical values from user input"""
        new_values = self.get_values()

        if not new_values:
            self.show_message('Please input a numerical value.', MessageType.INFO)
            self.set_values()
            return

        for name, value in new_values.items():
            if name in ['resx', 'resy']:
                setattr(self.settings, name, value)
            else:
                self.custom_bbox_params[name] = value

    def get_values(self):
        """ Retrieves numerical values from user input"""
        new_values = {
            'resx': self.dockwidget.resXLineEdit.text(),
            'resy': self.dockwidget.resYLineEdit.text(),
            'latMin': self.dockwidget.latMinLineEdit.text(),
            'latMax': self.dockwidget.latMaxLineEdit.text(),
            'lngMin': self.dockwidget.lngMinLineEdit.text(),
            'lngMax': self.dockwidget.lngMaxLineEdit.text()
        }
        QgsMessageLog.logMessage(str(new_values))
        for name, value in new_values.items():
            if value != '':
                try:
                    float(value)
                except ValueError:
                    return
        return new_values

    def change_show_logo(self):
        """ Determines if Sentinel Hub logo will be shown in downloaded image
        """
        self.settings.show_logo = 'true' if self.dockwidget.showLogoCheckBox.isChecked() else 'false'

    def toggle_extent(self, extent_type):
        """ Switches between an option to download current window bbox or a custom bbox
        """
        self.settings.download_extent_type = extent_type
        if extent_type is ExtentType.CURRENT:
            self.dockwidget.widgetCustomExtent.hide()
        else:
            self.dockwidget.widgetCustomExtent.show()

    def on_close_plugin(self):
        """ Cleanup necessary items here when a close event on the dockwidget is triggered
        """
        self.dockwidget.closingPlugin.disconnect(self.on_close_plugin)
        self.dockwidget = None
