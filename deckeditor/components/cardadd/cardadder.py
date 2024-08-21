from __future__ import annotations

import typing as t

from magiccube.collections.delta import CubeDeltaOperation
from mtgimg.interface import SizeSlug
from mtgorp.models.interfaces import Cardboard, Printing
from mtgorp.tools.parsing.exceptions import ParseException
from mtgorp.tools.search.extraction import PrintingStrategy
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QCompleter, QInputDialog

from deckeditor.application.embargo import EmbargoApp
from deckeditor.context.context import Context
from deckeditor.models.focusables.lists import CardboardList, ExpansionPrintingList
from deckeditor.views.focusables.multi import FocusableMultiView


class QueryEditor(QtWidgets.QLineEdit):
    new_search = pyqtSignal(str)

    def __init__(self):
        super().__init__()
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
            self.new_search.emit(self.text())
        else:
            super().keyPressEvent(key_event)


class CardSelector(QtWidgets.QWidget):
    def __init__(
        self,
        parent: t.Optional[QtWidgets.QWidget] = None,
        *,
        cardboard_image_size: SizeSlug = SizeSlug.THUMBNAIL,
    ):
        super().__init__(parent)

        self._search_button = QtWidgets.QPushButton("Search", self)

        self._cardboards = CardboardList()
        self._cardboard_selector = FocusableMultiView(image_size=cardboard_image_size)
        self._cardboard_selector.set_model(self._cardboards)

        self._query_editor = QueryEditor()
        self._query_editor.new_search.connect(self._search)
        self.setFocusProxy(self._query_editor)

        self._top_bar = QtWidgets.QHBoxLayout()

        self._layout = QtWidgets.QVBoxLayout(self)

        self._top_bar.addWidget(self._query_editor)
        self._top_bar.addWidget(self._search_button)

        self._layout.addLayout(self._top_bar)

        self._search_button.clicked.connect(lambda _: self._search(self._query_editor.text()))

    @property
    def query_edit(self) -> QueryEditor:
        return self._query_editor

    def _search(self, query: str) -> None:
        try:
            pattern = Context.search_pattern_parser.parse(query)
        except ParseException as e:
            Context.notification_message.emit(f"Invalid search query {e}")
            return

        self._cardboards.set_items(list(pattern.matches(Context.db.cardboards.values())))
        self._cardboard_selector.refocus()

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Escape:
            self.parent().hide()

        else:
            super().keyPressEvent(key_event)


class CardboardSelector(CardSelector):
    cardboard_selected = pyqtSignal(Cardboard)
    current_cardboard_changed = pyqtSignal(Cardboard)

    def __init__(self, parent: t.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)

        self._layout.addWidget(self._cardboard_selector)
        self._cardboard_selector.focusable_selected.connect(self.cardboard_selected)
        self._cardboard_selector.current_focusable_changed.connect(self.current_cardboard_changed)


class PrintingSelector(CardSelector):
    add_printings = pyqtSignal(CubeDeltaOperation)

    def __init__(
        self,
        parent: t.Optional[QtWidgets.QWidget] = None,
        *,
        cardboard_image_size: SizeSlug = SizeSlug.THUMBNAIL,
        printing_image_size: SizeSlug = SizeSlug.SMALL,
    ):
        super().__init__(parent, cardboard_image_size=cardboard_image_size)

        self._cardboard_selector.current_focusable_changed.connect(self._on_cardboard_changed)

        self._printing_list_selector = FocusableMultiView(image_size=printing_image_size)
        self._printings = ExpansionPrintingList()
        self._printing_list_selector.set_model(self._printings)
        self._printing_list_selector.focusable_selected.connect(self._on_printing_selected)

        self._cardboard_selector.focusable_selected.connect(self._on_cardboard_selected)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        splitter.addWidget(self._cardboard_selector)
        splitter.addWidget(self._printing_list_selector)

        self._layout.addWidget(splitter)

    def _on_printing_selected(self, printing: Printing) -> None:
        modifiers = EmbargoApp.current.keyboardModifiers()
        if modifiers & QtCore.Qt.ControlModifier:
            amount, ok = QInputDialog.getInt(
                self,
                "Choose printing amount",
                "",
                4,
                1,
                99,
            )
            if not ok:
                amount = 0
        else:
            amount = 4 if modifiers & QtCore.Qt.ShiftModifier else 1
        if amount:
            self.add_printings.emit(CubeDeltaOperation({printing: amount}))

    def _on_cardboard_changed(self, cardboard: Cardboard) -> None:
        printings = cardboard.printings_chronologically
        if self._query_editor.text():
            try:
                printings = Context.search_pattern_parser.parse(
                    self._query_editor.text(),
                    strategy=PrintingStrategy,
                ).matches(printings)
            except ParseException:
                pass

        self._printings.set_items(list(printings))

    def _on_cardboard_selected(self, cardboard: Cardboard) -> None:
        self._printing_list_selector.refocus()
