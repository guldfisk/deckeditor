from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtCore, QtGui

from magiccube.laps.tickets.ticket import Ticket
from magiccube.laps.traps.trap import Trap
from magiccube.laps.traps.tree.printingtree import PrintingNode, AnyNode
from mtgorp.models.persistent.card import Card
from mtgorp.models.persistent.printing import Printing

from mtgimg.interface import ImageRequest

from magiccube.collections.cubeable import Cubeable

from deckeditor.context.context import Context
from deckeditor.utils.images import ScaledImageLabel


class CubeableImageView(ScaledImageLabel):
    _image_ready = QtCore.pyqtSignal(ImageRequest, QtGui.QPixmap)

    def __init__(self, cubeable_view: CubeableView):
        super().__init__()

        self._cubeable_view = cubeable_view

        self._cubeable: t.Optional[Printing] = None
        self._image_request: t.Optional[ImageRequest] = None
        self._pixmap: QtGui.QPixmap = Context.pixmap_loader.get_default_pixmap()

        self.setPixmap(self._pixmap)

        self._image_ready.connect(self._on_new_cubeable)
        self._cubeable_view.new_cubeable.connect(self._set_cubeable)

    def _on_new_cubeable(self, image_request: ImageRequest, pixmap: QtGui.QPixmap):
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


class CubeableTextView(QtWidgets.QWidget):

    def __init__(self, cubeable_view: CubeableView):
        super().__init__()
        self._latest_cubeable: t.Optional[Cubeable] = None

        self._cubeable_view = cubeable_view

        self._stack = QtWidgets.QStackedWidget()

        self._blank = QtWidgets.QWidget()
        self._printing_view = PrintingTextView()
        self._ticket_view = TicketTextView()
        self._trap_view = TrapTextView()

        self._stack.addWidget(self._blank)
        self._stack.addWidget(self._printing_view)
        self._stack.addWidget(self._ticket_view)
        self._stack.addWidget(self._trap_view)

        self._cubeable_view_map = {
            Printing: self._printing_view,
            Ticket: self._ticket_view,
            Trap: self._trap_view,
        }

        self._stack.setCurrentWidget(self._blank)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._stack)

        self.setLayout(layout)

        self._cubeable_view.new_cubeable.connect(self._on_new_cubeable)

    def _on_new_cubeable(self, cubeable: Cubeable) -> None:
        if self._latest_cubeable == cubeable:
            return

        self._latest_cubeable = cubeable

        view = self._cubeable_view_map.get(type(cubeable))

        if view is None:
            self._stack.setCurrentWidget(self._blank)

        else:
            self._stack.setCurrentWidget(view)
            view.set_cubeable(cubeable)


class CardTextView(QtWidgets.QWidget):

    def __init__(self, card: t.Optional[Card] = None):
        super().__init__()
        self._card: t.Optional[Card] = card

        self._typeline_label = QtWidgets.QLabel()
        self._mana_cost_label = QtWidgets.QLabel()
        self._oracle_text_box = QtWidgets.QTextEdit()
        self._oracle_text_box.setReadOnly(True)
        self._power_toughness_loyalty_label = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout()

        top_splitter = QtWidgets.QHBoxLayout()

        top_splitter.addWidget(self._typeline_label)
        top_splitter.addWidget(self._mana_cost_label)

        layout.addLayout(top_splitter)
        layout.addWidget(self._oracle_text_box)
        layout.addWidget(self._power_toughness_loyalty_label)

        self.setLayout(layout)

        if self._card is not None:
            self.set_card(card)

    def set_card(self, card: Card) -> None:
        self._card = card
        self._typeline_label.setText(str(card.type_line))
        self._mana_cost_label.setText(str(card.mana_cost))
        self._oracle_text_box.setText(card.oracle_text)
        if card.power_toughness is not None:
            self._power_toughness_loyalty_label.setText(str(card.power_toughness))
            self._power_toughness_loyalty_label.show()
        elif card.loyalty is not None:
            self._power_toughness_loyalty_label.setText(str(card.loyalty))
            self._power_toughness_loyalty_label.show()
        else:
            self._power_toughness_loyalty_label.hide()


