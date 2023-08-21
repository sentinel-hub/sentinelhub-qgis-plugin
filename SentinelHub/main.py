"""
The main module
"""
import os

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QIcon, QTextCharFormat
from PyQt5.QtWidgets import QAction, QFileDialog
from qgis.core import QgsMessageLog, QgsProject, QgsRasterLayer, QgsVectorLayer

from .constants import (
    ACTION_COOLDOWN,
    AVAILABLE_SERVICE_TYPES,
    COVERAGE_MAX_BBOX_SIZE,
    VECTOR_LAYER_COLOR_OPACITY,
    BaseUrl,
    CrsType,
    ExtentType,
    ImageFormat,
    ImagePriority,
    MessageType,
    ServiceType,
    TimeType,
)
from .dockwidget import SentinelHubDockWidget
from .exceptions import (
    BBoxTransformError,
    DownloadFolderValidator,
    ExtentValidator,
    LayerValidator,
    ResolutionValidator,
    action_handler,
    show_message,
)
from .sentinelhub.client import Client
from .sentinelhub.configuration import ConfigurationManager
from .sentinelhub.ogc import get_service_uri
from .sentinelhub.wcs import download_wcs_image
from .sentinelhub.wfs import get_cloud_cover
from .settings import Settings
from .utils.common import is_float_or_undefined
from .utils.geo import bbox_to_string, get_bbox, get_custom_bbox, is_bbox_too_large, is_current_map_crs
from .utils.map import get_qgis_layers, set_layer_fill_color_opacity
from .utils.meta import PLUGIN_NAME, get_plugin_version
from .utils.naming import get_qgis_layer_name
from .utils.time import get_month_time_interval, parse_date


