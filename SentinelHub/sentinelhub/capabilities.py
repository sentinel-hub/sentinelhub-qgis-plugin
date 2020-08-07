"""
Module handling Sentinel Hub service capabilities
"""
from ..constants import CRS


class Capabilities:
    """ Stores info about capabilities of Sentinel Hub services
    """

    class Layer:
        """ Stores info about Sentinel Hub WMS layer
        """
        def __init__(self, layer_id, name, info='', data_source=None):
            self.id = layer_id
            self.name = name
            self.info = info
            self.data_source = data_source

    class CRS:
        """ Stores info about available CRS at Sentinel Hub WMS
        """
        def __init__(self, crs_id, name):
            self.id = crs_id
            self.name = name

    def __init__(self, instance_id, base_url):
        self.instance_id = instance_id
        self.base_url = base_url

        self.layers = []
        self.crs_list = []

    def load_xml(self, xml_root):
        """ Loads info from getCapabilities.xml
        """
        if xml_root.tag.startswith('{'):
            namespace = '{}}}'.format(xml_root.tag.split('}')[0])
        else:
            namespace = ''

        self.layers = []
        for layer in xml_root.findall('./{0}Capability/{0}Layer/{0}Layer'.format(namespace)):
            info_node = layer.find('{}Abstract'.format(namespace))
            self.layers.append(self.Layer(layer.find('{}Name'.format(namespace)).text,
                                          layer.find('{}Title'.format(namespace)).text,
                                          info_node.text if info_node is not None else ''))
        self.layers.sort(key=lambda l: l.name)

        self.crs_list = []
        for crs in xml_root.findall('./{0}Capability/{0}Layer/{0}CRS'.format(namespace)):
            self.crs_list.append(self.CRS(crs.text, crs.text.replace(':', ': ')))
        self._sort_crs_list()

    def load_json(self, json_dict):
        """ Loads info from getCapabilities.json
        """
        try:
            json_layers = {json_layer['id']: json_layer for json_layer in json_dict['layers']}
            for layer in self.layers:
                json_layer = json_layers.get(layer.id)
                if json_layer:
                    layer.data_source = json_layer['dataset']
        except KeyError:
            pass

    def _sort_crs_list(self):
        """ Sorts list of CRS so that 3857 and 4326 are on the top
        """
        new_crs_list = []
        for main_crs in [CRS.POP_WEB, CRS.WGS84]:
            for index, crs in enumerate(self.crs_list):
                if crs and crs.id == main_crs:
                    new_crs_list.append(crs)
                    self.crs_list[index] = None
        for crs in self.crs_list:
            if crs:
                new_crs_list.append(crs)
        self.crs_list = new_crs_list
