from __future__ import annotations

import typing
import typing as t
from dataclasses import dataclass

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal, QModelIndex, QVariant
from PyQt5.QtWidgets import QCompleter

from deckeditor.sorting import sorting
from deckeditor.sorting.sorting import SortProperty
from deckeditor.utils.actions import WithActions
from deckeditor.utils.delegates import CheckBoxDelegate
from deckeditor.utils.dialogs import SingleInstanceDialog
from deckeditor.utils.wrappers import returns_q_variant
from deckeditor.values import SortDirection


@dataclass
class SortLine(object):
    sort_property: t.Type[SortProperty]
    direction: SortDirection
    respect_custom: bool
    #
    # def __init__(self, sort_property: SortProperty, direction: SortDirection, respect_custom: bool):
    #     self._sort_property = sort_property
    #     self._direction = direction
    #     self._respect_custom = respect_custom


class SortsTableModel(QtCore.QAbstractTableModel):

    def __init__(self, sorts: t.List[SortLine]):
        super().__init__()

        self._sorts: t.List[SortLine] = sorts

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._sorts)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 3

    # @returns_q_variant
    def data(self, index: QModelIndex, role: int = ...) -> t.Any:
        if not role in (Qt.DisplayRole, Qt.EditRole, Qt.CheckStateRole):
            return None

        try:
            row = self._sorts[index.row()]
        except IndexError:
            return None

        if role == Qt.CheckStateRole:
            if not index.column() == 2:
                return None
            return Qt.Checked if row.respect_custom else Qt.Unchecked

        if index.column() == 0:
            return row.sort_property.name
        if index.column() == 1:
            return row.direction.value
        # if index.column() == 2:
        #     return QVariant(row.respect_custom)

        return None

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        print(value)
        return False

        if role != Qt.DisplayRole:
            return False

        try:
            row = self._sorts[index.row()]
        except IndexError:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.column() == 2:
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> typing.Any:
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Vertical:
            return str(section)

        if section == 0:
            return 'Sort Property'

        if section == 1:
            return 'Direction'

        if section == 2:
            return 'Respect Custom'

        return None

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        if row + count > len(self._sorts):
            return False
        self.beginRemoveRows(parent, row, row - 1 + count)
        del self._sorts[row:row - 1 + count]
        self.endRemoveRows()
        return True

    # def insertRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
    #     if not 0 <= row <= len(self._sorts):
    #         return False
    #     self.beginInsertRows(parent, row, count)
    #     self._sorts[row:row - 1 + count] = [
    #         SortLine(sorting.CMCExtractor, SortDirection.AUTO, True)
    #         for _ in
    #         range(count)
    #     ]
    #     self.endInsertRows()
    #     return True

    def append(self, line: SortLine) -> None:
        parent = QModelIndex()
        row = self.rowCount()
        self.beginInsertRows(parent, row, row)
        self._sorts.append(line)
        self.endInsertRows()


class SortsTable(QtWidgets.QTableView):
    model: t.Callable[[], SortsTableModel]

    def __init__(self):
        super().__init__()

        self.setItemDelegateForColumn(2, CheckBoxDelegate())

        # self._sorts: t.List[SortLine] = []
        self.verticalHeader().sectionClicked.connect(lambda i: self.model().append(SortLine(sorting.CMCExtractor, SortDirection.AUTO, True)))

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
                SortLine(sorting.CMCExtractor, SortDirection.ASCENDING, False),
                SortLine(sorting.NameExtractor, SortDirection.AUTO, True),
            ]
        )
        self._sorts_table = SortsTable()
        self._sorts_table.setModel(self._sorts_model)

        self._sorts_model_vertical = SortsTableModel(
            [
                SortLine(sorting.CMCExtractor, SortDirection.ASCENDING, False),
                SortLine(sorting.NameExtractor, SortDirection.AUTO, True),
            ]
        )
        self._sorts_table_vertical = SortsTable()
        self._sorts_table_vertical.setModel(self._sorts_model_vertical)

        self._sort_selector = SortSelector(self)
        self._direction_selector = DirectionSelector()
        self._respect_custom_box = QtWidgets.QCheckBox('Respect custom sort values')
        self._respect_custom_box.setChecked(True)

        layout.addWidget(self._sort_selector, 0, 0, 1, 0)
        layout.addWidget(self._direction_selector, 1, 0)
        layout.addWidget(self._respect_custom_box, 2, 0)
        layout.addWidget(self._sorts_table, 3, 0)
        layout.addWidget(self._sorts_table_vertical, 3, 1)

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
