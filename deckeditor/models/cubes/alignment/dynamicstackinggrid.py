from __future__ import annotations

import typing as t

from PyQt5 import QtCore

from deckeditor import values
from deckeditor.models.cubes.alignment.stackinggrid import CardStacker, StackingGrid, StackerMap
from deckeditor.models.cubes.physicalcard import PhysicalCard
from deckeditor.models.cubes.selection import SelectionScene
from deckeditor.values import IMAGE_HEIGHT, IMAGE_WIDTH


class DynamicCardStacker(CardStacker):


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

    def _get_spacing_free_room(self) -> float:
        return max(1., self.height - IMAGE_HEIGHT)

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

    # def __init__(
    #     self,
    #     aligner: DynamicStackingGrid,
    #     index: t.Tuple[int, int],
    #     width: float,
    #     max_spacing: float = 50.,
    #     width_margin: float = .2,
    # ):
    #     super().__init__(aligner, index)
    #     self._real_offset = values.IMAGE_HEIGHT * card_offset
    #     self._real_width_margin = values.IMAGE_WIDTH * margin
    #     # self._real_height_margin = IMAGE_HEIGHT * margin
    #     self._real_height_margin = 0
    #
    # def remove_cards(self, cards: t.Iterable[PhysicalCard]):
    #     super().remove_cards(cards)
    #
    #     if self.y_index != 0 and not self._cards and not any(
    #         self._aligner.stacker_map.get_stacker(x, self.y_index).cards
    #         for x in
    #         range(self._aligner.stacker_map.row_length)
    #     ):
    #         self._aligner.stacker_map.remove_row(self.y_index)
    #
    # def map_position_to_index(self, x: float, y: float) -> int:
    #     return y // self._real_offset
    #
    # def requested_size(self) -> t.Tuple[float, float]:
    #     return (
    #         self.width,
    #         (
    #             0
    #             if not self._cards else
    #             ( len(self._cards) - 1 ) * self._real_offset + values.IMAGE_HEIGHT + self._real_height_margin
    #         )
    #     )
    #
    # def _stack(self):
    #     x, y = self.x, self.y
    #
    #     for i in range(len(self._cards)):
    #         self._cards[i].setPos(
    #             x,
    #             y + i * self._real_offset,
    #         )


class DynamicStackingGrid(StackingGrid):

    def __init__(
        self,
        scene: SelectionScene,
        *,
        stacker_width: float = 1.6,
        margin: float = .1,
    ):
        self._margin = margin
        self._stacker_width = stacker_width

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
            default_row_height = IMAGE_HEIGHT * (1 + self._margin),
        )

    def request_space(self, card_stacker: CardStacker, x: int, y: int) -> None:
        if not y == 0:
            return


    def create_stacker(self, x: int, y: int) -> CardStacker:
        pass

# def __init__(self, scene: SelectionScene, *, margin: float = .2):
    #     super().__init__(scene, margin = margin)
    #
    #     margin = 0.
    #
    #     self._stacker_width = values.IMAGE_WIDTH + values.IMAGE_WIDTH * margin
    #     self._minimum_stacker_height = values.IMAGE_HEIGHT + values.IMAGE_HEIGHT * margin
    #
    #     self.stacker_map.add_row()
    #
    #     for _ in range(int(self._scene.sceneRect().width() // self._stacker_width)):
    #         self._stacker_map.add_column()
    #
    # def request_space(self, card_stacker: CardStacker, width: int, height: int) -> None:
    #     print('request space', height)
    #
    #     old_height = card_stacker.height
    #     card_stacker.height = height
    #
    #     row_heights_at_index = sorted(
    #         list(
    #             self.stacker_map.row_heights_at(
    #                 card_stacker.y_index
    #             )
    #         )
    #     )
    #
    #     if (
    #         height > row_heights_at_index[-1]
    #         or (
    #             old_height >= row_heights_at_index[-1] > row_heights_at_index[-2]
    #             and len(row_heights_at_index) > 1
    #         )
    #     ):
    #
    #         for _x in range(self.stacker_map.row_length):
    #             for _y in range(card_stacker.y_index + 1, self.stacker_map.column_height):
    #                 stacker = self.stacker_map.get_stacker(_x, _y)
    #                 stacker.y = self.stacker_map.height_at(_y)
    #
    # def create_stacker(self, x: int, y: int) -> CardStacker:
    #     return DynamicCardStacker(
    #         self,
    #         (x, y),
    #         (
    #             x * self._stacker_width,
    #             self.stacker_map.height_at(y),
    #             self._stacker_width,
    #             self._minimum_stacker_height,
    #         )
    #     )
    #
    # def _can_create_rows(self, amount: int) -> bool:
    #     print('can create rows', amount)
    #     free_space = self.scene.height() - self.stacker_map.height
    #     can = amount * IMAGE_HEIGHT <= free_space
    #     print(can, IMAGE_HEIGHT, free_space)
    #     return True
    #
    # def _can_create_columns(self, amount: int) -> bool:
    #     return amount <= 0
    #
    # def _create_rows(self, amount: int) -> None:
    #     print('create rows', amount)
    #     for i in range(amount):
    #         self.stacker_map.add_row()
    #
    # def _create_columns(self, amount: int) -> None:
    #     # print('create columns', amount)
    #     # for i in range(amount):
    #     # 	self.stacker_map.add_column(IMAGE_WIDTH)
    #     raise NotImplementedError()