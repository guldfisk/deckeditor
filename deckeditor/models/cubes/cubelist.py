from __future__ import annotations

import typing as t

from magiccube.collections.delta import CubeDeltaOperation
from mtgorp.models.interfaces import Printing
from PyQt5 import QtGui
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtWidgets import QUndoStack
from sortedcontainers import SortedDict

from deckeditor.models.cubes.cubescene import CubeScene, PhysicalCardChange
from deckeditor.models.focusables.color import UIColor


class ChangeOperationCheck(object):
    def __init__(self):
        self._changing = False

    @property
    def changing(self) -> bool:
        return self._changing

    def __enter__(self) -> ChangeOperationCheck:
        self._changing = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._changing = False


class CubeList(QAbstractTableModel):
    def __init__(self, cube_scene: CubeScene, undo_stack: QUndoStack):
        super().__init__()
        self._cube_scene = cube_scene
        self._undo_stack = undo_stack

        self._lines = SortedDict(lambda c: str(c.id))
        self._column_names = (
            "Qty",
            "Name",
            "Set",
            "Mana Cost",
            "Typeline",
            "p/t/l",
        )
        self._changing = ChangeOperationCheck()
        self._cube_scene.content_changed.connect(self._on_cards_changed)

        self.update()

    def items_at(self, idx: int):
        return self._lines.items()[idx]

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._lines)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self._column_names)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> t.Any:
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Vertical:
            return str(section + 1)

        return self._column_names[section]

    def _on_cards_changed(self, change: PhysicalCardChange) -> None:
        self.update()

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        with self._changing:
            self.beginRemoveRows(parent, row, row - 1 + count)

            if row + count > len(self._lines):
                return False

            self._undo_stack.push(
                self._cube_scene.get_cube_modification(
                    modification=CubeDeltaOperation(
                        {cubeable: -value for cubeable, value in self._lines.items()[row : row + count]}
                    )
                )
            )

            self.endRemoveRows()
        return True

    def setData(self, index: QModelIndex, value: int, role: int = ...) -> bool:
        if role != Qt.EditRole or index.column() != 0:
            return False

        try:
            cubeable, quantity = self._lines.items()[index.row()]
        except IndexError:
            return False

        self._undo_stack.push(
            self._cube_scene.get_cube_modification(modification=CubeDeltaOperation({cubeable: value - quantity}))
        )
        return True

    def data(self, index: QModelIndex, role: int = ...) -> t.Any:
        if role not in (Qt.DisplayRole, Qt.EditRole, Qt.BackgroundRole):
            return None

        try:
            cubeable, quantity = self._lines.items()[index.row()]
        except IndexError:
            return None

        c = index.column()

        if role == Qt.BackgroundRole:
            return QtGui.QBrush(UIColor.for_focusable(cubeable).value)

        if c == 0:
            return quantity

        if c == 1:
            return cubeable.cardboard.name if isinstance(cubeable, Printing) else cubeable.description

        if c == 2:
            return cubeable.expansion.code if isinstance(cubeable, Printing) else ""

        if c == 3:
            return (
                str(cubeable.cardboard.front_card.mana_cost)
                if isinstance(cubeable, Printing) and cubeable.cardboard.front_card.mana_cost is not None
                else ""
            )

        if c == 4:
            return str(cubeable.cardboard.front_card.type_line) if isinstance(cubeable, Printing) else ""

        if c == 5:
            return (
                str(
                    cubeable.cardboard.front_card.loyalty
                    if cubeable.cardboard.front_card.loyalty is not None
                    else (
                        cubeable.cardboard.front_card.power_toughness
                        if cubeable.cardboard.front_card.power_toughness is not None
                        else ""
                    )
                )
                if isinstance(cubeable, Printing)
                else ""
            )

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.column() == 0:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def _update(self) -> None:
        self._lines.clear()
        for cubeable, multiplicity in self._cube_scene.cube.cubeables.items():
            self._lines[cubeable] = multiplicity

    def update(self) -> None:
        if self._changing.changing:
            self._update()
        else:
            self.beginResetModel()
            self._update()
            self.endResetModel()
