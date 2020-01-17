from __future__ import annotations

import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets

from deckeditor.components.views.cubeedit.graphical.graphicpixmapobject import GraphicPixmapObject
from magiccube.laps.lap import Lap
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AnyNode, BorderedNode

from mtgimg.interface import ImageRequest

from magiccube.collections import cubeable as Cubeable
from mtgorp.models.interfaces import Printing

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.context.context import Context

# C = t.TypeVar('C', bound = t.Union[Printing, Lap])
C = t.TypeVar('C')


class PhysicalCard(GraphicPixmapObject, t.Generic[C]):
    signal = QtCore.pyqtSignal(QtGui.QPixmap)
    pixmap_loader: PixmapLoader = None

    DEFAULT_PIXMAP: QtGui.QPixmap = None

    def __init__(self, cubeable: C):
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
    def cubeable(self) -> C:
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

    def flip(self) -> None:
        self._back = not self._back
        self._update_image()

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            self.cubeable,
        )

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
    #     # if isinstance(self.cubeable, Trap):
    #     #
    #
    #     # other_printings = self.cubeable.cardboard.printings - {self.cubeable}
    #     #
    #     # if other_printings:
    #     #     change_printing_menu = menu.addMenu('Change Printing')
    #     #
    #     #     for printing in sorted(other_printings, key = lambda _printing: _printing.expansion.name):
    #     #         action = QtWidgets.QAction(printing.expansion.name, change_printing_menu)
    #     #         action.triggered.connect(self._PrintingChanger(self, printing))
    #     #         change_printing_menu.addAction(action)
    #     #
    #     if self._cubeable.cardboard.back_cards:
    #         transform = QtWidgets.QAction('Transform', menu)
    #         transform.triggered.connect(self._transform)
    #
    #         menu.addAction(transform)


class PhysicalOrCardOption(object):
    _options: t.Sequence[PhysicalOrCard]
    node: AnyNode

    def __init__(self, options: t.Sequence[PhysicalOrCard], node: AnyNode):
        self._options = options
        self._node = node

    @property
    def options(self) -> t.Sequence[PhysicalOrCardOption]:
        return self._options

    @property
    def node(self) -> AnyNode:
        return self._node

    @classmethod
    def from_or_selection(
        cls,
        node: AnyNode,
        selection: t.Union[Printing, BorderedNode],
    ) -> PhysicalOrCardOption:
        option = cls(
            list(
                map(
                    PhysicalOrCard,
                    (selection,)
                    if isinstance(selection, Printing) else
                    (
                        _child if isinstance(_child, Printing) else Trap(_child)
                        for _child in
                        selection.flattened
                    )
                )
            ),
            node,
        )

        for card in option.options:
            card._option = option

        return option



class PhysicalOrCard(PhysicalCard[C]):
    _option: PhysicalOrCardOption
