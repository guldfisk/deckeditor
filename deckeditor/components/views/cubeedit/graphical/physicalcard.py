from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from deckeditor.components.views.cubeedit.graphical.graphicpixmapobject import GraphicPixmapObject
from mtgorp.models.persistent.printing import Printing

from mtgimg.interface import ImageRequest

from magiccube.collections import cubeable as Cubeable

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.context.context import Context


class PhysicalCard(GraphicPixmapObject):

    signal = QtCore.pyqtSignal(QtGui.QPixmap)
    pixmap_loader = None #type: PixmapLoader

    DEFAULT_PIXMAP = None #type: QtGui.QPixmap

    def __init__(self, cubeable: Cubeable):
        super().__init__(Context.pixmap_loader.get_default_pixmap())

        self._selection_highlight_pen = QtGui.QPen(
            QtGui.QColor(255, 0, 0),
            Context.settings.value('card_selected_frame_width', 15),
        )

        self._cubeable = cubeable
        self._back = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

        self.signal.connect(self._set_pixmap)

        self._update_image()

    @property
    def cubeable(self) -> Cubeable:
        return self._cubeable

    def image_request(self) -> ImageRequest:
        return ImageRequest(self._cubeable, back = self._back)

    def _update_image(self):
        image_request = self.image_request()
        Context.pixmap_loader.get_pixmap(image_request = image_request).then(
            lambda pixmap: self._set_updated_pixmap(pixmap, image_request)
        )

    def _set_updated_pixmap(self, pixmap: QtGui.QPixmap, image_request: ImageRequest):
        if image_request == self.image_request():
            self.signal.emit(pixmap)

    def _set_pixmap(self, pixmap: QtGui.QPixmap):
        self.set_pixmap(pixmap)
        self.update()

    def _transform(self) -> None:
        self._back = not self._back
        self._update_image()

    # def _change_printing(self, printing: Printing) -> None:
    #     self._cubeable = printing
    #     self._set_pixmap(self.DEFAULT_PIXMAP)
    #     self._update_image()
    #
    # class _PrintingChanger(object):
    #
    #     def __init__(self, card: PhysicalCard, printing: Printing):
    #         self._card = card
    #         self._printing = printing
    #
    #     def __call__(self):
    #         self._card._change_printing(self._printing)
    #
    #
    # def context_menu(self, menu: QtWidgets.QMenu) -> None:
    #     other_printings = self.cubeable.cardboard.printings - {self.cubeable}
    #
    #     if other_printings:
    #         change_printing_menu = menu.addMenu('Change Printing')
    #
    #         for printing in sorted(other_printings, key = lambda _printing: _printing.expansion.name):
    #             action = QtWidgets.QAction(printing.expansion.name, change_printing_menu)
    #             action.triggered.connect(self._PrintingChanger(self, printing))
    #             change_printing_menu.addAction(action)
    #
    #     if self._cubeable.cardboard.back_cards:
    #         transform = QtWidgets.QAction('Transform', menu)
    #         transform.triggered.connect(self._transform)
    #
    #         menu.addAction(transform)
