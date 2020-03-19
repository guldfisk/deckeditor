from __future__ import annotations

import typing as t

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene


class SelectionScene(QGraphicsScene):
    selection_cleared = QtCore.pyqtSignal(QGraphicsScene)

    def remove_selected(self, items: t.Iterable[QGraphicsItem]):
        for item in items:
            item.setSelected(False)

    def clear_selection(self, propagate: bool = True):
        if propagate:
            self.selection_cleared.emit(self)
        self.remove_selected(self.selectedItems())

    def add_selection(
        self,
        items: t.Iterable[QGraphicsItem],
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,
    ):
        if modifiers == Qt.AltModifier:
            for item in items:
                item.setSelected(False)
        elif modifiers == Qt.AltModifier | Qt.ShiftModifier:
            items = set(items)
            for item in self.selectedItems():
                item.setSelected(item in items)
        else:
            for item in items:
                item.setSelected(True)

    def set_selection(
        self,
        items: t.Iterable[QGraphicsItem],
        modifiers: Qt.KeyboardModifiers = Qt.NoModifier,
    ):
        if modifiers == Qt.AltModifier:
            for item in items:
                item.setSelected(False)
        elif modifiers == Qt.ShiftModifier:
            for item in items:
                item.setSelected(True)
        elif modifiers == Qt.AltModifier | Qt.ShiftModifier:
            items = set(items)
            for item in self.selectedItems():
                item.setSelected(item in items)
        else:
            self.clear_selection()
            for item in items:
                item.setSelected(True)

    def select_all(self):
        for item in self.items():
            item.setSelected(True)
        self.selection_cleared.emit(self)
