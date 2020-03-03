import typing as t

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QUndoStack

from deckeditor.components.views.cubeedit.cubeedit import CubeEditMode
from mtgorp.models.persistent.printing import Printing

from magiccube.collections.cubeable import Cubeable
from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.context.context import Context
from deckeditor.models.cubes.cubescene import CubeScene


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


class NonEditableItem(QTableWidgetItem):

    def __init__(self, text: str) -> None:
        super().__init__(text, 0)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)


class CubeListView(QTableWidget):
    cubeable_double_clicked = pyqtSignal(object)

    def __init__(
        self,
        cube_model: CubeScene,
        undo_stack: QUndoStack,
        parent: t.Optional[QObject] = None,
    ):
        super().__init__(0, 6, parent)
        self._cube_scene = cube_model
        self._undo_stack = undo_stack

        self.setHorizontalHeaderLabels(
            (
                'Qty',
                'Name',
                'Set',
                'Mana Cost',
                'Typeline',
                'p/t/l',
            )
        )

        self.itemChanged.connect(self._handle_item_edit)
        self._update_content()
        self._cube_scene.content_changed.connect(self._update_content)
        self.resizeColumnsToContents()
        self.setSortingEnabled(True)
        self.setMouseTracking(True)
        self.currentCellChanged.connect(self._handle_current_cell_changed)
        self.itemDoubleClicked.connect(self._handle_item_double_clicked)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        pressed_key = key_event.key()
        modifiers = key_event.modifiers()

        if pressed_key == QtCore.Qt.Key_Delete:
            self._undo_stack.push(
                self._cube_scene.get_cube_modification(
                    CubeDeltaOperation(
                        {
                            self.item(item.row(), 1).cubeable: -int(self.item(item.row(), 0).text())
                            for item in
                            self.selectedItems()
                        }
                    ),
                )
            )

        elif pressed_key == QtCore.Qt.Key_Plus:
            self._undo_stack.push(
                self._cube_scene.get_cube_modification(
                    CubeDeltaOperation(
                        {
                            self.item(item.row(), 1).cubeable: 1
                            for item in
                            self.selectedItems()
                        }
                    ),
                )
            )

        elif pressed_key == QtCore.Qt.Key_Minus:
            self._undo_stack.push(
                self._cube_scene.get_cube_modification(
                    CubeDeltaOperation(
                        {
                            self.item(item.row(), 1).cubeable: -1
                            for item in
                            self.selectedItems()
                        }
                    ),
                )
            )

        else:
            super().keyPressEvent(key_event)

    def _handle_item_double_clicked(self, item: QTableWidgetItem) -> None:
        self.cubeable_double_clicked.emit(self.item(item.row(), 1).cubeable)

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
            self._undo_stack.push(
                self._cube_scene.get_cube_modification(
                    CubeDeltaOperation(
                        {
                            cubeable: item.data(0) - self._cube_scene.cube.cubeables[cubeable]
                        }
                    ),
                )
            )

    def _update_content(self, delta_operation: t.Optional[CubeDeltaOperation] = None) -> None:
        self.blockSignals(True)
        self.setSortingEnabled(False)
        self.setRowCount(len(self._cube_scene.cube.cubeables.distinct_elements()))

        for index, (cubeable, multiplicity) in enumerate(
                sorted(
                    self._cube_scene.cube.cubeables.items(),
                    key=lambda vs: str(vs[0].id),
                )
        ):
            item = QTableWidgetItem()
            item.setData(0, multiplicity)
            self.setItem(index, 0, item)

            self.setItem(index, 1, CubeableTableItem(cubeable))

            self.setItem(
                index,
                2,
                NonEditableItem(
                    cubeable.expansion.code
                    if isinstance(cubeable, Printing) else
                    ''
                ),
            )
            self.setItem(
                index,
                3,
                NonEditableItem(
                    str(cubeable.cardboard.front_card.mana_cost)
                    if isinstance(cubeable, Printing) and cubeable.cardboard.front_card.mana_cost is not None else
                    ''
                ),
            )
            self.setItem(
                index,
                4,
                NonEditableItem(
                    str(cubeable.cardboard.front_card.type_line)
                    if isinstance(cubeable, Printing) else
                    ''
                ),
            )
            self.setItem(
                index,
                5,
                NonEditableItem(
                    str(
                        cubeable.cardboard.front_card.loyalty
                        if cubeable.cardboard.front_card.loyalty is not None else
                        (
                            cubeable.cardboard.front_card.power_toughness
                            if cubeable.cardboard.front_card.power_toughness is not None else
                            ''
                        )
                    )
                    if isinstance(cubeable, Printing) else
                    ''
                ),
            )

        self.setSortingEnabled(True)
        self.resizeColumnsToContents()
        self.blockSignals(False)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item is not None:
            Context.focus_card_changed.emit(self.item(item.row(), 1).cubeable)
