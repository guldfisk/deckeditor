from __future__ import annotations

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCompleter

from deckeditor.sorting.sorting import SortProperty


class SortSelector(QtWidgets.QLineEdit):

    def __init__(self, sort_dialog: SortDialog):
        super().__init__()

        self._sort_dialog = sort_dialog

        completer = QCompleter(sorted(SortProperty.names_to_sort_property.keys()))
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setModelSorting(QCompleter.CaseSensitivelySortedModel)
        completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(completer)

    def focusInEvent(self, focus_event: QtGui.QFocusEvent):
        super().focusInEvent(focus_event)
        self.selectAll()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        modifiers = key_event.modifiers()

        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            super().keyPressEvent(key_event)
            try:
                sort_property = SortProperty.names_to_sort_property[self.text()]
            except KeyError:
                return
            self._sort_dialog.accept()
            self._sort_dialog.selection_done.emit(
                sort_property,
                QtCore.Qt.Vertical
                if modifiers & QtCore.Qt.AltModifier else
                QtCore.Qt.Horizontal
            )
        else:
            super().keyPressEvent(key_event)


class SortDialog(QtWidgets.QDialog):
    selection_done = pyqtSignal(object, int)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()

        self._sort_selector = SortSelector(self)

        layout.addWidget(self._sort_selector)

        self.setLayout(layout)
