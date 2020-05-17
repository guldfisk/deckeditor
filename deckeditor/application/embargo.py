import logging
import os
import sys
import typing

from PyQt5.QtWidgets import QApplication

from deckeditor import paths, values
from deckeditor.context.context import Context


class EmbargoApp(QApplication):

    def __init__(self, argv: typing.List[str]) -> None:
        super().__init__(argv)
        if not values.IS_WINDOWS:
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

        self.setOrganizationDomain('prohunterdogkeeper.dk')
        self.setApplicationName(values.APPLICATION_NAME)


def restart(save_session: bool = True):
    if save_session:
        try:
            Context.main_window.save_state()
        except:
            pass

    if not Context.compiled:
        logging.warning('cannot restart when not compiled, qutting instead')
        sys.exit()

    os.execl(values.EXECUTE_PATH, values.EXECUTE_PATH, *sys.argv[1:])
