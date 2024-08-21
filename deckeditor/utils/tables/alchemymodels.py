import typing as t
from abc import abstractmethod
from collections import OrderedDict
from enum import Enum

from lru import LRU
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.sip import wrappertype
from sqlalchemy import func
from sqlalchemy.orm import Query
from sqlalchemy.orm.attributes import QueryableAttribute

from deckeditor.store import EDB
from deckeditor.utils.delegates import ComboBoxDelegate


T = t.TypeVar("T")

Primitive = t.Union[None, str, int, float, bool]


class PrimitiveConversionError(Exception):
    pass


class ConvertibleColumn(t.Generic[T]):
    def __init__(self, column: QueryableAttribute):
        self._column = column

    @property
    def column(self) -> QueryableAttribute:
        return self._column

    def preferred_delegate(self, parent: t.Optional[QtWidgets.QWidget]) -> QtWidgets.QAbstractItemDelegate:
        return QtWidgets.QItemDelegate(parent)

    @abstractmethod
    def to_primitive(self, value: T) -> Primitive:
        pass

    @abstractmethod
    def from_primitive(self, primitive: Primitive) -> T:
        pass


class PrimitiveColumn(ConvertibleColumn[T]):
    def to_primitive(self, value: T) -> Primitive:
        return value

    def from_primitive(self, primitive: Primitive) -> T:
        return primitive


class MappingColumn(ConvertibleColumn[T]):
    def __init__(self, column: QueryableAttribute, mapping: t.Iterable[t.Tuple[Primitive, T]]):
        super().__init__(column)
        self._mapping = OrderedDict(mapping)
        self._reverse = {v: k for k, v in self._mapping.items()}

    def preferred_delegate(self, parent: t.Optional[QtWidgets.QWidget]) -> QtWidgets.QAbstractItemDelegate:
        return ComboBoxDelegate(list(self._mapping.keys()), parent)

    def to_primitive(self, v: T) -> Primitive:
        return self._reverse[v]

    def from_primitive(self, v: Primitive) -> T:
        try:
            return self._mapping[v]
        except KeyError:
            raise PrimitiveConversionError()


E = t.TypeVar("E", bound=Enum)


class EnumColumn(MappingColumn[E]):
    def __init__(self, column: QueryableAttribute, enum: t.Type[E]):
        super().__init__(
            column,
            ((e.value, e) for e in enum),
        )


class _SqlAlchemyTableModelMeta(wrappertype):
    def __new__(mcs, classname, base_classes, attributes):
        attributes["_columns"] = [v for k, v in attributes.items() if isinstance(v, ConvertibleColumn)]

        return wrappertype.__new__(mcs, classname, base_classes, attributes)


