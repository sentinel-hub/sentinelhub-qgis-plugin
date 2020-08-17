"""
Module for querying Sentinel Hub Configuration API
"""
from .capabilities import WmsCapabilities
from .common import Configuration, Layer


class ConfigurationManager:

    def __init__(self, settings, client):
        self.settings = settings
        self.client = client

        self._configurations = None
        self._instance_to_index_map = {}
        self._layer_to_index_maps = {}

        self._wms_capabilities = None
        self._data_sources_names_map = None

    @property
    def configuration_url(self):
        return '{}/configuration/v1'.format(self.settings.base_url)

    @property
    def wms_capabilities(self):
        if self._wms_capabilities is None:
            self._wms_capabilities = WmsCapabilities(self.settings, self.client)
        return self._wms_capabilities

    def get_configurations(self, reload=False):

        if reload or self._configurations is None:
            url = '{}/wms/instances'.format(self.configuration_url)
            result_list = self.client.download(url, session_settings=self.settings).json()

            self._configurations = [Configuration.load(result) for result in result_list]
            self._configurations.sort(key=lambda conf: conf.name.lower())

            self._instance_to_index_map = {conf.id: index for index, conf in enumerate(self._configurations)}

        return self._configurations

    def get_configuration_index(self, instance_id):
        return self._instance_to_index_map.get(instance_id, -1)

    def get_layers(self, instance_id, reload=False):
        conf_index = self.get_configuration_index(instance_id)
        configuration = self._configurations[conf_index]

        if reload or configuration.layers is None:
            url = '{}/wms/instances/{}/layers'.format(self.configuration_url, instance_id)
            result_list = self.client.download(url, session_settings=self.settings).json()

            configuration.layers = [Layer.load(result) for result in result_list]
            configuration.layers.sort(key=lambda layer: layer.name.lower())

            self._layer_to_index_maps[configuration.id] = {
                layer.id: index for index, layer in enumerate(configuration.layers)
            }

        return configuration.layers

    def get_layer_index(self, instance_id, layer_id):
        return self._layer_to_index_maps[instance_id].get(layer_id, 0)

    def get_layer(self, instance_id, layer_id, load_url=False):
        conf_index = self.get_configuration_index(instance_id)
        layer_index = self.get_layer_index(instance_id, layer_id)
        layer = self._configurations[conf_index].layers[layer_index]
        data_source = layer.data_source

        if load_url and data_source.service_url is None:
            url = '{}/datasets/{}/sources/{}'.format(self.configuration_url, data_source.type, data_source.id)
            result = self.client.download(url, session_settings=self.settings).json()

            data_source.name = result['description']
            data_source_settings = result['settings']
            if 'indexServiceUrl' in data_source_settings:
                data_source.service_url = data_source_settings['indexServiceUrl'].rsplit('/', 1)[0]
            else:
                # This happens in case of DEM
                data_source.service_url = self.settings.base_url

        return layer

    def get_datasource_names(self):
        if self._data_sources_names_map is None:
            url = '{}/datasets'.format(self.configuration_url)
            result_list = self.client.download(url, session_settings=self.settings).json()

            self._data_sources_names_map = {result['id']: result['name'] for result in result_list}
            # TODO: save into layer datasource objects

        # TODO: join with layers...

    def get_available_crs(self):
        return self.wms_capabilities.get_available_crs()

    def get_crs_index(self, crs_id):
        return self.wms_capabilities.get_crs_index(crs_id)
