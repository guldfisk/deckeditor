from __future__ import annotations

import typing as t
from collections import defaultdict

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoStack, QUndoCommand, QMenu

from magiccube.laps.lap import Lap
from magiccube.laps.purples.purple import Purple
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AnyNode, AllNode

from mtgimg.interface import ImageRequest, SizeSlug

from mtgorp.models.interfaces import Printing
from mtgorp.models.persistent.cardboard import Cardboard
from mtgorp.models.serilization.strategies.jsonid import JsonId

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.components.views.cubeedit.graphical.graphicpixmapobject import GraphicPixmapObject
from deckeditor.utils.undo import CommandPackage
from deckeditor.context.context import Context

C = t.TypeVar('C', bound = t.Union[Printing, Lap])


class PhysicalCard(GraphicPixmapObject, t.Generic[C]):
    signal = QtCore.pyqtSignal(QtGui.QPixmap)
    pixmap_loader: PixmapLoader = None

    DEFAULT_PIXMAP: QtGui.QPixmap = None

    def __init__(self, cubeable: C, node_parent: t.Optional[PhysicalCard] = None):
        super().__init__(Context.pixmap_loader.get_default_pixmap(SizeSlug.MEDIUM))

        self._selection_highlight_pen = QtGui.QPen(
            QtGui.QColor(255, 0, 0),
            Context.settings.value('card_selected_frame_width', 15),
        )

        self._cubeable = cubeable
        self.node_parent = node_parent
        self._back = False

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

        self.signal.connect(self._set_pixmap)

        self._update_image()

    @classmethod
    def from_cubeable(cls, cubeable: C, node_parent: t.Optional[PhysicalCard] = None) -> PhysicalCard[C]:
        if isinstance(cubeable, Printing):
            return PhysicalPrinting(cubeable, node_parent)

        elif isinstance(cubeable, Trap):
            if isinstance(cubeable.node, AllNode):
                return PhysicalAllCard(cubeable, node_parent)
            elif isinstance(cubeable.node, AnyNode):
                return PhysicalAnyCard(cubeable, node_parent)
            else:
                raise ValueError('unknown node type')

        elif isinstance(cubeable, Ticket):
            return PhysicalTicket(cubeable, node_parent)

        elif isinstance(cubeable, Purple):
            return PhysicalPurple(cubeable, node_parent)

        else:
            return PhysicalCard(cubeable, node_parent)

    @property
    def cubeable(self) -> C:
        return self._cubeable

    def image_request(self) -> ImageRequest:
        return ImageRequest(self._cubeable, back = self._back, size_slug = SizeSlug.MEDIUM)

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

    def context_child_menu(self, child: PhysicalCard, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        if self.node_parent is not None:
            self.node_parent.context_menu(menu, undo_stack)

    def context_menu(self, context_menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        if self.node_parent is not None:
            self.node_parent.context_child_menu(self, context_menu, undo_stack)

    @staticmethod
    def _inflate(
        card_type: t.Type[PhysicalCard],
        cubeable: t.Any,
        cubeable_type: t.Optional[t.Type],
        node_parent: t.Optional[PhysicalCard],
        additional_values: t.Optional[t.Dict[str, t.Any]],
    ) -> PhysicalCard:
        card = card_type(
            (
                Context.db.printings[cubeable]
                if isinstance(cubeable, int) else
                JsonId(Context.db).deserialize(cubeable_type, cubeable)
            ),
            node_parent,
        )
        if additional_values:
            card.__dict__.update(additional_values)
        return card

    def _get_additional_reduce(self) -> t.Optional[t.Dict[str, t.Any]]:
        return None

    def __reduce__(self):
        return (
            self._inflate,
            (
                self.__class__,
                self.cubeable.id if isinstance(self.cubeable, Printing) else JsonId.serialize(self.cubeable),
                type(self.cubeable),
                self.node_parent,
                self._get_additional_reduce(),
            )
        )


class PhysicalPrinting(PhysicalCard[Printing]):

    def _get_change_printing_action(self, printing: Printing, undo_stack: QUndoStack) -> t.Callable[[], None]:
        def _change_printing():
            undo_stack.push(
                self.scene().get_cube_modification(
                    (
                        (PhysicalCard.from_cubeable(printing),),
                        (self,),
                    ),
                    self.pos() + QPoint(1, 1),
                )
            )

        return _change_printing

    def _get_change_all_printings_to_printing(
        self,
        from_printing: Printing,
        to_printing: Printing,
        undo_stack: QUndoStack,
    ) -> t.Callable[[], None]:
        def _change_all_printings_to_printing():
            cards = [
                item
                for item in
                self.scene().items()
                if isinstance(item, PhysicalPrinting) and item.cubeable == from_printing
            ]
            undo_stack.push(
                self.scene().get_cube_modification(
                    (
                        [
                            PhysicalCard.from_cubeable(to_printing)
                            for _ in
                            cards
                        ],
                        cards,
                    ),
                    self.pos() + QPoint(1, 1),
                )
            )

        return _change_all_printings_to_printing

    def _get_change_all_cardboards_to_printing(
        self,
        cardboard: Cardboard,
        printing: Printing,
        undo_stack: QUndoStack,
    ) -> t.Callable[[], None]:
        def _change_all_cardboards_to_printing():
            cards = [
                item
                for item in
                self.scene().items()
                if isinstance(item, PhysicalPrinting) and item.cubeable.cardboard == cardboard
            ]
            undo_stack.push(
                self.scene().get_cube_modification(
                    (
                        [
                            PhysicalCard.from_cubeable(printing)
                            for _ in
                            cards
                        ],
                        cards,
                    ),
                    self.pos() + QPoint(1, 1),
                )
            )

        return _change_all_cardboards_to_printing

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        super().context_menu(menu, undo_stack)

        change_this_menu = menu.addMenu('Change Printing')
        change_printings_like_this_menu = menu.addMenu('Change All Printing')
        change_cardboards_like_this_menu = menu.addMenu('Change All Cardboards')

        def _add_action_to_menu(_menu: QMenu, action: t.Callable[[], None], name: str):
            _action = QtWidgets.QAction(name, _menu)
            _action.triggered.connect(action)
            _menu.addAction(_action)

        if len(self.cubeable.cardboard.printings) > 1:
            for printing in sorted(
                (
                    p
                    for p in
                    self.cubeable.cardboard.printings
                    if not p == self.cubeable
                ),
                key = lambda p: p.expansion.name,
            ):
                _add_action_to_menu(
                    change_this_menu,
                    self._get_change_printing_action(printing, undo_stack),
                    printing.expansion.name,
                )
                _add_action_to_menu(
                    change_printings_like_this_menu,
                    self._get_change_all_printings_to_printing(self.cubeable, printing, undo_stack),
                    printing.expansion.name,
                )
                _add_action_to_menu(
                    change_cardboards_like_this_menu,
                    self._get_change_all_cardboards_to_printing(self.cubeable.cardboard, printing, undo_stack),
                    printing.expansion.name,
                )

        else:
            change_this_menu.setEnabled(False)
            change_printings_like_this_menu.setEnabled(False)
            change_cardboards_like_this_menu.setEnabled(False)

        if self.cubeable.cardboard.back_cards:
            transform = QtWidgets.QAction('Transform', menu)
            transform.triggered.connect(self.flip)
            menu.addAction(transform)


class PhysicalTrap(PhysicalCard[Trap]):

    def __init__(self, cubeable: C, node_parent: t.Optional[PhysicalTrap]):
        super().__init__(cubeable, node_parent)
        self.node_children: t.Sequence[PhysicalTrap] = []

    def _get_additional_reduce(self) -> t.Dict[str, t.Any]:
        return {
            'node_children': self.node_children,
        }

    def _generate_children(self) -> None:
        self.node_children = [
            PhysicalCard.from_cubeable(
                child
                if isinstance(child, Printing) else
                Trap(child),
                self,
            )
            for child in
            self.cubeable.node.children
        ]

    def _compress(self, child: PhysicalCard, undo_stack: QUndoStack):
        scene_remove_map = defaultdict(list)

        for card in self.node_children:
            scene_remove_map[card.scene()].append(card)

        undo_stack.push(
            CommandPackage(
                [
                    scene.get_cube_modification(
                        (
                            (self,),
                            cards,
                        ),
                        child.pos() + QPoint(1, 1),
                    )
                    if scene == child.scene() else
                    scene.get_cube_scene_remove(cards)
                    for scene, cards in
                    scene_remove_map.items()
                    if scene is not None
                ]
            )
        )

    @property
    def iter_node_children(self) -> t.Iterator[PhysicalTrap]:
        for child in self.node_children:
            if child.node_children:
                yield from child.iter_node_children
            else:
                yield child


class PhysicalAllCard(PhysicalTrap):

    def get_flatten_command(self) -> QUndoCommand:
        if not self.node_children:
            self._generate_children()
        return self.scene().get_cube_modification(
            (
                self.node_children,
                (self,),
            ),
            self.pos() + QPoint(1, 1),
        )

    def _flatten(self, undo_stack: QUndoStack) -> None:
        undo_stack.push(
            self.get_flatten_command()
        )

    def context_child_menu(self, child: PhysicalCard, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        compress = QtWidgets.QAction('Compress', menu)
        compress.triggered.connect(lambda: self._compress(child, undo_stack))
        menu.addAction(compress)

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        super().context_menu(menu, undo_stack)
        flatten = QtWidgets.QAction('Flatten', menu)
        flatten.triggered.connect(lambda: self._flatten(undo_stack))
        menu.addAction(flatten)


class PhysicalAnyCard(PhysicalTrap):

    def _get_re_select_action(
        self,
        previous_child: PhysicalCard,
        new_child: PhysicalCard,
        undo_stack: QUndoStack,
    ):
        def _re_select():
            undo_stack.push(
                previous_child.scene().get_cube_modification(
                    (
                        (new_child,),
                        (previous_child,),
                    ),
                    previous_child.pos() + QPoint(1, 1),
                )
            )

        return _re_select

    def _get_select_or(self, child: PhysicalCard, undo_stack: QUndoStack):
        def _select_or():
            undo_stack.push(
                self.scene().get_cube_modification(
                    (
                        (child,),
                        (self,),
                    ),
                    self.pos() + QPoint(1, 1),
                )
            )

        return _select_or

    def context_child_menu(self, child: PhysicalCard, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        compress = QtWidgets.QAction('Compress', menu)
        compress.triggered.connect(lambda: self._compress(child, undo_stack))
        menu.addAction(compress)

        reselection_menu = menu.addMenu('Reselect')

        for _child in self.node_children:
            if _child.cubeable != child.cubeable:
                re_select = QtWidgets.QAction(
                    child.cubeable.cardboard.name
                    if isinstance(child.cubeable, Printing) else
                    child.cubeable.node.get_minimal_string(),
                    reselection_menu,
                )
                re_select.triggered.connect(self._get_re_select_action(child, _child, undo_stack))
                reselection_menu.addAction(re_select)

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        super().context_menu(menu, undo_stack)
        flatten = menu.addMenu('Select')

        if not self.node_children:
            self._generate_children()

        for child in self.node_children:
            _flatten = QtWidgets.QAction(
                child.cubeable.cardboard.name
                if isinstance(child.cubeable, Printing) else
                child.cubeable.node.get_minimal_string(),
                flatten,
            )
            _flatten.triggered.connect(self._get_select_or(child, undo_stack))
            flatten.addAction(_flatten)


class PhysicalTicket(PhysicalCard[Ticket]):
    pass


class PhysicalPurple(PhysicalCard[Purple]):
    pass
