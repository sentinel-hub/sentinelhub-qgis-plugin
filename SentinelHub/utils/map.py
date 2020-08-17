"""
Utilities about QGIS map
"""
from qgis.core import QgsProject


def get_qgis_layers():
    """ Provides a list of QGIS map layers

    :return: List of existing QGIS layers in the same order as they are in the QGIS menu
    :rtype: list(QgsMapLayer)
    """
    return [tree_layer.layer() for tree_layer in QgsProject.instance().layerTreeRoot().findLayers()]
