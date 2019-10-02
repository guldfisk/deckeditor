import typing as t

from PyQt5 import QtCore

from deckeditor.garbage.cardcontainers.alignment import CardScene
from deckeditor.garbage.undo import UndoStack

from mtgimg.interface import IMAGE_SIZE_MAP, SizeSlug

from deckeditor.garbage.cardcontainers.alignment import StackingGrid, CardStacker, StackerMap


IMAGE_WIDTH, IMAGE_HEIGHT = IMAGE_SIZE_MAP[frozenset((SizeSlug.ORIGINAL, False))]


class StaticCardStacker(CardStacker):

	def __init__(
		self,
		aligner: 'StackingGrid',
		index: t.Tuple[int, int],
		# geometry: t.Tuple[float, float, float, float],
		max_spacing: float = 100,
	):
		super().__init__(aligner, index)
		self._max_spacing = max_spacing #type: float
		self._spacing_free_room = max(1, self.height - IMAGE_HEIGHT)

	@property
	def _spacing(self):
		return min(
			self._max_spacing,
			self._spacing_free_room / max(len(self._cards), 1)
		)

	def calculate_requested_size(self) -> t.Tuple[float, float]:
		return 0, 0

	def map_position_to_index(self, x: float, y: float) -> int:
		return int(y // self._spacing)

	def _stack(self):
		spacing = self._spacing

		x, y = self.x, self.y

		for i in range(len(self._cards)):
			self._cards[i].setPos(
				x,
				y + i * spacing,
			)


class StaticStackingGrid(StackingGrid):

	def __init__(self, scene: CardScene, undo_stack: UndoStack, margin: float = .2, stacker_height: float = 2.):
		self._stacker_height = stacker_height

		super().__init__(
			scene,
			undo_stack,
			margin,
		)

		# self._card_stacker_width = int(IMAGE_WIDTH + self._margin_pixel_size)
		# self._card_stacker_height = int(IMAGE_HEIGHT * stacker_height)

		# for _ in range(int( r.width() // self._card_stacker_width )):
		# 	self._stacker_map.add_column(self._card_stacker_width)
		#
		# for _ in range(int( r.height() // self._card_stacker_height )):
		# 	self._stacker_map.add_row(self._card_stacker_height)

	def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
		pass

	def create_stacker_map(self) -> StackerMap:
		_card_stacker_width = int(IMAGE_WIDTH + self._margin_pixel_size)
		_card_stacker_height = int(IMAGE_HEIGHT * self._stacker_height)

		r = self._scene.sceneRect()  # type: QtCore.QRectF

		return StackerMap(
			self,
			int(r.height() // _card_stacker_width),
			int(r.height() // _card_stacker_height),
			_card_stacker_width,
			_card_stacker_height,
		)

	def create_stacker(self, x: int, y: int) -> CardStacker:
		return StaticCardStacker(
			self,
			(x, y),
		)

	# def _can_create_rows(self, amount: int) -> bool:
	# 	return False
	#
	# def _can_create_columns(self, amount: int) -> bool:
	# 	return False
	#
	# def _create_rows(self, amount: int) -> None:
	# 	pass
	#
	# def _create_columns(self, amount: int) -> None:
	# 	pass