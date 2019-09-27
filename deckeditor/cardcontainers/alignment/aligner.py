import typing as t
from abc import abstractmethod
from enum import Enum

from PyQt5 import QtCore

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug

from deckeditor.cardcontainers.alignment.cursor import Cursor
from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.cardcontainers.selection import SelectionScene
from deckeditor.undo.command import UndoCommand, UndoStack
from deckeditor.values import SortProperty, Direction


IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.ORIGINAL, False))]


class AttachmentChange(UndoCommand):
	pass


class AlignDetach(AttachmentChange):

	def expecting(self) -> t.Tuple[t.Type['AlignAttach'], t.Type['AlignRemove']]:
		return AlignAttach, AlignRemove


class AlignAttach(AttachmentChange):

	def merge(self, command: 'UndoCommand') -> bool:
		return isinstance(command, AlignRemove)


class AlignRemove(AttachmentChange):
	pass


class AlignSort(AttachmentChange):
	pass


class CardScene(SelectionScene):
	cards_changed = QtCore.pyqtSignal(SelectionScene)
	cursor_moved = QtCore.pyqtSignal(QtCore.QPointF)

	def __init__(
		self,
		aligner_type: t.Type['Aligner'],
		undo_stack: UndoStack,
	):
		super().__init__()
		self._undo_stack = undo_stack

		self.setSceneRect(0, 0, IMAGE_WIDTH * 12, IMAGE_HEIGHT * 8)

		self._cursor = Cursor()

		self.addItem(self._cursor)

		self._cursor.setZValue(3)

		self._aligner = None
		self.aligner = aligner_type(self, undo_stack)

	@property
	def aligner(self) -> 'Aligner':
		return self._aligner

	@aligner.setter
	def aligner(self, aligner: 'Aligner') -> None:
		self._aligner = aligner
		self._aligner.cursor_moved.connect(lambda pos: self.cursor_moved.emit(pos))

	@property
	def cursor(self) -> Cursor:
		return self._cursor

	@property
	def undo_stack(self) -> UndoStack:
		return self._undo_stack

	@property
	def cards(self) -> t.Iterable[PhysicalCard]:
		return (item for item in self.items() if isinstance(item, PhysicalCard))

	def add_cards(self, *cards: PhysicalCard) -> None:
		for card in cards:
			self.addItem(card)

		self.cards_changed.emit(self)

	def remove_cards(self, *cards: PhysicalCard):
		for card in cards:
			self.removeItem(card)

		self.cards_changed.emit(self)

	def add_select_if(self, criteria: t.Callable[[PhysicalCard], bool]):
		self.add_selection(
			item for item in self.items() if isinstance(item, PhysicalCard) and criteria(item)
		)


class Aligner(QtCore.QObject):
	cursor_moved = QtCore.pyqtSignal(QtCore.QPointF)

	def __init__(self, scene: CardScene, undo_stack: UndoStack):
		super().__init__()
		self._scene = scene
		self._undo_stack = undo_stack

	@property
	def scene(self) -> CardScene:
		return self._scene

	@abstractmethod
	def attach_cards(
		self,
		cards: t.Iterable[PhysicalCard],
		position: t.Optional[QtCore.QPointF] = None
	) -> AlignAttach:
		pass

	@abstractmethod
	def detach_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignDetach:
		pass

	@abstractmethod
	def remove_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignRemove:
		pass

	@abstractmethod
	def move_cursor(self, direction: Direction, modifiers: int = 0):
		pass

	@abstractmethod
	def sort(self, sort_property: SortProperty, orientation: int) -> AlignSort:
		pass