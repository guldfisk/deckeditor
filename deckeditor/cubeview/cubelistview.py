import typing as t

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

from deckeditor.models.deck import CubeModel


class CubeListView(QTableWidget):

    def __init__(self, cube_model: CubeModel, parent: t.Optional[QObject] = None):
        super().__init__(0, 3, parent)
        self.itemChanged.connect(self._handle_item_edit)

        self._cube_model = cube_model
        self._update_content()
        self._cube_model.changed.connect(self._update_content)
        self.resizeColumnsToContents()

    def _handle_item_edit(self, item: QTableWidgetItem):
        print(int(item.data(0)))

    def _update_content(self) -> None:
        self.blockSignals(True)
        printings = sorted(
            self._cube_model.cube.printings.items(),
            key = lambda vs: vs[0].cardboard.name,
        )
        self.setRowCount(len(printings))
        for index, (printing, multiplicity) in enumerate(printings):
            item = QTableWidgetItem()
            item.setData(0, str(multiplicity))
            self.setItem(index, 0, item)

            item = QTableWidgetItem(printing.cardboard.name)
            item.setFlags(item.flags() & ~item.flags())
            self.setItem(index, 1, item)

            item = QTableWidgetItem(printing.expansion.code)
            item.setFlags(item.flags() & ~item.flags())
            self.setItem(index, 2, item)

        self.blockSignals(False)