import typing as t

from itertools import chain
from abc import abstractmethod, ABC

from PyQt5 import QtCore

from mtgorp.models.persistent.attributes import typeline
from mtgorp.models.persistent.attributes import colors

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug

from deckeditor.garbage.undo import UndoStack, UndoCommand
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard
from deckeditor.garbage.cardcontainers.alignment import (
	Aligner,
	AlignAttach,
	AlignDetach,
	AlignRemove,
	AlignSort,
	CardScene,
)
from deckeditor.context.context import Context
from deckeditor.values import SortProperty, Direction


IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.ORIGINAL, False))]


class CardStacker(ABC):

	def __init__(
		self,
		aligner: 'StackingGrid',
		index: t.Sequence[int],
		# geometry: t.Tuple[float, float, float, float],
	):
		self._aligner = aligner #type: StackingGrid
		self._index = list(index) #type: t.List[int]

		# self._geometry = list(geometry) # type: t.List[float]

		self._cards = []  # type: t.List[PhysicalCard]

		self._requested_size = (0., 0.) #type: t.Tuple[float, float]

	@property
	def grid(self) -> 'StackingGrid':
		return self._aligner

	@property
	def index(self) -> t.List[int]:
		return self._index

	@property
	def x_index(self) -> int:
		return self._index[0]

	# @x_index.setter
	# def x_index(self, value: int) -> None:
	# 	self._index[0] = value

	@property
	def y_index(self) -> int:
		return self._index[1]

	# @y_index.setter
	# def y_index(self, value: int) -> None:
	# 	self._index[1] = value

	@property
	def x(self) -> float:
		return self._aligner.stacker_map.width_at(self.x_index)

	# @x.setter
	# def x(self, value: float) -> None:
	# 	self._geometry[0] = value

	@property
	def y(self) -> float:
		return self._aligner.stacker_map.height_at(self.y_index)

	# @y.setter
	# def y(self, value: float) -> None:
	# 	self._geometry[1] = value

	@property
	def position(self) -> t.Tuple[float, float]:
		return self.x, self.y

	# @position.setter
	# def position(self, value: t.Tuple[float, float]) -> None:
	# 	self._geometry[0:2] = value

	@property
	def width(self) -> float:
		return self._aligner.stacker_map.column_width_at(self.x_index)

	# @width.setter
	# def width(self, value: float) -> None:
	# 	self._geometry[2] = value

	@property
	def height(self) -> float:
		return self._aligner.stacker_map.row_height_at(self.y_index)

	# @height.setter
	# def height(self, value: float) -> None:
	# 	self._geometry[3] = value

	@property
	def size(self) -> t.Tuple[float, float]:
		return self.width, self.height

	# @size.setter
	# def size(self, values: t.Sequence[float]) -> None:
	# 	self._geometry[2:4] = values

	# @property
	# def dimensions(self) -> t.List[float]:
	# 	return self._geometry[2:4]
	#
	# @dimensions.setter
	# def dimensions(self, value: t.Tuple[float, float]) -> None:
	# 	self._geometry[2:4] = value

	@property
	def requested_size(self) -> t.List[float]:
		return self._requested_size

	@property
	def requested_width(self) -> float:
		return self._requested_size[0]

	@property
	def requested_height(self) -> float:
		return self._requested_size[1]

	@property
	def cards(self) -> t.List[PhysicalCard]:
		return self._cards

	@abstractmethod
	def map_position_to_index(self, x: float, y: float) -> int:
		pass

	@abstractmethod
	def calculate_requested_size(self) -> t.Tuple[float, float]:
		pass

	def update(self):
		self._aligner.request_space(self, *self.requested_size())
		self._stack()

		for index, card in enumerate(self._cards):
			if card == self._aligner.cursor_position:
				self._aligner.scene.cursor.setPos(
					card.pos()
				)

			card.setZValue(index - len(self._cards) - 1)
			self._aligner.get_card_info(card).position = index

	@abstractmethod
	def _stack(self):
		pass

	def add_card_no_restack(self, card: PhysicalCard):
		info = self._aligner.get_card_info(card)

		if info.card_stacker is not None:
			info.card_stacker.remove_cards((card,))

		info.card_stacker = self
		self._cards.append(card)

	def _remove_card_no_restack(self, card: PhysicalCard):
		self._cards.remove(card)
		self._aligner.remove_card(card)

	def _insert_card_no_restack(self, index: int, card: PhysicalCard):
		info = self._aligner.get_card_info(card)

		if info.card_stacker is not None:
			info.card_stacker.remove_cards((card,))

		info.card_stacker = self
		self._cards.insert(index, card)

	def insert_card(self, index: int, card: PhysicalCard):
		self._insert_card_no_restack(index, card)
		self.update()

	def remove_cards(self, cards: t.Iterable[PhysicalCard]):
		cards = list(cards)

		cursor_info = self._aligner.get_card_info(self._aligner.cursor_position)

		for card in cards:
			self._remove_card_no_restack(card)

		self.update()

		if self._aligner.cursor_position in cards:
			if cursor_info.card_stacker.cards:
				self._aligner.link_cursor(
					cursor_info.card_stacker.cards[
						min(
							len(cursor_info.card_stacker.cards) - 1,
							cursor_info.position,
						)
					]
				)
			else:
				stacker = self._aligner.find_stacker(
					*cursor_info.card_stacker.index,
					direction = Direction.UP
				)
				if stacker:
					self._aligner.link_cursor(stacker.cards[-1])
				# else:
				# 	stacker = self._aligner.find_stacker_spiraled(
				# 		*cursor_info.card_stacker.index,
				# 		direction = Direction.UP,
				# 	)
				# 	if stacker:
				# 		self._aligner.link_cursor(stacker.cards[-1])
				else:
					self._aligner.link_cursor(None)

	def add_cards(self, cards: t.Iterable[PhysicalCard]):
		for card in cards:
			self.add_card_no_restack(card)
		self.update()

	def insert_cards(self, indexes: t.Iterable[int], cards: t.Iterable[PhysicalCard]):
		for index, card in zip(indexes, cards):
			self._insert_card_no_restack(index, card)
		self.update()

	def clear_no_restack(self):
		for card in self._cards:
			self._aligner.remove_card(card)
		self._cards.clear()


