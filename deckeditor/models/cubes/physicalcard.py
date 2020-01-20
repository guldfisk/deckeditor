from __future__ import annotations

import typing as t
from collections import defaultdict

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoStack, QUndoCommand

from deckeditor.components.views.cubeedit.graphical.graphicpixmapobject import GraphicPixmapObject
from deckeditor.utils.undo import CommandPackage
from magiccube.laps.lap import Lap
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AnyNode, BorderedNode, AllNode

from mtgimg.interface import ImageRequest

from magiccube.collections import cubeable as Cubeable
from mtgorp.models.interfaces import Printing

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.context.context import Context

C = t.TypeVar('C', bound = t.Union[Printing, Lap])
# C = t.TypeVar('C')


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

    @classmethod
    def from_cubeable(cls, cubeable: C) -> PhysicalCard[C]:
        if isinstance(cubeable, Printing):
            return PhysicalCard(cubeable)
        elif isinstance(cubeable, Trap):
            if isinstance(cubeable.node, AllNode):
                pass
            elif isinstance(cubeable, AnyNode):
                pass
            else:
                raise ValueError('unknown node type')
        else:
            return PhysicalCard(cubeable)

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

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        pass
        # if isinstance(self.cubeable, Trap):
        #

        # other_printings = self.cubeable.cardboard.printings - {self.cubeable}
        #
        # if other_printings:
        #     change_printing_menu = menu.addMenu('Change Printing')
        #
        #     for printing in sorted(other_printings, key = lambda _printing: _printing.expansion.name):
        #         action = QtWidgets.QAction(printing.expansion.name, change_printing_menu)
        #         action.triggered.connect(self._PrintingChanger(self, printing))
        #         change_printing_menu.addAction(action)
        #
        # if self._cubeable.cardboard.back_cards:
        #     transform = QtWidgets.QAction('Transform', menu)
        #     transform.triggered.connect(self._transform)
        #
        #     menu.addAction(transform)


class PhysicalTrap(PhysicalCard):
    node_children: t.Sequence[PhysicalTrap]

    def __init__(self, cubeable: C, node_parent: PhysicalCard):
        super().__init__(cubeable)
        self.node_children = []
        self.node_parent: PhysicalCard = node_parent

    @property
    def iter_node_children(self) -> t.Iterator[PhysicalTrap]:
        for child in self.node_children:
            if child.node_children:
                yield from child.iter_node_children
            else:
                yield child


class PhysicalAllNodeTrap(PhysicalTrap):
    _node: AllNode

    @property
    def siblings(self) -> t.Sequence[PhysicalAllNodeTrap]:
        return self._siblings

    @property
    def node(self) -> AllNode:
        return self._node

    @classmethod
    def from_node(cls, card: PhysicalTrap, node: AllNode) -> t.Sequence[PhysicalAllNodeTrap]:
        cards = [
            PhysicalAllNodeTrap(
                child
                if isinstance(child, Printing) else
                Trap(child),
                card,
            )
            for child in
            node.children
        ]

        card.node_children = cards

        for card in cards:
            card._node = node

        return cards

    def _get_compress_action(
        self,
        undo_stack: QUndoStack,
    ):
        def _compress():
            scene_remove_map = defaultdict(list)

            for card in self.node_parent.iter_node_children:
                scene_remove_map[card.scene()].append(card)

            undo_stack.push(
                CommandPackage(
                    [
                        scene.get_cube_modification(
                            (
                                (PhysicalCard(Trap(self._node)),),
                                cards,
                            ),
                            self.pos() + QPoint(1, 1),
                        )
                        if scene == self.scene() else
                        scene.get_cube_scene_remove(cards)
                        for scene, cards in
                        scene_remove_map.items()
                    ]
                )
            )

        return _compress

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        compress = QtWidgets.QAction('Compress', menu)
        compress.triggered.connect(self._get_compress_action(undo_stack))
        menu.addAction(compress)


class PhysicalOrCardOption(object):

    def __init__(
        self,
        cards: t.Sequence[PhysicalOrCard],
        node: AnyNode,
        chosen_child: t.Union[Printing, BorderedNode],
    ):
        self._cards = cards
        self._node = node
        self._chosen_child = chosen_child

    @property
    def cards(self) -> t.Sequence[PhysicalOrCard]:
        return self._cards

    @property
    def node(self) -> AnyNode:
        return self._node

    @property
    def chosen_child(self) -> t.Union[Printing, BorderedNode]:
        return self._chosen_child

    @property
    def siblings(self) -> t.Iterator[t.Union[Printing, BorderedNode]]:
        return (
            child
            for child in
            self._node.children
            if child != self._chosen_child
        )

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
            selection,
        )

        for card in option._cards:
            card._option = option

        return option


class PhysicalOrCard(PhysicalCard[C]):
    _option: PhysicalOrCardOption

    @property
    def option(self) -> PhysicalOrCardOption:
        return self._option

    def _get_re_select_action(
        self,
        sibling: t.Union[Printing, BorderedNode],
        undo_stack: QUndoStack,
    ):
        def _re_select():
            scene_remove_map = defaultdict(list)

            for card in self._option.cards:
                scene_remove_map[card.scene()].append(card)

            undo_stack.push(
                CommandPackage(
                    [
                        scene.get_cube_modification(
                            (
                                PhysicalOrCardOption.from_or_selection(
                                    self._option.node,
                                    sibling,
                                ).cards,
                                cards,
                            ),
                            self.pos() + QPoint(1, 1),
                        )
                        if scene == self.scene() else
                        scene.get_cube_scene_remove(cards)
                        for scene, cards in
                        scene_remove_map.items()
                    ]
                )
            )

        return _re_select

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        reselection_menu = menu.addMenu('Reselect')

        for sibling in self._option.siblings:
            re_select = QtWidgets.QAction(str(sibling), reselection_menu)
            re_select.triggered.connect(self._get_re_select_action(sibling, undo_stack))
            reselection_menu.addAction(re_select)
