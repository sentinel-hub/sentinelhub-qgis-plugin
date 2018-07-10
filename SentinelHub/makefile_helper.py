"""
A simple script called by Makefile which opens resources.py and changes imports in the way that plugin will become
compatible with QGIS 2 and QGIS 3
"""

RESOURCE_FILE = 'resources.py'

NEW_CONTENT = 'from sys import version_info\n' \
              '\n' \
              'if version_info[0] >= 3:\n' \
              '    from PyQt5 import QtCore\n' \
              'else:\n' \
              '    from PyQt4 import QtCore'


def main():
    with open(RESOURCE_FILE, 'r+') as file:
        content = file.read().split('\n')

        import_cnt = 0
        for index, line in enumerate(content):
            if 'import' in line:
                content[index] = NEW_CONTENT
                import_cnt += 1

        if import_cnt == 0:
            raise ValueError('Failed to edit {} file'.format(RESOURCE_FILE))
        if import_cnt == 1:
            file.seek(0)
            file.write('\n'.join(content))


if __name__ == '__main__':
    main()