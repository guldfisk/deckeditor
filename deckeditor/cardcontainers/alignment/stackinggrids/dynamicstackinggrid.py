import typing as t

from itertools import chain

from PyQt5 import QtCore

from deckeditor.cardcontainers.alignment.aligner import CardScene
from deckeditor.undo.command import UndoStack

from mtgimg.load import IMAGE_WIDTH, IMAGE_HEIGHT

from deckeditor.cardcontainers.alignment.stackinggrids.stackinggrid import StackingGrid, CardStacker



class DynamicCardStacker(CardStacker):

	def __init__(
		self,
		grid: 'DynamicStackingGrid',
		index: t.Tuple[int, int],
		geometry: t.Tuple[float, float, float, float],
		card_offset: float = .2,
		margin: float = .1,
	):
		super().__init__(grid, index, geometry)
		self._real_offset = IMAGE_HEIGHT * card_offset
		self._real_width_margin = IMAGE_WIDTH * margin
		self._real_height_margin = IMAGE_HEIGHT * margin

	def map_position_to_index(self, x: float, y: float) -> int:
		return y // self._real_offset

	def _requested_space(self) -> t.Tuple[float, float]:
		return (
			self.width,
			(len(self._cards) - 1) * self._real_offset + IMAGE_HEIGHT + self._real_height_margin
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

		self._stacker_width = IMAGE_WIDTH + IMAGE_WIDTH * margin
		self._minimum_stacker_height = IMAGE_HEIGHT + IMAGE_HEIGHT * margin

		self.stacker_map.add_row(self._minimum_stacker_height)
		self.stacker_map.add_column(self._stacker_width)

	def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
		if y > self.stacker_map.row_height_at(card_stacker.y_index):
			self.stacker_map.set_row_height(card_stacker.y_index, y)

			for _x in range(self.stacker_map.row_length):
				stacker = self.stacker_map.get_stacker(_x, card_stacker.y_index)
				stacker.height = y
				if not stacker == card_stacker:
					stacker.update()

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
		return amount * IMAGE_HEIGHT <= free_space

	def _can_create_columns(self, amount: int) -> bool:
		print('can create columns', amount)
		free_space = self.scene.width() - self.stacker_map.width
		return amount * IMAGE_WIDTH <= free_space

	def _create_rows(self, amount: int) -> None:
		for i in range(amount):
			self.stacker_map.add_row(IMAGE_HEIGHT)

	def _create_columns(self, amount: int) -> None:
		for i in range(amount):
			self.stacker_map.add_column(IMAGE_WIDTH)