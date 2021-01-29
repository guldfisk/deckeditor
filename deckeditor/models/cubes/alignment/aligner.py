from __future__ import annotations

import typing as t

from abc import ABC, abstractmethod

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand, QUndoStack

from hardcandy.schema import Schema

from deckeditor.models.cubes.scenecard import SceneCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting.sorting import SortMacro


class AlignmentCommand(ABC):

    @abstractmethod
    def redo(self):
        pass

    @abstractmethod
    def undo(self):
        pass


class AlignmentPickUp(AlignmentCommand):
    pass


class AlignmentDrop(AlignmentCommand):
    pass


class AlignmentMultiDrop(AlignmentCommand):
    pass


class Aligner(ABC):
    name: str

    schema: Schema = Schema()

    def __init__(self, scene: SelectionScene, **kwargs):
        self._scene = scene

    @property
    @abstractmethod
    def options(self) -> t.Mapping[str, t.Any]:
        pass

    @property
    def scene(self) -> SelectionScene:
        return self._scene

    @staticmethod
    def _inflate(aligner_type: t.Type[Aligner], values: t.Dict[str, t.Any]) -> Aligner:
        aligner = aligner_type.__new__(aligner_type)
        aligner.__dict__.update(values)
        return aligner

    def __reduce__(self):
        return (
            self._inflate,
            (
                self.__class__,
                {k: v for k, v in self.__dict__.items() if not k == '_scene'}
            )
        )

    @property
    def supports_sort_orientation(self) -> bool:
        return True

    @property
    def supports_sub_sort(self) -> bool:
        return False

    @abstractmethod
    def pick_up(self, cards: t.Iterable[SceneCard]) -> AlignmentPickUp:
        pass

    @abstractmethod
    def drop(self, cards: t.Iterable[SceneCard], position: QPoint) -> AlignmentDrop:
        pass

    @abstractmethod
    def multi_drop(self, drops: t.Iterable[t.Tuple[t.Sequence[SceneCard], QPoint]]) -> AlignmentMultiDrop:
        pass

    @abstractmethod
    def context_menu(self, menu: QtWidgets.QMenu, position: QPoint, undo_stack: QUndoStack) -> None:
        pass

    @property
    @abstractmethod
    def cards(self) -> t.Iterable[SceneCard]:
        pass

    @abstractmethod
    def realign(self) -> None:
        pass

    @abstractmethod
    def sort(
        self,
        sort_macro: SortMacro,
        cards: t.Sequence[SceneCard],
        in_place: bool = False,
    ) -> QUndoCommand:
        pass

    def draw_background(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        pass
