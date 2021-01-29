from __future__ import annotations

import typing as t

from PyQt5 import QtCore

from deckeditor.models.cubes.alignment.stackinggrid import CardStacker, StackingGrid, StackerMap
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.values import IMAGE_HEIGHT, IMAGE_WIDTH, STANDARD_IMAGE_MARGIN


class DynamicCardStacker(CardStacker):

    def __init__(
        self,
        aligner: StackingGrid,
        index: t.Tuple[int, int],
        max_spacing: float = 50.,
    ):
        super().__init__(aligner, index)
        self._max_spacing: float = max_spacing

    def _get_spacing_free_room(self) -> float:
        return max(1., self.height - IMAGE_HEIGHT)

    @property
    def _spacing(self):
        return min(
            self._max_spacing,
            self._get_spacing_free_room() / max(len(self._cards), 1)
        )

    def calculate_requested_size(self) -> t.Tuple[float, float]:
        return IMAGE_WIDTH, IMAGE_HEIGHT + self._max_spacing * len(self._cards)

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


class DynamicStackingGrid(StackingGrid):
    name = 'Dynamic Stacking Grid'

    def __init__(
        self,
        scene: SelectionScene,
        *,
        margin: float = STANDARD_IMAGE_MARGIN,
        rows: int = 5,
        columns: int = 5,
        show_grid: bool = False,
    ):
        self._margin = margin
        self._stacker_width = IMAGE_WIDTH * (1 + self._margin)
        self._min_row_height = IMAGE_HEIGHT * (1 + self._margin)
        super().__init__(
            scene,
            margin = margin,
            rows = rows,
            columns = columns,
            show_grid = show_grid,
        )

    def create_stacker_map(self, rows: int, columns: int) -> StackerMap:
        return StackerMap(
            self,
            row_amount = rows,
            column_amount = columns,
            default_column_width = self._stacker_width,
            default_row_height = self._min_row_height,
        )

    def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
        for i in range(card_stacker.y_index, self._stacker_map.column_height):
            max_requested = max(
                [
                    stacker.requested_size[1]
                    for stacker in
                    self._stacker_map.row_at(i)
                ] + [self._min_row_height]
            )
            if max_requested != self._stacker_map.row_height_at(i):
                self._stacker_map.set_row_height_at(i, max_requested)

            for stacker in self.stacker_map.row_at(i):
                if stacker != card_stacker:
                    stacker.update(external = True)

    def create_stacker(self, x: int, y: int) -> CardStacker:
        return DynamicCardStacker(
            self,
            (x, y),
        )
