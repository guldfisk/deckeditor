import typing as t

from hardcandy.schema import Primitive, Schema
from PyQt5 import QtCore
from PyQt5.QtCore import QModelIndex, Qt


T = t.TypeVar("T")


class ListTableModel(t.Generic[T], QtCore.QAbstractTableModel):
    def __init__(self, schema: Schema, lines: t.Iterable[T] = ()):
        super().__init__()

        self._schema = schema
        self._lines: t.List[T] = list(lines)

    @property
    def lines(self) -> t.List[T]:
        return self._lines

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._lines)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self._schema.fields)

    def data(self, index: QModelIndex, role: int = None) -> Primitive:
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None

        try:
            row = self._lines[index.row()]
        except IndexError:
            return None

        return self._schema.fields.get_value_by_index(index.column()).extract(row, self._schema)

    # def setData(self, index: QModelIndex, value: t.Any, role: int = ...) -> bool:
    #     if role != Qt.EditRole:
    #         return False
    #
    #     try:
    #         row = self._lines[index.row()]
    #     except IndexError:
    #         return False
    #
    #     try:
    #         row.from_primitive(self._headers[index.column()], value)
    #     except PrimitiveConversionError:
    #         return False
    #     return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        # return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = None) -> t.Any:
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Vertical:
            return str(section)

        return self._schema.fields.get_value_by_index(section).display_name

    def removeRows(self, row: int, count: int, parent: QModelIndex = None) -> bool:
        if row + count > len(self._lines):
            return False
        self.beginRemoveRows(parent, row, row - 1 + count)
        del self._lines[row : row + count]
        self.endRemoveRows()
        return True

    def moveRows(
        self,
        sourceParent: QModelIndex,
        sourceRow: int,
        count: int,
        destinationParent: QModelIndex,
        destinationChild: int,
    ) -> bool:
        self.beginMoveRows(QModelIndex(), sourceRow, sourceRow + count - 1, QModelIndex(), destinationChild)

        if sourceRow + count - 1 >= len(self._lines) or destinationChild >= len(self._lines):
            return False

        for _ in range(count):
            self._lines.insert(destinationChild, self._lines.pop(sourceRow))

        self.endMoveRows()
        return True

    def moveRow(
        self,
        sourceParent: QModelIndex,
        sourceRow: int,
        destinationParent: QModelIndex,
        destinationChild: int,
    ) -> bool:
        if not self.beginMoveRows(sourceParent, sourceRow, sourceRow, destinationParent, destinationChild):
            return False
        # if sourceRow >= len(self._lines) or destinationChild >= len(self._lines) + 1:
        #     print('end', sourceRow, len(self._lines), destinationChild)
        #     return False
        line = self._lines.pop(sourceRow)
        self._lines.insert(destinationChild if destinationChild < sourceRow else destinationChild - 1, line)
        self.endMoveRows()
        return True

    # def insertRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
    #     if not 0 <= row <= len(self._sorts):
    #         return False
    #     self.beginInsertRows(parent, row, count)
    #     for _ in range(count):
    #         self._sorts.insert(row, SortLine(sorting.CMCExtractor, SortDirection.AUTO, True))
    #     self.endInsertRows()
    #     return True

    def append(self, line: T) -> None:
        parent = QModelIndex()
        row = self.rowCount()
        self.beginInsertRows(parent, row, row)
        self._lines.append(line)
        self.endInsertRows()

    def insert(self, idx: int, line: T) -> None:
        self.beginInsertRows(QModelIndex(), idx, idx)
        self._lines.insert(idx, line)
        self.endInsertRows()

    def set_lines(self, lines: t.Iterable[T]) -> None:
        self.beginResetModel()
        self._lines[:] = lines
        self.endResetModel()

    def __getitem__(self, i: int) -> T:
        return self._lines[i]

    def __setitem__(self, i: int, o: T) -> None:
        raise NotImplementedError()

    def __delitem__(self, i: int) -> None:
        raise NotImplementedError()

    def __len__(self) -> int:
        return self._lines.__len__()
