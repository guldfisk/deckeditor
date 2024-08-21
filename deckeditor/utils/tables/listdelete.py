from PyQt5 import QtCore, QtGui


class LineDeleteMixin(object):
    def _enable_row_header_delete(self) -> None:
        self.verticalHeader().sectionClicked.connect(lambda i: self.model().removeRow(i))

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        pressed_key = key_event.key()

        if pressed_key == QtCore.Qt.Key_Delete:
            current_index = self.selectionModel().currentIndex()
            if current_index is None:
                return
            self.model().removeRow(current_index.row())
