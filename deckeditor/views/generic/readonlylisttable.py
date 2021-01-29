from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, QModelIndex
from PyQt5.QtWidgets import QHeaderView, QAbstractItemView

from deckeditor.models.listtable import ListTableModel


T = t.TypeVar('T')


class ReadOnlyListTableView(t.Generic[T], QtWidgets.QTableView):
    model: t.Callable[[], ListTableModel[T]]
    setModel: t.Callable[[ListTableModel[T]], None]

    item_clicked = pyqtSignal(object)
    item_double_clicked = pyqtSignal(object)
    current_item_changed = pyqtSignal(object)
    item_selected = pyqtSignal(object)

    def __init__(self):
        super().__init__()

        self.setEditTriggers(self.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.verticalHeader().hide()
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setTabKeyNavigation(False)

        self.doubleClicked.connect(lambda idx: self.item_double_clicked.emit(self.map_index_to_item(idx)))
        self.clicked.connect(lambda idx: self.item_clicked.emit(self.map_index_to_item(idx)))
        self.item_double_clicked.connect(self.item_selected)

    def current(self) -> t.Optional[T]:
        return self.map_index_to_item(self.currentIndex())

    def map_index_to_item(self, idx: QModelIndex) -> t.Optional[T]:
        if not idx.isValid():
            return None
        return self.model().lines[idx.row()]

    def currentChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex) -> None:
        item = self.map_index_to_item(current)
        if item is None:
            return
        self.current_item_changed.emit(item)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            item = self.current()
            if item is None:
                return
            self.item_selected.emit(item)
        else:
            super().keyPressEvent(key_event)
