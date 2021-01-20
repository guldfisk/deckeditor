import typing as t

from PIL import Image

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt5.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget, QTableView, QHeaderView, QAbstractItemView

from mtgorp.models.interfaces import Cardboard

from mtgimg.interface import SizeSlug, IMAGE_SIZE_MAP

from deckeditor.components.cardview.focuscard import FocusEvent
from deckeditor.context.context import Context
from deckeditor.models.focusables.grid import CubeablesGrid
from deckeditor.utils.actions import WithActions


T = t.TypeVar('T')


class CubeableImageDelegate(QStyledItemDelegate):

    def __init__(self, parent: t.Optional[QtCore.QObject], size_slug: SizeSlug = SizeSlug.MEDIUM) -> None:
        super().__init__(parent)
        self._size_slug = size_slug

    def set_size(self, size: SizeSlug) -> None:
        self._size_slug = size

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
        cubeable = index.model().get_item(index)
        if not cubeable:
            return

        if isinstance(cubeable, Cardboard):
            cubeable = cubeable.original_printing

        image_promise = Context.pixmap_loader.get_pixmap(cubeable, size_slug = self._size_slug)

        if image_promise.is_fulfilled:
            painter.drawPixmap(option.rect, image_promise.get())
        else:
            painter.drawPixmap(option.rect, Context.pixmap_loader.get_default_pixmap(size_slug = self._size_slug))
            image_promise.then(self._get_image_done_callback(index, index.model()))


class FocusableGridView(QTableView, WithActions):
    focusable_selected = pyqtSignal(object)
    current_focusable_changed = pyqtSignal(object)

    _image_width: int
    _image_height: int

    def __init__(self, size_slug: SizeSlug = SizeSlug.SMALL):
        super().__init__()

        self._size_slug = size_slug

        self._delegate = CubeableImageDelegate(self, self._size_slug)

        self.setItemDelegate(self._delegate)

        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().hide()

        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().hide()

        self._set_size(self._size_slug)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.setMouseTracking(True)

        self.customContextMenuRequested.connect(self._context_menu_event)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        self._check_width()

        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def currentChanged(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex) -> None:
        self.scrollTo(current)
        cubeable = self.model().get_item(current)
        if cubeable is not None:
            self.current_focusable_changed.emit(cubeable)
            Context.focus_card_changed.emit(
                FocusEvent(
                    cubeable
                )
            )

    def _get_change_size_action(self, size_slug: SizeSlug) -> QtWidgets.QAction:
        return self._create_action(size_slug.name, lambda: self.set_size(size_slug))

    def _context_menu_event(self, position: QtCore.QPoint):
        menu = QtWidgets.QMenu(self)

        change_size_menu = menu.addMenu('Change Image Size')

        for size_slug in SizeSlug:
            change_size_menu.addAction(self._get_change_size_action(size_slug))

        menu.exec_(self.mapToGlobal(position))

    def _set_size(self, size_slug: SizeSlug) -> None:
        self._size_slug = size_slug

        self._delegate.set_size(self._size_slug)

        self._image_width, self._image_height = IMAGE_SIZE_MAP[frozenset((self._size_slug, False))]

        self.verticalHeader().setDefaultSectionSize(self._image_height)
        self.horizontalHeader().setDefaultSectionSize(self._image_width)

    def _check_width(self):
        if isinstance(self.model(), CubeablesGrid):
            desired_width = max(1, int(self.width() / self._image_width))
            if desired_width != self.model().width:
                self.model().set_width(desired_width)

    def set_size(self, size_slug: SizeSlug) -> None:
        self._set_size(size_slug)
        self._check_width()

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        cubeable = self.model().get_item(
            self.indexAt(e.pos())
        )
        if cubeable is not None:
            Context.focus_card_changed.emit(
                FocusEvent(
                    cubeable
                )
            )

    def keyPressEvent(self, key_event: QtGui.QKeyEvent) -> None:
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            cubeable = self.model().get_item(
                self.currentIndex()
            )
            if cubeable is not None:
                self.focusable_selected.emit(cubeable)

        else:
            super().keyPressEvent(key_event)

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        super().resizeEvent(e)
        self._check_width()

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        focusable = self.model().get_item(self.indexAt(e.pos()))

        if focusable is None:
            return

        self.focusable_selected.emit(focusable)
