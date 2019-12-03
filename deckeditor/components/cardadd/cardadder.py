import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter

from deckeditor.undo.command.commands import ModifyCubeModel
from magiccube.collections.delta import CubeDeltaOperation
from mtgorp.models.persistent.printing import Printing
from mtgorp.models.persistent.cardboard import Cardboard
from mtgorp.tools.parsing.exceptions import ParseException
from mtgorp.tools.parsing.search.parse import SearchPatternParseException

from mtgimg.interface import ImageRequest

from deckeditor.context.context import Context
from deckeditor.notifications.notifyable import Notifyable
from deckeditor.components.cardview.widget import CardViewWidget
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
        completer.setFilterMode(Qt.MatchContains)
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


class PrintingList(QtWidgets.QListView):

    def __init__(
        self,
        addable: CardAddable,
        target_selector: TargetSelector,
        amounter: QtWidgets.QLineEdit,
        parent: QtWidgets.QWidget,
    ):
        super().__init__(parent)

        self._addable = addable
        self._target_selector = target_selector
        self._amounter = amounter

        self._item_model = QtGui.QStandardItemModel(parent)
        self.setModel(self._item_model)

    def currentChanged(self, index, _index):
        current = self.model().item(self.currentIndex().row())

        if current is not None:
            Context.focus_card_changed.emit(
                current.printing
            )
            self.scrollTo(self.currentIndex())

    def _add_printings(self) -> None:
        Context.undo_group.activeStack().push(
            ModifyCubeModel(
                #TODO get current cube model.
                CubeDeltaOperation(
                    {
                        self.model().item(self.currentIndex().row().printing): int(self._amounter.text())
                    }
                )
            )
        )
        # self._addable.add_printings(
        #     DeckZoneType[self._target_selector.currentText()],
        #     [self.model().item(self.currentIndex().row()).cubeable] * int(self._amounter.text()),
        # )

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self._add_printings()
        else:
            super().keyPressEvent(key_event)

    def set_printings(self, printings: t.Iterable[Printing]) -> None:
        _printings = sorted(printings, key = lambda _printing: _printing.expansion.code)
        self.model().clear()
        for printing in _printings:
            item = PrintingItem(printing)
            self.model().appendRow(item)


class CardboardList(QtWidgets.QListView):

    def __init__(
        self,
        printing_list: PrintingList,
        parent: QtWidgets.QWidget,
    ):
        super().__init__(parent)
        self._printing_list = printing_list

        self._item_model = QtGui.QStandardItemModel(parent)
        self.setModel(self._item_model)

    def currentChanged(self, index, _index):
        current = self.model().item(self.currentIndex().row())

        if current is not None:
            self._printing_list.set_printings(current.cardboard.printings)
            self._printing_list.setCurrentIndex(self._printing_list.model().index(0, 0))
            self.scrollTo(self.currentIndex())

    def _select_cardboard(self):
        self._printing_list.setFocus()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self._select_cardboard()
        else:
            super().keyPressEvent(key_event)

    def set_cardboards(self, cardboards: t.Iterable[Cardboard]):
        _cardboards = sorted(cardboards, key = lambda _cardboard: _cardboard.name)
        self.model().clear()
        for cardboard in _cardboards:
            item = CardboardItem(cardboard)
            self.model().appendRow(item)


class CardboardItem(QtGui.QStandardItem):

    def __init__(self, cardboard: Cardboard):
        super().__init__()
        self._cardboard = cardboard
        self.setText(cardboard.name)

    @property
    def cardboard(self) -> Cardboard:
        return self._cardboard


class PrintingItem(QtGui.QStandardItem):

    def __init__(self, printing: Printing):
        super().__init__()
        self._printing = printing
        self.setText(f'{printing.expansion.name} - {printing.expansion.code}')

    @property
    def printing(self) -> Printing:
        return self._printing


class CardAdder(QtWidgets.QWidget):

    def __init__(
        self,
        addable: CardAddable,
        notifyable: Notifyable,
        card_view: CardViewWidget,
        parent: QtWidgets.QWidget,
    ):
        super().__init__(parent)

        self._addable = addable
        self._notifyable = notifyable
        self._card_view = card_view

        self._search_button = QtWidgets.QPushButton(self)
        self._target_selector = TargetSelector(self)
        self._amounter = QtWidgets.QLineEdit(self)
        self._amount_label = QtWidgets.QLabel(self)
        self._printing_list = PrintingList(
            addable = self._addable,
            target_selector = self._target_selector,
            amounter = self._amounter,
            parent = self,
        )
        self._cardboard_list = CardboardList(
            self._printing_list,
            self,
        )
        self._query_edit = QueryEditor(self)

        self.setTabOrder(self._printing_list, self._cardboard_list)

        self._amount_label.setText('Amount:')

        self._amounter.setValidator(QtGui.QIntValidator(1, 99, self))
        self._amounter.setMaximumWidth(50)
        self._amounter.setText('1')

        self._search_button.setText('Search')

        self._top_bar = QtWidgets.QHBoxLayout()
        self._bottom_bar = QtWidgets.QHBoxLayout()
        self._right_panel = QtWidgets.QVBoxLayout()
        self._amount_bar = QtWidgets.QHBoxLayout()
        self._layout = QtWidgets.QVBoxLayout()

        self._top_bar.addWidget(self._query_edit)
        self._top_bar.addWidget(self._search_button)

        self._amount_bar.addWidget(self._amount_label, alignment = QtCore.Qt.AlignLeft)
        self._amount_bar.addWidget(self._amounter, alignment = QtCore.Qt.AlignLeft)
        self._amount_bar.addStretch(1)

        self._right_panel.addWidget(self._target_selector)
        self._right_panel.addWidget(self._printing_list)
        self._right_panel.addLayout(self._amount_bar)

        self._bottom_bar.addWidget(self._cardboard_list)
        self._bottom_bar.addLayout(self._right_panel)

        self._layout.addLayout(self._top_bar)
        self._layout.addLayout(self._bottom_bar)

        self._search_button.clicked.connect(self.initiate_search)

        self.setLayout(self._layout)

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
