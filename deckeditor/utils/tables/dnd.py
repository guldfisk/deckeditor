import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QModelIndex


class ListDNDTable(QtWidgets.QTableView):

    def __init__(self):
        super().__init__()

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.dragging_index: t.Optional[int] = None

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        idx = self.rowAt(event.y())
        if idx >= 0:
            self.dragging_index = idx

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.dragging_index = None

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        if self.dragging_index is not None:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            stream = QtCore.QByteArray()

            mime.setData('cards', stream)
            drag.setMimeData(mime)
            drag.exec_()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        pass

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.source() == self:
            event.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        event.acceptProposedAction()
        target_row = self.rowAt(event.pos().y())
        if target_row < 0:
            target_row = self.model().rowCount() - 1
        if self.dragging_index != target_row:
            self.model().moveRow(
                QModelIndex(),
                self.dragging_index,
                QModelIndex(),
                target_row if target_row < self.dragging_index else target_row + 1,
            )

        self.dragging_index = None
