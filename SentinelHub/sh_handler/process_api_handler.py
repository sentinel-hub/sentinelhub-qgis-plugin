from qgis.core import QgsRasterLayer, QgsProject, QgsDataProvider
from qgis.utils import iface
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from io import BytesIO
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QByteArray
import tempfile


class SentinelHubQGISLoader:
    def __init__(self, instance_id, layer_name, time_interval, max_cloud_cover=30):
        self.instance_id = instance_id
        self.layer_name = "pingo"
        self.time_interval = time_interval  # Time interval in the format (start_date, end_date)
        self.max_cloud_cover = max_cloud_cover

    """
    def download_image(self):
        config = SHConfig()
        config.instance_id = self.instance_id

        bbox = BBox(self.get_visible_bbox(), crs=CRS.WGS84)
        geometry = Geometry(bbox, crs=CRS.WGS84)
        true_color_evalscript = ""
        # Define the request for Sentinel Hub data
        request = SentinelHubRequest(
            data_folder=None,  # You can specify a data folder if needed
            evalscript=true_color_evalscript,  # Custom Evalscript
            input_data=[SentinelHubRequest.input_data(data_collection=DataCollection.SENTINEL2_L2A)],
            responses=[SentinelHubRequest.output_response("default", "TIFF")],
            geometry=geometry,
            time=self.time_interval,
            config=config,
        )

        # Execute the request and get the image data
        image_data = request.get_data()[0]

        return image_data
    """

    def load_image_to_qgis(self, image_data):
        # Download the image
        if image_data:
            # Load the downloaded image data into a QGIS raster layer
            layer_name = "SentinelHubImage"
            layer = QgsRasterLayer(f"raw: {layer_name}", layer_name, "memory")
            layer.setDataProviderImage(image_data)

            # Add the raster layer to the QGIS map canvas
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                return f"Image '{layer_name}' loaded into QGIS successfully."
            else:
                return "Failed to load the image into QGIS."
        else:
            return "Image download failed."


def get_visible_bbox():
    # Get the extent of the current view in the QGIS map canvas
    canvas = iface.mapCanvas()
    extent = canvas.extent()

    # Extract the bounding box coordinates
    bbox = [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]

    return bbox


def make_request():
    # Your client credentials
    client_id = "sh-516f400a-e281-42a1-b6f3-00971bbed8eb"
    client_secret = "n5ZY2CIJm3Ee0RIx3vNpcnZjP2poivRg"
    bbox = get_visible_bbox()
    print(bbox)
    # Create a session
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)

    # Get token for the session
    token = oauth.fetch_token(
        token_url="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        client_secret=client_secret,
    )

    evalscript = """
    //VERSION=3
    function setup() {
    return {
        input: ["B02", "B03", "B04"],
        output: {
        bands: 3,
        sampleType: "AUTO", // default value - scales the output values from [0,1] to [0,255].
        },
    }
    }

    function evaluatePixel(sample) {
    return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02]
    }
    """

    request = {
        "input": {
            "bounds": {
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
                "bbox": bbox,
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": "2018-10-01T00:00:00Z",
                            "to": "2018-12-31T00:00:00Z",
                        }
                    },
                }
            ],
        },
        "output": {
            "width": 512,
            "height": 512,
        },
        "evalscript": evalscript,
    }

    url = "https://sh.dataspace.copernicus.eu/api/v1/process"
    response = oauth.post(url, json=request)
    image = BytesIO(response.content)

    load_image_to_qgis(image)


def load_image_to_qgis(image_data):
    tiff_byte = QByteArray(image_data.read())

    with open("/home/apaolo/proyects/sentinelhub-qgis-plugin/SentinelHub/sh_handler/a.tiff", "wb") as temp_file:
        temp_file.write(tiff_byte)
    # Download the image
    if image_data:
        qimage = QImage.fromData(tiff_byte)
        # Load the downloaded image data into a QGIS raster layer
        layer_name = "SentinelHubImage"
        layer = QgsRasterLayer(
            "/home/apaolo/proyects/sentinelhub-qgis-plugin/SentinelHub/sh_handler/a.tiff",
            "l",
        )
        # <layer.setDataProvider(qimage)
        # Add the raster layer to the QGIS map canvas
        QgsProject.instance().addMapLayer(layer)

    else:
        return "Image download failed."
