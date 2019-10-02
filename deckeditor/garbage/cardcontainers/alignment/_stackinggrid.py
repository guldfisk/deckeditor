import typing as t

from itertools import chain
from abc import abstractmethod

from PyQt5 import QtCore

from mtgorp.models.persistent.attributes import typeline
from mtgorp.models.persistent.attributes import colors

from mtgimg.load import IMAGE_HEIGHT, IMAGE_WIDTH

from deckeditor.garbage.undo import UndoStack, UndoCommand
from deckeditor.garbage.cardcontainers.physicalcard import PhysicalCard
from deckeditor.garbage.cardcontainers.alignment import (
	Aligner,
	AlignAttach,
	AlignDetach,
	AlignRemove,
	AlignSort,
	Direction,
	CardScene,
)
from deckeditor.context.context import Context
from deckeditor.values import SortProperty


def _spiral(direction: Direction):
	if direction == Direction.UP:
		_x = 0
		_y = -1
		dx = 1
		dy = 0

	elif direction == Direction.RIGHT:
		_x = 1
		_y = 0
		dx = 0
		dy = -1

	elif direction == Direction.DOWN:
		_x = 0
		_y = -1
		dx = -1
		dy = 0

	else:
		_x = -1
		_y = 0
		dx = 0
		dy = -1

	swaps = 0

	while True:

		yield _x, _y

		if _x == _y or _x == -_y:
			if swaps == 3:
				_x, _y = _x + dx, _y + dy
				yield _x, _y
				swaps = 0

			dx, dy = -dy, dx
			swaps += 1

		_x, _y = _x+dx, _y+dy


