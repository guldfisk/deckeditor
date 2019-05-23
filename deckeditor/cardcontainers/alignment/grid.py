import typing as t

from abc import abstractmethod

from PyQt5 import QtCore

from mtgorp.models.persistent.attributes import typeline
from mtgorp.models.persistent.attributes import colors

from mtgimg.load import IMAGE_HEIGHT, IMAGE_WIDTH

from deckeditor.undo.command import UndoStack, UndoCommand
from deckeditor.values import SortProperty
from deckeditor.cardcontainers.alignment.aligner import (
	Aligner,
	AlignRemove,
	AlignAttach,
	AlignDetach,
	CardScene,
	AlignSort,
	Direction,
)
from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.context.context import Context


class GridDetach(AlignDetach):

	def __init__(self, grid: 'GridAligner', cards: t.Iterable[PhysicalCard]):
		self._grid = grid
		self._cards = cards
		self._indexes = None  # type: t.List[t.Tuple[int, PhysicalCard]]

	def _indexed(self, cards: t.Iterable[PhysicalCard]) -> t.Iterator[t.Tuple[int, PhysicalCard]]:
		for card in cards:
			try:
				yield self._grid.cards.index(card), card
			except ValueError:
				pass

	def setup(self):
		self._indexes = sorted(
			self._indexed(self._cards),
			key=lambda v: v[0],
		)

	def redo(self) -> None:
		self._grid.unalign_cards(card for index, card in self._indexes)
		self._grid.re_position(self._indexes[0][0])

	def undo(self) -> None:
		for index, card in self._indexes:
			self._grid.insert_card(index, card)

		self._grid.re_position(self._indexes[0][0])

	def ignore(self) -> bool:
		return not self._cards


class GridRemove(AlignRemove):

	def __init__(self, grid: 'GridAligner', cards: t.Iterable[PhysicalCard]):
		self._grid = grid
		self._cards = list(cards)

	def redo(self) -> None:
		self._grid.scene.remove_cards(*self._cards)

	def undo(self) -> None:
		self._grid.scene.add_cards(*self._cards)

	def ignore(self) -> bool:
		return not self._cards


class GridAttach(AlignAttach):

	def __init__(self, grid: 'GridAligner', cards: t.Iterable[PhysicalCard], position: QtCore.QPointF):
		super().__init__()
		self._grid = grid
		self._cards = list(cards)
		self._position = position
		self._index = None #type: int

	def setup(self):
		self._index = self._grid.index_at_position(self._position)

	def redo(self) -> None:
		for card in reversed(self._cards):
			if not card.scene() == self._grid.scene:
				self._grid.scene.add_cards(card)

			self._grid.insert_card(self._index, card)

		self._grid.re_position(self._index)

	def undo(self) -> None:
		self._grid.unalign_cards(self._cards)
		self._grid.re_position(self._index)

	def ignore(self) -> bool:
		return not self._cards


# class GridMove(UndoCommand):
#
# 	def __init__(self, grid: 'GridAligner', cards: t.Iterable[PhysicalCard], index: int):
# 		self._grid = grid
# 		self._cards = list(cards)
# 		self._index = index
# 		self._indexes = None  # type: t.List[t.Tuple[int, PhysicalCard]]
#
# 	def _indexed(self, cards: t.Iterable[PhysicalCard]) -> t.Iterator[t.Tuple[int, PhysicalCard]]:
# 		for card in cards:
# 			try:
# 				yield self._grid.cards.index(card), card
# 			except ValueError:
# 				pass
#
# 	def setup(self):
# 		self._indexes = sorted(
# 			self._indexed(self._cards),
# 			key=lambda v: v[0],
# 		)
#
# 	def redo(self) -> None:
# 		self._grid.unalign_cards(card for index, card in self._indexes)
#
# 		self._grid.insert_cards(self._index, self._cards)
#
# 		self._grid.re_position(
# 			min(
# 				self._indexes[0][0],
# 				self._index,
# 			)
# 		)
#
# 	def undo(self) -> None:
# 		self._grid.unalign_cards(card for index, card in self._indexes)
#
# 		for index, card in self._indexes:
# 			self._grid.insert_card(index, card)
#
# 		self._grid.re_position(self._indexes[0][0])
#
# 	def ignore(self) -> bool:
# 		return not self._cards



class GridSort(AlignSort):

	def __init__(self, grid: 'GridAligner'):
		self._grid = grid
		self._card_order = None #type: t.List[PhysicalCard]

	def setup(self):
		self._card_order = list(self._grid.cards)

	@abstractmethod
	def _key(self, card: PhysicalCard) -> t.Any:
		pass

	def redo(self) -> None:
		self._grid.cards.sort(key = self._key)
		self._grid.re_position(0)

	def undo(self) -> None:
		self._grid.cards[:] = self._card_order
		self._grid.re_position(0)


class CollectorNumberGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> int:
		return card.printing.collector_number


class NameGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> str:
		return card.printing.cardboard.name


class CmcGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> int:
		return (
			-1
			if typeline.LAND in card.printing.cardboard.front_card.type_line else
			card.printing.cardboard.front_card.cmc
		)


class TypeGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> bool:
		return typeline.CREATURE in card.printing.cardboard.front_card.type_line


class RarityGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> int:
		return card.printing.rarity.value


class ColorGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> int:
		return colors.color_set_sort_value_len_first(
			card.printing.cardboard.front_card.color
		)


class ExpansionGridSort(GridSort):

	def _key(self, card: PhysicalCard) -> str:
		return card.printing.expansion.code


