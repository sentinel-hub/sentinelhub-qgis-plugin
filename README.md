# SentinelHub QGIS Plugin

SentinelHub QGIS Plugin enables users to harness the power of [Sentinel Hub services](https://www.sentinel-hub.com/) directly from QGIS.

## Install

SentinelHub QGIS Plugin is available in the official [QGIS Python Plugins Repository](https://plugins.qgis.org/plugins/SentinelHub/). For install just open QGIS, select `Plugins -> Manage and Install Plugins` and search for `SentinelHub` plugin.

In case of manual installation, you can download a [released version](https://github.com/sentinel-hub/sentinelhub-qgis-plugin/releases), unzip it into QGIS Plugin directory and enable the plugin under QGIS Installed Plugins.

Compatibility:

- versions `<2.0.0` support both QGIS 2 and QGIS 3,
- version `2.0.0` supports QGIS 3 and Python version `>=3.5,
- version `2.1.0` supports QGIS versions `>=3.22` and Python versions `>=3.8`.


## Usage

For a quick tutorial check this [blog post](https://medium.com/sentinel-hub/control-sentinel-hub-from-within-qgis-2a83eb7f13db).

## Development

### Set up an environment

- Set up an empty Python environment.
- Install development requirements
```bash
pip install -r requirements.txt -r requirements-dev.txt
```
- Download Python packages that QGIS might not have by default and will be packed together with the plugin:
```
mkdir ./SentinelHub/external
pip download -d ./SentinelHub/external --no-deps -r requirements.txt
```
- Configure a path to QGIS Python environment. The path depends on your OS and QGIS installation. Here is an example for Linux:
```bash
export PYTHONPATH=/usr/lib/python3/dist-packages
```

### Development tips

- Use `pb_tool` to package and deploy the code to your local QGIS repository
```bash
cd ./SentinelHub
pbt deploy -y
```
- Use `pylint` to check code style
```bash
pylint SentinelHub
```
- Install [Plugin Reloader](https://plugins.qgis.org/plugins/plugin_reloader/) in QGIS in order to dynamically reload your plugin every time you redeploy it.

### Release

- Package code into a zip file using `pb_tool`
```bash
cd ./SentinelHub
pbt zip
```
- Release the plugin on [GitHub](https://github.com/sentinel-hub/sentinelhub-qgis-plugin/releases) and attach the generated zip file.
- Release the plugin to [QGIS Python Plugins Repository](https://plugins.qgis.org/plugins/SentinelHub/) by manually uploading the zip file to a [release form](https://plugins.qgis.org/plugins/SentinelHub/version/add/).
