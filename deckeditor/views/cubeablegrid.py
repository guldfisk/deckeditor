import math
import typing as t

from PIL import Image

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt5.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget, QTableView, QDialog, QHeaderView, QAbstractItemView

from mtgimg.interface import SizeSlug, IMAGE_SIZE_MAP

from magiccube.collections.cubeable import Cubeable

from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.context.context import Context


class CubeablesGrid(QAbstractTableModel):

    def __init__(self, cubeables: t.Optional[t.Sequence[Cubeable]] = (), width: int = 3):
        super().__init__()
        self._cubeables = cubeables
        self._width = width

    def set_cubeables(self, cubeables: t.Sequence[Cubeable]):
        self.beginResetModel()
        self._cubeables = cubeables
        self.endResetModel()

    def set_width(self, width: int) -> None:
        self.beginResetModel()
        self._width = width
        self.endResetModel()

    @property
    def width(self) -> int:
        return self._width

    def get_cubeable(self, idx: QModelIndex) -> t.Optional[Cubeable]:
        try:
            return self._cubeables[int(idx.column() + idx.row() * self._width)]
        except IndexError:
            return None

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return int(math.ceil(len(self._cubeables) / self._width))

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return min(self._width, len(self._cubeables))

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...) -> t.Any:
        return None

    def data(self, index: QModelIndex, role: int = ...) -> t.Any:
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled


class CubeableImageDelegate(QStyledItemDelegate):

    def __init__(self, parent: t.Optional[QtCore.QObject], size_slug: SizeSlug = SizeSlug.MEDIUM) -> None:
        super().__init__(parent)
        self._size_slug = size_slug

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> t.Optional[QWidget]:
        return None

    def _get_image_done_callback(self, index: QModelIndex, model: QAbstractTableModel) -> t.Callable[[Image.Image], None]:
        def _image_done(image: Image.Image) -> None:
            model.dataChanged.emit(index, index)

        return _image_done

    def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        checked = index.model().get_cubeable(index)
        if not checked:
            return

        image_promise = Context.pixmap_loader.get_pixmap(checked, size_slug = self._size_slug)

        if image_promise.is_fulfilled:
            painter.drawPixmap(option.rect, image_promise.get())
        else:
            painter.drawPixmap(option.rect, Context.pixmap_loader.get_default_pixmap(size_slug = self._size_slug))
            image_promise.then(self._get_image_done_callback(index, index.model()))


class CubeableGridView(QTableView):
    cubeable_clicked = pyqtSignal(object)

    def __init__(self, size_slug: SizeSlug = SizeSlug.MEDIUM):
        super().__init__()

        self._size_slug = size_slug
        self._image_width, self._image_height = IMAGE_SIZE_MAP[frozenset((self._size_slug, False))]

        delegate = CubeableImageDelegate(self, self._size_slug)

        for column in range(10):
            self.setItemDelegateForColumn(column, delegate)

        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(self._image_height)
        self.verticalHeader().hide()

        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setDefaultSectionSize(self._image_width)
        self.horizontalHeader().hide()

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.clicked.connect(self._on_clicked)

        self.setMouseTracking(True)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        cubeable = self.model().get_cubeable(
            self.indexAt(e.pos())
        )
        if cubeable is not None:
            Context.focus_card_changed.emit(
                CubeableFocusEvent(
                    cubeable
                )
            )

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        if isinstance(self.model(), CubeablesGrid):
            desired_width = max(1, int(self.width() / self._image_width))
            if desired_width != self.model().width:
                self.model().set_width(desired_width)

    def _on_clicked(self, index: QModelIndex) -> None:
        cubeable = self.model().get_cubeable(index)
        if cubeable is not None:
            self.cubeable_clicked.emit(cubeable)

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(
            int(self.model().width * self._image_width) if isinstance(self.model(), CubeablesGrid) else 0,
            200,
        )


class SelectCubeableDialog(QDialog):
    cubeable_selected = pyqtSignal(object)

    def __init__(self, cubeables: t.Sequence[Cubeable]):
        super().__init__()
        self.setWindowTitle('Select cubeable')
        self._model = CubeablesGrid(cubeables)
        self._view = CubeableGridView(SizeSlug.SMALL)
        self._view.setModel(self._model)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(self._view)

        self._view.cubeable_clicked.connect(self._on_cubeable_clicked)

    def _on_cubeable_clicked(self, cubeable: Cubeable) -> None:
        self.cubeable_selected.emit(cubeable)
        self.accept()
