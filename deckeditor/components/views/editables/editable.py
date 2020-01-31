from __future__ import annotations

import typing as t

from PyQt5.QtWidgets import QWidget


class Editable(QWidget):

    def get_key(self) -> str:
        pass

    def persist(self) -> t.Any:
        pass

    @classmethod
    def load(cls, state: t.Any) -> Editable:
        pass
