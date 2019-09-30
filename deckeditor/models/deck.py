from __future__ import annotations

import typing
import typing as t

from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, QObject, pyqtSignal, QAbstractTableModel, QVariant

from magiccube.collections.cubeable import Cubeable
from yeetlong.multiset import IndexedOrderedMultiset

from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation
from mtgorp.models.collections.deck import Deck


# class CubeTable(QAbstractTableModel):
#
#     def __init__(self, cube: t.Optional[Cube]) -> None:
#         super().__init__()
#         self._cube: t.List[t.Tuple[Cubeable, int]] = (
#             []
#             if cube is None else
#             list(cube.cubeables.items())
#         )
#
#         self._item_data_role_map = {
#             0: self._invalid_item_data_role,
#             1: self._invalid_item_data_role,
#             2: self._invalid_item_data_role,
#             3: self._invalid_item_data_role,
#         }
#
#     @classmethod
#     def _invalid_item_data_role(cls, index: int) -> QVariant:
#         return QVariant()
#
#     def _display_role(self, index: str) -> QVariant:
#         return
#
#     def rowCount(self, parent: QModelIndex = None) -> int:
#         return len(self._cube.cubeables)
#
#     def columnCount(self, parent: QModelIndex = None) -> int:
#         return 2
#
#     def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
#         return super().data(index, role)


class CubeModel(QObject):

    changed = pyqtSignal()

    def __init__(self, cube: t.Optional[Cube]) -> None:
        super().__init__()
        self._cube = Cube() if cube is None else cube

    @property
    def cube(self) -> Cube:
        return self._cube

    def modify(self, cube_delta_operation: CubeDeltaOperation) -> None:
        self._cube += cube_delta_operation
        self.changed.emit()


class DeckModel(QObject):

    changed = pyqtSignal()

    def __init__(self, maindeck: CubeModel, sideboard: CubeModel):
        super().__init__()
        self._maindeck = maindeck
        self._sideboard = sideboard

        self._maindeck.changed.connect(self.changed)
        self._sideboard.changed.connect(self.changed)

    @property
    def maindeck(self) -> CubeModel:
        return self._maindeck

    @property
    def sideboard(self) -> CubeModel:
        return self._sideboard