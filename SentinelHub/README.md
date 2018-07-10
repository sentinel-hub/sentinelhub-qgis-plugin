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
and upload the package to [Official QGIS Repository](https://plugins.qgis.org/plugins/SentinelHub/).