class StackingAttach(AlignAttach):

	def __init__(
		self,
		grid: 'StackingGrid',
		stacker: CardStacker,
		index: int,
		cards: t.Tuple[PhysicalCard, ...],
	):
		super().__init__()
		self._grid = grid
		self._stacker = stacker
		self._index = index
		self._cards = cards

	def redo(self):
		self._stacker.grid.scene.add_cards(
			*(
				card
				for card in
				self._cards
				if card.scene() != self._stacker.grid.scene
			)
		)

		self._stacker.insert_cards(
			range(self._index, self._index + len(self._cards)),
			self._cards,
		)

		if self._grid.cursor_position is None:
			self._grid.link_cursor(self._cards[-1])

	def undo(self):
		self._stacker.remove_cards(self._cards)

	def ignore(self) -> bool:
		return not self._cards


class StackingDetach(AlignDetach):

	def __init__(
		self,
		grid: 'StackingGrid',
		cards: t.Iterable[PhysicalCard],
	):
		super().__init__()
		self._grid = grid
		self._cards = list(cards)

		self._stackers = {}  # type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

	def setup(self):
		for card in self._cards:
			info = self._grid.get_card_info(card)
			self._stacker_cards(info.card_stacker).append((info.position, card))

	def _stacker_cards(self, stacker: CardStacker) -> t.List[t.Tuple[int, PhysicalCard]]:
		try:
			return self._stackers[stacker]
		except KeyError:
			self._stackers[stacker] = info = []
			return info

	def redo(self):

		for stacker, infos in self._stackers.items():
			if stacker is not None:
				stacker.remove_cards(card for index, card in infos)

		for card in self._cards:
			card.setZValue(0)

	def undo(self):
		for stacker, infos in self._stackers.items():
			_infos = sorted(infos, key=lambda info: info[0])

			adjusted_indexes = []
			passed = 0

			for index, card in _infos:
				if card.scene() != stacker.grid.scene:
					stacker.grid.scene.add_cards(card)
				adjusted_indexes.append((index - passed, card))
				passed += 1

			stacker.insert_cards(*zip(*adjusted_indexes))

		if self._grid.cursor_position is None:
			self._grid.link_cursor(self._cards[-1])

	def ignore(self) -> bool:
		return not self._cards


