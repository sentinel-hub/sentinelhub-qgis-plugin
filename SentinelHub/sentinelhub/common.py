"""
Module implementing common service-related dataclasses
"""


class Configuration:
    """ Stores info about a Sentinel Hub configuration
    """
    def __init__(self, configuration_id, name, layers=None):
        self.id = configuration_id
        self.name = name
        self.layers = layers

    @classmethod
    def load(cls, payload):
        return cls(
            configuration_id=payload['id'],
            name=payload['name']
        )


class Layer:
    """ Stores info about a Sentinel Hub layer
    """
    def __init__(self, layer_id, name, data_source):
        self.id = layer_id
        self.name = name
        self.data_source = data_source

    @classmethod
    def load(cls, payload):
        defaults_payload = payload['datasourceDefaults']
        return cls(
            layer_id=payload['id'],
            name=payload['title'],
            data_source=DataSource(
                data_source_type=defaults_payload['type'],
                data_source_id=payload['datasetSource']['@id'].rsplit('/', 1)[-1],
                collection_id=defaults_payload.get('collectionId')
            )
        )


class DataSource:
    """ Stores info about a Sentinel Hub data source
    """
    def __init__(self, data_source_type, data_source_id, collection_id=None, name=None, service_url=None):
        self.type = data_source_type
        self.id = data_source_id
        self.collection_id = collection_id
        self.name = name
        self.service_url = None


class CRS:
    """ Stores info about an available CRS
    """
    def __init__(self, crs_id, name):
        self.id = crs_id
        self.name = name
