# SentinelHub QGIS Plugin

SentinelHub QGIS Plugin enables users to harness the power of [Sentinel Hub services](https://www.sentinel-hub.com/) directly from QGIS.

Since version `2.0.0` the plugin only works with QGIS 3 and Python version `>=3.5` while earlier versions support both QGIS 2 and QGIS 3.

## Install

SentinelHub QGIS Plugin is available in QGIS Official Plugin Repository. For install just open QGIS, select `Plugins -> Manage and Install Plugins` and search for the plugin.

In case of manual installation, you can download [latest release](https://github.com/sentinel-hub/sentinelhub-qgis-plugin/releases/latest), unzip it into QGIS Plugin directory and enable plugin under QGIS Installed Plugins.

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
- Configure a path to QGIS Python environment. The path depends on your OS and QGIS installation. Examples:
```bash
# Linux
export PYTHONPATH=/usr/lib/python3/dist-packages

# macOS (check your QGIS.app version)
export PYTHONPATH=/Applications/QGIS.app/Contents/Resources/python

# Windows
set PYTHONPATH=C:\Program Files\QGIS 3.x\apps\qgis\python
```

### Development tips

- Use `pb_tool` to package and deploy the code to your local QGIS repository (run from the `SentinelHub` directory where `pb_tool.cfg` is located)
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

- Verify the plugin passes the checks that the [QGIS plugin repository runs on upload](https://plugins.qgis.org/docs/security-scanning). Bandit and detect-secrets findings are blocking; flake8 is informational but worth resolving:
```bash
pip install bandit detect-secrets flake8
bandit -r SentinelHub/ -x SentinelHub/tests
detect-secrets scan SentinelHub/
flake8 SentinelHub/
```
- Package code into a zip file using `pb_tool`
```bash
cd ./SentinelHub
pbt zip
```
- Release the plugin on [GitHub](https://github.com/sentinel-hub/sentinelhub-qgis-plugin/releases) and attach the generated zip file.
- Release the plugin to [QGIS Python Plugins Repository](https://plugins.qgis.org/plugins/SentinelHub/) by manually uploading the zip file to a [release form](https://plugins.qgis.org/plugins/SentinelHub/version/add/).
