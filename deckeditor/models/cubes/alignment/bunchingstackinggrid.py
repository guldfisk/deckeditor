from __future__ import annotations

import math
import typing as t

from PyQt5 import QtCore

from deckeditor.models.cubes.alignment.stackinggrid import CardStacker, StackingGrid, StackerMap
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT


class StaticCardStacker(CardStacker):

    def __init__(
        self,
        aligner: StackingGrid,
        index: t.Tuple[int, int],
        size: t.Tuple[float, float],
        max_spacing: float = 50.,
        width_margin: float = .2,
    ):
        super().__init__(aligner, index)
        self._max_spacing: float = max_spacing
        self._size = size
        self._vertical_spacing_free_room = max(1, self.height - IMAGE_HEIGHT)
        self._horizontal_spacing_free_room = max(1, self.width - (1 + width_margin) * IMAGE_WIDTH)

    @property
    def width(self) -> float:
        return self._size[0]

    @property
    def height(self) -> float:
        return self._size[1]

    @property
    def _spacing(self):
        return self._max_spacing

    def calculate_requested_size(self) -> t.Tuple[float, float]:
        return 0, 0

    def map_position_to_index(self, x: float, y: float) -> int:
        max_cards_per_column = int(self._vertical_spacing_free_room // self._max_spacing)
        columns = int(max(1, math.ceil(len(self._cards) / max_cards_per_column)))

        if x == 0:
            column = 0
        elif x >= self._horizontal_spacing_free_room:
            column = columns - 1
        else:
            column = int(x / self._horizontal_spacing_free_room * (columns - 1))

        if column == 0:
            v = int(
                min(
                    y // self._max_spacing,
                    max_cards_per_column - (columns * max_cards_per_column) + len(self._cards),
                )
            )
            return v
        else:
            return int(
                max_cards_per_column - (columns * max_cards_per_column) + len(self._cards)
                + (column - 1) * max_cards_per_column +
                min(y // self._max_spacing, max_cards_per_column)
            )

    def _stack(self):
        max_cards_per_column = int(self._vertical_spacing_free_room // self._max_spacing)
        columns = math.ceil(len(self._cards) / max_cards_per_column)
        x, y = self.x, self.y
        card_iter = self._cards.__iter__()

        for column in range(columns):
            if column == 0:
                _x = x
                _loop = int(max_cards_per_column - (columns * max_cards_per_column) + len(self._cards))
            else:
                _x = x + self._horizontal_spacing_free_room / (columns - 1) * column
                _loop = max_cards_per_column
            for i in range(_loop):
                next(card_iter).setPos(
                    _x,
                    y + i * self._max_spacing,
                )


class BunchingStackingGrid(StackingGrid):
    name = 'Bunch'

    _card_stacker_width: float
    _card_stacker_height: float

    def __init__(
        self,
        scene: SelectionScene,
        *,
        stacker_width: float = 1.6,
        margin: float = .1,
        stacker_height: float = 2.,
    ):
        self._stacker_height = stacker_height
        self._stacker_width = stacker_width

        super().__init__(
            scene,
            margin = margin,
        )

    def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
        pass

    def create_stacker_map(self) -> StackerMap:
        self._card_stacker_width = int(IMAGE_WIDTH * self._stacker_width + self._margin_pixel_size)
        self._card_stacker_height = int(IMAGE_HEIGHT * self._stacker_height)

        r: QtCore.QRectF = self._scene.sceneRect()

        return StackerMap(
            self,
            int(r.height() // self._card_stacker_height),
            int(r.width() // self._card_stacker_width),
            self._card_stacker_width,
            self._card_stacker_height,
        )

    def create_stacker(self, x: int, y: int) -> CardStacker:
        return StaticCardStacker(
            self,
            (x, y),
            (
                self._card_stacker_width,
                self._card_stacker_height,
            ),
        )
