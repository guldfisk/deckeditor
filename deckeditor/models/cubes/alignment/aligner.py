from __future__ import annotations

import typing as t

from abc import ABC, abstractmethod

from PyQt5 import QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand, QUndoStack

from deckeditor.models.cubes.scenecard import SceneCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting.sorting import SortProperty


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

    def __init__(self, scene: SelectionScene):
        self._scene = scene

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
        sort_property: t.Type[SortProperty],
        cards: t.Sequence[SceneCard],
        orientation: int,
        in_place: bool = False,
    ) -> QUndoCommand:
        pass
