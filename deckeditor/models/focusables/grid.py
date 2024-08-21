import math
import typing as t

from magiccube.collections.cubeable import Cubeable
from PyQt5.QtCore import QIdentityProxyModel, QModelIndex, QObject

from deckeditor.models.focusables.lists import CubeablesList


class CubeablesGrid(QIdentityProxyModel):
    sourceModel: t.Callable[[], CubeablesList]

    def __init__(self, width: int = 3) -> None:
        super().__init__()
        self._width = width

    def mapFromSource(self, sourceIndex: QModelIndex) -> QModelIndex:
        return self.createIndex(
            int(sourceIndex.row() / self._width),
            int(sourceIndex.row() % self._width),
            sourceIndex,
        )

    def mapToSource(self, proxyIndex: QModelIndex) -> QModelIndex:
        return self.createIndex(
            int(proxyIndex.row() * self._width + proxyIndex.column()),
            0,
            proxyIndex,
        )

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        return self.createIndex(row, column, parent)

    def parent(self, idx: QModelIndex) -> QObject:
        return QModelIndex()

    @property
    def width(self) -> int:
        return self._width

    def set_width(self, width: int) -> None:
        self.beginResetModel()
        self._width = max(width, 1)
        self.endResetModel()

    def get_item(self, idx: QModelIndex) -> t.Optional[Cubeable]:
        return self.sourceModel().get_item(self.mapToSource(idx))

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return int(math.ceil(len(self.sourceModel().items) / self._width))

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return min(self._width, len(self.sourceModel().items))