class SentinelHubPlugin:
    """The main class defining the high-level plugin logic and interactions with UI

    The methods that are called externally by QGIS are:
      - __init__
      - initGui
      - unload

    Any other public method is connected to UI and can be triggered by a user's action in QGIS. Non-public methods are
    the ones that are only called by other methods.
    """

    # pylint: disable=too-many-public-methods

    ICON_PATH = ":/plugins/SentinelHub/favicon.ico"

    def __init__(self, iface):
        """Called by QGIS at the beginning when you open QGIS or when the plugin is enabled in the
        Plugin Manager.

        :param iface: A QGIS interface instance, it is the same object as qgis.utils.iface
        :type iface: QgsInterface
        """
        self.iface = iface
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.plugin_actions = []
        self.dockwidget = None

        self.settings = Settings()
        self.client = Client()
        self.manager = None

        self._default_layer_selection_event = None

    def initGui(self):
        """This method is called by QGIS when the main GUI starts up or when the plugin is enabled in the
        Plugin Manager.
        """
        icon = QIcon(self.ICON_PATH)
        bold_plugin_name = f"<b>{PLUGIN_NAME}</b>"
        action = QAction(icon, bold_plugin_name, self.iface.mainWindow())

        action.triggered.connect(self.run)
        action.setEnabled(True)

        self.toolbar.addAction(action)
        self.iface.addPluginToWebMenu(PLUGIN_NAME, action)

        self.plugin_actions.append(action)

    def unload(self):
        """This is called by QGIS when a user disables or uninstalls the plugin. This method removes the plugin and
        it's icon from everywhere it appears in QGIS GUI.
        """
        if self.dockwidget:
            self.dockwidget.close()

        for action in self.plugin_actions:
            self.iface.removePluginWebMenu(PLUGIN_NAME, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """It loads and starts the plugin and binds all UI actions."""
        if self.dockwidget is not None:
            return

        self.dockwidget = SentinelHubDockWidget()
        self.dockwidget.setWindowTitle(f"{PLUGIN_NAME} plugin v{get_plugin_version()}")
        self.initialize_ui()

        # Login widget
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
        self.dockwidget.maxccSlider.sliderReleased.connect(self.update_available_calendar_dates)
        self.dockwidget.priorityComboBox.activated.connect(self.update_image_priority)

        # Create widget bottom buttons
        self.dockwidget.createLayerPushButton.clicked.connect(self.add_qgis_layer)
        self.dockwidget.updateLayerPushButton.clicked.connect(self.update_qgis_layer)

        self._default_layer_selection_event = self.dockwidget.mapLayerComboBox.mousePressEvent
        self.dockwidget.mapLayerComboBox.mousePressEvent = self.qgis_layer_selection_event

        # Tracks which layer is selected in left menu
        self.iface.currentLayerChanged.connect(self.update_current_map_layers)

        # Download widget
        self.dockwidget.imageFormatComboBox.activated.connect(self.update_download_format)

        self.dockwidget.resXLineEdit.editingFinished.connect(self.update_download_extent_values)
        self.dockwidget.resYLineEdit.editingFinished.connect(self.update_download_extent_values)
        self.dockwidget.currentExtentRadioButton.clicked.connect(lambda: self.toggle_extent(ExtentType.CURRENT))
        self.dockwidget.customExtentRadioButton.clicked.connect(lambda: self.toggle_extent(ExtentType.CUSTOM))
        self.dockwidget.latMinLineEdit.editingFinished.connect(self.update_download_extent_values)
        self.dockwidget.latMaxLineEdit.editingFinished.connect(self.update_download_extent_values)
        self.dockwidget.lngMinLineEdit.editingFinished.connect(self.update_download_extent_values)
        self.dockwidget.lngMaxLineEdit.editingFinished.connect(self.update_download_extent_values)
        self.dockwidget.refreshExtentPushButton.clicked.connect(self.set_window_bbox)

        self.dockwidget.showLogoCheckBox.stateChanged.connect(self.change_show_logo)

        self.dockwidget.downloadFolderLineEdit.editingFinished.connect(self.change_download_folder)
        self.dockwidget.selectDownloadFolderPushButton.clicked.connect(self.select_download_folder)

        self.dockwidget.downloadPushButton.clicked.connect(self.download_caption)

        # Close event
        self.dockwidget.closingPlugin.connect(self.on_close_plugin)

        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dockwidget)
        self.dockwidget.show()

    def initialize_ui(self):
        """Initializes and resets entire UI"""
        self.dockwidget.clientIdLineEdit.setText(self.settings.client_id)
        self.dockwidget.clientSecretLineEdit.setText(self.settings.client_secret)
        if self.settings.base_url == BaseUrl.MAIN:
            self.dockwidget.serviceUrlLineEdit.setCurrentIndex(0)
        else:
            self.dockwidget.serviceUrlLineEdit.setCurrentIndex(1)

        self.dockwidget.serviceTypeComboBox.addItems(AVAILABLE_SERVICE_TYPES)
        self.update_service_type(self.settings.service_type.upper())

        self.dockwidget.startTimeLineEdit.setText(self.settings.start_time)
        self.dockwidget.endTimeLineEdit.setText(self.settings.end_time)
        self.dockwidget.calendarSpacer.hide()

        self.dockwidget.priorityComboBox.addItems([priority.nice_name for priority in ImagePriority])
        priorities = [priority.url_param for priority in ImagePriority]
        if self.settings.priority in priorities:
            priority_index = priorities.index(self.settings.priority)
            self.dockwidget.priorityComboBox.setCurrentIndex(priority_index)
        else:
            self.update_image_priority()

        self.update_current_map_layers()

        self.dockwidget.imageFormatComboBox.addItems([image_format.nice_name for image_format in ImageFormat])
        image_formats = [image_format.url_param for image_format in ImageFormat]
        if self.settings.image_format in image_formats:
            image_format_index = image_formats.index(self.settings.image_format)
            self.dockwidget.imageFormatComboBox.setCurrentIndex(image_format_index)
        else:
            self.update_download_format()

        self._set_download_extent_values()
        self.toggle_extent(self.settings.download_extent_type)
        self.dockwidget.downloadFolderLineEdit.setText(self.settings.download_folder)

    @action_handler(cooldown=ACTION_COOLDOWN)
    def login(self, *_):
        """Uses credentials to connect to Sentinel Hub services and updates"""
        new_settings = self.settings.copy()
        self._load_new_credentials(new_settings)

        new_manager = ConfigurationManager(new_settings, self.client)
        configurations = new_manager.get_configurations(reload=True)

        self.settings = new_settings
        self.manager = new_manager
        self.settings.save_credentials()

        self.dockwidget.configurationComboBox.clear()
        self.dockwidget.layersComboBox.clear()
        self.dockwidget.crsComboBox.clear()

        login_text = "Logged in"
        self.dockwidget.loginInfoLabel.setText(login_text)

        configuration_names = [configuration.name for configuration in configurations]
        self.dockwidget.configurationComboBox.addItems(configuration_names)
        configuration_index = self.manager.get_configuration_index(self.settings.instance_id)
        self.update_configuration(configuration_index)

        show_message("Login successful", MessageType.SUCCESS)

    def _load_new_credentials(self, settings):
        """Loads new credentials into settings"""
        settings.base_url = self.dockwidget.serviceUrlLineEdit.currentText()
        settings.client_id = self.dockwidget.clientIdLineEdit.text()
        settings.client_secret = self.dockwidget.clientSecretLineEdit.text()

    @action_handler()
    def update_configuration(self, configuration_index=None):
        """A different configuration has been chosen"""
        if configuration_index is not None:
            self.dockwidget.configurationComboBox.setCurrentIndex(configuration_index)

        configuration_index = self.dockwidget.configurationComboBox.currentIndex()
        if configuration_index < 0:
            self.settings.instance_id = ""
            return

        self.settings.instance_id = self.manager.get_configurations()[configuration_index].id

        self.dockwidget.layersComboBox.clear()
        layers = self.manager.get_layers(self.settings.instance_id)
        self.dockwidget.layersComboBox.addItems([layer.name for layer in layers])
        layer_index = self.manager.get_layer_index(self.settings.instance_id, self.settings.layer_id)
        self.update_layer(layer_index)

        self._update_available_crs()

    @action_handler()
    def update_service_type(self, service_type=None):
        """Update service type and content that depends on it"""
        if service_type is not None and service_type in AVAILABLE_SERVICE_TYPES:
            index = AVAILABLE_SERVICE_TYPES.index(service_type)
            self.dockwidget.serviceTypeComboBox.setCurrentIndex(index)

        self.settings.service_type = self.dockwidget.serviceTypeComboBox.currentText().lower()
        self.dockwidget.createLayerLabel.setText(f"Create new {self.settings.service_type.upper()} layer")

        if self.manager:
            self._update_available_crs()

    @action_handler()
    def update_layer(self, layer_index=None):
        """Updates properties of selected Sentinel Hub layer"""
        if layer_index is not None:
            self.dockwidget.layersComboBox.setCurrentIndex(layer_index)

        available_layers = self.manager.get_layers(self.settings.instance_id)
        layer_index = self.dockwidget.layersComboBox.currentIndex()
        if not 0 <= layer_index < len(available_layers):
            self.settings.layer_id = ""
            self.settings.data_source = ""
            self._clear_calendar_cells()
            return

        layer = available_layers[layer_index]
        self.settings.layer_id = layer.id
        self.settings.data_source = layer.data_source.type

        self.update_available_calendar_dates()

        if layer.data_source.is_cloudless():
            self.dockwidget.maxccSlider.hide()
            self.dockwidget.maxccLabel.hide()
        else:
            self.dockwidget.maxccSlider.show()
            self.dockwidget.maxccLabel.show()

        if layer.data_source.is_timeless():
            self.dockwidget.calendarWidget.hide()
            self.dockwidget.timeRangeLabel.hide()
            self.dockwidget.timeLabel.hide()
            self.dockwidget.startTimeLineEdit.hide()
            self.dockwidget.endTimeLineEdit.hide()
            self.dockwidget.verticalCalendarWidget.hide()
        else:
            self.dockwidget.calendarWidget.show()
            self.dockwidget.timeRangeLabel.show()
            self.dockwidget.startTimeLineEdit.show()
            self.dockwidget.verticalCalendarWidget.show()
            self.change_exact_date()

        if layer.data_source.is_cloudless() and layer.data_source.is_timeless():
            self.dockwidget.priorityLabel.hide()
            self.dockwidget.priorityComboBox.hide()
        else:
            self.dockwidget.priorityLabel.show()
            self.dockwidget.priorityComboBox.show()

    @action_handler()
    def update_crs(self, crs_index=None):
        """Updates crs with selected Sentinel Hub CRS"""
        if crs_index is not None:
            self.dockwidget.crsComboBox.setCurrentIndex(crs_index)

        crs_index = self.dockwidget.crsComboBox.currentIndex()
        crs_list = self.manager.get_available_crs()

        self.settings.crs = self.manager.get_available_crs()[crs_index].id if 0 <= crs_index < len(crs_list) else ""

    def _update_available_crs(self):
        """Updates the list of available CRS"""
        self.dockwidget.crsComboBox.clear()
        self.dockwidget.crsComboBox.addItems([crs.name for crs in self.manager.get_available_crs()])
        crs_index = self.manager.get_crs_index(self.settings.crs)
        self.update_crs(crs_index)

    def move_calendar(self, active):
        """Moves calendar between the "start time" and "end time" line edit fields"""
        if active is TimeType.START_TIME:
            self.dockwidget.calendarSpacer.hide()
        else:
            self.dockwidget.calendarSpacer.show()
        self.settings.active_time = active

    def update_dates(self):
        """Checks if newly inserted dates are valid and updates date attributes"""
        new_start_time = parse_date(self.dockwidget.startTimeLineEdit.text())
        new_end_time = parse_date(self.dockwidget.endTimeLineEdit.text())

        if new_start_time is None or new_end_time is None:
            show_message("Please insert a valid date in a form YYYY-MM-DD", MessageType.INFO)
        elif new_start_time and new_end_time and new_start_time > new_end_time and not self.settings.is_exact_date:
            show_message("Start date must not be later than end date", MessageType.INFO)
        else:
            self.settings.start_time = new_start_time
            self.settings.end_time = new_end_time

        self.dockwidget.startTimeLineEdit.setText(self.settings.start_time)
        self.dockwidget.endTimeLineEdit.setText(self.settings.end_time)

    def change_exact_date(self):
        """A switch between specifying a time interval and an exact date"""
        self.settings.is_exact_date = self.dockwidget.exactDateCheckBox.isChecked()

        if self.settings.is_exact_date:
            self.dockwidget.endTimeLineEdit.hide()
            self.dockwidget.timeLabel.hide()
            self.dockwidget.startTimeLineEdit.setPlaceholderText("Select date")
            self.move_calendar(TimeType.START_TIME)
        else:
            if (
                self.settings.start_time
                and self.settings.end_time
                and self.settings.start_time > self.settings.end_time
            ):
                self.settings.end_time = ""
                self.dockwidget.endTimeLineEdit.setText(self.settings.end_time)

            self.dockwidget.endTimeLineEdit.show()
            self.dockwidget.timeLabel.show()
            self.dockwidget.startTimeLineEdit.setPlaceholderText("Select start date")

    def add_calendar_date(self):
        """Handles selected calendar date"""
        calendar_time = str(self.dockwidget.calendarWidget.selectedDate().toPyDate())

        if self.settings.active_time is TimeType.START_TIME and (
            self.settings.is_exact_date or not self.settings.end_time or calendar_time <= self.settings.end_time
        ):
            self.settings.start_time = calendar_time
            self.dockwidget.startTimeLineEdit.setText(calendar_time)
        elif self.settings.active_time is TimeType.END_TIME and (
            not self.settings.start_time or self.settings.start_time <= calendar_time
        ):
            self.settings.end_time = calendar_time
            self.dockwidget.endTimeLineEdit.setText(calendar_time)
        else:
            show_message("Start date must not be later than end date", MessageType.INFO)

    @action_handler(suppressed_exceptions=(BBoxTransformError,))
    def update_available_calendar_dates(self, *_):
        """For the current extent, current layer and current month it will find all days for which there is available
        data for that layer
        """
        if self.manager is None or not self.settings.instance_id or not self.settings.layer_id:
            return

        self._clear_calendar_cells()

        bbox = get_bbox(CrsType.POP_WEB)
        if is_bbox_too_large(bbox, CrsType.POP_WEB, COVERAGE_MAX_BBOX_SIZE):
            return

        year = self.dockwidget.calendarWidget.yearShown()
        month = self.dockwidget.calendarWidget.monthShown()
        time_interval = get_month_time_interval(year, month)

        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)
        cloud_cover_map = get_cloud_cover(self.settings, layer, bbox, time_interval, self.client)

        for date, cloud_cover_percentage in cloud_cover_map.items():
            if cloud_cover_percentage <= int(self.settings.maxcc):
                date_props = list(map(int, date.split("-")))
                qdate = QDate(*date_props)
                style = QTextCharFormat()
                style.setBackground(Qt.gray)
                self.dockwidget.calendarWidget.setDateTextFormat(qdate, style)

    def _clear_calendar_cells(self):
        """Resets all highlighted calendar cells"""
        style = QTextCharFormat()
        style.setBackground(Qt.white)
        self.dockwidget.calendarWidget.setDateTextFormat(QDate(), style)

    def update_maxcc(self):
        """Updates maximum cloud coverage and it's label"""
        self.settings.maxcc = str(self.dockwidget.maxccSlider.value())
        self.dockwidget.maxccLabel.setText(f"Cloud coverage {self.settings.maxcc}%")

    def update_image_priority(self):
        """Updates settings for image priority"""
        priority_index = self.dockwidget.priorityComboBox.currentIndex()
        self.settings.priority = list(ImagePriority)[priority_index].url_param

    @action_handler(validators=(LayerValidator,), cooldown=ACTION_COOLDOWN)
    def add_qgis_layer(self, *_):
        """An action that creates and adds a new QGIS layer to the Layers menu"""
        self._create_and_add_qgis_layer()

    def _create_and_add_qgis_layer(self):
        """Creates, adds and returns a new QGIS layer"""
        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)
        qgis_layer_name = get_qgis_layer_name(self.settings, layer)

        service_uri = get_service_uri(self.settings, layer)
        QgsMessageLog.logMessage(str(service_uri))

        if self.settings.service_type.upper() == ServiceType.WFS:
            new_layer = QgsVectorLayer(service_uri, qgis_layer_name, ServiceType.WFS)
            set_layer_fill_color_opacity(new_layer, VECTOR_LAYER_COLOR_OPACITY)
        else:
            new_layer = QgsRasterLayer(service_uri, qgis_layer_name, ServiceType.WMS.lower())

        if not new_layer.isValid():
            show_message(f"Failed to create layer {qgis_layer_name}.", MessageType.CRITICAL)
            return None

        if self.settings.service_type.upper() == ServiceType.WFS and not is_current_map_crs(CrsType.POP_WEB):
            show_message(
                (
                    "WFS layer will only be visible if the underlying CRS on your map is set to "
                    "Popular Web Mercator (EPSG:3857)"
                ),
                MessageType.WARNING,
            )

        QgsProject.instance().addMapLayer(new_layer)
        self.update_current_map_layers()

        return new_layer

    @action_handler(validators=(LayerValidator,), cooldown=ACTION_COOLDOWN)
    def update_qgis_layer(self, *_):
        """Update an existing QGIS map layer by removing it and adding a new one instead of it"""
        chosen_layer_name = self.dockwidget.mapLayerComboBox.currentText()
        if not chosen_layer_name:
            return

        for layer in get_qgis_layers():
            if layer.name() == chosen_layer_name:
                self.iface.setActiveLayer(layer)
                new_layer = self._create_and_add_qgis_layer()

                if new_layer:
                    QgsProject.instance().removeMapLayer(layer)
                    self.update_current_map_layers(selected_layer=new_layer)
                return

        show_message(f"Chosen layer {chosen_layer_name} does not exist anymore", MessageType.INFO)
        self.update_current_map_layers()

    def update_current_map_layers(self, selected_layer=None):
        """Updates the list of QGIS layers available in the combo box"""
        qgis_layers = get_qgis_layers()
        layer_names = [layer.name() for layer in qgis_layers]

        self.dockwidget.mapLayerComboBox.clear()
        self.dockwidget.mapLayerComboBox.addItems(layer_names)

        if selected_layer and selected_layer in qgis_layers:
            layer_index = qgis_layers.index(selected_layer)
            self.dockwidget.mapLayerComboBox.setCurrentIndex(layer_index)

    def qgis_layer_selection_event(self, event):
        """An overloaded even of clicking on the combo box of available QGIS layers"""
        self.update_current_map_layers()
        self._default_layer_selection_event(event)

    def update_download_format(self):
        """Update an image format in which to download"""
        image_format_index = self.dockwidget.imageFormatComboBox.currentIndex()
        self.settings.image_format = list(ImageFormat)[image_format_index].url_param

    def toggle_extent(self, extent_type):
        """Switches between an option to download current window bbox or a custom bbox"""
        self.settings.download_extent_type = extent_type
        if extent_type is ExtentType.CURRENT:
            self.dockwidget.widgetCustomExtent.hide()
        else:
            self.dockwidget.widgetCustomExtent.show()

    def update_download_extent_values(self):
        """Updates numerical values from user input"""
        new_values = {
            "resx": self.dockwidget.resXLineEdit.text(),
            "resy": self.dockwidget.resYLineEdit.text(),
            "lat_min": self.dockwidget.latMinLineEdit.text(),
            "lat_max": self.dockwidget.latMaxLineEdit.text(),
            "lng_min": self.dockwidget.lngMinLineEdit.text(),
            "lng_max": self.dockwidget.lngMaxLineEdit.text(),
        }

        if not all(map(is_float_or_undefined, new_values.values())):
            show_message("Please input a numerical value", MessageType.INFO)
            self._set_download_extent_values()
            return

        for name, value in new_values.items():
            setattr(self.settings, name, value)

    def _set_download_extent_values(self):
        """Sets values from settings"""
        self.dockwidget.resXLineEdit.setText(self.settings.resx)
        self.dockwidget.resYLineEdit.setText(self.settings.resy)
        self.dockwidget.latMinLineEdit.setText(self.settings.lat_min)
        self.dockwidget.latMaxLineEdit.setText(self.settings.lat_max)
        self.dockwidget.lngMinLineEdit.setText(self.settings.lng_min)
        self.dockwidget.lngMaxLineEdit.setText(self.settings.lng_max)

    def set_window_bbox(self):
        """Takes the coordinates of the current map window bbox and sets them into the fields"""
        bbox = get_bbox(CrsType.WGS84)
        bbox_list = bbox_to_string(bbox, CrsType.WGS84).split(",")

        self.settings.lat_min = bbox_list[0]
        self.settings.lng_min = bbox_list[1]
        self.settings.lat_max = bbox_list[2]
        self.settings.lng_max = bbox_list[3]

        self._set_download_extent_values()

    def change_show_logo(self):
        """Determines if Sentinel Hub logo will be shown in downloaded image"""
        self.settings.show_logo = "true" if self.dockwidget.showLogoCheckBox.isChecked() else "false"

    def change_download_folder(self):
        """Sets new download folder from the line edit"""
        new_download_folder = self.dockwidget.downloadFolderLineEdit.text()
        if new_download_folder == self.settings.download_folder:
            return

        if new_download_folder == "" or os.path.exists(new_download_folder):
            self.settings.download_folder = new_download_folder
        else:
            self.dockwidget.downloadFolderLineEdit.setText(self.settings.download_folder)
            show_message(
                f"Folder {new_download_folder} does not exist. Please set a valid folder", MessageType.CRITICAL
            )

    def select_download_folder(self):
        """Opens a dialog to select a download folder"""
        folder = QFileDialog.getExistingDirectory(self.dockwidget, "Select folder")
        self.dockwidget.downloadFolderLineEdit.setText(folder)
        self.change_download_folder()

    @action_handler(
        validators=(LayerValidator, ResolutionValidator, ExtentValidator, DownloadFolderValidator),
        cooldown=ACTION_COOLDOWN,
    )
    def download_caption(self, *_):
        """Downloads an image from given parameters"""
        layer = self.manager.get_layer(self.settings.instance_id, self.settings.layer_id, load_url=True)

        is_current_extent = self.settings.download_extent_type is ExtentType.CURRENT
        bbox = get_bbox(self.settings.crs) if is_current_extent else get_custom_bbox(self.settings)

        filename = download_wcs_image(self.settings, layer, bbox, self.client)
        show_message(f"Image downloaded to file {filename}", MessageType.SUCCESS)

    def on_close_plugin(self):
        """Cleanup necessary items here when a close event on the dockwidget is triggered

        Note that all connections to the QGIS interface have to be cleaned here.
        """
        self._load_new_credentials(self.settings)
        self.settings.save_credentials()

        self.iface.currentLayerChanged.disconnect(self.update_current_map_layers)

        self.dockwidget.closingPlugin.disconnect(self.on_close_plugin)
        self.dockwidget = None
