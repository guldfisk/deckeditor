from __future__ import annotations

import typing as t

from PyQt5 import QtCore

from deckeditor.models.cubes.alignment.stackinggrid import CardStacker, StackingGrid, StackerMap
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.values import IMAGE_HEIGHT, IMAGE_WIDTH


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

    def __init__(
        self,
        scene: SelectionScene,
        *,
        margin: float = .1,
    ):
        self._margin = margin
        self._stacker_width = (1 + margin) * IMAGE_WIDTH
        self._min_row_height = IMAGE_HEIGHT * (1 + self._margin)
        super().__init__(
            scene,
            margin = margin,
        )

    def create_stacker_map(self) -> StackerMap:
        r: QtCore.QRectF = self._scene.sceneRect()

        return StackerMap(
            self,
            row_amount = 2,
            column_amount = int(r.width() // self._stacker_width),
            default_column_width = self._stacker_width,
            default_row_height = self._min_row_height,
        )

    def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
        if not card_stacker.y_index == 0:
            return

        max_requested = max(stacker.requested_size[1] for stacker in self._stacker_map.row_at(0))

        if max_requested != self._stacker_map.row_height_at(0):
            remaining = self._scene.height() - max_requested
            if remaining < self._min_row_height:
                remaining = self._min_row_height
                max_requested = self._scene.height() - self._min_row_height

            self._stacker_map.set_row_height_at(0, max_requested)
            self._stacker_map.set_row_height_at(1, remaining)

            for stacker in self._stacker_map.stackers:
                if stacker != card_stacker:
                    stacker.update(external = True)

    def create_stacker(self, x: int, y: int) -> CardStacker:
        return DynamicCardStacker(
            self,
            (x, y),
        )
