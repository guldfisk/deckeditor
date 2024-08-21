from __future__ import annotations

import logging
import typing as t
from abc import abstractmethod

from cubeclient.models import CubeRelease
from magiccube.collections.cubeable import Cubeable
from magiccube.collections.nodecollection import ConstrainedNode
from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import AllNode, AnyNode, PrintingNode
from mtgimg.interface import ImageRequest
from mtgorp.models.interfaces import Card, Cardboard, Printing
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal

from deckeditor.components.cardview.focuscard import Focusable, FocusEvent
from deckeditor.components.settings import settings
from deckeditor.context.context import Context
from deckeditor.utils.images import ScaledImageLabel


class CubeableImageView(ScaledImageLabel):
    _image_ready = QtCore.pyqtSignal(ImageRequest, QtGui.QPixmap)

    def __init__(self, cubeable_view: CubeableView):
        super().__init__()

        self._cubeable_view = cubeable_view

        self._image_request: t.Optional[ImageRequest] = None
        self._pixmap: QtGui.QPixmap = Context.pixmap_loader.get_default_pixmap()

        self.setPixmap(self._pixmap)

        self._image_ready.connect(self._on_image_ready)
        self._cubeable_view.new_cubeable.connect(self.set_cubeable)

    def _on_image_ready(self, image_request: ImageRequest, pixmap: QtGui.QPixmap):
        if image_request == self._image_request:
            self.setPixmap(pixmap)

    def set_cubeable(self, focus_event: FocusEvent) -> None:
        if Context.focus_card_frozen:
            return
        if (
            isinstance(focus_event.focusable, Trap)
            and focus_event.size is not None
            and focus_event.position is not None
            and bool(focus_event.modifiers is not None and focus_event.modifiers & QtCore.Qt.ShiftModifier)
            != settings.DEFAULT_FOCUS_TRAP_SUB_PRINTING.get_value()
        ):
            pictureable = focus_event.focusable.get_printing_at(*focus_event.position, *focus_event.size)
        elif isinstance(focus_event.focusable, Cardboard):
            pictureable = focus_event.focusable.original_printing
        else:
            pictureable = focus_event.focusable

        image_request = ImageRequest(pictureable, back=focus_event.back)

        if image_request == self._image_request:
            return

        self._image_request = image_request

        promise = Context.pixmap_loader.get_pixmap(image_request=image_request)

        if promise.is_pending:
            self.setPixmap(Context.pixmap_loader.get_default_pixmap())

        promise.then(lambda pixmap: self._image_ready.emit(image_request, pixmap)).catch(logging.warning)


class CubeableTextView(QtWidgets.QStackedWidget):
    new_focus_card = pyqtSignal(FocusEvent)

    def __init__(self, cubeable_view: CubeableView):
        super().__init__()
        self._latest_cubeable: t.Optional[Cubeable] = None

        self._cubeable_view = cubeable_view

        self.setContentsMargins(0, 0, 0, 0)

        self._blank = QtWidgets.QWidget()

        self._printing_view = PrintingTextView()
        self._cardboard_view = CardboardTextView()
        self._ticket_view = TicketTextView()
        self._trap_view = TrapTextView()

        self.addWidget(self._blank)
        self.addWidget(self._printing_view)
        self.addWidget(self._cardboard_view)
        self.addWidget(self._ticket_view)
        self.addWidget(self._trap_view)

        self._cubeable_view_map = {
            "Printing": self._printing_view,
            "Cardboard": self._cardboard_view,
            "Ticket": self._ticket_view,
            "Trap": self._trap_view,
        }

        self.setCurrentWidget(self._blank)

        self._cubeable_view.new_cubeable.connect(self._on_new_cubeable)
        self._trap_view.printing_focused.connect(lambda p: self.new_focus_card.emit(FocusEvent(p)))
        self._printing_view.new_focus_card.connect(self.new_focus_card)

    def _on_new_cubeable(self, focus: FocusEvent) -> None:
        if self._latest_cubeable == focus.focusable or Context.focus_card_frozen:
            return

        self._latest_cubeable = focus.focusable

        view = self._cubeable_view_map.get(focus.focusable.__class__.__name__)

        if view is None:
            self.setCurrentWidget(self._blank)

        else:
            self.setCurrentWidget(view)
            view.set_cubeable(focus.focusable, release_id=focus.release_id)


