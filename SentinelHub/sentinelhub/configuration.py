"""
Module for querying Sentinel Hub Configuration API
"""
from .capabilities import WmsCapabilities
from .common import Configuration, Layer, DataSource


class ConfigurationManager:

    def __init__(self, settings, client):
        self.settings = settings
        self.client = client

        self._configurations = None
        self._instance_to_index_map = {}
        self._layer_to_index_maps = {}

        self._wms_capabilities = None

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
            conf_list = self.client.download(url, use_session=True, settings=self.settings).json()

            self._configurations = [Configuration(conf['id'], conf['name']) for conf in conf_list]
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
            layer_list = self.client.download(url, use_session=True, settings=self.settings).json()

            configuration.layers = [Layer(layer['id'], layer['title']) for layer in layer_list]
            configuration.layers.sort(key=lambda layer: layer.name.lower())

            self._layer_to_index_maps[configuration.id] = {
                layer.id: index for index, layer in enumerate(configuration.layers)
            }

        return configuration.layers

    def get_layer_index(self, instance_id, layer_id):
        return self._layer_to_index_maps[instance_id].get(layer_id, 0)

    def get_datasets(self):
        url = '{}/datasets'.format(self.configuration_url)

        return self.client.download(url, use_session=True, settings=self.settings).json()

    def get_available_crs(self):
        return self.wms_capabilities.get_available_crs()

    def get_crs_index(self, crs_id):
        return self.wms_capabilities.get_crs_index(crs_id)
