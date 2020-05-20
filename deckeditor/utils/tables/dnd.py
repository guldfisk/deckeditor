import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore


class ListDNDTable(QtWidgets.QTableView):

    def __init__(self):
        super().__init__()

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self._dragging_index: t.Optional[int] = None

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(e)
        idx = self.rowAt(e.y())
        if idx >= 0:
            self._dragging_index = idx

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(e)
        self._dragging_index = None

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        super().mouseMoveEvent(e)
        if self._dragging_index is not None:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            stream = QtCore.QByteArray()

            mime.setData('cards', stream)
            drag.setMimeData(mime)
            drag.exec_()

    def dragMoveEvent(self, drag_event: QtGui.QDragMoveEvent):
        pass

    def dragEnterEvent(self, drag_event: QtGui.QDragEnterEvent):
        if drag_event.source() == self:
            drag_event.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        e.acceptProposedAction()
        target_row = self.rowAt(e.pos().y())
        if self._dragging_index != target_row:
            ln = self.model().lines[self._dragging_index]
            self.model().removeRow(self._dragging_index)
            self.model().insert(target_row, ln)

        self._dragging_index = None