class AlchemyModel(t.Generic[T], QtCore.QAbstractTableModel, metaclass=_SqlAlchemyTableModelMeta):
    _columns: t.Sequence[ConvertibleColumn]

    def __init__(
        self,
        model_type: t.Type[T],
        order_by: QueryableAttribute,
        *,
        columns: t.Optional[t.Sequence[ConvertibleColumn]] = None,
        page_size: int = 64,
        auto_commit: bool = True,
    ):
        super().__init__()
        self._model_type = model_type
        self._order_by_column = order_by
        self._page_size = page_size
        self._auto_commit = auto_commit

        if columns is not None:
            self._columns = columns

        if not self._columns:
            raise ValueError("Specify at least one column")

        self._header_names = tuple(" ".join(v.capitalize() for v in c.column.name.split("_")) for c in self._columns)

        self._cache = LRU(int(page_size * 2))
        self._cached_size = None

    def filter_query(self, query: Query) -> Query:
        return query

    def get_query(self) -> Query:
        return self.filter_query(EDB.Session.query(self._model_type))

    def clear_cache(self) -> None:
        self._cache.clear()
        self._cached_size = None

    def _load_page(self, offset: int, limit: int) -> None:
        for idx, model in enumerate(self.get_query().order_by(self._order_by_column).limit(limit).offset(offset)):
            self._cache[idx + offset] = model

    def get_item_at_index(self, index: int) -> t.Optional[T]:
        if index < 0:
            return None
        try:
            return self._cache[index]
        except KeyError:
            self._load_page(index, self._page_size)
            return self._cache.get(index, None)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if self._cached_size is None:
            self._cached_size = self.get_query().count()
        return self._cached_size

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = ...) -> t.Any:
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None

        row = self.get_item_at_index(index.row())
        if not row:
            return None

        column = self._columns[index.column()]

        return column.to_primitive(getattr(row, column.column.name))

    def setData(self, index: QModelIndex, value: t.Any, role: int = ...) -> bool:
        if role != Qt.EditRole:
            return False

        row = self.get_item_at_index(index.row())
        if not row:
            return False

        column = self._columns[index.column()]

        setattr(row, column.column.name, column.from_primitive(value))

        if self._auto_commit:
            EDB.Session.commit()

        if self._columns[index.column()] == self._order_by_column:
            self.clear_cache()

        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> t.Any:
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Vertical:
            return str(section + 1)

        return self._header_names[section]

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        self.beginRemoveRows(parent, row, row - 1 + count)
        pk_column = self._model_type.__mapper__.primary_key[0]
        items = list(
            filter(
                lambda i: i is not None,
                (getattr(self.get_item_at_index(idx), pk_column.name) for idx in range(row, row + count)),
            )
        )

        if not items:
            return False

        EDB.Session.query(self._model_type).filter(pk_column.in_(items)).delete(
            syncronize_session="fetch",
        )

        if self._auto_commit:
            EDB.Session.commit()

        self.clear_cache()
        self.endRemoveRows()
        return True

    def pop(self, row: int) -> t.Optional[T]:
        model = self.get_item_at_index(row)
        if not model:
            return
        self.removeRows(row, 1)
        return model

    def moveRows(
        self,
        sourceParent: QModelIndex,
        sourceRow: int,
        count: int,
        destinationParent: QModelIndex,
        destinationChild: int,
    ) -> bool:
        self.beginMoveRows(QModelIndex(), sourceRow, sourceRow + count - 1, QModelIndex(), destinationChild)

        floor = min(sourceRow, destinationChild)

        items = [
            _item
            for _item in (
                self.get_item_at_index(idx) for idx in range(floor, max(sourceRow, destinationChild) + count)
            )
            if _item is not None
        ]
        old_values = [getattr(_item, self._order_by_column.name) for _item in items]

        for _ in range(count):
            items.insert(destinationChild - floor, items.pop(sourceRow - floor))

        for item, new_value in zip(items, old_values):
            setattr(item, self._order_by_column.name, new_value)

        if self._auto_commit:
            EDB.Session.commit()

        self.clear_cache()

        self.endMoveRows()
        return True

    def reset(self) -> None:
        self.beginResetModel()
        self.clear_cache()
        self.endResetModel()


class IndexedAlchemyModel(AlchemyModel[T]):
    def removeRows(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginRemoveRows(parent, row, row - 1 + count)
        pk_column = self._model_type.__mapper__.primary_key[0]

        items = list(filter(lambda i: i is not None, (self.get_item_at_index(idx) for idx in range(row, row + count))))

        if not items:
            return False

        EDB.Session.query(self._model_type).filter(
            pk_column.in_([getattr(_item, pk_column.name) for _item in items])
        ).delete(
            synchronize_session="fetch",
        )

        self.get_query().filter(self._order_by_column >= getattr(items[-1], self._order_by_column.name)).update(
            {self._order_by_column: self._order_by_column - len(items)},
        )

        if self._auto_commit:
            EDB.Session.commit()

        self.clear_cache()
        self.endRemoveRows()
        return True

    def insert(self, item: T, index: int) -> None:
        setattr(
            item,
            self._order_by_column.name,
            index,
        )
        self.get_query().filter(self._order_by_column >= index).update(
            {self._order_by_column: self._order_by_column + 1},
        )
        EDB.Session.add(item)

        if self._auto_commit:
            EDB.Session.commit()

        self.reset()

    def append(self, item: T) -> None:
        max_index = self.filter_query(EDB.Session.query(func.max(self._order_by_column))).scalar()
        setattr(
            item,
            self._order_by_column.name,
            (-1 if max_index is None else max_index) + 1,
        )
        EDB.Session.add(item)

        if self._auto_commit:
            EDB.Session.commit()

        self.reset()
