from __future__ import annotations

import typing as t

from PyQt5.QtWidgets import QWidget, QUndoStack


class Editable(QWidget):

    def is_empty(self) -> bool:
        pass

    def close(self) -> None:
        pass

    @property
    def undo_stack(self) -> QUndoStack:
        pass

    def persist(self) -> t.Any:
        pass

    @classmethod
    def load(cls, state: t.Any) -> Editable:
        pass
