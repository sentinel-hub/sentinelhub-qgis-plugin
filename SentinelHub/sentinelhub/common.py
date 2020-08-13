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


class Layer:
    """ Stores info about a Sentinel Hub layer
    """
    def __init__(self, layer_id, name, info='', data_source=None):
        self.id = layer_id
        self.name = name
        self.info = info
        self.data_source = data_source


class DataSource:
    """ Stores info about a Sentinel Hub data source
    """
    def __init__(self, data_source_id, name):
        self.id = data_source_id
        self.name = name


class CRS:
    """ Stores info about an available CRS
    """
    def __init__(self, crs_id, name):
        self.id = crs_id
        self.name = name
