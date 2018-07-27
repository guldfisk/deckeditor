
import typing as t

from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene

# class SelectionChange(UndoCommand):
# 	pass
#
#
# class SetSelected(SelectionChange):
#
# 	def __init__(self, scene: 'CardScene', cards: t.Iterable[PhysicalCard]):
# 		self._cards = list(cards)
# 		self._previous = list(scene.selectedItems())
#
# 	def redo(self) -> None:
# 		for card in self._previous:
# 			card.setSelected(False)
#
# 		for card in self._cards:
# 			card.setSelected(True)
#
# 	def undo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(False)
#
# 		for card in self._previous:
# 			card.setSelected(True)
#
# 	def ignore(self) -> bool:
# 		return not (self._cards or self._previous)
#
#
# class AddSelected(SelectionChange):
#
# 	def __init__(self, cards: t.Iterable[PhysicalCard]):
# 		self._cards = list(
# 			card
# 			for card in
# 			cards
# 			if not card.isSelected()
# 		)
#
# 	def redo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(True)
#
# 	def undo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(False)
#
# 	def ignore(self) -> bool:
# 		return not self._cards
#
#
# class Deselect(SelectionChange):
#
# 	def __init__(self, cards: t.Iterable[PhysicalCard]):
# 		self._cards = list(
# 			card
# 			for card in
# 			cards
# 			if card.isSelected()
# 		)
#
# 	def redo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(False)
#
# 	def undo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(True)
#
# 	def ignore(self) -> bool:
# 		return not self._cards
#
#
# class PositiveSelectionIntersection(SelectionChange):
#
# 	def __init__(self, scene: 'CardScene', cards: t.Iterable[PhysicalCard]):
# 		_cards = set(cards)
# 		self._cards = list(
# 			card
# 			for card in
# 			scene.selectedItems()
# 			if not card in _cards
# 		)
#
# 	def redo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(False)
#
# 	def undo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(True)
#
# 	def ignore(self) -> bool:
# 		return not self._cards
#
#
# class NegativeSelectionIntersection(SelectionChange):
#
# 	def __init__(self, scene: 'CardScene', cards: t.Iterable[PhysicalCard]):
# 		_cards = set(cards)
# 		self._cards = list(
# 			card
# 			for card in
# 			scene.selectedItems()
# 			if card in _cards
# 		)
#
# 	def redo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(False)
#
# 	def undo(self) -> None:
# 		for card in self._cards:
# 			card.setSelected(True)
#
# 	def ignore(self) -> bool:
# 		return not self._cards
#
#
# class ClearSelection(SelectionChange):
#
# 	def __init__(self, scene: 'CardScene'):
# 		self._scene = scene
# 		self._deselected = scene.selectedItems()
#
# 	def redo(self) -> None:
# 		self._scene.clearSelection()
#
# 	def undo(self) -> None:
# 		for card in self._deselected:
# 			card.setSelected(True)
#
# 	def ignore(self) -> bool:
# 		return not self._deselected


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
