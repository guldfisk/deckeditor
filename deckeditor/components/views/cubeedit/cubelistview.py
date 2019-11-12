import typing as t

from PyQt5.QtCore import QObject, Qt, QVariant, QSortFilterProxyModel
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QTableView
from PyQt5.uic.properties import QtGui

from deckeditor.context.context import Context
from deckeditor.models.deck import CubeModel
from magiccube.collections.cubeable import Cubeable
from magiccube.collections.delta import CubeDeltaOperation
from magiccube.laps.lap import Lap
from mtgorp.models.persistent.printing import Printing


class CubeableTableItem(QTableWidgetItem):

    def __init__(self, cubeable: Cubeable):
        super().__init__()
        self._cubeable = cubeable
        if isinstance(cubeable, Printing):
            self.setData(0, cubeable.cardboard.name)
        else:
            self.setData(0, cubeable.description)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)

    @property
    def cubeable(self) -> Cubeable:
        return self._cubeable


class CubeListView(QTableWidget):

    def __init__(self, cube_model: CubeModel, parent: t.Optional[QObject] = None):
        super().__init__(0, 2, parent)
        self._cube_model = cube_model

        self.itemChanged.connect(self._handle_item_edit)
        self._update_content()
        self._cube_model.changed.connect(self._update_content)
        self.resizeColumnsToContents()
        self.setSortingEnabled(True)
        self.setMouseTracking(True)
        self.currentCellChanged.connect(self._handle_current_cell_changed)

    def _handle_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        previous_row: int,
        previous_column: int,
    ):
        Context.focus_card_changed.emit(self.item(current_row, 1).cubeable)

    def _handle_item_edit(self, item: CubeableTableItem):
        if item.column() == 0:
            cubeable = self.item(item.row(), 1).cubeable
            self._cube_model.modify(
                CubeDeltaOperation(
                    {
                        cubeable: item.data(0) - self._cube_model.cube.cubeables[cubeable]
                    }
                )
            )

    def _update_content(self, delta_operation: t.Optional[CubeDeltaOperation] = None) -> None:
        self.blockSignals(True)
        self.setSortingEnabled(False)
        self.setRowCount(len(self._cube_model.cube.cubeables.distinct_elements()))

        for index, (cubeable, multiplicity) in enumerate(
            sorted(
                self._cube_model.cube.cubeables.items(),
                key = lambda vs: str(vs[0].id),
            )
        ):
            item = QTableWidgetItem()
            item.setData(0, multiplicity)
            self.setItem(index, 0, item)

            item = CubeableTableItem(cubeable)
            self.setItem(
                index,
                1,
                item
            )
        self.setSortingEnabled(True)
        self.blockSignals(False)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item is not None:
            Context.focus_card_changed.emit(self.item(item.row(), 1).cubeable)


# class CubeListView(QTableView):
#
#     def __init__(self, cube_model: CubeTable):
#         super().__init__()
#         proxy = QSortFilterProxyModel()
#         proxy.setSourceModel(cube_model)
#         self.setModel(proxy)
#         self.setSortingEnabled(True)
#         self.resizeColumnsToContents()