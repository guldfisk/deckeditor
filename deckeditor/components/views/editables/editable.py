from __future__ import annotations

import typing as t
from abc import abstractmethod
from enum import Enum

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QUndoStack, QWidget


class TabType(Enum):
    DECK = "deck"
    POOL = "pool"
    DRAFT = "draft"


class Tab(QWidget):
    editable_loaded = pyqtSignal(object)

    def __init__(self, undo_stack: QUndoStack) -> None:
        super().__init__()
        self._undo_stack = undo_stack

    @abstractmethod
    def load(self) -> None:
        pass

    @property
    @abstractmethod
    def loaded(self) -> bool:
        pass

    @property
    @abstractmethod
    def editable(self) -> Editable:
        pass

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @abstractmethod
    def persist(self) -> t.Any:
        pass

    @property
    @abstractmethod
    def tab_type(self) -> str:
        pass


class Editable(QWidget):
    def __init__(self, undo_stack: QUndoStack) -> None:
        super().__init__()
        self.tab: t.Optional[Tab] = None
        self._undo_stack = undo_stack

    @property
    @abstractmethod
    def tab_type(self) -> TabType:
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        pass

    def close(self) -> None:
        pass

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @abstractmethod
    def persist(self) -> t.Any:
        pass

    @classmethod
    @abstractmethod
    def load(cls, state: t.Any, undo_stack: QUndoStack) -> Editable:
        pass
