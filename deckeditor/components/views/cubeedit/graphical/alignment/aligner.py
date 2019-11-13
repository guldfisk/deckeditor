import typing as t

from abc import ABC, abstractmethod

from PyQt5.QtCore import QPoint

from deckeditor.components.views.cubeedit.graphical.selection import SelectionScene
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard


class Aligner(ABC):

    def __init__(self, scene: SelectionScene):
        self._scene = scene

    @abstractmethod
    def pick_up(self, items: t.Iterable[PhysicalCard]) -> None:
        pass

    @abstractmethod
    def drop(self, items: t.Iterable[PhysicalCard], position: QPoint) -> None:
        pass
