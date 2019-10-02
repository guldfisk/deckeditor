import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui

from deckeditor.components.cardview.cardview import CardView
from magiccube.collections.cubeable import Cubeable
from mtgimg.interface import ImageRequest

from deckeditor.context.context import Context
from deckeditor.utils.images import ScaledImageLabel
from mtgorp.models.persistent.printing import Printing


class CardViewWidget(QtWidgets.QWidget, CardView):

    _image_ready = QtCore.pyqtSignal(ImageRequest, QtGui.QPixmap)
    set_image = QtCore.pyqtSignal(object)

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._cubeable: t.Optional[Printing] = None
        self._image_request: t.Optional[ImageRequest] = None
        self._pixmap: QtGui.QPixmap = Context.pixmap_loader.get_default_pixmap()

        self._info_label = ScaledImageLabel(self)
        self._info_label.setPixmap(self._pixmap)

        self._image_ready.connect(self._set_pixmap)
        self.set_image.connect(self._set_cubeable)

        self._layout = QtWidgets.QVBoxLayout()

        self._layout.addWidget(self._info_label)

        self.setLayout(self._layout)

    def _set_pixmap(self, image_request: ImageRequest, pixmap: QtGui.QPixmap):
        if image_request == self._image_request:
            self._info_label.setPixmap(pixmap)

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
        self.resize(self._info_label.pixmap.size())

    def contextMenuEvent(self, context_event: QtGui.QContextMenuEvent):
        menu = QtWidgets.QMenu(self)

        resize = QtWidgets.QAction('100%', self)

        resize.triggered.connect(self.fit_image)

        menu.addAction(resize)

        menu.exec_(self.mapToGlobal(context_event.pos()))


