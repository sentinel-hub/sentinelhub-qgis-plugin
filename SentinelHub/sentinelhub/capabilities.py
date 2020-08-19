"""
Module handling Sentinel Hub service capabilities
"""
from xml.etree import ElementTree

from .common import CRS
from ..constants import CrsType, ServiceType


class WmsCapabilities:
    """ Stores info about capabilities of Sentinel Hub services
    """
    def __init__(self, settings, client):
        self.settings = settings
        self.client = client

        self._xml_root = None

        self._crs_list = None
        self._crs_to_index_map = None

    def get_available_crs(self):
        """ Provides a list of all available CRS from Sentinel Hub WMS capabilities
        """
        if self._crs_list is None:
            self._load_xml()
            namespace = self._get_xml_namespace()

            crs_tag_iter = self._xml_root.findall('./{0}Capability/{0}Layer/{0}CRS'.format(namespace))
            self._crs_list = [CRS(crs.text, crs.text.replace(':', ': ')) for crs in crs_tag_iter]

            self._sort_crs_list()

        if self.settings.service_type.upper() != ServiceType.WMS:
            # Reasons why other CRS aren't supported
            # - for WMTS CRS is specified with TileMatrixSet parameter which has different names and for UTM something
            #   is not configured correctly
            # - for WFS the problem is that QGIS would pass CRS in a way that the service couldn't parse
            return self._crs_list[:1]
        return self._crs_list

    def get_crs_index(self, crs_id):
        """ For a given CRS it provides its position in the list of all available CRS
        """
        if self._crs_to_index_map is None:
            crs_list = self.get_available_crs()
            self._crs_to_index_map = {crs.id: index for index, crs in enumerate(crs_list)}

        crs_index = self._crs_to_index_map.get(crs_id, 0)

        if crs_index >= len(self.get_available_crs()):
            return 0
        return crs_index

    def _load_xml(self):
        """ Downloads and provides an xml
        """
        if self._xml_root is None:
            url = self._get_capabilities_url()
            response = self.client.download(url)

            self._xml_root = ElementTree.fromstring(response.content)

        return self._xml_root

    def _get_capabilities_url(self, get_json=False):
        """ Generates url for obtaining service capabilities
        """
        url = '{0}/ogc/{1}/{2}?service={1}&request=GetCapabilities&version=1.3.0'.format(
            self.settings.base_url, ServiceType.WMS.lower(), self.settings.instance_id
        )
        if get_json:
            return url + '&format=application/json'
        return url

    def _get_xml_namespace(self):
        """ Parses a namespace string out of the xml
        """
        if self._xml_root.tag.startswith('{'):
            return '{}}}'.format(self._xml_root.tag.split('}')[0])
        return ''

    def _sort_crs_list(self):
        """ Sorts list of CRS so that 3857 and 4326 are on the top
        """
        main_crs_ids = [CrsType.POP_WEB, CrsType.WGS84]

        main_crs_list = [crs for crs in self._crs_list if crs.id in main_crs_ids]
        other_crs_list = [crs for crs in self._crs_list if crs.id not in main_crs_ids]

        main_crs_list.sort(key=lambda crs: crs.id)
        other_crs_list.sort(key=lambda crs: crs.id)

        self._crs_list = main_crs_list + other_crs_list
