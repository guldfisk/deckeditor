from __future__ import annotations

import typing as t

from deckeditor.models.cubes.alignment.stackinggrid import CardStacker, StackingGrid, StackerMap
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.values import IMAGE_WIDTH, IMAGE_HEIGHT, STANDARD_IMAGE_MARGIN


class StaticCardStacker(CardStacker):

    def __init__(
        self,
        aligner: StackingGrid,
        index: t.Tuple[int, int],
        size: t.Tuple[float, float],
        max_spacing: float = 50.,
    ):
        super().__init__(aligner, index)
        self._max_spacing: float = max_spacing
        self._size = size
        self._spacing_free_room = max(1, self.height - IMAGE_HEIGHT)

    @property
    def width(self) -> float:
        return self._size[0]

    @property
    def height(self) -> float:
        return self._size[1]

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
    name = 'Static Stacking Grid'

    _card_stacker_width: float
    _card_stacker_height: float

    def __init__(
        self,
        scene: SelectionScene,
        *,
        margin: float = STANDARD_IMAGE_MARGIN,
        stacker_height: float = 2.,
        rows: int = 5,
        columns: int = 5,
        show_grid: bool = False,
    ):
        self._stacker_height = stacker_height

        super().__init__(
            scene,
            margin = margin,
            rows = rows,
            columns = columns,
            show_grid = show_grid,
        )

    def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
        pass

    def create_stacker_map(self, rows: int, columns: int) -> StackerMap:
        self._card_stacker_width = int(IMAGE_WIDTH + self._margin_pixel_size)
        self._card_stacker_height = int(IMAGE_HEIGHT * self._stacker_height)

        return StackerMap(
            aligner = self,
            row_amount = rows,
            column_amount = columns,
            default_column_width = self._card_stacker_width,
            default_row_height = self._card_stacker_height,
        )

    def create_stacker(self, x: int, y: int) -> CardStacker:
        return StaticCardStacker(
            self,
            (x, y),
            (
                self._card_stacker_width,
                self._card_stacker_height,
            )
        )
