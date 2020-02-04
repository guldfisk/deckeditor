from __future__ import annotations

import typing as t

from PyQt5.QtWidgets import QWidget


class Editable(QWidget):

    def is_empty(self) -> bool:
        pass

    def persist(self) -> t.Any:
        pass

    @classmethod
    def load(cls, state: t.Any) -> Editable:
        pass
