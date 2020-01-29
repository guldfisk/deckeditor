from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter, QInputDialog

from mtgorp.models.persistent.printing import Printing
from mtgorp.models.persistent.cardboard import Cardboard
from mtgorp.tools.parsing.exceptions import ParseException

from magiccube.collections.delta import CubeDeltaOperation

from deckeditor.context.context import Context
from deckeditor.notifications.notifyable import Notifyable
from deckeditor.components.cardview.cubeableview import CubeableView
from deckeditor.values import DeckZoneType


class CardAddable(object):

    def add_printings(self, target: DeckZoneType, printings: t.Iterable[Printing]):
        pass


class TargetSelector(QtWidgets.QComboBox):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        for target in DeckZoneType:
            self.addItem(target.name)


class QueryEditor(QtWidgets.QLineEdit):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        completer = QCompleter(
            Context.db.cardboards.keys()
        )
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchStartsWith)
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


# class QuantitySelectDialog(QtWidgets.QDialog):
#
#     def __init__(self, parent: PrintingList):
#         super().__init__(parent)
#
#         self._query_edit = QueryEdit(self)
#
#         self._error_label = QtWidgets.QLabel()
#         self._error_label.hide()
#
#         self._box = QtWidgets.QVBoxLayout()
#
#         self._box.addWidget(self._query_edit)
#         self._box.addWidget(self._error_label)
#
#         self.setLayout(self._box)
#
#     def compile(self):
#         try:
#             self.parent().search_select.emit(
#                 Context.search_pattern_parser.parse_criteria(
#                     self._query_edit.text()
#                 )
#             )
#             self.accept()
#         except ParseException as e:
#             self._error_label.setText(str(e))
#             self._error_label.show()
#             return


class PrintingList(QtWidgets.QListWidget):

    def __init__(
        self,
        card_adder: CardAdder,
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
                current.printing
            )
            self.scrollTo(self.currentIndex())

    def _add_printings(self, amount: int) -> None:
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

        else:
            super().keyPressEvent(key_event)

    def set_printings(self, printings: t.Iterable[Printing]) -> None:
        _printings = sorted(printings, key = lambda _printing: _printing.expansion.code)
        self.clear()
        for idx, printing in enumerate(_printings):
            self.addItem(
                PrintingItem(printing)
            )


class CardboardList(QtWidgets.QListWidget):

    def __init__(
        self,
        printing_list: PrintingList,
        parent: QtWidgets.QWidget,
    ):
        super().__init__(parent)
        self._printing_list = printing_list

        self._item_model = QtGui.QStandardItemModel(parent)

    def currentChanged(self, index, _index):
        current = self.currentItem()

        if current is not None:
            self._printing_list.set_printings(current.cardboard.printings)
            self._printing_list.setCurrentIndex(self._printing_list.model().index(0, 0))
            self.scrollTo(self.currentIndex())
            Context.focus_card_changed.emit(
                current.cardboard.latest_printing
            )

    def _select_cardboard(self):
        self._printing_list.setFocus()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self._select_cardboard()
        else:
            super().keyPressEvent(key_event)

    def set_cardboards(self, cardboards: t.Iterable[Cardboard]):
        _cardboards = sorted(cardboards, key = lambda _cardboard: _cardboard.name)
        self.clear()
        for cardboard in _cardboards:
            self.addItem(
                CardboardItem(cardboard)
            )


class CardboardItem(QtWidgets.QListWidgetItem):

    def __init__(self, cardboard: Cardboard):
        super().__init__()
        self._cardboard = cardboard
        self.setText(cardboard.name)

    @property
    def cardboard(self) -> Cardboard:
        return self._cardboard


class PrintingItem(QtWidgets.QListWidgetItem):

    def __init__(self, printing: Printing):
        super().__init__()
        self._printing = printing
        self.setText(f'{printing.expansion.name} - {printing.expansion.code}')

    @property
    def printing(self) -> Printing:
        return self._printing


class CardAdder(QtWidgets.QWidget):
    add_printings = QtCore.pyqtSignal(CubeDeltaOperation)

    def __init__(
        self,
        notifyable: Notifyable,
        parent: QtWidgets.QWidget,
    ):
        super().__init__(parent)

        self._notifyable = notifyable

        self._search_button = QtWidgets.QPushButton(self)
        self._target_selector = TargetSelector(self)
        self._printing_list = PrintingList(
            card_adder = self,
            target_selector = self._target_selector,
        )
        self._cardboard_list = CardboardList(
            self._printing_list,
            self,
        )
        self._query_edit = QueryEditor(self)

        self._search_button.setText('Search')

        self._top_bar = QtWidgets.QHBoxLayout()
        self._bottom_bar = QtWidgets.QHBoxLayout()
        self._right_panel = QtWidgets.QVBoxLayout()
        self._layout = QtWidgets.QVBoxLayout()

        self._top_bar.addWidget(self._query_edit)
        self._top_bar.addWidget(self._search_button)

        self._right_panel.addWidget(self._target_selector)
        self._right_panel.addWidget(self._printing_list)

        self._bottom_bar.addWidget(self._cardboard_list)
        self._bottom_bar.addLayout(self._right_panel)

        self._layout.addLayout(self._top_bar)
        self._layout.addLayout(self._bottom_bar)

        self._search_button.clicked.connect(self.initiate_search)

        self.setLayout(self._layout)

        self.setTabOrder(self._printing_list, self._cardboard_list)

    @property
    def query_edit(self) -> QueryEditor:
        return self._query_edit

    def initiate_search(self):
        self._search(self._query_edit.text())
        self._cardboard_list.setCurrentIndex(self._cardboard_list.model().index(0, 0))
        self._cardboard_list.setFocus()

    def _search(self, s: str) -> None:
        try:
            pattern = Context.search_pattern_parser.parse(s)
        except ParseException as e:
            self._notifyable.notify(f'Invalid search query {e}')
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
