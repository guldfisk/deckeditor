import typing as t

from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtCore import QPointF, QPoint

from mtgimg.load import IMAGE_HEIGHT, IMAGE_WIDTH

from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.cardcontainers.alignment.aligner import Aligner, AlignAttach, AlignDetach, AlignRemove


class CardStacker(object):

	def __init__(
		self,
		grid: 'StackingGrid',
		geometry: t.Tuple[float, float, float, float],
		max_spacing: float = 100.,
		z: int = 0,
	):
		self._grid = grid
		self._geometry = geometry #type: t.Tuple[float, float, float, float]
		self._max_spacing = max_spacing #type: float
		self._cards = [] #type: t.List[PhysicalCard]
		self._z = z #type: int

		self._spacing_free_room = max(1, self.height - IMAGE_HEIGHT)

	@property
	def grid(self) -> 'StackingGrid':
		return self._grid

	@property
	def x(self) -> float:
		return self._geometry[0]

	@property
	def y(self) -> float:
		return self._geometry[1]

	@property
	def width(self) -> float:
		return self._geometry[2]

	@property
	def height(self) -> float:
		return self._geometry[3]

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
				QPoint(
					self._geometry[0],
					self._geometry[1] + i * spacing,
				)
			)

			self._cards[i].setZValue(self._z + i)
			self._grid.get_card_info(self._cards[i]).position = i

	def _add_card(self, card: PhysicalCard):
		info = self._grid.get_card_info(card)

		if info.card_stacker is not None:
			info.card_stacker.remove_card(card)

		info.card_stacker = self
		self._cards.append(card)

	def _remove_card(self, card: PhysicalCard):
		try:
			self._cards.remove(card)
			self._grid.get_card_info(card).card_stacker = None
		except KeyError:
			pass

	def _insert_card(self, index: int, card: PhysicalCard):
		info = self._grid.get_card_info(card)

		if info.card_stacker is not None:
			info.card_stacker.remove_card(card)

		info.card_stacker = self
		self._cards.insert(index, card)

	def remove_card(self, card: PhysicalCard):
		self._remove_card(card)
		self.stack()

	def add_card(self, card: PhysicalCard):
		self._add_card(card)
		self.stack()

	def insert_card(self, index: int, card: PhysicalCard):
		self._insert_card(index, card)
		self.stack()

	def remove_cards(self, cards: t.Iterable[PhysicalCard]):
		for card in cards:
			self._remove_card(card)
		self.stack()

	def add_cards(self, cards: t.Iterable[PhysicalCard]):
		for card in cards:
			self._add_card(card)
		self.stack()

	def insert_cards(self, indexes: t.Iterable[int], cards: t.Iterable[PhysicalCard]):
		for index, card in zip(indexes, cards):
			self._insert_card(index, card)
		self.stack()


class StackingAttach(AlignAttach):

	def __init__(
		self,
		stacker: CardStacker,
		index: int,
		cards: t.Tuple[PhysicalCard, ...],
	):
		super().__init__()
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

	def undo(self):
		self._stacker.remove_cards(self._cards)


class StackingDetach(AlignDetach):

	def __init__(
		self,
		grid: 'StackingGrid',
		cards: t.Iterable[PhysicalCard],
	):
		super().__init__()
		self._grid = grid
		self._cards = cards

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
		for stacker, infos in self._stackers.items():
			if stacker is not None:
				stacker.remove_cards(card for index, card in infos)

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


class StackingRemove(AlignRemove):

	def __init__(
		self,
		grid: 'StackingGrid',
		cards: t.Iterable[PhysicalCard],
	):
		super().__init__()
		self._grid = grid
		self._cards = cards

		self._stackers = {} #type: t.Dict[CardStacker, t.List[t.Tuple[int, PhysicalCard]]]

	def setup(self):
		for card in self._cards:
			info = self._grid.get_card_info(card)
			self._stacker_cards(info.card_stacker).append(
				(info.position, card)
			)

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

			for index, card in infos:
				self._grid.scene.removeItem(card)

	def undo(self):
		for stacker, infos in self._stackers.items():
			for index, card in infos:
				self._grid.scene.addItem(card)

			if stacker is None:
				continue

			_infos = sorted(infos, key = lambda info: info[0])

			adjusted_indexes = []
			passed = 0

			for index, card in _infos:
				# if card.scene() != stacker.grid.scene:
				# 	stacker.grid.scene.addItem(card)
				adjusted_indexes.append((index - passed, card))
				passed += 1

			stacker.insert_cards(*zip(*adjusted_indexes))


class _CardInfo(object):

	def __init__(self, stacker: CardStacker = None, position: int = None):
		self.card_stacker = stacker #type: t.Optional[CardStacker]
		self.position = position #type: t.Optional[int]

	def __repr__(self):
		return f'{self.__class__.__name__}({self.card_stacker, self.position})'


class StackingGrid(Aligner):

	def __init__(self, scene: QGraphicsScene, margin: float = .1, stacker_height: float = 2.5):
		super().__init__(scene)
		self._card_stackers = {} #type: t.Dict[t.Tuple[int, int], CardStacker]
		self._stacked_cards = {} #type: t.Dict[PhysicalCard, _CardInfo]

		self._card_stacker_width = int(IMAGE_WIDTH * (1 + margin)) #type: int
		self._card_stacker_height = int(IMAGE_HEIGHT * stacker_height) #type: int

	@property
	def scene(self) -> QGraphicsScene:
		return self._scene

	def get_card_info(self, card: PhysicalCard) -> _CardInfo:
		try:
			return self._stacked_cards[card]
		except KeyError:
			self._stacked_cards[card] = info = _CardInfo()
			return info

	def attach_cards(self, cards: t.Iterable[PhysicalCard], position: QPointF) -> StackingAttach:
		stacker = self._get_card_stacker(position.x(), position.y())
		return StackingAttach(
			stacker,
			stacker.position_index(position.y() - stacker.y),
			tuple(cards),
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

	def _get_card_stacker(self, x: int, y: int):
		_x, _y, = key = x // self._card_stacker_width, y // self._card_stacker_height
		try:
			return self._card_stackers[key]
		except KeyError:
			self._card_stackers[key] = _card_stacker = CardStacker(
				self,
				(
					_x * self._card_stacker_width,
				 	_y * self._card_stacker_height,
					self._card_stacker_width,
					self._card_stacker_height,
				)
			)
			return _card_stacker
