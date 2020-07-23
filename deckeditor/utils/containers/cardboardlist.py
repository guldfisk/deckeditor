from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QPoint, QModelIndex

from mtgorp.models.persistent.cardboard import Cardboard

from deckeditor.components.cardview.focuscard import CubeableFocusEvent
from deckeditor.context.context import Context


class CardboardItem(QtWidgets.QListWidgetItem):

    def __init__(self, cardboard: Cardboard):
        super().__init__()
        self._cardboard = cardboard
        self.setText(cardboard.name)

    @property
    def cardboard(self) -> Cardboard:
        return self._cardboard


class CardboardList(QtWidgets.QListWidget):
    currentItem: t.Callable[[], t.Optional[CardboardItem]]
    itemAt: t.Callable[[QPoint], t.Optional[CardboardItem]]

    item_selected = QtCore.pyqtSignal(CardboardItem)

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        item = self.itemAt(e.pos())
        if item:
            self.item_selected.emit(item)

    def on_current_changes(self, current: CardboardItem) -> None:
        pass

    def currentChanged(self, top_left: QModelIndex, bottom_right: QModelIndex) -> None:
        current = self.currentItem()

        if current is not None:
            self.scrollTo(self.currentIndex())
            Context.focus_card_changed.emit(CubeableFocusEvent(current.cardboard.latest_printing))
            self.on_current_changes(current)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() == QtCore.Qt.Key_Enter or key_event.key() == QtCore.Qt.Key_Return:
            self.item_selected.emit(self.currentItem())
        else:
            super().keyPressEvent(key_event)

    def set_cardboards(self, cardboards: t.Iterable[Cardboard]):
        self.clear()
        for cardboard in sorted(cardboards, key = lambda _cardboard: _cardboard.name):
            self.addItem(
                CardboardItem(cardboard)
            )
