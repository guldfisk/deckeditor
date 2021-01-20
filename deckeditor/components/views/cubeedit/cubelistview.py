from PyQt5.QtCore import Qt, pyqtSignal, QModelIndex
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QTableWidgetItem, QTableView, QHeaderView

from mtgorp.models.interfaces import Printing

from magiccube.collections.cubeable import Cubeable

from deckeditor.components.cardview.focuscard import FocusEvent
from deckeditor.context.context import Context
from deckeditor.utils.tables.listdelete import LineDeleteMixin


class CubeListView(QTableView, LineDeleteMixin):
    cubeable_double_clicked = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._enable_row_header_delete()
        self.setSortingEnabled(True)
        self.setMouseTracking(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.doubleClicked.connect(self._on_double_clicked)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        self.cubeable_double_clicked.emit(self.model().sourceModel().items_at(self.model().mapToSource(index).row())[0])

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        idx = self.model().mapToSource(self.indexAt(event.pos())).row()
        if idx >= 0:
            Context.focus_card_changed.emit(FocusEvent(self.model().sourceModel().items_at(idx)[0]))


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
