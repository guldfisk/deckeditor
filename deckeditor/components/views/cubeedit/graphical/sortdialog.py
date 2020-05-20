from __future__ import annotations

import typing as t
from dataclasses import dataclass

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCompleter

from deckeditor.sorting import sorting
from deckeditor.sorting.sorting import SortProperty
from deckeditor.utils.actions import WithActions
from deckeditor.utils.delegates import CheckBoxDelegate
from deckeditor.utils.dialogs import SingleInstanceDialog
from deckeditor.utils.tables.dnd import ListDNDTable
from deckeditor.utils.tables.listtable import ListTableModel, TableLine, EnumField, T, MappingField
from deckeditor.values import SortDirection


@dataclass
class SortLine(TableLine):
    sort_property: t.Type[SortProperty] = MappingField(SortProperty.names_to_sort_property.items())
    direction: SortDirection = EnumField(SortDirection)
    respect_custom: bool

    def __repr__(self) -> str:
        return '{}({})'.format(
            self.__class__.__name__,
            self.sort_property.__name__,
        )


class SortsTableModel(ListTableModel[SortLine]):

    def __init__(self, lines: t.List[SortLine]):
        super().__init__(SortLine, lines)


class SortsTable(ListDNDTable):
    model: t.Callable[[], SortsTableModel]

    def __init__(self):
        super().__init__()

        self._delegate_classes = (
            (0, SortLine.field('sort_property').preferred_delegate(self)),
            (1, SortLine.field('direction').preferred_delegate(self)),
            (2, CheckBoxDelegate(self)),
        )

        for column, delegate in self._delegate_classes:
            self.setItemDelegateForColumn(column, delegate)

        self.verticalHeader().sectionClicked.connect(lambda i: self.model().removeRow(i))

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            sum(self.columnWidth(i) for i in range(self.model().columnCount())) + 10,
            200,
        )

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        super().setModel(model)
        self.resizeColumnsToContents()


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


class SortDialog(SingleInstanceDialog, WithActions):
    selection_done = pyqtSignal(object, int, bool)
    sort_selected = pyqtSignal(object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle('Sort')

        layout = QtWidgets.QGridLayout()

        self._sorts_model = SortsTableModel(
            [
                SortLine(
                    sort_property = sorting.ColorIdentityExtractor,
                    respect_custom = False,
                    direction = SortDirection.ASCENDING,
                ),
                SortLine(
                    sort_property = sorting.ColorExtractor,
                    respect_custom = True,
                    direction = SortDirection.AUTO,
                ),
                SortLine(
                    sort_property = sorting.CMCExtractor,
                    respect_custom = True,
                    direction = SortDirection.DESCENDING,
                ),
            ]
        )
        self._sorts_table = SortsTable()
        self._sorts_table.setModel(self._sorts_model)

        self._sub_sorts_model = SortsTableModel(
            [
            ]
        )
        self._sorts_table_vertical = SortsTable()
        self._sorts_table_vertical.setModel(self._sub_sorts_model)

        self._sub_sorts_model = SortsTableModel(
            [
            ]
        )
        self._sub_sorts_table = SortsTable()
        self._sub_sorts_table.setModel(self._sub_sorts_model)

        self._sort_selector = SortSelector(self)
        self._direction_selector = DirectionSelector()
        self._respect_custom_box = QtWidgets.QCheckBox('Respect custom sort values')
        self._respect_custom_box.setChecked(True)

        self._macroes_table = QtWidgets.QTableView()

        layout.addWidget(self._sort_selector, 0, 0, 1, 2)
        layout.addWidget(self._direction_selector, 0, 2, 1, 1)
        layout.addWidget(self._respect_custom_box, 2, 0, 1, 1)
        layout.addWidget(self._sorts_table, 3, 0, 1, 1)
        layout.addWidget(self._sorts_table_vertical, 3, 1, 1, 1)
        layout.addWidget(self._sub_sorts_table, 3, 2, 1, 1)
        layout.addWidget(self._macroes_table, 4, 0, 1, 2)

        self._create_action('Auto', lambda: self._direction_selector.setCurrentText('Auto'), 'Alt+G')
        self._create_action('Horizontal', lambda: self._direction_selector.setCurrentText('Horizontal'), 'Alt+H')
        self._create_action('Vertical', lambda: self._direction_selector.setCurrentText('Vertical'), 'Alt+V')

        self.setLayout(layout)

        self.sort_selected.connect(self._handle_sort_selected)

    @classmethod
    def get(cls) -> SortDialog:
        return super().get()

    def _handle_sort_selected(self, sort_property: t.Type[SortProperty]) -> None:
        self.selection_done.emit(
            sort_property,
            self._direction_selector.get_direction(sort_property),
            self._respect_custom_box.isChecked(),
        )
