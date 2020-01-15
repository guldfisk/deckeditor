
import typing as t

from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene


class SelectionScene(QGraphicsScene):

    def remove_selected(self, items: t.Iterable[QGraphicsItem]):
        for item in items:
            item.setSelected(False)

    def clear_selection(self):
        self.remove_selected(self.selectedItems())

    def add_selection(self, items: t.Iterable[QGraphicsItem]):
        for item in items:
            item.setSelected(True)

    def set_selection(self, item: t.Iterable[QGraphicsItem]):
        self.clear_selection()
        self.add_selection(item)

    def select_all(self):
        for item in self.items():
            item.setSelected(True)