class CardStacker(object):

	def __init__(
		self,
		grid: 'StackingGrid',
		index: t.Tuple[int, int],
		geometry: t.Tuple[float, float, float, float],
		max_spacing: float = 100.,
	):
		self._grid = grid
		self._index = index
		self._geometry = geometry #type: t.Tuple[float, float, float, float]
		self._max_spacing = max_spacing #type: float
		self._cards = [] #type: t.List[PhysicalCard]

		self._spacing_free_room = max(1, self.height - IMAGE_HEIGHT)

	@property
	def grid(self) -> 'StackingGrid':
		return self._grid

	@property
	def index(self) -> t.Tuple[int, int]:
		return self._index

	@property
	def x(self) -> float:
		return self._geometry[0]

	@property
	def y(self) -> float:
		return self._geometry[1]

	@property
	def position(self) -> t.Tuple[float, float]:
		return self._geometry[0:2]

	@property
	def width(self) -> float:
		return self._geometry[2]

	@property
	def height(self) -> float:
		return self._geometry[3]

	@property
	def cards(self) -> t.List[PhysicalCard]:
		return self._cards

	@property
	def _spacing(self):
		return min(
			self._max_spacing,
			self._spacing_free_room / max(len(self._cards), 1)
		)

	def position_index(self, position: float) -> int:
		return int(position // self._spacing)

	def stack(self):
		spacing = self._spacing

		for i in range(len(self._cards)):

			self._cards[i].setPos(
				self._geometry[0],
				self._geometry[1] + i * spacing,
			)

			if self._cards[i] == self._grid.cursor_position:
				self._grid.scene.cursor.setPos(
					self._geometry[0],
					self._geometry[1] + i * spacing,
				)

			self._cards[i].setZValue(i - len(self._cards) - 1)
			self._grid.get_card_info(self._cards[i]).position = i

	def add_card_no_restack(self, card: PhysicalCard):
		info = self._grid.get_card_info(card)

		if info.card_stacker is not None:
			info.card_stacker.remove_card(card)

		info.card_stacker = self
		self._cards.append(card)

	def remove_card_no_restack(self, card: PhysicalCard):
		try:
			self._cards.remove(card)
			self._grid.remove_card(card)
		except KeyError:
			pass

	def _insert_card(self, index: int, card: PhysicalCard):
		info = self._grid.get_card_info(card)

		if info.card_stacker is not None:
			info.card_stacker.remove_card(card)

		info.card_stacker = self
		self._cards.insert(index, card)

	def remove_card(self, card: PhysicalCard):
		self.remove_card_no_restack(card)
		self.stack()

	def add_card(self, card: PhysicalCard):
		self.add_card_no_restack(card)
		self.stack()

	def insert_card(self, index: int, card: PhysicalCard):
		self._insert_card(index, card)
		self.stack()

	def remove_cards(self, cards: t.Iterable[PhysicalCard]):
		for card in cards:
			self.remove_card_no_restack(card)
		self.stack()

	def add_cards(self, cards: t.Iterable[PhysicalCard]):
		for card in cards:
			self.add_card_no_restack(card)
		self.stack()

	def insert_cards(self, indexes: t.Iterable[int], cards: t.Iterable[PhysicalCard]):
		for index, card in zip(indexes, cards):
			self._insert_card(index, card)
		self.stack()

	def clear_no_restack(self):
		for card in self._cards:
			self._grid.remove_card(card)
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
		for card in self._cards:
			if card.scene() != self._stacker.grid.scene:
				self._stacker.grid.scene.addItem(card)

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

		self._stackers = {} #type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

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

		cursor_info = self._grid.get_card_info(self._grid.cursor_position)

		for stacker, infos in self._stackers.items():
			if stacker is not None:
				stacker.remove_cards(card for index, card in infos)

		for card in self._cards:
			card.setZValue(0)

		if self._grid.cursor_position in self._cards:
			if cursor_info.card_stacker.cards:
				self._grid.link_cursor(
					cursor_info.card_stacker.cards[
						min(
							len(cursor_info.card_stacker.cards) - 1,
							cursor_info.position,
						)
					]
				)
			else:
				stacker = self._grid.find_stacker(
					*cursor_info.card_stacker.index,
					direction = Direction.UP
				)
				if stacker:
					self._grid.link_cursor(stacker.cards[-1])
				else:
					stacker = self._grid.find_stacker_spiraled(
						*cursor_info.card_stacker.index,
						direction = Direction.UP,
					)
					if stacker:
						self._grid.link_cursor(stacker.cards[-1])
					else:
						self._grid.link_cursor(None)

	def undo(self):
		for stacker, infos in self._stackers.items():
			_infos = sorted(infos, key = lambda info: info[0])

			adjusted_indexes = []
			passed = 0

			for index, card in _infos:
				if card.scene() != stacker.grid.scene:
					stacker.grid.scene.addItem(card)
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
		for card in self._cards:
			self._grid.scene.removeItem(card)

	def undo(self):
		for card in self._cards:
			self._grid.scene.addItem(card)

	def ignore(self) -> bool:
		return not self._cards


class StackingMove(UndoCommand):

	def __init__(self, grid: 'StackingGrid', cards: t.Iterable[PhysicalCard], stacker: CardStacker):
		self._grid = grid
		self._cards = list(cards)
		self._stacker = stacker

		self._stackers = {} #type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

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
				stacker.remove_cards(card for index, card in infos)

		self._stacker.add_cards(self._cards)

	def undo(self) -> None:
		self._stacker.remove_cards(self._cards)

		for stacker, infos in self._stackers.items():
			_infos = sorted(infos, key = lambda info: info[0])

			adjusted_indexes = []
			passed = 0

			for index, card in _infos:
				if card.scene() != stacker.grid.scene:
					stacker.grid.scene.addItem(card)
				adjusted_indexes.append((index - passed, card))
				passed += 1

			stacker.insert_cards(*zip(*adjusted_indexes))

	def ignore(self) -> bool:
		return not self._cards


class StackingSort(AlignSort):
	EXCESS_LEFT = True #type: bool

	def __init__(self, grid: 'StackingGrid', orientation: int):
		self._grid = grid
		self._orientation = orientation

		self._card_infos = {} #type: t.Dict[PhysicalCard, t.Tuple[CardStacker, int]]
		self._stackers = {}  # type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

	def _sorted_cards(self) -> t.List[PhysicalCard]:
		return sorted(
			self._card_infos.keys(),
			key=lambda card: card.printing.cardboard.name,
		)

	def _cards_separated(self) -> t.Iterable[t.Tuple[PhysicalCard, int]]:
		sorted_cards = self._sorted_cards()

		parts = (
			self._grid.stacker_row_length
			if self._orientation == QtCore.Qt.Horizontal else
			self._grid.stacker_column_height
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
			( lambda i, info: (i, info[0].index[1]) )
			if self._orientation == QtCore.Qt.Horizontal else
			( lambda i, info: (info[0].index[0], i) )
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
		for stacker in self._grid.stackers:
			stacker.clear_no_restack()

		for card, x, y in self._card_sorted_indexes():
			(
				self
				._grid
				.get_card_stacker_at_index(x, y)
				.add_card_no_restack(card)
			)

		for stacker in self._grid.stackers:
			stacker.stack()

		self._grid.link_cursor(self._grid.cursor_position)

	def undo(self) -> None:
		for stacker in self._grid.stackers:
			stacker.clear_no_restack()

		for stacker, infos in self._stackers.items():
			stacker.add_cards(card for index, card in infos)

	def ignore(self) -> bool:
		return not self._grid.stacked_cards


class NameSort(StackingSort):
	pass


class ValueToPositionSort(StackingSort):

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
			self._grid.stacker_row_length
			if self._orientation == QtCore.Qt.Horizontal else
			self._grid.stacker_column_height
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


class CmcSort(ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> int:
		return (
			-1
			if typeline.LAND in card.printing.cardboard.front_card.type_line else
			card.printing.cardboard.front_card.cmc
		)


class TypeSort(ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> bool:
		return not typeline.CREATURE in card.printing.cardboard.front_card.type_line


class RaritySort(ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> int:
		return -1 if card.printing.rarity is None else card.printing.rarity.value


class ColorSort(ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> int:
		return (
			-1
			if typeline.LAND in card.printing.cardboard.front_card.type_line else
			colors.color_set_sort_value_len_first(
				card.printing.cardboard.front_card.color
			)

		)


class ExpansionSort(ValueToPositionSort):

	def _sort_value(self, card: PhysicalCard) -> str:
		return '' if card.printing.expansion is None else card.printing.expansion.code


class CollectorsNumberSort(StackingSort):

	def _sorted_cards(self) -> t.List[PhysicalCard]:
		return sorted(self._card_infos.keys(), key = lambda card: card.printing.collector_number)


class _CardInfo(object):

	def __init__(self, stacker: CardStacker = None, position: int = None):
		self.card_stacker = stacker #type: t.Optional[CardStacker]
		self.position = position #type: t.Optional[int]

	def __repr__(self):
		return f'{self.__class__.__name__}({self.card_stacker, self.position})'
	

class StackerMap(dict):

	def __init__(self):
		super().__init__()
		self._min_x = 0
		self._max_x = 0
		self._min_y = 0
		self._max_y = 0

	@property
	def min_x(self) -> int:
		return self._min_x

	@property
	def max_x(self) -> int:
		return self._max_x

	@property
	def min_y(self) -> int:
		return self._min_y

	@property
	def max_y(self) -> int:
		return self._max_y

	def __setitem__(self, key: t.Tuple[int, int], value: CardStacker) -> None:
		super().__setitem__(key, value)
		x, y = key
		
		if x < self._min_x:
			self._min_x = x
		elif x > self._max_x:
			self._max_x = x
			
		if y < self._min_y:
			self._min_y = y
		elif y > self.max_y:
			self._max_y = y
			

class StackingGrid(Aligner):

	def __init__(
		self,
		scene: CardScene,
		undo_stack: UndoStack,
		margin: float = .1,
		stacker_height: float = 2.,
	):
		super().__init__(scene, undo_stack)

		print('HMMMM')

		self._card_stackers = StackerMap() #type: StackerMap[t.Tuple[int, int], CardStacker]
		self._stacked_cards = {} #type: t.Dict[PhysicalCard, _CardInfo]

		self._card_stacker_width = int(IMAGE_WIDTH * (1 + margin)) #type: int
		self._card_stacker_height = int(IMAGE_HEIGHT * stacker_height) #type: int

		r = self._scene.sceneRect() #type: QtCore.QRectF

		self._stacker_row_length = int( r.width()// self._card_stacker_width )
		self._stacker_column_height = int( r.height() // self._card_stacker_height )

		self._cursor_position = None #type: t.Optional[PhysicalCard]
		self._cursor_index = 0

	@property
	def stacker_row_length(self) -> int:
		return self._stacker_row_length

	@property
	def stacker_column_height(self) -> int:
		return self._stacker_column_height

	@property
	def stacked_cards(self) -> t.Dict[PhysicalCard, _CardInfo]:
		return self._stacked_cards

	@property
	def stackers(self) -> t.Iterable[CardStacker]:
		return self._card_stackers.values()

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
			index = stacker.position_index(y - stacker.y)

		return StackingAttach(
			grid = self,
			stacker = stacker,
			index = index,
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
				range(x, self._card_stackers.max_x + 1),
				reversed(range(self._card_stackers.min_x, x)),
			):
				for _y in reversed(range(self._card_stackers.min_y, y + 1)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _x in chain(
				range(x, self._card_stackers.max_x + 1),
				reversed(range(self._card_stackers.min_x, x)),
			):
				for _y in reversed(range(y + 1, self._card_stackers.max_y + 1)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

		elif direction == Direction.RIGHT:
			for _y in chain(
				range(y, self._card_stackers.max_y + 1),
				reversed(range(self._card_stackers.min_y, y)),
			):
				for _x in range(x, self._card_stackers.max_x + 1):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _y in chain(
				range(y, self._card_stackers.max_y + 1),
				reversed(range(self._card_stackers.min_y, y)),
			):
				for _x in range(self._card_stackers.min_x, x):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

		elif direction == Direction.DOWN:
			for _x in chain(
				reversed(range(self._card_stackers.min_x, x + 1)),
				range(x + 1, self._card_stackers.max_x + 1),
			):
				for _y in range(y + 1, self._card_stackers.max_y + 1):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _x in chain(
				reversed(range(self._card_stackers.min_x, x + 1)),
				range(x + 1, self._card_stackers.max_x + 1),
			):
				for _y in range(self._card_stackers.min_y, y + 1):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

		elif direction == Direction.LEFT:
			for _y in chain(
				reversed(range(self._card_stackers.min_y, y + 1)),
				range(y + 1, self._card_stackers.max_y + 1),
			):
				for _x in reversed(range(self._card_stackers.min_x, x + 1)):
					if _x == x and _y == y:
						continue
					stacker = self.get_card_stacker_at_index(_x, _y)
					if stacker.cards:
						return stacker

			for _y in chain(
					reversed(range(self._card_stackers.min_y, y + 1)),
					range(y + 1, self._card_stackers.max_y + 1),
				):
					for _x in reversed(range(x + 1, self._card_stackers.max_x + 1)):
						if _x == x and _y == y:
							continue
						stacker = self.get_card_stacker_at_index(_x, _y)
						if stacker.cards:
							return stacker

	def find_stacker_spiraled(self, x: int, y: int, direction: Direction) -> t.Optional[CardStacker]:
		if not self._stacked_cards:
			return None

		x, y = int(x), int(y)

		_iter = _spiral(direction)

		for dx, dy in (
			next(_iter)
			for _ in
			range(
				(-self._card_stackers.min_x + self._card_stackers.max_x + 1)
				* (-self._card_stackers.min_y + self._card_stackers.max_y + 1)
				* 4
			)
		):
			stacker = self.get_card_stacker_at_index(x + dx, y + dy)

			if stacker.cards:
				return stacker

		return None

	def _move_cards(self, cards: t.List[PhysicalCard], stacker: CardStacker):
		if not cards:
			return

		self._undo_stack.push(
			StackingMove(
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
				stacker = self.find_stacker(*info.card_stacker.index, direction = direction)

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

	def get_card_stacker_at_index(self, x: int, y: int) -> CardStacker:
		x = min(max(int(x), 0), self._stacker_row_length - 1)
		y = min(max(int(y), 0), self._stacker_column_height - 1)

		key = x, y

		try:
			return self._card_stackers[key]
		except KeyError:
			self._card_stackers[key] = _card_stacker = CardStacker(
				self,
				(x, y),
				(
					x * self._card_stacker_width,
				 	y * self._card_stacker_height,
					self._card_stacker_width,
					self._card_stacker_height,
				)
			)
			return _card_stacker

	def get_card_stacker(self, x: int, y: int) -> CardStacker:
		return self.get_card_stacker_at_index(
			x // self._card_stacker_width,
			y // self._card_stacker_height,
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