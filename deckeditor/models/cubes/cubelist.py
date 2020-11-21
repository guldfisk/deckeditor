# import typing
# from operator import itemgetter
#
# from PyQt5.QtCore import Qt
# from PyQt5.QtCore import QAbstractTableModel, QModelIndex
# from sortedcontainers import SortedDict
#
# from deckeditor.models.cubes.cubescene import CubeScene, PhysicalCardChange
# from magiccube.collections.delta import CubeDeltaOperation
# from mtgorp.models.interfaces import Printing
#
#
# class CubeList(QAbstractTableModel):
#
#     def __init__(self, cube_scene: CubeScene):
#         super().__init__()
#         self._cube_scene = cube_scene
#
#         self._lines = SortedDict(key = itemgetter('id'))
#
#     def _on_cards_changed(self, change: PhysicalCardChange) -> None:
#         for cubeable, multiplicity in change.cube_delta_operation.removed_cubeables:
#             pass
#
#     def setData(self, index: QModelIndex, value: int, role: int = ...) -> bool:
#         if role != Qt.EditRole or index.column() != 0:
#             return False
#
#         try:
#             cubeable, quantity = self._lines.items()[index.row()]
#         except IndexError:
#             return False
#
#         self._cube_scene.get_cube_modification(
#             modification = CubeDeltaOperation({cubeable: value - quantity})
#         )
#
#         # setattr(row, column.column.name, column.from_primitive(value))
#         #
#         # if self._auto_commit:
#         #     EDB.Session.commit()
#         #
#         # if self._columns[index.column()] == self._order_by_column:
#         #     self.clear_cache()
#
#         return True
#
#     def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
#         if not role in (Qt.DisplayRole, Qt.EditRole):
#             return None
#
#         try:
#             cubeable, quantity = self._lines.items()[index.row()]
#         except IndexError:
#             return None
#
#         c = index.column()
#
#         if c == 0:
#             return quantity
#
#         if c == 1:
#             return cubeable.full_name() if isinstance(cubeable, Printing) else cubeable.description
#
#         if c == 2:
#             return cubeable.expansion.code if isinstance(cubeable, Printing) else ''
#
#         if c == 3:
#             return (
#                 str(cubeable.cardboard.front_card.mana_cost)
#                 if isinstance(cubeable, Printing) and cubeable.cardboard.front_card.mana_cost is not None else
#                 ''
#             )
#
#         if c == 4:
#             return (
#                 str(cubeable.cardboard.front_card.type_line)
#                 if isinstance(cubeable, Printing) else
#                 ''
#             )
#
#         if c == 5:
#             return (
#                 str(
#                     cubeable.cardboard.front_card.loyalty
#                     if cubeable.cardboard.front_card.loyalty is not None else
#                     (
#                         cubeable.cardboard.front_card.power_toughness
#                         if cubeable.cardboard.front_card.power_toughness is not None else
#                         ''
#                     )
#                 )
#                 if isinstance(cubeable, Printing) else
#                 ''
#             )
#
#     def update(self) -> None:
#         self._lines.clear()
#         for cubeable, multiplicity in self._cube_scene.cube.cubeables.items():
#             self._lines[cubeable] = multiplicity
