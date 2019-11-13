from __future__ import annotations

import typing as t

from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt, QObject, pyqtSignal, QAbstractTableModel, QVariant

from deckeditor.utils.functions import compress_intervals
from magiccube.collections.cubeable import Cubeable
from mtgorp.models.persistent.cardboard import Cardboard
from mtgorp.models.persistent.printing import Printing
from yeetlong.multiset import IndexedOrderedMultiset

from magiccube.collections.cube import Cube
from magiccube.collections.delta import CubeDeltaOperation
from mtgorp.models.collections.deck import Deck


# class CubeTable(QAbstractTableModel):
#
#     def __init__(self, cube: t.Optional[Cube]) -> None:
#         super().__init__()
#         self._cube: IndexedOrderedMultiset[Cubeable] = (
#             IndexedOrderedMultiset()
#             if cube is None else
#             IndexedOrderedMultiset(cube.cubeables)
#         )
#
#         self._item_data_role_map = {
#             0: self._display_role,
#             # 1: self._invalid_item_data_role,
#             # 2: self._invalid_item_data_role,
#             # 3: self._invalid_item_data_role,
#             256: self._cube
#         }
#
#     @classmethod
#     def _invalid_item_data_role(cls, index: int) -> QVariant:
#         return QVariant()
#
#     def _display_role(self, index: QModelIndex) -> t.Any:
#         if index.column() == 0:
#             return self._cube.get_multiplicity_at_index(index.row())
#
#         cubeable = self._cube.get_value_at_index(index.row())
#         return cubeable.cardboard.name if isinstance(cubeable, Printing) else cubeable.description
#
#     def _cubeable(self, index: QModelIndex) -> Cubeable:
#         return self._cube.get_value_at_index(index.row())
#
#     def rowCount(self, parent: QModelIndex = None) -> int:
#         return len(self._cube.distinct_elements())
#
#     def columnCount(self, parent: QModelIndex = None) -> int:
#         return 2
#
#     def data(self, index: QModelIndex, role: int = 0) -> t.Any:
#         return self._item_data_role_map.get(role, self._invalid_item_data_role)(index)
#
#     def modify(self, cube_delta_operation: CubeDeltaOperation) -> None:
#         new_cube = self._cube + cube_delta_operation.cubeables
#         added_rows = new_cube.distinct_elements() - self._cube.distinct_elements()
#         removed_rows = self._cube.distinct_elements() - new_cube.distinct_elements()
#
#         for index_from, index_to in compress_intervals(
#             sorted(self._cube.get_index_of_item(row) for row in removed_rows)
#         ):
#             self.beginRemoveRows(QModelIndex(), index_from, index_to)
#
#         for index_from, index_to in compress_intervals(
#             sorted(new_cube.get_index_of_item(row) for row in added_rows)
#         ):
#             print(index_from, index_to)
#             self.beginInsertRows(QModelIndex(), index_from, index_to)
#
#         self._cube = new_cube
#
#         if removed_rows:
#             self.endRemoveRows()
#
#         if added_rows:
#             self.endInsertRows()


class CubeModel(QObject):

    changed = pyqtSignal(CubeDeltaOperation)

    def __init__(self, cube: t.Optional[Cube] = None) -> None:
        super().__init__()
        self._cube = Cube() if cube is None else cube

    @property
    def cube(self) -> Cube:
        return self._cube

    def modify(self, cube_delta_operation: CubeDeltaOperation) -> None:
        self._cube += cube_delta_operation
        self.changed.emit(cube_delta_operation)


class DeckModel(QObject):

    changed = pyqtSignal()

    def __init__(self, maindeck: t.Optional[CubeModel] = None, sideboard: t.Optional[CubeModel] = None):
        super().__init__()
        self._maindeck = CubeModel() if maindeck is None else maindeck
        self._sideboard = CubeModel() if sideboard is None else sideboard

        self._maindeck.changed.connect(self.changed)
        self._sideboard.changed.connect(self.changed)

    @property
    def maindeck(self) -> CubeModel:
        return self._maindeck

    @property
    def sideboard(self) -> CubeModel:
        return self._sideboard