class CardTextView(QtWidgets.QWidget):
    def __init__(self, card: t.Optional[Card] = None):
        super().__init__()
        self._card: t.Optional[Card] = None

        self._typeline_label = QtWidgets.QLabel()
        self._mana_cost_label = QtWidgets.QLabel()
        self._oracle_text_box = QtWidgets.QTextEdit()
        self._oracle_text_box.setContentsMargins(0, 1, 0, 1)
        self._oracle_text_box.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        self._oracle_text_box.setReadOnly(True)
        self._power_toughness_loyalty_label = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)

        top_splitter = QtWidgets.QHBoxLayout()
        top_splitter.setContentsMargins(0, 0, 0, 0)

        top_splitter.addWidget(self._typeline_label)
        top_splitter.addWidget(self._mana_cost_label)

        layout.addLayout(top_splitter)
        layout.addWidget(self._oracle_text_box)
        layout.addWidget(self._power_toughness_loyalty_label, alignment=QtCore.Qt.AlignRight)
        layout.addStretch()

        if card is not None:
            self.set_card(card)

    @property
    def card(self) -> Card:
        return self._card

    def set_card(self, card: Card) -> None:
        if card == self._card:
            return
        self._card = card
        self._typeline_label.setText(str(card.type_line))
        self._mana_cost_label.setText(str(card.mana_cost) if card.mana_cost is not None else "")
        self._oracle_text_box.setText(card.oracle_text)
        if card.power_toughness is not None:
            self._power_toughness_loyalty_label.setText(str(card.power_toughness))
            self._power_toughness_loyalty_label.show()
        elif card.loyalty is not None:
            self._power_toughness_loyalty_label.setText(str(card.loyalty))
            self._power_toughness_loyalty_label.show()
        else:
            self._power_toughness_loyalty_label.hide()


F = t.TypeVar("F", bound=Focusable)


class FocusableTextView(t.Generic[F], QtWidgets.QWidget):
    new_focus_card = pyqtSignal(FocusEvent)

    def __init__(self):
        super().__init__()

        self._focusable: t.Optional[F] = None

        self._name_label = QtWidgets.QLabel()

        self._card_view = CardTextView()
        self._card_views_tabs = QtWidgets.QTabWidget()

        self._cards_stack = QtWidgets.QStackedWidget()
        self._cards_stack.addWidget(self._card_view)
        self._cards_stack.addWidget(self._card_views_tabs)
        self._cards_stack.setCurrentWidget(self._card_view)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._layout.addWidget(self._name_label)
        self._layout.addWidget(self._cards_stack)
        self._layout.addStretch()

        self._card_views_tabs.currentChanged.connect(self._handle_tab_changed)

    @property
    @abstractmethod
    def cardboard(self) -> Cardboard:
        pass

    def _handle_tab_changed(self, idx: int) -> None:
        if self._focusable is None:
            return
        tab: CardTextView = self._card_views_tabs.widget(idx)
        if tab is None:
            return
        self.new_focus_card.emit(FocusEvent(self._focusable, back=tab.card in self.cardboard.back_cards))

    def set_cubeable(self, focusable: F, release_id: t.Optional[int] = None) -> None:
        if focusable == self._focusable:
            return
        self._focusable = focusable

        self._name_label.setText(self.cardboard.name)
        if len(self.cardboard.cards) > 1:
            self._card_views_tabs.clear()
            for card in self.cardboard.cards:
                self._card_views_tabs.addTab(
                    CardTextView(card),
                    card.name,
                )
            self._cards_stack.setCurrentWidget(self._card_views_tabs)
        else:
            self._card_view.set_card(self.cardboard.front_card)
            self._cards_stack.setCurrentWidget(self._card_view)


class CardboardTextView(FocusableTextView[Cardboard]):
    @property
    def cardboard(self) -> Cardboard:
        return self._focusable


class PrintingTextView(FocusableTextView[Printing]):
    def __init__(self):
        super().__init__()
        self._expansion_label = QtWidgets.QLabel()

        self._layout.insertWidget(1, self._expansion_label)

    @property
    def cardboard(self) -> Cardboard:
        return self._focusable.cardboard

    def set_cubeable(self, focusable: Printing, release_id: t.Optional[int] = None) -> None:
        super().set_cubeable(focusable, release_id)
        self._expansion_label.setText(focusable.expansion.name_and_code)


class TicketTextView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self._ticket: t.Optional[Ticket] = None

        self._name_label = QtWidgets.QLabel()
        self._printings_tabs = QtWidgets.QTabWidget()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 2, 1, 1)

        layout.addWidget(self._name_label)
        layout.addWidget(self._printings_tabs)

        self.setLayout(layout)

    def set_cubeable(self, ticket: Ticket, release_id: t.Optional[int] = None) -> None:
        if ticket == self._ticket:
            return
        self._ticket = ticket
        self._name_label.setText(ticket.name)
        self._printings_tabs.clear()
        for printing in sorted(ticket.options, key=lambda p: p.cardboard.name):
            printing_text_view = PrintingTextView()
            printing_text_view.set_cubeable(printing)
            self._printings_tabs.addTab(
                printing_text_view,
                printing.cardboard.name,
            )


class NodeTreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, node: PrintingNode, _type: str, constrained_node: t.Optional[ConstrainedNode] = None):
        super().__init__()
        self._node = node
        self.setData(1, 0, _type)
        self.setData(0, 0, "any" if isinstance(node, AnyNode) else "all")
        self.setData(2, 0, "" if constrained_node is None else str(constrained_node.value))
        self.setData(3, 0, "" if constrained_node is None else ", ".join(constrained_node.groups))


class PrintingTreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, printing: Printing, _type: str, constrained_node: t.Optional[ConstrainedNode] = None):
        super().__init__()

        self._printing = printing
        self.setData(0, 0, self._printing.cardboard.name)
        self.setData(1, 0, _type)
        self.setData(2, 0, "" if constrained_node is None else str(constrained_node.value))
        self.setData(3, 0, "" if constrained_node is None else ", ".join(constrained_node.groups))

    @property
    def printing(self) -> Printing:
        return self._printing


class TrapTextView(QtWidgets.QWidget):
    printing_focused = pyqtSignal(Printing)
    update_release = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._trap: t.Optional[Trap] = None
        self._release_id: t.Optional[int] = None

        self._intention_type_label = QtWidgets.QLabel()

        self._node_tree = QtWidgets.QTreeWidget()
        self._node_tree.setColumnCount(2)
        self._node_tree.setHeaderLabels(("name", "type", "weight", "groups"))
        self._node_tree.currentItemChanged.connect(self._on_current_item_changed)

        self._printing_view = PrintingTextView()
        self._printing_view.hide()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)

        splitter.addWidget(self._node_tree)
        splitter.addWidget(self._printing_view)

        layout.addWidget(self._intention_type_label)
        layout.addWidget(splitter)

        self.setLayout(layout)

        self.update_release.connect(self._on_update_release)

    def _on_update_release(self, release_id: int) -> None:
        self.set_cubeable(self._trap, release_id, force_update=True)

    def _on_current_item_changed(self, current, previous) -> None:
        if isinstance(current, PrintingTreeItem):
            self._printing_view.set_cubeable(current.printing)
            self._printing_view.show()
            self.printing_focused.emit(current.printing)

    def _span_tree(
        self,
        option: t.Union[Printing, PrintingNode],
        item: t.Any,
        is_top_level: bool,
        _type: str,
        release: t.Optional[CubeRelease] = None,
    ) -> None:
        constrained_node = (
            release.constrained_nodes.node_for_node(AllNode((option,)) if isinstance(option, Printing) else option)
            if release
            else None
        )

        if isinstance(option, Printing):
            _item = PrintingTreeItem(option, _type, constrained_node)

        else:
            _item = NodeTreeItem(
                option,
                _type,
                constrained_node,
            )
            _option_type = "any" if isinstance(option, AnyNode) else "all"
            for child in option.children:
                self._span_tree(child, _item, False, _option_type)

        if is_top_level:
            item.addTopLevelItem(_item)
        else:
            item.addChild(_item)

    def set_cubeable(self, trap: Trap, release_id: t.Optional[int] = None, force_update: bool = False) -> None:
        if trap is None or trap == self._trap and self._release_id == release_id and not force_update:
            return

        self._trap = trap
        self._release_id = release_id
        self._intention_type_label.setText(trap.intention_type.value)
        self._node_tree.clear()
        self._printing_view.hide()

        _option_type = "any" if isinstance(trap.node, AnyNode) else "all"

        if self._release_id is not None:
            release = Context.cube_api_client.get_release_managed_noblock(self._release_id)
            if release is None:
                Context.cube_api_client.get_release_managed(self._release_id).then(
                    lambda _release: self.update_release.emit(_release.id)
                )
        else:
            release = None

        for child in trap.node.children:
            self._span_tree(child, self._node_tree, True, _option_type, release=release)

        self._node_tree.resizeColumnToContents(0)
        self._node_tree.expandAll()


class TextImageCubeableView(QtWidgets.QWidget):
    def __init__(self, cubeable_view: CubeableView):
        super().__init__()
        self._cubeable_view = cubeable_view

        self._image_view = CubeableImageView(cubeable_view)
        self._text_view = CubeableTextView(cubeable_view)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._image_view)
        layout.addWidget(self._text_view)

        self._text_view.new_focus_card.connect(self._image_view.set_cubeable)


class CubeableView(QtWidgets.QWidget):
    new_cubeable = QtCore.pyqtSignal(FocusEvent)

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._view_type_tabs = QtWidgets.QTabWidget()

        self._image_view = CubeableImageView(self)
        self._text_view = CubeableTextView(self)
        self._both_view = TextImageCubeableView(self)

        self._view_type_tabs.addTab(self._image_view, "image")
        self._view_type_tabs.addTab(self._text_view, "text")
        self._view_type_tabs.addTab(self._both_view, "both")
        self._view_type_tabs.setCurrentWidget(self._image_view)
        self._view_type_tabs.setCurrentIndex(
            {
                "image": 0,
                "text": 1,
                "both": 2,
            }.get(settings.DEFAULT_CARD_VIEW_TYPE.get_value())
        )

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._view_type_tabs)

        self.setLayout(layout)
