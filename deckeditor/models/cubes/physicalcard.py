from __future__ import annotations

import itertools
import typing as t
from collections import defaultdict

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QUndoStack, QUndoCommand, QMenu

from deckeditor.models.cubes.scenecard import SceneCard, C
from mtgorp.models.serilization.strategies.raw import RawStrategy

from magiccube.laps.purples.purple import Purple
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AnyNode, AllNode

from mtgimg.interface import ImageRequest, SizeSlug

from mtgorp.models.interfaces import Printing
from mtgorp.models.persistent.cardboard import Cardboard

from mtgqt.pixmapload.pixmaploader import PixmapLoader

from deckeditor.utils.undo import CommandPackage
from deckeditor.context.context import Context
from deckeditor.models.cubes.cubescene import CubeScene


class PhysicalCard(SceneCard[C]):
    scene: t.Callable[[], CubeScene]

    signal = QtCore.pyqtSignal(QtGui.QPixmap)
    pixmap_loader: PixmapLoader = None

    DEFAULT_PIXMAP: QtGui.QPixmap = None

    def __init__(
        self,
        cubeable: C,
        node_parent: t.Optional[PhysicalCard] = None,
        values: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ):
        super().__init__(Context.pixmap_loader.get_default_pixmap(SizeSlug.MEDIUM))

        self._selection_highlight_pen = QtGui.QPen(
            QtGui.QColor(255, 0, 0),
            Context.settings.value('card_selected_frame_width', 15),
        )

        self._cubeable = cubeable
        self.node_parent = node_parent
        self._back = False

        self.values: t.MutableMapping[str, t.Any] = values if values is not None else {}

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
        values: t.MutableMapping[str, t.Any],
        additional_values: t.Optional[t.Dict[str, t.Any]],
    ) -> PhysicalCard:
        card = card_type(
            (
                Context.db.printings[cubeable]
                if isinstance(cubeable, int) else
                RawStrategy(Context.db).deserialize(cubeable_type, cubeable)
            ),
            node_parent,
            values,
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
                self.cubeable.id if isinstance(self.cubeable, Printing) else RawStrategy.serialize(self.cubeable),
                type(self.cubeable),
                self.node_parent,
                self.values,
                self._get_additional_reduce(),
            )
        )


SceneCard.from_cubeable = PhysicalCard.from_cubeable


