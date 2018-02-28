## Instructions for developers

Use Makefile during the development ([instructions](http://g-sherman.github.io/Qgis-Plugin-Builder/#using-the-makefile)).

### Plugin testing

To locally install the plugin use
```bash
make deploy
```
For testing with QGIS 2.* first change QGIS path in Makefile to
```bash
QGISDIR=.qgis2
```

### Creating a release

In order for plugin to work on both QGIS versions do
```bash
make zip
```
then manually change imports in `resources.py` to
```Python
from sys import version_info

if version_info[0] >= 3:
    from PyQt5 import QtCore
else:
    from PyQt4 import QtCore
```
and upload the package to [Official QGIS Repository](https://plugins.qgis.org/plugins/SentinelHub/).