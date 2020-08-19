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
        """ Creates an instance of the class from a payload
        """
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
        """ Creates an instance of the class from a payload
        """
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
        self.id = int(data_source_id)
        self.collection_id = collection_id
        self.name = name
        self.service_url = service_url

    def get_wfs_id(self):
        """ Provides a datasource ID used by Sentinel Hub WFS
        """
        if self.id == 1:
            return 'S2.TILE'

        wfs_id = 'DSS{}'.format(self.id)
        if self.collection_id is not None:
            wfs_id = '{}-{}'.format(wfs_id, self.collection_id)
        return wfs_id

    def is_cloudless(self):
        """ Decides if a data source cannot contain clouds

        :return: True if data source has no clouds and False otherwise
        :rtype: bool
        """
        return self.type in ['S1GRD', 'DEM']

    def is_timeless(self):
        """ Decides if a data source doesn't depend on time

        :return: True if data source is time independent and False otherwise
        :rtype: bool
        """
        return self.type == 'DEM'


class CRS:
    """ Stores info about an available CRS
    """
    def __init__(self, crs_id, name):
        self.id = crs_id
        self.name = name
