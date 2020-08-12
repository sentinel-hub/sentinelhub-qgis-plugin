"""
Module for querying Sentinel Hub Configuration API
"""


class ConfigurationManager:

    def __init__(self, settings, client):
        self.settings = settings
        self.client = client

        self._configurations = None
        self._instance_to_index_map = {}

    @property
    def configuration_url(self):
        return '{}/configuration/v1'.format(self.settings.base_url)

    def get_instances(self, reload=False):

        if reload or self._configurations is None:
            url = '{}/wms/instances'.format(self.configuration_url)
            self._configurations = self.client.download(url, use_session=True, settings=self.settings).json()
            self._configurations.sort(key=lambda conf: conf['name'].lower())

            self._instance_to_index_map = {conf['id']: index for index, conf in enumerate(self._configurations)}

        return [(conf['id'], conf['name']) for conf in self._configurations]

    def get_configuration_index(self, instance_id):
        return self._instance_to_index_map.get(instance_id, -1)

    def get_layers(self, instance_id, reload=False):
        conf_index = self.get_configuration_index(instance_id)
        configuration = self._configurations[conf_index]

        if reload or isinstance(configuration.get('layers', {}), dict):
            url = '{}/wms/instances/{}/layers'.format(self.configuration_url, instance_id)
            configuration['layers'] = self.client.download(url, use_session=True, settings=self.settings).json()
            configuration['layers'].sort(key=lambda layer: layer['title'].lower())

            configuration['layer_to_index_map'] = {
                layer['id']: index for index, layer in enumerate(configuration['layers'])
            }

        return [(layer['id'], layer['title']) for layer in configuration['layers']]

    def get_layer_index(self, instance_id, layer):
        conf_index = self.get_configuration_index(instance_id)
        return self._configurations[conf_index]['layer_to_index_map'].get(layer, 0)

    def get_datasets(self):
        url = '{}/datasets'.format(self.configuration_url)

        return self.client.download(url, use_session=True, settings=self.settings).json()
