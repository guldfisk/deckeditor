import typing as t
import dataclasses
from collections import OrderedDict
from enum import Enum

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt

from deckeditor.utils.delegates import ComboBoxDelegate


F = t.TypeVar('F')
Primitive = t.Union[None, str, int, float, bool]


class PrimitiveConversionError(Exception):
    pass


class TableLineField(dataclasses.Field):

    def __init__(
        self,
        *,
        default = dataclasses.MISSING,
        default_factory = dataclasses.MISSING,
        init = True,
        repr = True,
        hash = None,
        compare = True,
        metadata = None,
    ):
        super().__init__(default, default_factory, init, repr, hash, compare, metadata)

    def preferred_delegate(self, parent: t.Optional[QtWidgets.QWidget]) -> QtWidgets.QItemDelegate:
        return QtWidgets.QItemDelegate(parent)

    def to_primitive(self, v: t.Any) -> Primitive:
        return v

    def from_primitive(self, v: Primitive) -> t.Any:
        return v


class MappingField(t.Generic[F], TableLineField):

    def __init__(self, mapping: t.Iterable[t.Tuple[Primitive, F]], **kwargs):
        super().__init__(**kwargs)
        self._mapping = OrderedDict(mapping)
        self._reverse = {v: k for k, v in self._mapping.items()}

    def preferred_delegate(self, parent: t.Optional[QtWidgets.QWidget]) -> QtWidgets.QItemDelegate:
        return ComboBoxDelegate(list(self._mapping.keys()), parent)

    def to_primitive(self, v: F) -> Primitive:
        return self._reverse[v]

    def from_primitive(self, v: Primitive) -> F:
        try:
            return self._mapping[v]
        except KeyError:
            raise PrimitiveConversionError()


class EnumField(MappingField):

    def __init__(self, enum: t.Type[Enum], **kwargs):
        super().__init__(
            (
                (e.value, e)
                for e in
                enum
            ),
            **kwargs,
        )


class TableLine(object):
    __dataclass_fields__: t.Mapping[str, TableLineField]

    def to_primitive(self, field: TableLineField) -> Primitive:
        v = getattr(self, field.name)
        if field.type in ('str', 'int', 'float', 'bool'):
            return v

        return field.to_primitive(v)

    def from_primitive(self, field: TableLineField, v: Primitive) -> t.Any:
        if field.type not in ('str', 'int', 'float', 'bool'):
            v = field.from_primitive(v)
        setattr(self, field.name, v)

    @classmethod
    def field(cls, name: str) -> TableLineField:
        return cls.__dataclass_fields__[name]


T = t.TypeVar('T', bound = TableLine)


class ListTableModel(t.Generic[T], QtCore.QAbstractTableModel):

    def __init__(self, line_type: t.Type[TableLine], lines: t.Iterable[T]):
        super().__init__()

        self._line_type = line_type
        self._lines: t.List[T] = list(lines)

        self._headers = tuple(field for field in dataclasses.fields(self._line_type))
        self._header_names = tuple(' '.join(v.capitalize() for v in header.name.split('_')) for header in self._headers)

    @property
    def line_type(self) -> t.Type[TableLine]:
        return self._line_type

    @property
    def lines(self) -> t.List[T]:
        return self._lines

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._lines)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = ...) -> t.Any:
        if not role in (Qt.DisplayRole, Qt.EditRole):
            return None

        try:
            row = self._lines[index.row()]
        except IndexError:
            return None

        return row.to_primitive(self._headers[index.column()])

    def setData(self, index: QModelIndex, value: t.Any, role: int = ...) -> bool:
        if role != Qt.EditRole:
            return False

        try:
            row = self._lines[index.row()]
        except IndexError:
            return False

        try:
            row.from_primitive(self._headers[index.column()], value)
        except PrimitiveConversionError:
            return False
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> t.Any:
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Vertical:
            return str(section)

        return self._header_names[section]

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        if row + count > len(self._lines):
            return False
        self.beginRemoveRows(parent, row, row - 1 + count)
        del self._lines[row:row + count]
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

    def set_lines(self, lines: t.Sequence[T]) -> None:
        self.beginResetModel()
        self._lines[:] = lines
        self.endResetModel()