class StackingRemove(AlignRemove):

	def __init__(
		self,
		grid: 'StackingGrid',
		cards: t.Iterable[PhysicalCard],
	):
		super().__init__()
		self._grid = grid
		self._cards = cards

	def redo(self):
		self._grid.scene.remove_cards(*self._cards)

	def undo(self):
		self._grid.scene.add_cards(*self._cards)

	def ignore(self) -> bool:
		return not self._cards


class _StackingMove(UndoCommand):

	def __init__(self, grid: 'StackingGrid', cards: t.Iterable[PhysicalCard], stacker: CardStacker):
		self._grid = grid
		self._cards = list(cards)
		self._stacker = stacker

		self._stackers = {}  # type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

	def _stacker_cards(self, stacker: CardStacker) -> t.List[t.Tuple[int, PhysicalCard]]:
		try:
			return self._stackers[stacker]
		except KeyError:
			self._stackers[stacker] = info = []
			return info

	def setup(self):
		for card in self._cards:
			info = self._grid.get_card_info(card)
			self._stacker_cards(info.card_stacker).append((info.position, card))

	def redo(self) -> None:
		for stacker, infos in self._stackers.items():
			if stacker is not None:
				stacker.remove_cards(card for _, card in infos)

		self._stacker.add_cards(self._cards)

	def undo(self) -> None:
		self._stacker.remove_cards(self._cards)

		for stacker, infos in self._stackers.items():
			_infos = sorted(infos, key=lambda info: info[0])

			adjusted_indexes = []
			passed = 0

			for index, card in _infos:
				if card.scene() != stacker.grid.scene:
					stacker.grid.scene.add_cards(card)
				adjusted_indexes.append((index - passed, card))
				passed += 1

			stacker.insert_cards(*zip(*adjusted_indexes))

	def ignore(self) -> bool:
		return not self._cards


class _StackingSort(AlignSort):
	EXCESS_LEFT = True  # type: bool

	def __init__(self, grid: 'StackingGrid', orientation: int):
		self._grid = grid
		self._orientation = orientation

		self._card_infos = {}  # type: t.Dict[PhysicalCard, t.Tuple[CardStacker, int]]
		self._stackers = {}  # type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

	def _sorted_cards(self) -> t.List[PhysicalCard]:
		return sorted(
			self._card_infos.keys(),
			key=lambda card: card.cubeable.cardboard.name,
		)

	def _cards_separated(self) -> t.Iterable[t.Tuple[PhysicalCard, int]]:
		sorted_cards = self._sorted_cards()

		parts = (
			self._grid.stacker_map.row_length
			if self._orientation == QtCore.Qt.Horizontal else
			self._grid.stacker_map.column_height
		)

		part, excess = (
			len(sorted_cards) // parts,
			len(sorted_cards) % parts,
		)

		if self.EXCESS_LEFT:
			for i in range(excess):
				yield (sorted_cards[i], 0)

		for i in range(parts):
			for n in range(part):
				yield (
					sorted_cards[
						(excess if self.EXCESS_LEFT else 0) + i * part + n
						],
					i,
				)

		if not self.EXCESS_LEFT:
			for i in range(excess):
				yield (sorted_cards[parts * part + i], parts - 1)

	def _card_sorted_indexes(self) -> t.Iterable[t.Tuple[PhysicalCard, int, int]]:
		info_extractor = (
			(lambda i, info: (i, info[0].index[1]))
			if self._orientation == QtCore.Qt.Horizontal else
			(lambda i, info: (info[0].index[0], i))
		)

		for card, i in self._cards_separated():
			yield (card, *info_extractor(i, self._card_infos[card]))

	def _stacker_cards(self, stacker: CardStacker) -> t.List[t.Tuple[int, PhysicalCard]]:
		try:
			return self._stackers[stacker]
		except KeyError:
			self._stackers[stacker] = info = []
			return info

	def setup(self):
		for card, info in self._grid.stacked_cards.items():
			self._stacker_cards(info.card_stacker).append((info.position, card))
			self._card_infos[card] = (info.card_stacker, info.position)

	def redo(self) -> None:
		for stacker in self._grid.stacker_map.stackers:
			stacker.clear_no_restack()

		for card, x, y in self._card_sorted_indexes():
			(
				self
					._grid
					.get_card_stacker_at_index(x, y)
					.add_card_no_restack(card)
			)

		for stacker in self._grid.stacker_map.stackers:
			stacker.update()

		self._grid.link_cursor(self._grid.cursor_position)

	def undo(self) -> None:
		for stacker in self._grid.stacker_map.stackers:
			stacker.clear_no_restack()

		for stacker, infos in self._stackers.items():
			stacker.add_cards(*(card for index, card in infos))

	def ignore(self) -> bool:
		return not self._grid.stacked_cards


