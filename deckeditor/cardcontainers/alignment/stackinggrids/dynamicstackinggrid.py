import typing as t

from deckeditor.cardcontainers.alignment.aligner import CardScene
from deckeditor.cardcontainers.physicalcard import PhysicalCard
from deckeditor.undo.command import UndoStack

from mtgimg.load import IMAGE_WIDTH, IMAGE_HEIGHT

from deckeditor.cardcontainers.alignment.stackinggrids.stackinggrid import StackingGrid, CardStacker


class DynamicCardStacker(CardStacker):

	def __init__(
		self,
		aligner: 'DynamicStackingGrid',
		index: t.Tuple[int, int],
		geometry: t.Tuple[float, float, float, float],
		card_offset: float = .2,
		margin: float = .1,
	):
		super().__init__(aligner, index, geometry)
		self._real_offset = IMAGE_HEIGHT * card_offset
		self._real_width_margin = IMAGE_WIDTH * margin
		# self._real_height_margin = IMAGE_HEIGHT * margin
		self._real_height_margin = 0

	def remove_cards(self, cards: t.Iterable[PhysicalCard]):
		super().remove_cards(cards)

		if self.y_index != 0 and not self._cards and not any(
			self._aligner.stacker_map.get_stacker(x, self.y_index).cards
			for x in
			range(self._aligner.stacker_map.row_length)
		):
			print('remove row', self.y_index)
			print(
				self._aligner.stacker_map
			)
			self._aligner.stacker_map.remove_row(self.y_index)
			print(
				self._aligner.stacker_map
			)

	def map_position_to_index(self, x: float, y: float) -> int:
		return y // self._real_offset

	def requested_size(self) -> t.Tuple[float, float]:
		return (
			self.width,
			(
				0
				if not self._cards else
				( len(self._cards) - 1 ) * self._real_offset + IMAGE_HEIGHT + self._real_height_margin
			)
		)

	def _stack(self):
		for i in range(len(self._cards)):
			self._cards[i].setPos(
				self._geometry[0],
				self._geometry[1] + i * self._real_offset,
			)


class DynamicStackingGrid(StackingGrid):

	def __init__(self, scene: CardScene, undo_stack: UndoStack, margin: float = .2):
		super().__init__(scene, undo_stack, margin)

		margin = 0.

		self._stacker_width = IMAGE_WIDTH + IMAGE_WIDTH * margin
		self._minimum_stacker_height = IMAGE_HEIGHT + IMAGE_HEIGHT * margin

		self.stacker_map.add_row()

		for _ in range(int(self._scene.sceneRect().width() // self._stacker_width)):
			self._stacker_map.add_column()

		print('stacker', self._stacker_map)

	def request_space(self, card_stacker: CardStacker, width: int, height: int) -> None:
		print('request space', height)

		old_height = card_stacker.height
		card_stacker.height = height

		row_heights_at_index = sorted(
			list(
				self.stacker_map.row_heights_at(
					card_stacker.y_index
				)
			)
		)

		if (
			height > row_heights_at_index[-1]
			or (
				old_height >= row_heights_at_index[-1]
				and len(row_heights_at_index) > 1
				and row_heights_at_index[-1] > row_heights_at_index[-2]
			)
		):

			# for _x in range(self.stacker_map.row_length):
			# 	stacker = self.stacker_map.get_stacker(_x, card_stacker.y_index)
			# 	stacker.height = height
			# 	if not stacker == card_stacker:
			# 		stacker.update()

			for _x in range(self.stacker_map.row_length):
				for _y in range(card_stacker.y_index + 1, self.stacker_map.column_height):
					stacker = self.stacker_map.get_stacker(_x, _y)
					stacker.y = self.stacker_map.height_at(_y)

	def create_stacker(self, x: int, y: int) -> CardStacker:
		return DynamicCardStacker(
			self,
			(x, y),
			(
				x * self._stacker_width,
				self.stacker_map.height_at(y),
				self._stacker_width,
				self._minimum_stacker_height,
			)
		)

	def _can_create_rows(self, amount: int) -> bool:
		print('can create rows', amount)
		free_space = self.scene.height() - self.stacker_map.height
		can = amount * IMAGE_HEIGHT <= free_space
		print(can, IMAGE_HEIGHT, free_space)
		return True

	def _can_create_columns(self, amount: int) -> bool:
		return amount <= 0
		# print('can create columns', amount)
		# free_space = self.scene.width() - self.stacker_map.width
		# return amount * IMAGE_WIDTH <= free_space

	def _create_rows(self, amount: int) -> None:
		print('create rows', amount)
		for i in range(amount):
			self.stacker_map.add_row()

	def _create_columns(self, amount: int) -> None:
		# print('create columns', amount)
		# for i in range(amount):
		# 	self.stacker_map.add_column(IMAGE_WIDTH)
		raise NotImplementedError()