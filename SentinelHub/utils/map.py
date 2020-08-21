"""
Utilities about QGIS map
"""
from qgis.core import QgsProject
from qgis.utils import iface


def get_qgis_layers():
    """ Provides a list of QGIS map layers

    :return: List of existing QGIS layers in the same order as they are in the QGIS menu
    :rtype: list(QgsMapLayer)
    """
    return [tree_layer.layer() for tree_layer in QgsProject.instance().layerTreeRoot().findLayers()]


def set_layer_fill_color_opacity(layer, opacity, repaint=False):
    """ Changes a fill color opacity of a QGIS vector layer

    :param layer: A QGIS map layer
    :type layer: QgsVectorLayer
    :param opacity: A new opacity value from interval [0, 1]
    :type opacity: float
    :param repaint: A flag specifying if a layer should be repainted afterwards
    :type repaint: bool
    """
    fill_symbol_layer = layer.renderer().symbol().symbolLayer(0)
    color = fill_symbol_layer.color()
    color.setAlphaF(opacity)
    fill_symbol_layer.setColor(color)

    if repaint:
        layer.triggerRepaint()
        iface.layerTreeView().refreshLayerSymbology(layer.id())
