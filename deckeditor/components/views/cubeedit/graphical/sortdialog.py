from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCompleter

from deckeditor.sorting.sorting import SortProperty
from deckeditor.utils.actions import WithActions


class DirectionSelector(QtWidgets.QComboBox):
    _map = {
        'Horizontal': QtCore.Qt.Horizontal,
        'Vertical': QtCore.Qt.Vertical,
    }

    def __init__(self):
        super().__init__()
        self.addItems(('Auto', 'Horizontal', 'Vertical'))
        self.setCurrentText('Auto')

    def get_direction(self, sort_property: t.Type[SortProperty]) -> QtCore.Qt.Orientation:
        if self.currentText() == 'Auto':
            return sort_property.auto_direction
        return self._map[self.currentText()]


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
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            super().keyPressEvent(key_event)
            try:
                sort_property = SortProperty.names_to_sort_property[self.text()]
            except KeyError:
                fragments = self.text().split(' ')
                if not fragments:
                    return
                for key in sorted(SortProperty.names_to_sort_property.keys()):
                    if all(fragment.lower() in key.lower() for fragment in fragments):
                        self.setText(key)
                        return
                return
            self._sort_dialog.accept()
            self._sort_dialog.sort_selected.emit(sort_property)
        else:
            super().keyPressEvent(key_event)


class SortDialog(QtWidgets.QDialog, WithActions):
    selection_done = pyqtSignal(object, int, bool)
    sort_selected = pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle('Sort')

        layout = QtWidgets.QGridLayout()

        self._sort_selector = SortSelector(self)
        self._direction_selector = DirectionSelector()
        self._respect_custom_box = QtWidgets.QCheckBox()

        layout.addWidget(self._sort_selector, 0, 0, 1, 0)
        layout.addWidget(self._direction_selector, 1, 0)
        layout.addWidget(self._respect_custom_box, 1, 1)

        self._create_action('Auto', lambda: self._direction_selector.setCurrentText('Auto'), 'Alt+G')
        self._create_action('Horizontal', lambda: self._direction_selector.setCurrentText('Horizontal'), 'Alt+H')
        self._create_action('Vertical', lambda: self._direction_selector.setCurrentText('Vertical'), 'Alt+V')

        self.setLayout(layout)

        self.sort_selected.connect(self._handle_sort_selected)

    def _handle_sort_selected(self, sort_property: t.Type[SortProperty]) -> None:
        self.selection_done.emit(
            sort_property,
            self._direction_selector.get_direction(sort_property),
            self._respect_custom_box.isChecked(),
        )
