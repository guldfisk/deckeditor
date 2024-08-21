from __future__ import annotations

import logging
import os
import re
import sys
import typing
import typing as t

from PyQt5.QtWidgets import QApplication

from deckeditor import paths, values
from deckeditor.context.context import Context


class EmbargoApp(QApplication):
    current: t.Optional[EmbargoApp]

    def __init__(self, argv: typing.List[str]) -> None:
        super().__init__(argv)
        with open(os.path.join(paths.RESOURCE_PATH, "style.qss"), "r") as f:
            icon_path = os.path.join(
                paths.RESOURCE_PATH,
                "qss_icons",
                "rc",
                "",
            ).replace("\\", "/")

            pattern = re.compile(r"url\((.*)\)")

            r = pattern.sub(f'url("{icon_path}\\1")', f.read())

            self.setStyleSheet(r)

        self.setOrganizationDomain("prohunterdogkeeper.dk")
        self.setApplicationName(values.APPLICATION_NAME)

    @classmethod
    def init(cls, argv: typing.List[str]) -> EmbargoApp:
        cls.current = cls(argv)
        return cls.current


def restart(save_session: bool = True) -> None:
    if save_session:
        try:
            Context.main_window.save_state()
        except Exception:
            pass

    if not Context.compiled:
        logging.warning("cannot restart when not compiled, quiting instead")
        sys.exit()

    os.execl(values.EXECUTE_PATH, values.EXECUTE_PATH, *sys.argv[1:])
