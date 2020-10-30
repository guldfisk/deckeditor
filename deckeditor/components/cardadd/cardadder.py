from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter, QInputDialog

from mtgorp.models.interfaces import Printing, Cardboard
from mtgorp.tools.parsing.exceptions import ParseException
from mtgorp.tools.search.extraction import PrintingStrategy

from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.context.context import Context
from deckeditor.values import DeckZoneType
from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.utils.containers.cardboardlist import CardboardList, CardboardItem


class TargetSelector(QtWidgets.QComboBox):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        for target in DeckZoneType:
            self.addItem(target.name)


class QueryEditor(QtWidgets.QLineEdit):

    def __init__(self, parent: CardSelector):
        super().__init__(parent)
        completer = QCompleter(Context.cardboard_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchStartsWith)
        completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        completer.setCompletionMode(QCompleter.InlineCompletion)
        self.setCompleter(completer)

    def focusInEvent(self, focus_event: QtGui.QFocusEvent):
        super().focusInEvent(focus_event)
        self.selectAll()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self.parent().initiate_search()
        else:
            super().keyPressEvent(key_event)


class PrintingList(QtWidgets.QListWidget):

    def __init__(
        self,
        card_adder: PrintingSelector,
        target_selector: TargetSelector,
    ):
        super().__init__()
        self._card_adder = card_adder
        self._target_selector = target_selector
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def currentChanged(self, index, _index):
        current = self.currentItem()

        if current is not None:
            Context.focus_card_changed.emit(
                CubeableFocusEvent(current.printing)
            )
            self.scrollTo(self.currentIndex())

    def _add_printings(self, amount: int) -> None:
        if not self.currentItem():
            return
        self._card_adder.add_printings.emit(
            CubeDeltaOperation(
                {
                    self.currentItem().printing: amount
                }
            )
        )

    def _on_item_double_clicked(self, item: PrintingItem) -> None:
        self._card_adder.add_printings.emit(
            CubeDeltaOperation(
                {
                    item.printing: 1,
                }
            )
        )

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        modifiers = key_event.modifiers()

        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            if modifiers & QtCore.Qt.ControlModifier:
                amount, ok = QInputDialog.getInt(
                    self,
                    'Choose printing amount',
                    '',
                    4,
                    1,
                    99,
                )
                if not ok:
                    amount = 0
            else:
                amount = 4 if modifiers & QtCore.Qt.ShiftModifier else 1
            if amount:
                self._add_printings(amount)

        elif key_event.key() == QtCore.Qt.Key_Left:
            self._card_adder.cardboard_list.setFocus()

        else:
            super().keyPressEvent(key_event)

    def set_printings(self, printings: t.Iterable[Printing]) -> None:
        _printings = sorted(printings, key = lambda _printing: _printing.expansion.code)
        self.clear()
        for idx, printing in enumerate(_printings):
            self.addItem(
                PrintingItem(printing)
            )


class AddCardboardList(CardboardList):

    def __init__(
        self,
        query_editor: QueryEditor,
        printing_list: t.Optional[PrintingList] = None,
    ):
        super().__init__()
        self._printing_list = printing_list
        self._query_editor = query_editor

        self._item_model = QtGui.QStandardItemModel(self)
        self.item_selected.connect(self._on_item_selected)

    def on_current_changes(self, current: CardboardItem) -> None:
        if self._printing_list is not None:
            printings = current.cardboard.printings
            if self._query_editor.text():
                try:
                    printings = Context.search_pattern_parser.parse(
                        self._query_editor.text(),
                        strategy = PrintingStrategy,
                    ).matches(printings)
                except ParseException:
                    pass

            self._printing_list.set_printings(printings)
            self._printing_list.setCurrentIndex(self._printing_list.model().index(0, 0))

    def _on_item_selected(self, item: CardboardItem) -> None:
        if self._printing_list is not None:
            self._printing_list.setFocus()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Right:
            self.item_selected.emit(self.currentItem())
        else:
            super().keyPressEvent(key_event)


class PrintingItem(QtWidgets.QListWidgetItem):

    def __init__(self, printing: Printing):
        super().__init__()
        self._printing = printing
        self.setText(f'{printing.expansion.name} - {printing.expansion.code}')

    @property
    def printing(self) -> Printing:
        return self._printing


class CardSelector(QtWidgets.QWidget):
    _cardboard_list: AddCardboardList

    cardboard_selected = QtCore.pyqtSignal(Cardboard)

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._search_button = QtWidgets.QPushButton('Search', self)

        self._query_edit = QueryEditor(self)
        self.setFocusProxy(self._query_edit)

        self._top_bar = QtWidgets.QHBoxLayout()
        self._bottom_bar = QtWidgets.QHBoxLayout()
        self._layout = QtWidgets.QVBoxLayout()

        self._top_bar.addWidget(self._query_edit)
        self._top_bar.addWidget(self._search_button)

        self._layout.addLayout(self._top_bar)
        self._layout.addLayout(self._bottom_bar)

        self._search_button.clicked.connect(self.initiate_search)

        self.setLayout(self._layout)

    def initiate_search(self):
        self._search(self._query_edit.text())
        self._cardboard_list.setCurrentIndex(self._cardboard_list.model().index(0, 0))
        self._cardboard_list.setFocus()

    @property
    def query_edit(self) -> QueryEditor:
        return self._query_edit

    def _search(self, s: str) -> None:
        try:
            pattern = Context.search_pattern_parser.parse(s)
        except ParseException as e:
            Context.notification_message.emit(f'Invalid search query {e}')
            return

        self._cardboard_list.set_cardboards(
            pattern.matches(
                Context.db.cardboards.values()
            )
        )

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Escape:
            self.parent().hide()

        else:
            super().keyPressEvent(key_event)


class CardboardSelector(CardSelector):

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._cardboard_list = AddCardboardList(
            self._query_edit,
        )
        self._cardboard_list.item_selected.connect(lambda i: self.cardboard_selected.emit(i.cardboard))

        self._bottom_bar.addWidget(self._cardboard_list)


class PrintingSelector(CardSelector):
    add_printings = QtCore.pyqtSignal(CubeDeltaOperation)

    def __init__(
        self,
        parent: QtWidgets.QWidget,
    ):
        super().__init__(parent)

        self._target_selector = TargetSelector(self)

        self._printing_list = PrintingList(
            card_adder = self,
            target_selector = self._target_selector,
        )

        self._cardboard_list = AddCardboardList(
            self._query_edit,
            self._printing_list,
        )
        self._cardboard_list.item_selected.connect(lambda i: self.cardboard_selected.emit(i.cardboard))

        self._right_panel = QtWidgets.QVBoxLayout()

        self._right_panel.addWidget(self._printing_list)
        self._right_panel.addWidget(self._target_selector)

        self._bottom_bar.addWidget(self._cardboard_list)
        self._bottom_bar.addLayout(self._right_panel)

    @property
    def cardboard_list(self) -> AddCardboardList:
        return self._cardboard_list