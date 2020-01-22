import typing as t

from abc import ABC, abstractmethod

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand

from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard
from deckeditor.sorting.sort import SortProperty


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

    @abstractmethod
    def pick_up(self, cards: t.Iterable[PhysicalCard]) -> AlignmentPickUp:
        pass

    @abstractmethod
    def drop(self, cards: t.Iterable[PhysicalCard], position: QPoint) -> AlignmentDrop:
        pass

    @abstractmethod
    def multi_drop(self, drops: t.Iterable[t.Tuple[t.Sequence[PhysicalCard], QPoint]]) -> AlignmentMultiDrop:
        pass

    @abstractmethod
    def sort(
        self,
        sort_property: SortProperty,
        cards: t.Sequence[PhysicalCard],
        orientation: int,
    ) -> QUndoCommand:
        pass
