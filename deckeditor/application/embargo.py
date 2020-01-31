import os
import typing
import sys

from PyQt5.QtWidgets import QApplication

from deckeditor import paths


class EmbargoApp(QApplication):

    def __init__(self, argv: typing.List[str]) -> None:
        super().__init__(argv)
        if not sys.platform.startswith('win'):
            with open(os.path.join(paths.RESOURCE_PATH, 'style.qss'), 'r') as f:
                self.setStyleSheet(
                    f.read().replace(
                        'url(',
                        'url(' + os.path.join(
                            paths.RESOURCE_PATH,
                            'qss_icons',
                            'rc',
                            '',
                        ),
                    )
                )

        self.setOrganizationName('EmbargoSoft')
        self.setOrganizationDomain('prohunterdogkeeper.dk')
        self.setApplicationName('Embargo Edit')





















