from __future__ import annotations

import typing as t

from abc import ABC, abstractmethod

from PyQt5 import QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoCommand, QUndoStack

from deckeditor.models.cubes.scenecard import SceneCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.sorting.sorting import SortProperty, SortMacro


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


class _AlingerResize(AlignmentCommand):
    pass


class AlignerResize(QUndoCommand):

    def __init__(
        self,
        aligner: Aligner,
        width: int,
        height: int,
    ):
        super().__init__('Aligner Resize')
        self._aligner = aligner
        self._new_width = width
        self._new_height = height

        self._old_width: t.Optional[int] = None
        self._old_height: t.Optional[int] = None
        self._pick_up: t.Optional[AlignmentPickUp] = None
        self._resize: t.Optional[_AlingerResize] = None
        self._drop: t.Optional[AlignmentMultiDrop] = None

    def redo(self) -> None:
        if self._pick_up is None:
            self._pick_up = self._aligner.pick_up(self._aligner.scene.items())
        self._pick_up.redo()

        if self._old_width is None:
            self._old_width = self._aligner.scene.width()
            self._old_height = self._aligner.scene.height()
        self._aligner.scene.setSceneRect(0, 0, self._new_width, self._new_height)

        if self._resize is None:
            self._resize = self._aligner._resize()
        self._resize.redo()

        if self._drop is None:
            self._drop = self._aligner.multi_drop(
                [
                    ((card,), card.pos())
                    for card in
                    self._aligner.scene.items()
                ]
            )
        self._drop.redo()

    def undo(self) -> None:
        self._drop.undo()
        self._aligner.scene.setSceneRect(0, 0, self._old_width, self._old_height)
        self._resize.undo()
        self._pick_up.undo()


class Aligner(ABC):
    name: str

    def __init__(self, scene: SelectionScene):
        self._scene = scene

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

    @abstractmethod
    def _resize(self) -> _AlingerResize:
        pass

    def resize(
        self,
        width: int,
        height: int,
    ) -> QUndoCommand:
        return AlignerResize(
            self,
            width,
            height,
        )
