"""
Utilities for creating names
"""


def get_qgis_layer_name(settings, layer):
    """ Creates a name for a QGIS layer from a given Sentinel Hub layer and settings

    :return: QGIS layer name
    :rtype: str
    """
    plugin_params = [settings.service_type.upper()]

    if not layer.data_source.is_timeless():
        plugin_params.append(_get_time_interval_name(settings))
    if not layer.data_source.is_cloudless():
        plugin_params.append('{}%'.format(settings.maxcc))
    if not (layer.data_source.is_timeless() and layer.data_source.is_cloudless()):
        plugin_params.append(settings.priority)

    plugin_params.append(settings.crs)

    return '{} - {} ({})'.format(_get_source_name(layer), layer.name, ', '.join(plugin_params))


def get_filename(settings, layer, bbox):
    """ Creates a filename from meta-information
    DataSource_LayerName_start_time_end_time_xmin_y_min_xmax_ymax_maxcc_priority.FORMAT
    """
    info_list = [_get_source_name(layer), layer.id]

    if not layer.data_source.is_timeless():
        info_list.append(_get_time_interval_name(settings))

    info_list.extend(bbox.split(','))

    if not layer.data_source.is_cloudless():
        info_list.append(settings.maxcc)

    if not (layer.data_source.is_timeless() and layer.data_source.is_cloudless()):
        info_list.append(settings.priority)

    filename = '_'.join(map(str, info_list))

    image_format = settings.image_format.split('/')[1]
    filename = '{}.{}'.format(filename, image_format)

    return filename.replace(' ', '').replace(':', '_').replace('/', '_')


def _get_time_interval_name(settings):
    """ Returns time interval in a form that will be displayed in qgis layer name

    :return: string describing time interval
    :rtype: str
    """
    time_interval = _get_time_name(settings.start_time), _get_time_name(settings.end_time)

    if settings.is_exact_date:
        return time_interval[0]

    return '{}/{}'.format(time_interval[0], time_interval[1])


def _get_time_name(time_str):
    """ Parses a single time string
    """
    return time_str if time_str else '-'


def _get_source_name(layer):
    """ Returns a name of a data source

    :return: A name
    :rtype: str
    """
    return layer.data_source.name