class PhysicalPrinting(PhysicalCard[Printing]):

    def _get_change_printing_action(self, printing: Printing, undo_stack: QUndoStack) -> t.Callable[[], None]:
        def _change_printing():
            undo_stack.push(
                self.scene().get_cube_modification(
                    add = (PhysicalCard.from_cubeable(printing),),
                    remove = (self,),
                    position = self.pos() + QPoint(1, 1),
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
                    add = [
                        PhysicalCard.from_cubeable(to_printing)
                        for _ in
                        cards
                    ],
                    remove = cards,
                    position = self.pos() + QPoint(1, 1),
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
                    add = [
                        PhysicalCard.from_cubeable(printing)
                        for _ in
                        cards
                    ],
                    remove = cards,
                    position = self.pos() + QPoint(1, 1),
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

    def __init__(
        self,
        cubeable: C,
        node_parent: t.Optional[PhysicalTrap],
        values: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ):
        super().__init__(cubeable, node_parent, values)
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
                        add = (self,),
                        remove = cards,
                        position = child.pos() + QPoint(1, 1),
                        closed_operation = True,
                    )
                    if scene == child.scene() else
                    scene.get_cube_modification(remove = cards)
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
            add = self.node_children,
            remove = (self,),
            position = self.pos() + QPoint(1, 1),
            closed_operation = True,
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
                    add = (new_child,),
                    remove = (previous_child,),
                    position = previous_child.pos() + QPoint(1, 1),
                    closed_operation = True,
                )
            )

        return _re_select

    def _get_select_or(self, child: PhysicalCard, undo_stack: QUndoStack):
        def _select_or():
            undo_stack.push(
                self.scene().get_cube_modification(
                    add = (child,),
                    remove = (self,),
                    position = self.pos() + QPoint(1, 1),
                    closed_operation = True,
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
                    _child.cubeable.cardboard.name
                    if isinstance(_child.cubeable, Printing) else
                    _child.cubeable.node.get_minimal_string(),
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

    def __init__(
        self,
        cubeable: C,
        node_parent: t.Optional[PhysicalCard],
        values: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ):
        super().__init__(cubeable, node_parent, values)
        self.option_children: t.Sequence[PhysicalPrinting] = []

    def _get_additional_reduce(self) -> t.Dict[str, t.Any]:
        return {
            'option_children': self.option_children,
        }

    def _generate_children(self) -> None:
        self.option_children = sorted(
            (
                PhysicalPrinting(option, self)
                for option in
                self.cubeable.options
            ),
            key = lambda c: c.cubeable.cardboard.name,
        )

    def _refund(self, child: PhysicalPrinting, undo_stack: QUndoStack):
        undo_stack.push(
            child.scene().get_cube_modification(
                add = child.values['tickets_payed'],
                remove = (child,),
                position = child.pos() + QPoint(1, 1),
                closed_operation = True,
            )
        )

    def _get_select_option(
        self,
        tickets: t.Mapping[CubeScene, t.List[PhysicalTicket]],
        option: PhysicalCard,
        undo_stack: QUndoStack,
    ) -> t.Callable[[], None]:
        def _select_option():
            option.values['tickets_payed'] = list(itertools.chain(*tickets.values()))
            undo_stack.push(
                CommandPackage(
                    [
                        (
                            cube_scene.get_cube_modification(
                                add = (option,),
                                remove = scene_tickets,
                                position = self.pos() + QPoint(1, 1),
                                closed_operation = True,
                            )
                            if cube_scene == self.scene() else
                            cube_scene.get_cube_modification(
                                remove = scene_tickets,
                                closed_operation = True
                            )
                        )
                        for cube_scene, scene_tickets in
                        tickets.items()
                    ]
                )
            )

        return _select_option

    def context_child_menu(self, child: PhysicalCard, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        refund_action = QtWidgets.QAction('Refund', menu)
        refund_action.triggered.connect(lambda: self._refund(child, undo_stack))
        menu.addAction(refund_action)

    def context_menu(self, menu: QtWidgets.QMenu, undo_stack: QUndoStack) -> None:
        super().context_menu(menu, undo_stack)

        if not self.option_children:
            self._generate_children()

        same_tickets = defaultdict(list)
        printings_amounts = defaultdict(int)

        for scene in self.scene().related_scenes:
            for item in scene.items():
                if isinstance(item, PhysicalTicket) and item.cubeable == self.cubeable:
                    same_tickets[scene].append(item)
                elif isinstance(item, PhysicalPrinting):
                    printings_amounts[item.cubeable] += 1

        flatten = menu.addMenu('Select')

        for option in self.option_children:
            _flatten = QtWidgets.QAction(
                option.cubeable.cardboard.name,
                flatten,
            )

            printing_amount = printings_amounts[option.cubeable]

            if sum(map(len, same_tickets.values())) > printing_amount:

                tickets = {}
                remaining_required_printings = printing_amount + 1

                for scene, cards in sorted(
                    same_tickets.items(),
                    key = lambda p: p[0] != self.scene(),
                ):
                    if len(cards) <= remaining_required_printings:
                        tickets[scene] = cards
                        remaining_required_printings -= len(cards)
                        if remaining_required_printings <= 0:
                            break
                    else:
                        tickets[scene] = (
                            sorted(cards, key = lambda c: c != self)
                            if scene == self.scene() else
                            cards
                        )[:remaining_required_printings]
                        break

                _flatten.triggered.connect(
                    self._get_select_option(
                        tickets,
                        option,
                        undo_stack,
                    )
                )
            else:
                _flatten.setEnabled(False)

            flatten.addAction(_flatten)


class PhysicalPurple(PhysicalCard[Purple]):
    pass
