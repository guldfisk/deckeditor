import typing as t

from abc import abstractmethod

from PyQt5.QtCore import Qt, QModelIndex, QAbstractItemModel, QObject


T = t.TypeVar('T')


class GenericItemSequence(t.Generic[T], QAbstractItemModel):

    def __init__(self, items: t.Optional[t.Sequence[T]] = ()):
        super().__init__()
        self._items = items

    def index(self, row: int, column: int, parent: QModelIndex = None) -> QModelIndex:
        return self.createIndex(row, column, parent)

    def parent(self, idx: QModelIndex) -> QObject:
        return QModelIndex()

    @property
    def items(self) -> t.Sequence[T]:
        return self._items

    def set_items(self, items: t.Sequence[T]):
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def get_item(self, idx: QModelIndex) -> t.Optional[T]:
        try:
            return self._items[idx.row()]
        except IndexError:
            return None

    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._items)

    def columnCount(self, parent: QModelIndex = None) -> int:
        return 1

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> t.Any:
        return None

    @abstractmethod
    def data(self, index: QModelIndex, role: int = None) -> t.Any:
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled
