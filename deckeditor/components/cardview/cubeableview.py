from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui

from mtgorp.models.persistent.card import Card
from mtgorp.models.persistent.printing import Printing

from mtgimg.interface import ImageRequest

from magiccube.collections.cubeable import Cubeable

from deckeditor.context.context import Context
from deckeditor.utils.images import ScaledImageLabel


class CubeableImageView(ScaledImageLabel):
    _image_ready = QtCore.pyqtSignal(ImageRequest, QtGui.QPixmap)

    def __init__(self, printing_view: CubeableView):
        super().__init__()

        self._printing_view = printing_view

        self._cubeable: t.Optional[Printing] = None
        self._image_request: t.Optional[ImageRequest] = None
        self._pixmap: QtGui.QPixmap = Context.pixmap_loader.get_default_pixmap()

        self.setPixmap(self._pixmap)

        self._image_ready.connect(self._set_pixmap)
        self._printing_view.new_cubeable.connect(self._set_cubeable)

    def _set_pixmap(self, image_request: ImageRequest, pixmap: QtGui.QPixmap):
        if image_request == self._image_request:
            self.setPixmap(pixmap)

    def _set_cubeable(self, cubeable: Cubeable) -> None:
        if cubeable == self._cubeable:
            return

        self._cubeable = cubeable

        image_request = ImageRequest(cubeable)
        self._image_request = image_request

        Context.pixmap_loader.get_pixmap(
            image_request = image_request
        ).then(
            lambda pixmap:
            self._image_ready.emit(
                image_request, pixmap
            )
        )

    def fit_image(self) -> None:
        self.resize(self.pixmap.size())

    def contextMenuEvent(self, context_event: QtGui.QContextMenuEvent):
        menu = QtWidgets.QMenu(self)

        resize = QtWidgets.QAction('100%', self)

        resize.triggered.connect(self.fit_image)

        menu.addAction(resize)

        menu.exec_(self.mapToGlobal(context_event.pos()))


class CardTextView(QtWidgets.QWidget):

    def __init__(self, card: Card):
        super().__init__()
        self._card = card

        self._name_label = QtWidgets.QLabel(card.name)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._name_label)

        self.setLayout(layout)


class PrintingTextView(QtWidgets.QWidget):

    def __init__(self, printing_view: CubeableView):
        super().__init__()
        self._cubeable_view = printing_view

        self._on_new_cubeable(None)

        self._cubeable_view.new_cubeable.connect(self._on_new_cubeable)

    def _on_new_cubeable(self, cubeable: t.Optional[Cubeable]) -> None:

        if isinstance(cubeable, Printing):
            layout = QtWidgets.QVBoxLayout()
            for card in cubeable.cardboard.cards:
                layout.addWidget(
                    CardTextView(card)
                )
        else:
            layout = QtWidgets.QVBoxLayout()

        self.setLayout(layout)


class CubeableView(QtWidgets.QWidget):
    new_cubeable = QtCore.pyqtSignal(object)

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._image_view = CubeableImageView(self)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._image_view)

        self.setLayout(layout)