class PrintingTextView(QtWidgets.QWidget):

    def __init__(self, printing: t.Optional[Printing] = None):
        super().__init__()
        self._printing: t.Optional[Printing] = printing

        self._name_label = QtWidgets.QLabel()
        self._expansion_label = QtWidgets.QLabel()

        self._card_view = CardTextView()
        self._card_views_tabs = QtWidgets.QTabWidget()

        self._cards_stack = QtWidgets.QStackedWidget()
        self._cards_stack.addWidget(self._card_view)
        self._cards_stack.addWidget(self._card_views_tabs)
        self._cards_stack.setCurrentWidget(self._card_view)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._name_label)
        layout.addWidget(self._expansion_label)
        layout.addWidget(self._cards_stack)

        self.setLayout(layout)

        if self._printing is not None:
            self.set_cubeable(printing)

    def set_cubeable(self, printing: Printing) -> None:
        self._name_label.setText(printing.cardboard.name)
        self._expansion_label.setText(printing.expansion.name)
        if len(printing.cardboard.cards) > 1:
            self._card_views_tabs.clear()
            for card in printing.cardboard.cards:
                self._card_views_tabs.addTab(
                    CardTextView(card),
                    card.name,
                )
            self._cards_stack.setCurrentWidget(self._card_views_tabs)
        else:
            self._card_view.set_card(printing.cardboard.front_card)
            self._cards_stack.setCurrentWidget(self._card_view)


class TicketTextView(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self._ticket: t.Optional[Ticket] = None

        self._name_label = QtWidgets.QLabel()
        self._printings_tabs = QtWidgets.QTabWidget()

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._name_label)
        layout.addWidget(self._printings_tabs)

        self.setLayout(layout)

    def set_cubeable(self, ticket: Ticket) -> None:
        self._name_label.setText(ticket.name)
        self._printings_tabs.clear()
        for printing in sorted(ticket.options, key = lambda p: p.cardboard.name):
            self._printings_tabs.addTab(
                PrintingTextView(printing),
                printing.cardboard.name,
            )


class PrintingTreeItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, printing: Printing, _type: str):
        super().__init__()
        self._printing = printing
        self.setData(0, 0, self._printing.cardboard.name)
        self.setData(1, 0, _type)

    @property
    def printing(self) -> Printing:
        return self._printing


class TrapTextView(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self._trap: t.Optional[Trap] = None

        self._intention_type_label = QtWidgets.QLabel()

        self._node_tree = QtWidgets.QTreeWidget()
        self._node_tree.setColumnCount(2)
        self._node_tree.setHeaderLabels(('name', 'type'))
        self._node_tree.currentItemChanged.connect(self._on_current_item_changed)

        self._printing_view = PrintingTextView()
        self._printing_view.hide()

        layout = QtWidgets.QVBoxLayout()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        splitter.addWidget(self._node_tree)
        splitter.addWidget(self._printing_view)

        layout.addWidget(self._intention_type_label)
        layout.addWidget(splitter)

        self.setLayout(layout)

    def _on_current_item_changed(self, current, previous) -> None:
        if isinstance(current, PrintingTreeItem):
            self._printing_view.set_cubeable(current.printing)
            self._printing_view.show()

    def _span_tree(self, option: t.Union[Printing, PrintingNode], item: t.Any, is_top_level: bool, _type: str) -> None:
        if isinstance(option, Printing):
            _item = PrintingTreeItem(option, _type)

        else:
            _item = QtWidgets.QTreeWidgetItem()
            _item.setData(1, 0, _type)
            _option_type = 'any' if isinstance(option, AnyNode) else 'all'
            _item.setData(0, 0, _option_type)
            for child in option.children:
                self._span_tree(child, _item, False, _option_type)

        if is_top_level:
            item.addTopLevelItem(_item)
        else:
            item.addChild(_item)

    def set_cubeable(self, trap: Trap) -> None:
        self._intention_type_label.setText(trap.intention_type.value)
        self._node_tree.clear()
        self._printing_view.hide()
        _option_type = 'any' if isinstance(trap.node, AnyNode) else 'all'
        for child in trap.node.children:
            self._span_tree(child, self._node_tree, True, _option_type)
        self._node_tree.resizeColumnToContents(0)
        self._node_tree.expandAll()


class TextImageCubeableView(QtWidgets.QWidget):

    def __init__(self, cubeable_view: CubeableView):
        super().__init__()
        self._cubeable_view = cubeable_view

        self._image_view = CubeableImageView(cubeable_view)
        self._text_view = CubeableTextView(cubeable_view)

        layout = QtWidgets.QVBoxLayout()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        splitter.addWidget(self._image_view)
        splitter.addWidget(self._text_view)

        layout.addWidget(splitter)

        self.setLayout(layout)


class CubeableView(QtWidgets.QWidget):
    new_cubeable = QtCore.pyqtSignal(object)

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._view_type_tabs = QtWidgets.QTabWidget()

        self._image_view = CubeableImageView(self)
        self._text_view = CubeableTextView(self)
        self._both_view = TextImageCubeableView(self)

        self._view_type_tabs.addTab(self._image_view, 'image')
        self._view_type_tabs.addTab(self._text_view, 'text')
        self._view_type_tabs.addTab(self._both_view, 'both')
        self._view_type_tabs.setCurrentWidget(self._image_view)

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self._view_type_tabs)

        self.setLayout(layout)
