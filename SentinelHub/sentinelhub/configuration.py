"""
Module for querying Sentinel Hub Configuration API
"""
from .capabilities import WmsCapabilities
from .common import Configuration, Layer


class ConfigurationManager:
    """The main class for providing any kind of configuration info obtained from Sentinel Hub service

    Mainly it interacts with Sentinel Hub configuration API, which is the same as Sentinel Hub Configurator app
    """

    def __init__(self, settings, client):
        """
        :param settings: A settings object. When parameters in settings change this will be also reflected in this class
        :type settings: Settings
        :param client: An instance of a client for download from Sentinel Hub
        :type client: Client
        """
        self.settings = settings
        self.client = client

        self._configurations = None
        self._instance_to_index_map = {}
        self._layer_to_index_maps = {}

        self._wms_capabilities = None
        self._data_sources_names_map = None

    @property
    def configuration_url(self):
        """A URL of configuration API"""
        return f"{self.settings.base_url}/configuration/v1"

    @property
    def wms_capabilities(self):
        """Provides a class in charge of WMS capabilities info"""
        if self._wms_capabilities is None:
            self._wms_capabilities = WmsCapabilities(self.settings, self.client)
        return self._wms_capabilities

    def get_configurations(self, reload=False):
        """Provides a list of data configurations for the current user"""
        if reload or self._configurations is None:
            url = f"{self.configuration_url}/wms/instances"
            result_list = self.client.download(url, session_settings=self.settings).json()

            self._configurations = [Configuration.load(result) for result in result_list]
            self._configurations.sort(key=lambda conf: conf.name.lower())

            self._instance_to_index_map = {conf.id: index for index, conf in enumerate(self._configurations)}

        return self._configurations

    def get_configuration_index(self, instance_id):
        """For an instance ID it provides a position of it's configuration in the list of configurations"""
        return self._instance_to_index_map.get(instance_id, -1)

    def get_layers(self, instance_id, reload=False):
        """Provides a list of layers defined for a given instance ID (configuration) and the current user"""
        conf_index = self.get_configuration_index(instance_id)
        configuration = self._configurations[conf_index]

        if reload or configuration.layers is None:
            url = f"{self.configuration_url}/wms/instances/{instance_id}/layers"
            result_list = self.client.download(url, session_settings=self.settings).json()

            configuration.layers = [Layer.load(result) for result in result_list]
            configuration.layers.sort(key=lambda layer: layer.name.lower())

            self._layer_to_index_maps[configuration.id] = {
                layer.id: index for index, layer in enumerate(configuration.layers)
            }

        return configuration.layers

    def get_layer_index(self, instance_id, layer_id):
        """Provides a position of a layer in the list of all layers for a given configuration"""
        return self._layer_to_index_maps[instance_id].get(layer_id, 0)

    def get_layer(self, instance_id, layer_id, load_url=False):
        """Provides a single layer object, optionally it loads additional info about it's data source and service URL

        :param instance_id: A configuration instance ID
        :type instance_id: str
        :param layer_id: A layer ID
        :type layer_id: str
        :param load_url: If True it will make an additional request to find out which at which service URL a layer can
            be accessed
        :type load_url: bool
        :return: A layer
        :rtype: Layer
        """
        conf_index = self.get_configuration_index(instance_id)
        layer_index = self.get_layer_index(instance_id, layer_id)
        layer = self._configurations[conf_index].layers[layer_index]
        data_source = layer.data_source

        if load_url and data_source.service_url is None:
            url = f"{self.configuration_url}/datasets/{data_source.type}/sources/{data_source.id}"
            result = self.client.download(url, session_settings=self.settings).json()

            data_source.name = result["description"]
            data_source_settings = result["settings"]
            if "indexServiceUrl" in data_source_settings:
                data_source.service_url = data_source_settings["indexServiceUrl"].rsplit("/", 1)[0]
            else:
                # This happens in case of DEM
                data_source.service_url = self.settings.base_url

        return layer

    def get_datasource_names(self):
        """The method that could obtain data source names in case data sources will be ever displayed

        A query should be made to configuration/v1/datasets endpoint
        """
        raise NotImplementedError

    def get_available_crs(self):
        """Provides a list of available CRS"""
        return self.wms_capabilities.get_available_crs()

    def get_crs_index(self, crs_id):
        """Provides a position of a CRS in the list of available CRS"""
        return self.wms_capabilities.get_crs_index(crs_id)