class GridAligner(Aligner):

	def __init__(
		self,
		scene: CardScene,
		undo_stack: UndoStack,
		horizontal_margin: float = .1,
		vertical_margin: float = .1,
	):
		super().__init__(scene, undo_stack)

		self._horizontal_margin = horizontal_margin * IMAGE_WIDTH
		self._vertical_margin = vertical_margin * IMAGE_HEIGHT

		self._cell_width = IMAGE_WIDTH + self._horizontal_margin
		self._cell_height = IMAGE_HEIGHT + self._vertical_margin

		self._row_length = int( self._scene.width() // self._cell_width )
		self._column_height = int( self._scene.height() // self._cell_height )

		self._cards = [] #type: t.List[PhysicalCard]
		
		self._cursor_position = None #type: t.Optional[PhysicalCard]
		
	def insert_card(self, index: int, card: PhysicalCard) -> None:
		self._cards.insert(index, card)
		
		card.setZValue(-1)
		
		if self._cursor_position is None:
			self.link_cursor(card)

	def insert_cards(self, index: int, cards: t.Iterable[PhysicalCard]) -> None:
		cards = list(cards)

		for card in reversed(cards):
			self._cards.insert(index, card)
			card.setZValue(-1)

		if self._cursor_position is None and self._cards:
			self.link_cursor(self._cards[0])

	def add_cards(self, cards: t.Iterable[PhysicalCard]) -> None:
		self._cards.extend(cards)
		
		for card in cards:
			card.setZValue(-1)
		
		if self._cursor_position is None and self._cards:
			self.link_cursor(self._cards[0])
	
	def unalign_cards(self, cards: t.Iterable[PhysicalCard]) -> None:
		previous_cursor_index = self.index_at_position(
			self._cursor_position.pos()
		)

		cards = list(cards)
		
		for card in cards:
			self._cards.remove(card)
			card.setZValue(0)
			
		if self._cursor_position in cards:
			self._realign_cursor(previous_cursor_index)
			
	def _realign_cursor(self, previous_index: int) -> None:
		if not self._cards:
			self.link_cursor(None)
			return 
		
		self.link_cursor(
			self._cards[
				min(
					previous_index,
					len(self.cards) - 1,
				)
			]
		)

	def link_cursor(self, target: t.Optional[PhysicalCard]) -> None:
		self._cursor_position = target

		if target is None:
			self._scene.cursor.setPos(0, 0)
			self.cursor_moved.emit(QtCore.QPointF(0, 0))
			return

		self._scene.cursor.setPos(self._cursor_position.pos())
		self.cursor_moved.emit(self._cursor_position.pos())

	@property
	def cards(self) -> t.List[PhysicalCard]:
		return self._cards

	def re_position(self, index: int) -> None:
		i = index

		for card in self._cards[index:]:
			card.setPos(
				(i % self._row_length) * self._cell_width + self._horizontal_margin,
				(i // self._row_length) * self._cell_height + self._vertical_margin,
			)

			i += 1
			
		if not self._cursor_position is None:
			self.scene.cursor.setPos(self._cursor_position.pos())
			self.cursor_moved.emit(self._cursor_position.pos())

	def index_at_position(self, position: QtCore.QPointF) -> int:
		return int(
			min(
				max(min(position.x(), self.scene.width()), 0) // self._cell_width
				+ max(position.y(), 0) // self._cell_height * self._row_length,
				len(self._cards),
			)
		)

	def attach_cards(
		self,
		cards: t.Iterable[PhysicalCard],
		position: t.Optional[QtCore.QPointF] = None,
	) -> GridAttach:
		return GridAttach(self, cards, position)

	def detach_cards(self, cards: t.Iterable[PhysicalCard]) -> GridDetach:
		return GridDetach(self, cards)

	def remove_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignRemove:
		return GridRemove(self, cards)

	def move_cursor(self, direction: Direction, modifiers: int = 0):
		if self._cursor_position is None:
			return 
		
		original_position = self.index_at_position(self._cursor_position.pos())
		
		if direction == Direction.UP:
			delta = -self._row_length
		
		elif direction == Direction.RIGHT:
			delta = 1
			
		elif direction == Direction.DOWN:
			delta = self._row_length
			
		else:
			delta = -1

		new_index = (original_position + delta) % len(self._cards)

		self.link_cursor(self._cards[new_index])
		
		if modifiers & QtCore.Qt.ControlModifier:
			self.scene.add_selection((self._cursor_position,))

		elif modifiers & QtCore.Qt.AltModifier:
			self.scene.remove_selected((self._cursor_position,))

		# elif modifiers & QtCore.Qt.ShiftModifier:
		# 	self._undo_stack.push(
		# 		GridMove(
		# 			self,
		# 			self.scene.selectedItems(),
		# 			new_index,
		# 		)
		# 	)

		else:
			self.scene.set_selection((self._cursor_position,))

		Context.card_view.set_image.emit(self._cursor_position.image_request())

	_SORT_PROPERTY_MAP = {
		SortProperty.COLLECTOR_NUMBER: CollectorNumberGridSort,
		SortProperty.TYPE: TypeGridSort,
		SortProperty.CMC: CmcGridSort,
		SortProperty.NAME: NameGridSort,
		SortProperty.RARITY: RarityGridSort,
		SortProperty.COLOR: ColorGridSort,
		SortProperty.EXPANSION: ExpansionGridSort,
	} #type: t.Dict[SortProperty, t.Type[GridSort]]

	def sort(self, sort_property: SortProperty, orientation: int) -> GridSort:
		return self._SORT_PROPERTY_MAP[sort_property](self)
