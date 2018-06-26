import typing as t

from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene

from mtgimg.load import IMAGE_HEIGHT, IMAGE_WIDTH

from deckeditor.cardcontainers.alignment.aligner import Aligner, AlignRemove, AlignAttach, AlignDetach
from deckeditor.cardcontainers.physicalcard import PhysicalCard



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
		for index, card in self._indexes:
			self._grid.cards.remove(card)

		if self._indexes:
			self._grid.re_position(self._indexes[0][0])

	def undo(self) -> None:
		for index, card in self._indexes:
			self._grid.cards.insert(index, card)

		if self._indexes:
			self._grid.re_position(self._indexes[0][0])



class GridRemove(AlignRemove):

	def __init__(self, grid: 'GridAligner', cards: t.Iterable[PhysicalCard]):
		self._grid = grid
		self._cards = list(cards)
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
		for index, card in self._indexes:
			self._grid.cards.remove(card)

		for card in self._cards:
			self._grid.scene.removeItem(card)

		if self._indexes:
			self._grid.re_position(self._indexes[0][0])

	def undo(self) -> None:
		for card in self._cards:
			self._grid.scene.addItem(card)

		for index, card in self._indexes:
			self._grid.cards.insert(index, card)

		if self._indexes:
			self._grid.re_position(self._indexes[0][0])


class GridAttach(AlignAttach):

	def __init__(self, grid: 'GridAligner', cards: t.Iterable[PhysicalCard], position: QPointF):
		super().__init__()
		self._grid = grid
		self._cards = list(cards)
		self._position = position
		self._index = None #type: int

	def setup(self):
		self._index = min(
			len(self._grid.cards),
			self._grid.index_at_position(self._position),
		)

	def redo(self) -> None:
		for card in reversed(self._cards):
			if not card.scene() == self._grid.scene:
				self._grid.scene.addItem(card)

			self._grid.cards.insert(self._index, card)

		self._grid.re_position(self._index)

	def undo(self) -> None:
		for card in self._cards:
			self._grid.cards.remove(card)

		self._grid.re_position(self._index)


class GridAligner(Aligner):

	def __init__(
		self,
		scene: QGraphicsScene,
		row_length = 7,
		horizontal_margin: float = .1,
		vertical_margin: float = .1,
		x: float = 0,
		y: float = 0,
	):
		super().__init__(scene)

		self._row_length = row_length
		self._x = x
		self._y = y

		self._horizontal_margin = horizontal_margin * IMAGE_WIDTH
		self._vertical_margin = vertical_margin * IMAGE_HEIGHT

		self._cell_width = IMAGE_WIDTH + self._horizontal_margin
		self._cell_height = IMAGE_HEIGHT + self._vertical_margin

		self._width = self._cell_width * self._row_length

		self._cards = [] #type: t.List[PhysicalCard]

	@property
	def cards(self) -> t.List[PhysicalCard]:
		return self._cards

	def re_position(self, index: int) -> None:
		i = index

		for card in self._cards[index:]:
			card.setPos(
				(i % self._row_length) * self._cell_width + self._horizontal_margin + self._x,
				(i // self._row_length) * self._cell_height + self._vertical_margin + self._y,
			)

			i += 1

	def index_at_position(self, position: QPointF) -> int:
		return int(
			max(min(position.x() - self._x, self._width), 0) // self._cell_width
			+ max(position.y() - self._y, 0) // self._cell_height * self._row_length
		)

	def attach_cards(self, cards: t.Iterable[PhysicalCard], position: QPointF) -> AlignAttach:
		return GridAttach(
			self,
			cards,
			position,
		)

	def detach_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignDetach:
		return GridDetach(
			self,
			cards,
		)

	def remove_cards(self, cards: t.Iterable[PhysicalCard]) -> AlignRemove:
		return GridRemove(
			self,
			cards,
		)