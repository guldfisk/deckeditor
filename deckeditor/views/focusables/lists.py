from __future__ import annotations

import typing as t

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtSignal, QModelIndex

from deckeditor.components.cardview.cubeableview import F
from deckeditor.components.cardview.focuscard import FocusEvent
from deckeditor.context.context import Context
from deckeditor.models.sequence import GenericItemSequence


class FocusableListSelector(t.Generic[F], QtWidgets.QListView):
    model: t.Callable[[], GenericItemSequence[F]]

    focusable_selected = pyqtSignal(object)
    current_focusable_changed = pyqtSignal(object)

    def currentChanged(self, top_left: QModelIndex, bottom_right: QModelIndex) -> None:
        current_index = self.currentIndex()

        if current_index is None:
            return

        focusable = self.model().get_item(current_index)

        if focusable is None:
            return

        self.scrollTo(current_index)
        Context.focus_card_changed.emit(FocusEvent(focusable))
        self.current_focusable_changed.emit(focusable)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() in (
            QtCore.Qt.Key_Right,
            QtCore.Qt.Key_Enter,
            QtCore.Qt.Key_Return,
        ):
            current_index = self.currentIndex()

            if current_index is None:
                return

            cardboard = self.model().get_item(current_index)

            if cardboard is None:
                return

            self.focusable_selected.emit(cardboard)
        else:
            super().keyPressEvent(key_event)

