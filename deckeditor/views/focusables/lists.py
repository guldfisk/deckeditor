from __future__ import annotations

import typing as t

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QModelIndex, pyqtSignal

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

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        focusable = self.model().get_item(self.indexAt(e.pos()))

        if focusable is None:
            return

        self.focusable_selected.emit(focusable)

    def keyPressEvent(self, key_event: QtGui.QKeyEvent):
        if key_event.key() in (
            QtCore.Qt.Key_Right,
            QtCore.Qt.Key_Enter,
            QtCore.Qt.Key_Return,
        ):
            current_index = self.currentIndex()

            if current_index is None:
                return

            focusable = self.model().get_item(current_index)

            if focusable is None:
                return

            self.focusable_selected.emit(focusable)
        else:
            super().keyPressEvent(key_event)