class _ValueToPositionSort(_StackingSort):
	class ListDict(dict):

		def __getitem__(self, k: int) -> t.List[PhysicalCard]:
			try:
				return super().__getitem__(k)
			except KeyError:
				l = []
				self.__setitem__(k, l)
				return l

	@abstractmethod
	def _sort_value(self, card: PhysicalCard) -> t.Any:
		pass

	def _cards_separated(self) -> t.Iterable[t.Tuple[PhysicalCard, int]]:
		parts = (
			self._grid.stacker_map.row_length
			if self._orientation == QtCore.Qt.Horizontal else
			self._grid.stacker_map.column_height
		)

		value_map = self.ListDict()

		for card in self._card_infos.keys():
			value_map[self._sort_value(card)].append(card)

		values = sorted(value_map.keys()).__iter__()

		for i in range(parts):
			value = next(values, None)
			if value is None:
				break

			for card in value_map[value]:
				yield card, i

		for value in values:
			for card in value_map[value]:
				yield card, parts - 1


class CmcSort(_ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> int:
		return (
			-1
			if typeline.LAND in card.printing.cardboard.front_card.type_line else
			card.printing.cardboard.front_card.cmc
		)


class TypeSort(_ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> bool:
		return not typeline.CREATURE in card.printing.cardboard.front_card.type_line


class RaritySort(_ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> int:
		return -1 if card.printing.rarity is None else card.printing.rarity.value


class ColorSort(_ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> int:
		return (
			-1
			if typeline.LAND in card.printing.cardboard.front_card.type_line else
			colors.color_set_sort_value_len_first(
				card.printing.cardboard.front_card.color
			)

		)


class NameSort(_StackingSort):
	pass


class ExpansionSort(_ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> str:
		return '' if card.printing.expansion is None else card.printing.expansion.code


class CollectorsNumberSort(_StackingSort):

	def _sorted_cards(self) -> t.List[PhysicalCard]:
		return sorted(self._card_infos.keys(), key=lambda card: card.cubeable.collector_number)


class _CardInfo(object):

	def __init__(self, stacker: CardStacker = None, position: int = None):
		self.card_stacker = stacker  # type: t.Optional[CardStacker]
		self.position = position  # type: t.Optional[int]

	def __repr__(self):
		return f'{self.__class__.__name__}({self.card_stacker, self.position})'


class StackerMap(object):

	def __init__(
		self,
		aligner: 'StackingGrid',
		row_amount: int,
		column_amount: int,
		default_row_height: float = 1.,
		default_column_width: float= 1.,
	):
		self._aligner = aligner

		self._row_amount = row_amount
		self._column_amount = column_amount

		self._grid = [
			[
				self._aligner.create_stacker(
					row,
					column,
				)
				for column in
				range(column_amount)
			]
			for row in
			range(row_amount)
		]

		self._row_heights = [
			default_row_height
			for _ in
			range(self._row_amount)
		]
		self._column_widths = [
			default_column_width
			for _ in
			range(self._column_amount)
		]

	@property
	def row_length(self) -> int:
		return self._column_amount

	@property
	def column_height(self) -> int:
		return self._row_amount

	@property
	def width(self) -> int:
		return sum(self._column_widths)

	@property
	def height(self) -> int:
		return sum(self._row_heights)

	@property
	def columns(self) -> t.List[t.List[CardStacker]]:
		return self._grid

	@property
	def rows(self) -> t.Iterator[t.Tuple[CardStacker, ...]]:
		return zip(*self._grid)

	def width_at(self, index: int) -> int:
		return sum(self._column_widths[:index])

	def height_at(self, index: int) -> int:
		return sum(self._row_heights[:index])

	def row_height_at(self, index: int) -> float:
		return self._row_heights[index]

	def column_width_at(self, index: int) -> float:
		return self._column_widths[index]

	def map_position_to_index(self, x: float, y: float) -> t.Tuple[int, int]:
		xi = self.row_length
		for i in range(self.row_length):
			if x <= self.column_width_at(i):
				xi = i
				break
			x -= self.column_width_at(i)

		yi = self.column_height
		for i in range(self.column_height):
			if y <= self.row_height_at(i):
				yi = i
				break
			y -= self.row_height_at(i)

		return xi, yi

	def get_stacker(self, x: int, y: int) -> CardStacker:
		return self._grid[x][y]

	@property
	def stackers(self) -> t.Iterator[CardStacker]:
		for column in self._grid:
			for stacker in column:
				yield stacker

	def __iter__(self) -> t.Iterator[CardStacker]:
		return self.stackers

	def __str__(self):
		return '[\n' + '\n'.join(
			'\t[' + ', '.join(
				str(cell.position)
				for cell in
				row
			) + ']'
			for row in
			zip(*self._grid)
		) + '\n]'


class StackingGrid(Aligner):

	def __init__(
		self,
		scene: CardScene,
		undo_stack: UndoStack,
		margin: float = .2,
	):
		super().__init__(scene, undo_stack)

		self._stacked_cards = {}  # type: t.Dict[PhysicalCard, _CardInfo]

		self._margin_pixel_size = margin * IMAGE_WIDTH / 2.5

		self._stacker_map = self.create_stacker_map()

		self._cursor_position = None  # type: t.Optional[PhysicalCard]
		self._cursor_index = 0

	@abstractmethod
	def create_stacker_map(self) -> StackerMap:
		pass

	@abstractmethod
	def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
		pass

	@abstractmethod
	def create_stacker(self, x: int, y: int) -> CardStacker:
		pass

	@property
	def stacker_map(self) -> StackerMap:
		return self._stacker_map

	@property
	def stacked_cards(self) -> t.Dict[PhysicalCard, _CardInfo]:
		return self._stacked_cards

	@property
	def scene(self) -> CardScene:
		return self._scene

	@property
	def cursor_position(self) -> t.Optional[PhysicalCard]:
		return self._cursor_position

	def get_card_info(self, card: PhysicalCard) -> _CardInfo:
		try:
			return self._stacked_cards[card]
		except KeyError:
			self._stacked_cards[card] = info = _CardInfo()
			return info

	def remove_card(self, card: PhysicalCard) -> None:
		try:
			del self._stacked_cards[card]
		except KeyError:
			pass

	def attach_cards(
		self,
		cards: t.Iterable[PhysicalCard],
		position: t.Optional[QtCore.QPointF] = None
	) -> StackingAttach:

		if position is None:
			if self._cursor_position is None:
				stacker = self.get_card_stacker_at_index(0, 0)
				index = len(stacker.cards)

			else:
				info = self.get_card_info(self._cursor_position)
				stacker = info.card_stacker
				index = info.position

		else:
			x, y = position.x(), position.y()
			stacker = self.get_card_stacker(x, y)
			index = stacker.map_position_to_index(x, y - stacker.y)

		return StackingAttach(
			grid = self,
			stacker = stacker,
			index = int(index),
			cards = tuple(cards),
		)

	def detach_cards(self, cards: t.Iterable[PhysicalCard]) -> StackingDetach:
		return StackingDetach(
			self,
			cards,
		)

	def remove_cards(self, cards: t.Iterable[PhysicalCard]) -> StackingRemove:
		return StackingRemove(
			self,
			cards,
		)

	def link_cursor(self, card: t.Optional[PhysicalCard]) -> None:
		if card is None:
			self._cursor_position = None
			self._scene.cursor.setPos(0, 0)
			self.cursor_moved.emit(QtCore.QPointF(0, 0))
			return

		self._cursor_position = card
		self._scene.cursor.setPos(card.pos())
		self.cursor_moved.emit(self._cursor_position.pos())

	def find_stacker(self, x: int, y: int, direction: Direction) -> t.Optional[CardStacker]:

		if not self._stacked_cards:
			return None

		x, y = int(x), int(y)

		if direction == Direction.UP:
			for _x in chain(
				range(x, self.stacker_map.row_length),
				reversed(range(0, x)),
			):
				for _y in reversed(range(0, y + 1)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _x in chain(
				range(x, self.stacker_map.row_length),
				reversed(range(0, x)),
			):
				for _y in reversed(range(y + 1, self.stacker_map.column_height)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

		elif direction == Direction.RIGHT:
			for _y in chain(
				range(y, self.stacker_map.column_height),
				reversed(range(0, y)),
			):
				for _x in range(x, self.stacker_map.row_length):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _y in chain(
				range(y, self.stacker_map.column_height),
				reversed(range(0, y)),
			):
				for _x in range(0, x):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

		elif direction == Direction.DOWN:
			for _x in chain(
				reversed(range(0, x + 1)),
				range(x + 1, self.stacker_map.row_length),
			):
				for _y in range(y + 1, self.stacker_map.column_height):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _x in chain(
				reversed(range(0, x + 1)),
				range(x + 1, self.stacker_map.row_length),
			):
				for _y in range(0, y + 1):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

		elif direction == Direction.LEFT:
			for _y in chain(
				reversed(range(0, y + 1)),
				range(y + 1, self.stacker_map.column_height),
			):
				for _x in reversed(range(0, x + 1)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _y in chain(
				reversed(range(0, y + 1)),
				range(y + 1, self.stacker_map.column_height),
			):
				for _x in reversed(range(x + 1, self.stacker_map.row_length)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

	# def find_stacker_spiraled(self, x: int, y: int, direction: Direction) -> t.Optional[CardStacker]:
	# 	if not self._stacked_cards:
	# 		return None
	#
	# 	x, y = int(x), int(y)
	#
	# 	_iter = spiral(direction)
	#
	# 	for dx, dy in (
	# 		next(_iter)
	# 		for _ in
	# 		range(
	# 			self.stacker_map.row_length
	# 			* self.stacker_map.column_height
	# 			* 4
	# 		)
	# 	):
	# 		stacker = self.get_card_stacker_at_index(x + dx, y + dy)
	#
	# 		if stacker.cards:
	# 			return stacker
	#
	# 	return None

	def _move_cards(self, cards: t.List[PhysicalCard], stacker: CardStacker):
		if not cards:
			return

		self._undo_stack.push(
			_StackingMove(
				self,
				self._scene.selectedItems(),
				stacker,
			)
		)

		self.link_cursor(cards[-1])

	def move_cursor(self, direction: Direction, modifiers: int = 0):
		if self._cursor_position is None:
			return

		info = self._stacked_cards[self.cursor_position]

		if modifiers & QtCore.Qt.ShiftModifier:
			selected_items = self._scene.selectedItems()

			if modifiers & QtCore.Qt.ControlModifier:
				stacker = self.find_stacker(*info.card_stacker.index, direction=direction)

				if stacker is None:
					return

			else:

				stacker = self.get_card_stacker_at_index(
					info.card_stacker.index[0] + direction.value[0],
					info.card_stacker.index[1] + direction.value[1],
				)

			self._move_cards(selected_items, stacker)
			return

		if direction == Direction.UP:
			stacker = info.card_stacker
			position = info.position - 1

			if position < 0:
				next_stacker = self.find_stacker(*stacker.index, direction=direction)

				if next_stacker is not None:
					stacker = next_stacker

			self.link_cursor(stacker.cards[position])
			self._cursor_index = position

		elif direction == Direction.DOWN:
			stacker = info.card_stacker
			position = info.position + 1

			if position >= len(stacker.cards):
				next_stacker = self.find_stacker(*stacker.index, direction=direction)

				if next_stacker is not None:
					stacker = next_stacker

				position = 0

			self.link_cursor(stacker.cards[position])
			self._cursor_index = position

		else:
			stacker = info.card_stacker

			next_stacker = self.find_stacker(*stacker.index, direction=direction)

			if next_stacker is not None:
				stacker = next_stacker

			self.link_cursor(
				stacker.cards[
					min(
						len(stacker.cards) - 1,
						max(
							info.position,
							self._cursor_index,
						)
					)
				]
			)

		if modifiers & QtCore.Qt.ControlModifier:
			self._scene.add_selection((self._cursor_position,))

		elif modifiers & QtCore.Qt.AltModifier:
			self._scene.remove_selected((self._cursor_position,))

		else:
			self._scene.set_selection((self._cursor_position,))

		Context.card_view.set_image.emit(self._cursor_position.image_request())

	# @abstractmethod
	# def _can_create_rows(self, amount: int) -> bool:
	# 	pass
	#
	# @abstractmethod
	# def _can_create_columns(self, amount: int) -> bool:
	# 	pass
	#
	# @abstractmethod
	# def _create_rows(self, amount: int) -> None:
	# 	pass
	#
	# @abstractmethod
	# def _create_columns(self, amount: int) -> None:
	# 	pass

	def get_card_stacker_at_index(self, x: int, y: int) -> CardStacker:
		x = min(max(x, 0), self.stacker_map.row_length - 1)
		y = min(max(y, 0), self.stacker_map.column_height - 1)

		# required_columns = x - self._stacker_map.row_length + 1
		# required_rows = y - self._stacker_map.column_height + 1
		#
		# if (
		# 	( required_rows > 0 or required_columns > 0 )
		# 	and self._can_create_rows(required_rows)
		# 	and self._can_create_columns(required_columns)
		# ):
		# 	if required_rows > 0:
		# 		self._create_rows(required_rows)
		# 	if required_columns > 0:
		# 		self._create_columns(required_columns)
		#
		# else:
		# 	x = min(x, self.stacker_map.row_length - 1)
		# 	y = min(y, self.stacker_map.column_height - 1)

		return self.stacker_map.get_stacker(x, y)

	def get_card_stacker(self, x: int, y: int) -> CardStacker:
		return self.get_card_stacker_at_index(
			*self._stacker_map.map_position_to_index(x, y)
		)

	SORT_PROPERTY_MAP = {
		SortProperty.NAME: NameSort,
		SortProperty.CMC: CmcSort,
		SortProperty.COLOR: ColorSort,
		SortProperty.RARITY: RaritySort,
		SortProperty.TYPE: TypeSort,
		SortProperty.EXPANSION: ExpansionSort,
		SortProperty.COLLECTOR_NUMBER: CollectorsNumberSort,
	}

	def sort(self, sort_property: SortProperty, orientation: int) -> AlignSort:
		return self.SORT_PROPERTY_MAP[sort_property](self, orientation)