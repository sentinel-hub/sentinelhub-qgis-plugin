"""
Module for querying Sentinel Hub Configuration API
"""


class Configuration:

    def __init__(self, settings, client):
        self.settings = settings
        self.client = client

    @property
    def configuration_url(self):
        return '{}/configuration/v1'.format(self.settings.base_url.rstrip('/'))

    def get_instances(self):
        url = '{}/wms/instances'.format(self.configuration_url)

        return self.client.download(url, use_session=True, settings=self.settings)

    def get_layers(self, instance_id):
        url = '{}/wms/instances/{}/layers'.format(self.configuration_url, instance_id)

        return self.client.download(url, use_session=True, settings=self.settings)

    def get_datasets(self):
        url = '{}/datasets'.format(self.configuration_url)

        return self.client.download(url, use_session=True, settings=self.settings)
